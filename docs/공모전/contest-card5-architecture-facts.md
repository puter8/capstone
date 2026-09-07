# 카드 5 — 아키텍처·DB 최종 QA용 사실 확인 자료

> 김민주 팀원이 작성한 개발보고서/제작설계서의 아키텍처·ERD·API·DB·보안 부분을 이 자료와 대조해서 다른 내용이 있으면 표시. 아래는 실제 코드/마이그레이션 기준으로 100% 확인된 사실만 정리함(2026-09-07 기준). Notion 원본 초안은 접근 불가라 못 봤음 — 이 파일을 받는 즉시 초안이랑 줄 단위로 비교해서 다른 부분만 골라내면 됨.

## DB 테이블 (실제 `supabase/migrations/` 9개 파일 기준, 총 7개 테이블)

| 테이블 | 역할 | RLS |
|---|---|---|
| `sessions` | 대화(conversation) 단위, character_name/level/reopen 필드 포함 | ✅ 활성화 |
| `messages` | 턴 단위, transcript/axes/character/feedback(jsonb)/idempotency_key 포함 | ✅ 활성화 |
| `profiles` | 사용자 프로필, english_level, traits | ✅ 활성화 |
| `usage_daily` | 일일 사용량(quota) | ✅ 활성화 |
| `activity_events` | 화면 활동 이벤트(성취 시스템용) | ✅ 활성화 |
| `daily_task_snapshots` | 일일 과제 스냅샷 | ✅ 활성화 |
| `streak_days` | 연속 사용일 기록 | ✅ 활성화 |

**7개 테이블 전부 RLS 활성화 확인**(CLAUDE.md 규칙 "모든 테이블 RLS 활성화, 예외 없음"과 일치). `service_role` 정책과 `authenticated` 사용자 본인 소유 정책이 분리되어 있음(`allow_service_role_all_*`, `allow_authenticated_*_own_*`).

## API 엔드포인트 (실제 `backend/main.py` + `backend/README_API.md` 기준)

| Method | Path | 비고 |
|---|---|---|
| GET | `/api/health` | 헬스체크 |
| POST | `/api/stt` | Google Cloud STT |
| POST | `/api/chat` | 5축 분석+Gemini 응답(레거시 경로) |
| POST | `/api/tts` | Google Cloud TTS |
| POST | `/api/feedback` | 표현 교정(레거시, `{correction, tone_feedback, practice_prompt}` 형태 — turn API의 `FeedbackItem[]`과 다름, 혼동 주의) |
| POST | `/api/conversations` | 대화 생성 |
| POST | `/api/conversations/{id}/turns` | 턴 처리(STT→분석→Gemini→TTS→저장, 현재 운영 중인 핵심 경로) |
| POST | `/api/conversations/{id}/complete` | 대화 종료 |
| POST | `/api/conversations/{id}/reopen` | 대화 재개 |
| GET | `/api/conversations` | History 목록 |
| GET | `/api/conversations/{id}` | 대화 상세(turn+feedback) |
| GET | `/api/usage` | 사용량 조회 |
| GET | `/api/achievements` | 성취 조회 |

## 보안/키 관리 사실

- 클라이언트: Supabase `anon` key만 사용
- 서버: Supabase `service_role` key는 `backend/lib/supabase.py`에서만, server-only
- GCP(STT/TTS)·Gemini API 키는 서버 환경변수로만 존재, 클라이언트 번들에 미노출
- Idempotency: `messages.idempotency_key`로 turn 중복 저장 방지(unique index)

## 자주 틀리는 부분 (문서 작성 시 주의)

1. **`/api/chat`과 `/api/conversations/{id}/turns`를 같은 걸로 서술하지 말 것** — `/api/chat`은 초기(레거시) 경로, 실제 운영 중인 것은 turns 엔드포인트. 둘 다 언급하려면 "레거시/현재"로 명확히 구분.
2. **`/api/feedback`의 응답 형태를 `FeedbackItem[]`로 쓰면 사실 오류** — 이건 `{correction, tone_feedback, practice_prompt}` 객체를 반환하는 별도 레거시 엔드포인트. `FeedbackItem[]`(`{original, corrected, explanation_ko}`)은 turns 엔드포인트 안에서 생성됨.
3. Analyzer 기본값은 **`rule`**(ML/hybrid 아님) — 아키텍처 다이어그램에 "ML 분석기"라고 쓰면 안 됨.
