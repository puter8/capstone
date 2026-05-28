# Pre-Demo QA Checklist

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

## B. Mobile-First E2E (실기기, 360px) — 

> 실제 휴대폰 사용한 테스트

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

## C. 데이터 품질 — 5축 분포 검증 

> 한 문장만 말고 데모 시나리오 전체로 충분한 분포가 나와야 함.

- [ ] C1. 5축(Formality/Energy/Intimacy/Humor/Curiosity) 각각 데모 시나리오 안에서 의미 있는 편차(절댓값 ≥ 0.3) 1회 이상 발생
- [ ] C2. 캐릭터 라벨(tone/energy/humor)이 한 세션에서 최소 2회 변경
- [ ] C3. `messages` 테이블에 5턴 row 정상 적재 + `axes`·`character` 컬럼 비어있지 않음

---

## D. 데모 운영 준비

- [ ] G1. 데모 폰 풀충전 + 비행기 모드 OFF + Wi-Fi 안정 SSID 고정
- [ ] G2. 백업 폰에 동일 빌드 + 동일 세션 데이터 prepared
- [ ] G3. 데모 기기에서 Vercel/Railway/Supabase 대시보드 사전 로그인 (실시간 로그 모니터링용)

---

## 최소 검증 시나리오
1. Pally 실행, 새로운 대화 세션 생성
2. 세션 내에서 올바른 발화 실행 2회, 답변 받기
3. 세션 내에서 문법적으로 틀린 발화 실행 2회, 답변 받기
4. 세션 후 Pally의 달라진 생김새 확인
