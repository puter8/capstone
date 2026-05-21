# -*- coding: utf-8 -*-
"""
파트 C API 테스트 스크립트
실행: python test_api.py
서버가 localhost:8000에서 실행 중이어야 합니다.
"""
import base64
import json
import sys
import time

import httpx

BASE = "http://localhost:8000"


def ok(label):
    print(f"  ✓ {label}")


def fail(label, detail=""):
    print(f"  ✗ {label}", f"  → {detail}" if detail else "")


def section(title):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")


# ── 1. Health ─────────────────────────────────────────


def test_health():
    section("1. GET /api/health")
    r = httpx.get(f"{BASE}/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    ok(f"status: {r.json()}")


# ── 2. Feedback ───────────────────────────────────────


CASES = [
    {
        "label": "캐주얼 슬랭",
        "utterance": "yo what's up lol, u wanna hang or nah?",
    },
    {
        "label": "격식체",
        "utterance": "I would like to formally inquire about the implications of this matter.",
    },
    {
        "label": "유머/밈",
        "utterance": "omg have you seen that new meme?? it literally made me cry laughing 😂",
    },
    {
        "label": "EMA 누적 테스트 (2번째 발화)",
        "utterance": "that's so funny lol",
        "current_axes": {"Formality": 50, "Energy": 50, "Intimacy": 40, "Humor": 30, "Curiosity": 25},
    },
]


def test_feedback():
    section("2. POST /api/feedback")
    for case in CASES:
        payload = {"utterance": case["utterance"]}
        if "current_axes" in case:
            payload["current_axes"] = case["current_axes"]

        time.sleep(2)  # Gemini 무료 티어 RPM 제한 방지
        r = httpx.post(f"{BASE}/api/feedback", json=payload, timeout=30)

        if r.status_code != 200:
            fail(case["label"], f"HTTP {r.status_code}: {r.text[:100]}")
            continue

        data = r.json()
        axes = data["axes"]
        char = data["character"]
        fb = data["feedback"]
        has_tts = data["tts_audio"] is not None

        print(f"\n  [{case['label']}]")
        print(f"  발화: \"{case['utterance'][:50]}\"")
        print(f"  5축: F={axes['Formality']} E={axes['Energy']} I={axes['Intimacy']} H={axes['Humor']} C={axes['Curiosity']}")
        print(f"  캐릭터: tone={char['tone_casual']} energy={char['energy_level']} humor={char['humor_level']}")
        print(f"  피드백 correction: {fb.get('correction', '')[:80]}")
        print(f"  피드백 practice  : {fb.get('practice_prompt', '')[:80]}")
        is_fallback = fb.get("correction", "").startswith("Great attempt!")
        print(f"  Gemini: {'⚠ fallback (서버 로그 확인)' if is_fallback else '✓ 실제 응답'}")
        print(f"  TTS audio: {'있음 ✓' if has_tts else '없음'}")

        # TTS 오디오 저장 (첫 번째 케이스만)
        if has_tts and case["label"] == "캐주얼 슬랭":
            audio_bytes = base64.b64decode(data["tts_audio"])
            with open("test_tts_output.mp3", "wb") as f:
                f.write(audio_bytes)
            ok("TTS MP3 저장됨: test_tts_output.mp3")


# ── 3. TTS ────────────────────────────────────────────


def test_tts():
    section("3. POST /api/tts")
    r = httpx.post(
        f"{BASE}/api/tts",
        json={"text": "Hello! Your English sounds great today.", "voice": "en-US-Journey-F"},
        timeout=15,
    )
    if r.status_code != 200:
        fail("TTS 호출", f"HTTP {r.status_code}")
        print(f"  전체 에러:\n  {r.text}")
        return

    data = r.json()
    audio_bytes = base64.b64decode(data["audio_b64"])
    ok(f"voice: {data['voice']}, MP3 크기: {len(audio_bytes):,} bytes")


# ── 4. STT (오디오 파일 필요) ─────────────────────────


def test_stt():
    section("4. POST /api/stt")
    print("  → 실제 오디오 파일이 필요합니다.")
    print("  → 파트 A에서 MediaRecorder webm 파일을 전송해서 테스트하세요.")
    print("  → 또는 아래 curl 명령으로 테스트:")
    print('     curl -X POST http://localhost:8000/api/stt -F "audio=@your_file.webm"')


# ── Main ──────────────────────────────────────────────


if __name__ == "__main__":
    print("=" * 50)
    print("  Pally Backend API 테스트")
    print("=" * 50)

    try:
        httpx.get(f"{BASE}/api/health", timeout=3)
    except Exception:
        print("\n서버가 실행되지 않았습니다.")
        print("먼저 실행: python -m uvicorn main:app --reload --port 8000")
        sys.exit(1)

    try:
        test_health()
        test_feedback()
        test_tts()
        test_stt()
    except AssertionError as e:
        fail("테스트 실패", str(e))
    except Exception as e:
        fail("예상치 못한 오류", str(e))

    print(f"\n{'='*50}")
    print("  테스트 완료")
    print(f"{'='*50}\n")
