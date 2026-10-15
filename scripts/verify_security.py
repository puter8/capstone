# -*- coding: utf-8 -*-
"""
운영 보안 검증 — 19종 (우회 시나리오 6종 포함)
==============================================

실제로 공격하듯 요청을 쏘고 전부 막히는지 확인한다. 단위 테스트는 우리가 짠
mock 을 상대로 돌지만, 이 스크립트는 배포된 서버와 실제 Supabase 를 상대로
돌기 때문에 RLS·권한·원자성처럼 DB 에서만 드러나는 구멍을 잡는다.

검증 대상:
  A. 우회 시나리오 6종 — 정상 경로를 피해 한도·확인·소유권을 깨려는 시도
  B. 소유권·인증 8종 — 타인 데이터 접근과 미인증 요청
  C. RLS 4종       — 백엔드를 건너뛰고 anon key 로 테이블 직접 접근
  D. 노출 1종      — 디버그 라우트가 운영에 없는지

실행:
  py -3 scripts/verify_security.py                 # 운영 서버
  py -3 scripts/verify_security.py --base <url>    # 다른 환경

필요한 환경변수 (backend/.env, frontend/.env.local 에서 읽는다):
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY   테스트 계정 생성·정리용
  NEXT_PUBLIC_SUPABASE_ANON_KEY             RLS 검증용 (클라이언트가 쥐는 키)

테스트 계정 2개를 만들고 끝나면 지운다. 실패해도 지우도록 finally 로 묶었다.
"""
from __future__ import annotations

import argparse
import base64
import io
import os
import sys
import uuid
import wave

import httpx
from dotenv import load_dotenv

PROD = "https://web-production-8dee5.up.railway.app"
FREE_DAILY_TURNS = int(os.getenv("FREE_DAILY_TURNS", "20"))  # 서버 기본값과 같게


class Report:
    """검증 결과 집계. 통과만 세지 않고 실패한 항목을 그대로 보여준다."""

    def __init__(self) -> None:
        self.rows: list = []

    def check(self, group: str, name: str, passed: bool, detail: str = "") -> None:
        self.rows.append((group, name, bool(passed), detail))
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {name}" + ("" if passed else f"\n         -> {detail}"))

    def summary(self) -> int:
        groups: dict = {}
        for group, _name, passed, _detail in self.rows:
            ok, total = groups.get(group, (0, 0))
            groups[group] = (ok + int(passed), total + 1)
        print("\n" + "=" * 62)
        for group, (ok, total) in groups.items():
            print(f"  {group:28s} {ok}/{total}")
        total_ok = sum(1 for *_x, passed, _d in ((r[0], r[1], r[2], r[3]) for r in self.rows) if passed)
        print(f"  {'합계':28s} {total_ok}/{len(self.rows)}")
        failed = [r for r in self.rows if not r[2]]
        if failed:
            print("\n  실패 항목:")
            for group, name, _p, detail in failed:
                print(f"    - [{group}] {name}: {detail}")
        return 0 if not failed else 1


def silent_wav(seconds: float = 1.0) -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16000)
        target.writeframes(b"\0\0" * int(16000 * seconds))
    return stream.getvalue()


class Account:
    def __init__(self, sb: str, service_key: str, tag: str) -> None:
        self.sb, self.key = sb, service_key
        self.email = f"sec-{tag}-{uuid.uuid4().hex[:8]}@example.com"
        headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}",
                   "Content-Type": "application/json"}
        self.srv = headers
        created = httpx.post(f"{sb}/auth/v1/admin/users", headers=headers,
                             json={"email": self.email, "password": "x12345678", "email_confirm": True},
                             timeout=30).json()
        self.id = created["id"]
        token = httpx.post(f"{sb}/auth/v1/token?grant_type=password",
                           headers={"apikey": service_key, "Content-Type": "application/json"},
                           json={"email": self.email, "password": "x12345678"}, timeout=30).json()
        self.auth = {"Authorization": f"Bearer {token['access_token']}"}

    def idem(self) -> dict:
        return {**self.auth, "Idempotency-Key": str(uuid.uuid4())}

    def destroy(self) -> None:
        for table in ("usage_daily", "activity_events", "streak_days",
                      "daily_task_snapshots", "sessions", "profiles"):
            column = "id" if table == "profiles" else "user_id"
            httpx.request("DELETE", f"{self.sb}/rest/v1/{table}?{column}=eq.{self.id}",
                          headers={**self.srv, "Prefer": "return=minimal"}, timeout=30)
        httpx.delete(f"{self.sb}/auth/v1/admin/users/{self.id}", headers=self.srv, timeout=30)


def run(base: str, sb_url: str, service_key: str, anon_key: str) -> int:
    report = Report()
    victim = attacker = None
    try:
        victim, attacker = Account(sb_url, service_key, "v"), Account(sb_url, service_key, "a")
        api = httpx.Client(base_url=base, timeout=120)
        srv = victim.srv

        api.post("/api/onboarding", headers=victim.idem(),
                 json={"display_name": "victim", "english_level": "A2"})
        api.post("/api/onboarding", headers=attacker.idem(),
                 json={"display_name": "attacker", "english_level": "A2"})
        conversation = api.post("/api/conversations", headers=victim.idem(),
                                json={}).json()["conversation"]["id"]

        def usage_of(account: Account) -> int:
            rows = httpx.get(f"{sb_url}/rest/v1/usage_daily?user_id=eq.{account.id}&select=used_turns",
                             headers=srv, timeout=30).json()
            return sum(row["used_turns"] for row in rows)

        # ── A. 우회 시나리오 6종 ──────────────────────────────────────────
        print("\nA. 우회 시나리오 6종")

        # 1) 대화 기록을 지워 무료 한도를 되돌리려는 시도.
        #    사용량이 같이 지워지면 하루에 몇 번이고 한도를 초기화할 수 있다.
        httpx.post(f"{sb_url}/rest/v1/usage_daily", headers={**srv, "Prefer": "resolution=merge-duplicates"},
                   json={"user_id": victim.id, "date_kst": "2026-01-01", "used_turns": 7}, timeout=30)
        before = usage_of(victim)
        api.delete("/api/conversations", headers=victim.auth)
        report.check("A 우회", "기록 삭제로 무료 한도 초기화 불가",
                     usage_of(victim) == before > 0, f"{before} -> {usage_of(victim)}")

        # 2) 오늘 사용량을 한도까지 채운 뒤 턴을 밀어 넣는 시도. 차감이 원자적이지
        #    않거나 검사가 AI 호출 뒤에 있으면, 한도를 넘겨 외부 API 비용이 샌다.
        #    (쿼터 검사는 STT 보다 앞이라 무음 오디오여도 429 가 먼저 나와야 한다.)
        httpx.request("DELETE", f"{sb_url}/rest/v1/usage_daily?user_id=eq.{victim.id}",
                      headers={**srv, "Prefer": "return=minimal"}, timeout=30)
        httpx.post(f"{sb_url}/rest/v1/usage_daily", headers={**srv, "Prefer": "resolution=merge-duplicates"},
                   json={"user_id": victim.id, "date_kst": _kst_today(), "used_turns": FREE_DAILY_TURNS},
                   timeout=30)
        fresh = api.post("/api/conversations", headers=victim.idem(), json={}).json()["conversation"]["id"]
        blocked = api.post(f"/api/conversations/{fresh}/turns", headers=victim.idem(),
                           files={"audio": ("a.wav", silent_wav(), "audio/wav")})
        report.check("A 우회", "일일 한도 소진 후 턴 차단(429)",
                     blocked.status_code == 429, f"{blocked.status_code} {blocked.text[:90]}")
        httpx.request("DELETE", f"{sb_url}/rest/v1/usage_daily?user_id=eq.{victim.id}",
                      headers={**srv, "Prefer": "return=minimal"}, timeout=30)

        # 3) 같은 멱등 키를 다시 써서 한 번 말한 것을 두 번 차감·두 번 저장시키려는 시도.
        key = str(uuid.uuid4())
        headers = {**victim.auth, "Idempotency-Key": key}
        first = api.post(f"/api/conversations/{fresh}/turns", headers=headers,
                         files={"audio": ("a.wav", silent_wav(1.5), "audio/wav")})
        used_after_first = usage_of(victim)
        second = api.post(f"/api/conversations/{fresh}/turns", headers=headers,
                          files={"audio": ("a.wav", silent_wav(1.5), "audio/wav")})
        report.check("A 우회", "멱등 키 재사용으로 중복 차감 불가",
                     usage_of(victim) == used_after_first,
                     f"{used_after_first} -> {usage_of(victim)} ({first.status_code}/{second.status_code})")

        # 4) 끝난 대화에 발화를 뒤늦게 끼워 넣으려는 시도.
        api.post(f"/api/conversations/{fresh}/complete", headers=victim.idem())
        late = api.post(f"/api/conversations/{fresh}/turns", headers=victim.idem(),
                        files={"audio": ("a.wav", silent_wav(), "audio/wav")})
        report.check("A 우회", "종료된 대화에 발화 주입 불가(409)",
                     late.status_code == 409, f"{late.status_code} {late.text[:90]}")

        # 5) 확인 문구 없이 계정을 지우려는 시도. 오타·실수로 지워지면 복구할 수 없다.
        wrong = api.request("DELETE", "/api/account", headers=victim.auth, json={"confirmation": "yes"})
        report.check("A 우회", "확인 문구 없이 계정 삭제 불가(422)",
                     wrong.status_code == 422, f"{wrong.status_code} {wrong.text[:90]}")

        # 6) 삭제 요청 본문에 타인 id 를 끼워 삭제 대상을 바꾸려는 시도.
        injected = api.request("DELETE", "/api/account", headers=victim.auth,
                               json={"confirmation": "회원탈퇴", "user_id": attacker.id})
        still_alive = httpx.get(f"{sb_url}/auth/v1/admin/users/{attacker.id}", headers=srv, timeout=30)
        report.check("A 우회", "본문에 타인 id 를 넣어 삭제 대상 변경 불가",
                     injected.status_code == 422 and still_alive.status_code == 200,
                     f"{injected.status_code} / 피해자 생존={still_alive.status_code}")

        # ── B. 소유권·인증 8종 ───────────────────────────────────────────
        print("\nB. 소유권·인증 8종")
        other = attacker.auth
        # 존재를 숨기려고 403 이 아니라 404 로 답해야 한다. 403 이면 id 유효성이 샌다.
        for name, response in (
            ("타인 대화 상세 조회 차단", api.get(f"/api/conversations/{conversation}", headers=other)),
            ("타인 대화에 턴 추가 차단", api.post(f"/api/conversations/{conversation}/turns",
                                       headers={**other, "Idempotency-Key": str(uuid.uuid4())},
                                       files={"audio": ("a.wav", silent_wav(), "audio/wav")})),
            ("타인 대화 오프너 요청 차단", api.post(f"/api/conversations/{conversation}/opener",
                                        headers={**other, "Idempotency-Key": str(uuid.uuid4())})),
            ("타인 대화 종료 차단", api.post(f"/api/conversations/{conversation}/complete",
                                    headers={**other, "Idempotency-Key": str(uuid.uuid4())})),
        ):
            report.check("B 소유권", name + "(404)", response.status_code == 404,
                         f"{response.status_code} {response.text[:80]}")

        for name, response in (
            ("미인증 대화 목록 조회", api.get("/api/conversations")),
            ("미인증 프로필 조회", api.get("/api/profile")),
            ("미인증 기록 삭제", api.delete("/api/conversations")),
            ("위조 토큰 거부", api.get("/api/profile", headers={"Authorization": "Bearer forged.token.value"})),
        ):
            report.check("B 인증", name + "(401)", response.status_code == 401,
                         f"{response.status_code} {response.text[:80]}")

        # ── C. RLS 4종 ───────────────────────────────────────────────────
        # 백엔드를 통하지 않고, 브라우저가 쥐고 있는 anon key 로 테이블을 직접 친다.
        print("\nC. RLS 4종 (백엔드 우회, anon key 직접 접근)")
        anon = {"apikey": anon_key, "Authorization": f"Bearer {anon_key}"}
        for table in ("messages", "sessions", "usage_daily", "profiles"):
            response = httpx.get(f"{sb_url}/rest/v1/{table}?select=*&limit=5", headers=anon, timeout=30)
            leaked = response.status_code == 200 and response.json()
            report.check("C RLS", f"anon key 로 {table} 직접 조회 차단",
                         not leaked, f"{response.status_code} rows={len(response.json()) if response.status_code == 200 else '-'}")

        # ── D. 노출 1종 ──────────────────────────────────────────────────
        print("\nD. 디버그 노출 1종")
        debug = api.get("/api/debug-keys")
        spec = api.get("/openapi.json")
        hidden = debug.status_code == 404 and "/api/debug-keys" not in spec.json().get("paths", {})
        report.check("D 노출", "디버그 라우트가 운영에 없음", hidden, f"{debug.status_code}")

        api.close()
    finally:
        for account in (victim, attacker):
            if account is not None:
                account.destroy()
        print("\n테스트 계정 정리 완료")
    return report.summary()


def _kst_today() -> str:
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone(timedelta(hours=9))).date().isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Pally 운영 보안 검증 19종")
    parser.add_argument("--base", default=PROD, help="검증할 백엔드 주소")
    args = parser.parse_args()

    load_dotenv("backend/.env")
    load_dotenv("frontend/.env.local")
    sb_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    missing = [name for name, value in (("SUPABASE_URL", sb_url),
                                        ("SUPABASE_SERVICE_ROLE_KEY", service_key),
                                        ("NEXT_PUBLIC_SUPABASE_ANON_KEY", anon_key)) if not value]
    if missing:
        print(f"환경변수 없음: {', '.join(missing)}")
        return 2

    print(f"대상: {args.base}")
    return run(args.base, sb_url, service_key, anon_key)


if __name__ == "__main__":
    sys.exit(main())
