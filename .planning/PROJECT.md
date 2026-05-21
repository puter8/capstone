# Pally — CharaShift MVP

## What This Is

한국인 영어 학습자가 모바일 웹에서 음성으로 AI 캐릭터 "Pally"와 영어 회화를 연습하는 서비스. 사용자의 영어 발화를 5개 축(Formality, Energy, Intimacy, Humor, Curiosity)으로 분석해 Pally의 외형/색/표정과 응답 말투를 실시간으로 변화시키고, 대화 중·후에 한국어로 표현 피드백을 제공한다. 캡스톤 산학 트랙 MVP로, 2026-06-07 데모를 목표로 한다.

## Core Value

**"내 영어 발화 스타일에 반응하는 Pally."**

사용자가 영어로 말할 때마다 → 5축 분석 → CHARACTER MATRIX → Pally의 시각과 말투가 즉시 바뀌는 흐름이 끊김 없이 작동하는 것이 가장 중요하다. 피드백, UI, 세션 관리 같은 모든 보조 기능은 이 핵심 루프가 데모에서 안정적으로 보이는 것에 종속된다.

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

- [ ] **MAIN-01**: 메인 화면에 Pally 대기 상태 표시 + 음성 입력 시작 버튼 (rec)
- [ ] **VOICE-01**: 마이크 음성 → OpenAI Whisper STT로 영어 발화 텍스트화
- [ ] **VOICE-02**: GPT-4o 영어 응답 → GPT-4o-mini-tts 음성 출력 (스트리밍/말풍선 표시)
- [ ] **ENGINE-01**: 발화 텍스트 → 5축 분석 → CHARACTER MATRIX → 캐릭터 파라미터 계산 (서버에서 실행)
- [ ] **PALLY-01**: Canvas2D Superformula 기반 Pally 캐릭터 형태/색/표정이 캐릭터 파라미터에 따라 실시간 변화
- [ ] **PALLY-02**: 응답 생성 중 Pally 로딩/생각 애니메이션
- [ ] **CHAT-01**: 대화 화면 — 직전 발화/응답 미리보기 + 토글로 전체 스크립트 뷰 (SMS 스타일, 사용자 노란색·Pally 흰색)
- [ ] **FB-01**: 대화 중 인라인 피드백 — Gemini가 잘못된 영어 발화 감지 시 즉시 한국어 힌트 표시
- [ ] **FB-02**: 대화 종료 후 `/feedback` 페이지 — LLM 일괄 분석으로 표현 교정 + 한국어 설명
- [ ] **SESSION-01**: 익명 세션 기반 — Supabase `sessions`/`messages` 테이블에 axes/character 함께 저장
- [ ] **DEPLOY-01**: Vercel 배포된 URL로 모바일 브라우저에서 데모 가능

### Out of Scope

<!-- 명시적 제외. Post-MVP 또는 데모 범위 밖. -->

- 회원가입 / 로그인 — 익명 세션으로 단순화, Post-MVP에서 인증 도입
- 온보딩 스타일 선택 (캐주얼/격식/탐구형) — 메인에서 바로 대화로 진입하도록 단순화
- 대화 이력 영구 검색 / pgvector RAG — Post-MVP (장기 페르소나)
- Reddit PRAW 슬랭 파이프라인 — Post-MVP 데이터 확장
- ML/LLM 기반 5축 분석기 — MVP는 rule-based 유지, Phase 2 이후 검토
- 데스크탑 최적화 — 모바일 우선, 데스크탑은 표시만 깨지지 않게
- 발음/억양 피드백 — STT는 텍스트화에만, 발음 평가는 Post-MVP
- 별도 FastAPI 백엔드 / Railway 배포 — Next.js API routes로 통합 (Vercel 단일 배포)

## Context

- **프로젝트 성격**: 광운대 캡스톤 산학 트랙 MVP. 팀명 퓨터, 지도 심재형 교수님.
- **팀 구성 (4명)**:
  - 최윤서 — PM · 기획 · QA
  - 백은혜 — AI 엔진 · 데이터 파이프라인
  - 김민주 — 백엔드 (Next.js API routes · Supabase)
  - 이찬희 — 프론트엔드 · 디자인 (Next.js · Canvas2D)
- **June 7 개발 분담** (3명, 각 ★★★★ 분량):
  - **A — FE 화면 + 피드백 UI**: Figma → 실제 화면(랜딩/대화/스크립트), `/feedback` 페이지
  - **B — Pally 캐릭터 변화**: Canvas2D Superformula 형태 변화 고도화, 5축 변화에 따른 트랜지션/색상/표정
  - **C — STT/TTS + 피드백 BE**: Whisper STT 안정화, GPT-4o-mini-tts, `/api/feedback` 엔드포인트, LLM 프롬프트
- **중간발표 (2026-05) Q&A에서 검증된 설계 결정** (자세히는 [docs/mvp/2026-05-midterm-qa.md](../docs/mvp/2026-05-midterm-qa.md)):
  - 콜드 스타트 대응: 초기 세션 EMA α 일시 상승 (0.3 → 0.7), 첫 3~5턴에 캐릭터 변화 체감
  - 페르소나 제어: Base Personality(고정) + Relationship Layer(EMA 갱신, ±20 클램프) 2층 구조
  - 단기 맥락(`session_messages`)과 장기 페르소나(`user_persona`) 분리 — MVP는 단기만, 장기는 Post-MVP
  - 비용 관리: 5축/MATRIX는 자체 엔진(GPT 호출 X), GPT-4o는 응답 생성에만, 프롬프트 캐싱
  - 과몰입 방지: 학습 도구 포지셔닝, "AI 캐릭터와 대화 중" 라벨 상시 노출
- **기존 자산**: Python 핵심 엔진(`ai/`, `tests/`)은 검증 완료 상태. MVP에서는 이 로직을 Next.js 런타임에 통합하는 방식이 미정 (다음 단계에서 결정).
- **MVP 정본 문서**: [docs/mvp/PRD.md](../docs/mvp/PRD.md), [docs/mvp/2026-05-midterm-qa.md](../docs/mvp/2026-05-midterm-qa.md), [README.md](../README.md). 전체 제품·Post-MVP 기획은 [docs/final/](../docs/final/), 양쪽 공유 문서는 [docs/shared/](../docs/shared/)에 위치.

## Constraints

- **Timeline**: 2026-06-07 데모 마감 — 17일 남음. 모든 기능은 이 날짜에 안정적으로 동작해야 함.
- **Tech stack**: Next.js 14 (App Router) · TypeScript strict · Tailwind · Supabase (Postgres + Auth + RLS) · OpenAI (Whisper, GPT-4o, gpt-4o-mini-tts) · Google Gemini (인라인 피드백) · Canvas2D Superformula — 새 의존성 추가는 명시적 결정 필요.
- **Deployment**: Vercel (main 브랜치 push → 자동 배포). 별도 BE 서버 없음.
- **Mobile-first**: 데모는 발표자 모바일 또는 휴대용 디바이스에서 시연. 모든 화면이 ~360px 폭에서 작동.
- **Database**: Supabase 사용 (PRD대로). 모든 테이블 RLS 활성화 필수. 익명 세션이므로 정책은 `session_id` 기반.
- **Security**: OpenAI/Gemini API 키는 서버 측 환경변수, `service_role`은 클라이언트 코드에 절대 노출 금지.
- **Cost**: GPT-4o 호출 횟수 최소화(분석은 자체 엔진), 프롬프트 캐싱 사용, 데모 시연용 일일 한도 설정 권장.
- **Team capacity**: 3명이 17일 안에 4축 (FE + Pally + STT/TTS + Feedback BE)을 모두 끝내야 함. 병렬 가능한 단위로 phase를 쪼개는 것이 critical.

## Key Decisions

<!-- 프로젝트 lifecycle 동안 의미 있는 결정만 누적. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Vercel + Supabase 단일 스택, 별도 FastAPI/Railway 배포 제외 | 데모 환경 단순화, 17일 timeline 안에서 배포·디버깅 부담 최소화. 핵심 엔진은 Next.js API routes에서 실행. | — Pending |
| MVP는 rule-based 5축 분석기만 사용 | 이미 검증된 자산. ML/LLM 분석기는 정확도 향상은 있어도 timeline 안에 통합·검증 어려움. | — Pending |
| 피드백 이중 트랙 — 인라인(Gemini) + 종료 후(OpenAI 일괄) | 인라인은 즉각성, 종료 후는 종합성. 두 LLM 분담으로 비용 분산. | — Pending |
| 모바일 우선, 익명 세션, 온보딩 생략 | 데모 흐름을 최단 경로(메인 → 음성 시작 → 응답 → 피드백)로 단순화. Auth/온보딩은 Post-MVP. | — Pending |
| 5축이 Pally의 시각(Canvas2D)과 말투(GPT-4o 프롬프트 변수) 둘 다에 영향 | "스타일이 반응으로 이어진다"는 Core Value를 가장 잘 보여주는 구성. PRD와 일치. | — Pending |
| Next.js 앱을 repo 루트에 배치 (option A) | Vercel 표준 배포 구조. `frontend/`/`backend/` 빈 placeholder는 삭제. 17일 timeline에서 별도 서브폴더/모노레포 오버헤드 회피. | — Pending |
| Python 엔진(`ai/`)의 통합 방식은 Phase 0에서 결정 | TS 포팅 vs serverless Python vs subprocess — Foundation phase 계획 단계에서 비교/결정. 지금 결정하면 잘못된 가정 만들 위험. | — Pending |

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
*Last updated: 2026-05-21 after initialization*
