# Pally — CharaShift MVP

## What This Is

한국인 영어 학습자가 모바일 웹에서 음성으로 AI 캐릭터 "Pally"와 영어 회화를 연습하는 서비스. 사용자의 영어 발화를 5개 축(Formality, Energy, Intimacy, Humor, Curiosity)으로 분석해 Pally의 외형/색/표정과 응답 말투를 실시간으로 변화시키고, 대화 중 인라인 한국어 힌트/피드백을 제공한다. 캡스톤 산학 트랙 MVP로, 2026-06-07 데모를 목표로 한다.

## Core Value

**"내 영어 발화 스타일에 반응하는 Pally."**

사용자가 영어로 말할 때마다 → 5축 분석 → CHARACTER MATRIX → Pally의 시각과 말투가 즉시 바뀌는 흐름이 끊김 없이 작동하는 것이 가장 중요하다. 피드백, UI, 세션 관리 같은 보조 기능은 이 핵심 루프가 모바일 데모에서 안정적으로 보이는 것에 종속된다.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ 규칙 기반 5축 발화 분석기 — `ai/analyzer.py` (Python, 키워드+정규식)
- ✓ CHARACTER MATRIX 가중합 연산 — `ai/matrix_engine.py` (Python)
- ✓ EMA 기반 점수 완화 로직 — `ai/matrix_engine.py`
- ✓ 25개 수작업 라벨 데이터셋 — `data/dataset.py`
- ✓ 5축 → 캐릭터 파라미터 변환 테스트 스크립트 — `tests/test_matrix.py`
- ✓ Canvas2D 시각화 프로토타입 — `assets/visualizer.html`

### Active

<!-- June 7 데모 범위. Building toward these. -->

- [ ] **MAIN-01**: 메인 화면에 Pally 대기 상태 + 하단 음성 입력 시작 버튼(rec)을 표시한다
- [ ] **VOICE-01**: 사용자가 rec 버튼을 누르면 브라우저에서 마이크 권한 요청 → 녹음 Blob 생성 → FastAPI `/api/chat`로 전달 → Google Cloud Speech-to-Text로 영어 발화를 텍스트화한다
- [ ] **VOICE-02**: Gemini 2.5 Flash가 영어 응답을 생성하고 Google Cloud Text-to-Speech가 음성으로 변환해 클라이언트에서 재생한다
- [ ] **ENGINE-01**: 발화 텍스트 → rule-based 5축 분석 → CHARACTER MATRIX → EMA 보정(alpha=0.7 for demo) → 캐릭터 파라미터 계산 흐름이 서버 계약으로 동작한다
- [ ] **PALLY-01**: Pally는 Canvas2D Superformula 도형으로 렌더링되며 Formality / Energy / Intimacy / Humor / Curiosity 기반 캐릭터 파라미터에 따라 형태·색·표정이 실시간 변화한다
- [ ] **PALLY-02**: 응답 생성 중 Pally가 thinking/loading 애니메이션을 표시한다
- [ ] **CHAT-01**: 대화 화면에서 직전 발화/응답을 말풍선으로 미리 보여주고, 토글로 전체 대화 스크립트(SMS 스타일, 사용자=노란색, Pally=흰색)를 볼 수 있다
- [ ] **FB-01**: 대화 중 사용자의 어색한 영어 발화를 Gemini가 감지하면 한국어 힌트를 메인 화면 안의 작은 UI 요소로 즉시 표시한다
- [ ] **FB-02**: `/api/chat` 응답에 현재 발화에 대한 표현 교정, 한국어 설명, 더 자연스러운 대안 표현을 structured inline feedback payload로 포함한다. 별도 `/feedback` 페이지는 만들지 않는다
- [ ] **SESSION-01**: 익명 세션 ID로 Supabase `sessions` 테이블에 세션 생성, 모든 메시지는 `messages` 테이블에 `axes`/`character` JSONB와 함께 저장한다. RLS는 `session_id` 기반이다
- [ ] **DEPLOY-01**: 프론트는 Vercel, 백엔드는 Railway에 배포되고, 모바일 브라우저에서 배포 URL로 rec → 발화 → Pally 응답 음성 재생 → 인라인 힌트 표시 흐름이 데모 가능하다

### Out of Scope

<!-- 명시적 제외. Post-MVP 또는 데모 범위 밖. -->

- 회원가입 / 로그인 — 익명 세션으로 단순화, Post-MVP에서 인증 도입
- 온보딩 스타일 선택 또는 Pally 이름/영어 레벨 입력 — MVP는 `character_name = 'Pally'`, `level = 'B1'` 기본값 사용
- 별도 `/feedback` route/page — MVP는 `/api/chat` 응답의 inline feedback payload만 사용
- 대화 이력 영구 검색 / pgvector RAG — Post-MVP (장기 페르소나)
- Reddit PRAW 슬랭 파이프라인 — Post-MVP 데이터 확장
- ML/LLM 기반 5축 분석기 — MVP는 rule-based 유지, Phase 2 이후 검토
- 데스크탑 최적화 — 모바일 우선, 데스크탑은 표시만 깨지지 않게
- 발음/억양 피드백 — STT는 텍스트화에만, 발음 평가는 Post-MVP
- OpenAI Whisper / GPT-4o / GPT-4o-mini-tts — MVP LLM/음성 벤더는 GCP 단일로 통일

## Context

- **프로젝트 성격**: 광운대 캡스톤 산학 트랙 MVP. 팀명 퓨터, 지도 심재형 교수님.
- **팀 구성 (4명)**:
  - 최윤서 — PM · 기획 · QA
  - 이찬희 — FE · 디자인, Phase 0 + Phase 1A 담당
  - 김민주 — AI · 데이터, Phase 1B 담당
  - 백은혜 — BE · AI, Phase 1C 담당
- **June 7 개발 분담 (3명 병렬)**:
  - **Phase 0 — Foundation**: `frontend/` Next.js scaffold, 최소 UI 타입, Supabase anon client, Tailwind, env example
  - **Phase 1A — FE Screens & Audio Shell**: 메인 대화 화면, rec/audio UX shell, mock transport
  - **Phase 1B — Pally Canvas2D + Engine ADR**: Superformula renderer, character types, demo controls, Python engine integration ADR
  - **Phase 1C — Voice + Inline Feedback Backend**: FastAPI `/api/chat`, Google Cloud STT/TTS, Gemini 2.5 Flash, Supabase schema/RLS
  - **Phase 2 — Integration & Demo Polish**: Vercel + Railway 배포, real wiring, 모바일 실기기 리허설
- **Repo layout**:
  - `frontend/` — Next.js 14 App Router, Vercel Root Directory, 이찬희 작업 영역
  - `backend/` — FastAPI, Railway Root Directory, 백은혜 작업 영역, 루트 `ai/` import
  - `ai/` — Python 5축 엔진, 김민주 + 백은혜 공동 사용
  - 김민주 frontend 소유 영역 — `frontend/components/pally/`, `frontend/app/dev/pally/`, `frontend/lib/types/character.ts`
- **Current planning source of truth**: `.planning/ROADMAP.md`. 이 문서와 `REQUIREMENTS.md`, `STATE.md`는 ROADMAP 기준으로 동기화한다. `docs/mvp/*`는 배경 자료이며 현재 scope 판단에서는 ROADMAP이 우선한다.

## Constraints

- **Timeline**: 2026-06-07 데모 마감. 모든 기능은 이 날짜에 모바일 브라우저에서 안정적으로 동작해야 한다.
- **Tech stack**: Next.js 14 (App Router) · TypeScript strict · Tailwind · FastAPI · Python 3.11 · Supabase (Postgres + RLS) · GCP Vertex AI Gemini 2.5 Flash · Google Cloud Speech-to-Text · Google Cloud Text-to-Speech · Canvas2D Superformula.
- **Deployment**: 프론트엔드 Vercel (`frontend/` root), 백엔드 Railway (`backend/` root). GitHub main branch 배포 흐름을 기준으로 한다.
- **Mobile-first**: 데모는 발표자 모바일 또는 휴대용 디바이스에서 시연. 모든 화면이 ~360px 폭에서 작동해야 한다.
- **Database**: Supabase 사용. 모든 테이블 RLS 활성화 필수. 익명 세션이므로 정책은 `session_id` 기반.
- **Security**: GCP service account JSON, Supabase `service_role`은 서버 측 환경변수로만 사용한다. 클라이언트 번들에는 `NEXT_PUBLIC_*`와 anon key만 포함한다.
- **Cost**: 5축/MATRIX는 자체 엔진으로 처리하고 Gemini 호출은 응답 생성 및 인라인 피드백에 집중한다. 데모 시연용 GCP 사용량 한도 설정을 권장한다.
- **Parallelism**: Phase 0 이후 1A/1B/1C는 반드시 병렬 진행한다. 1C는 1B 전체 완료가 아니라 D+1 Python engine ADR만 coordination input으로 소비한다.

## Key Decisions

<!-- 프로젝트 lifecycle 동안 의미 있는 결정만 누적. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Monorepo를 `frontend/` + `backend/` + `ai/`로 분리 | 1A/1B/1C 병렬 작업 중 파일 충돌을 줄이고, Vercel/Railway 배포 root를 명확히 한다. | Accepted |
| 프론트는 Vercel, 백엔드는 Railway FastAPI로 배포 | Python 엔진과 GCP Python client libraries를 자연스럽게 사용하고, Next.js API route에 음성/AI 백엔드 책임을 몰지 않는다. | Accepted |
| LLM/음성 벤더는 GCP 단일로 통일 | OpenAI와 GCP 혼용을 없애고 STT/TTS/Gemini 응답 생성의 인증·운영 복잡도를 줄인다. | Accepted |
| `/feedback` 별도 화면은 MVP에서 제외 | 핵심 루프(rec → Pally 응답 → 인라인 힌트)에 집중하고 Phase 2 통합 부담을 줄인다. | Accepted |
| Phase 0은 최소 foundation만 수행 | 0.5일 안에 병렬 작업을 unblock하고, Supabase schema/engine ADR은 각 전문 phase로 옮긴다. | Accepted |
| `Axes` / `CharacterParams` 타입은 Phase 1B 소유 | 실제 `ai/analyzer.py`와 `matrix_engine.py` 출력 모양을 보는 사람이 타입을 정의해야 한다. | Accepted |
| 1C는 1B 전체가 아닌 D+1 engine ADR만 의존 | 1A/1B/1C 병렬성을 보존하면서 엔진 호출 방식만 조기에 합의한다. | Accepted |
| MVP는 rule-based 5축 분석기만 사용 | 이미 검증된 자산을 활용해 데모 안정성을 높인다. ML/LLM 분석기는 Post-MVP에서 검토한다. | Accepted |
| 온보딩 생략, `Pally`/`B1` 기본값 사용 | 데모 진입 경로를 짧게 유지하고 v2 사용자 입력으로 확장 가능하게 둔다. | Accepted |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-21 — synchronized to ROADMAP.md*
