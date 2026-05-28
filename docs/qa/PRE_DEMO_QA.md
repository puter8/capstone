# Pre-Demo QA Checklist — 2026-06-07

> Owner: 최윤서 (PM·QA) · Last updated: 2026-05-28 (D-10)
> Source rules: `CLAUDE.md` §5 (E2E 검증), §6 Top 5, §7 (Supabase RLS), §8 (배포 확인)
> Companion docs: `.planning/STATE.md`, `docs/mvp/2026-05-midterm-qa.md`, `docs/final/DEMO_SCRIPT.md`

데모 전 PM이 직접 돌려야 하는 QA 패스. 한 항목이라도 ✗면 데모 강행 금지. 데모 당일 아침(D-0)에는 §A·§B만 빠르게 재실행.

---

## A. Smoke — 외부 의존이 살아있는가 (D-1 / D-0 둘 다)

| # | Check | Pass 기준 | 도구 |
|---|-------|----------|------|
| A1 | Railway `/api/health` | `{"status":"ok"}` 200 | `curl https://capstone-production-e8c2.up.railway.app/api/health` |
| A2 | Vercel 프로덕션 URL 200 | `capstone-eight-virid.vercel.app` 메인 화면 로딩 | Vercel MCP `list_deployments` READY 1건 |
| A3 | Supabase 응답 | `sessions` 테이블 select 200, RLS 정책 active | Supabase MCP |
| A4 | GCP 키 유효 | STT/TTS/Gemini 모두 401·403 없이 응답 | A5 흐름이 통과하면 자동 충족 |
| A5 | end-to-end `/api/chat` 1회 | 응답에 `transcript`·`reply`·`tts_audio`·`axes`·`character`·`hint_ko` 키 모두 존재 | Postman 또는 dev page |

---

## B. Mobile-First E2E (실기기, 360px) — §5

> 시뮬레이터 금지. **실제 폰**으로. 데모용 폰 + 백업 폰 둘 다 동일하게 통과해야 함.

- [ ] B1. 메인 `/home` 진입, GNB 정상 노출, 첫 화면 1.5s 내 인터랙티브
- [ ] B2. TalkButton 탭 → 즉시 녹음 상태 진입 (PR #15 dispatch 즉시화 이후 회귀 없음)
- [ ] B3. iOS Safari에서 마이크 권한 허용 후 녹음 정상 (커밋 5bcdaab 기준)
- [ ] B4. 발화 종료 → Listening → Thinking → Speaking UI state 전이 자연스러움 (PR #15 영역)
- [ ] B5. STT 한국어/영어 혼용 발화 인식률 합격선 (5문장 중 4 정확)
- [ ] B6. Pally Canvas2D가 처리 중 freeze, X 버튼 누르면 reveal (커밋 dd1bc7b)
- [ ] B7. `hint_ko` 인라인 한국어 힌트 노출, 표현 교정 의도가 자연스러움
- [ ] B8. TTS 재생이 끊김 없음, mp3 base64 디코딩 성공
- [ ] B9. 같은 세션에서 5턴 진행 시 캐릭터 톤/라벨이 실제로 변화 (EMA α=0.7)
- [ ] B10. 화면 회전·앱 백그라운드 후 복귀 시 세션 깨지지 않음
- [ ] B11. 360px 폭 기준 텍스트 잘림·버튼 겹침 없음

---

## C. 데이터 품질 — 5축 분포 검증 (§5)

> 한 문장만 말고 데모 시나리오 전체로 충분한 분포가 나와야 함.

- [ ] C1. 5축(Formality/Energy/Intimacy/Humor/Curiosity) 각각 데모 시나리오 안에서 의미 있는 편차(절댓값 ≥ 0.3) 1회 이상 발생
- [ ] C2. 캐릭터 라벨(tone/energy/humor)이 한 세션에서 최소 2회 변경
- [ ] C3. `messages` 테이블에 5턴 row 정상 적재 + `axes`·`character` 컬럼 비어있지 않음
- [ ] C4. EMA 적용 결과가 단순 마지막 발화값이 아닌 누적 형태로 변동 (스파이크 후 다음 턴에 완화 패턴 확인)

---

## D. Performance — Latency 예산

목표는 "발화 종료부터 Pally 응답 시작까지 ≤ 5s". 초과 시 데모 폰 네트워크/녹화 조건 재점검.

| 구간 | 예산 | 실측 (D-1) | 실측 (D-0) |
|------|-----|----------|----------|
| STT (4초 발화) | ≤ 1.5s | | |
| `/api/chat` (Gemini + EMA + DB write) | ≤ 2.5s | | |
| TTS 첫 바이트 | ≤ 1.0s | | |
| **합계** | **≤ 5.0s** | | |

3회 측정 후 중앙값 기록. 95퍼센타일이 6초 넘으면 fallback 시나리오(§G3) 준비.

---

## E. Security / RLS (§7)

- [ ] E1. Supabase 모든 테이블 RLS enabled (`sessions`, `messages`) — Supabase MCP `select * from pg_tables`로 확인
- [ ] E2. 정책이 `session_id` 기반. `using (true)` 없음
- [ ] E3. 프론트엔드 번들 안에 `service_role` 문자열 0건 (`grep -ri "service_role" frontend/.next` 빈 결과)
- [ ] E4. Vercel/Railway 환경변수에 키 노출 없음 (대시보드 confirm)
- [ ] E5. `.env*`·GCP service account JSON git status에 잡힘 없음

---

## F. Error Handling 점검 — §6 #3

> "에러 삼키지 않는다. crash 가 silent 보다 낫다."

- [ ] F1. 마이크 권한 거부 시 사용자에게 명시적 안내 (silent 실패 X)
- [ ] F2. Railway 의도적 5xx 응답 시 UI에 에러 토스트/메시지 노출, Pally가 정지 상태 유지
- [ ] F3. STT 실패 응답 시 사용자에게 재시도 안내 (자동 재시도가 무한 루프 안 됨)
- [ ] F4. TTS 실패 시 텍스트 응답만이라도 사용자에게 노출 (완전 무응답 금지)
- [ ] F5. `catch {}` 비어있는 블록 0건 (`rg "catch \\{\\s*\\}" frontend backend ai`)
- [ ] F6. `|| {}` / `?? []` 같은 silent fallback 신규 패턴 0건 (PR diff 기준)

---

## G. 데모 운영 준비

- [ ] G1. 데모 폰 풀충전 + 비행기 모드 OFF + Wi-Fi 안정 SSID 고정
- [ ] G2. 백업 폰에 동일 빌드 + 동일 세션 데이터 prepared
- [ ] G3. **Fallback 시나리오 결정** — Railway 다운 시 미리 녹화한 80초 클립으로 대체할지, 아예 다른 데모 카드로 갈지 사전 합의
- [ ] G4. 데모 노트북에서 Vercel/Railway/Supabase 대시보드 사전 로그인 (실시간 로그 모니터링용)
- [ ] G5. 데모 시나리오 스크립트(`docs/final/DEMO_SCRIPT.md`) 인쇄본 1부
- [ ] G6. 중간발표 Q&A(`docs/mvp/2026-05-midterm-qa.md`) Top 6 답변 발표자 숙지

---

## H. 평가 직전 1시간 체크 (D-0 morning)

> 위 §A·§B 핵심만 압축. 6/7 발표 시작 1시간 전 마지막 패스.

1. `curl /api/health` — 200
2. 실제 폰에서 1회 full loop (rec → reply → TTS) 성공
3. Supabase 대시보드에서 직전 row 적재 확인
4. 배터리·네트워크·노트북 외부 모니터 케이블 sanity check
5. 발표자 + PM 한 명씩 동시 접속해서 세션 충돌 없음 확인

---

## 합격 기준

- §A 5개 전부 ✓
- §B 11개 중 ≤ 1개 ✗ 이고 해당 항목이 데모 시나리오 경로에 없음
- §C 4개 전부 ✓
- §D 합계 중앙값 ≤ 5.0s
- §E·§F 전부 ✓
- §G 6개 전부 ✓

§A·§B·§C 중 하나라도 미달 → **데모 강행 금지, 팀 즉시 소집**.
