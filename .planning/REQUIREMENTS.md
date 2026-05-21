# Requirements: Pally — CharaShift MVP

**Defined:** 2026-05-21
**Last synchronized:** 2026-05-21
**Planning source of truth:** `.planning/ROADMAP.md`
**Core Value:** 내 영어 발화 스타일에 반응하는 Pally — 5축 분석이 Pally의 시각·말투 변화로 즉시 이어지는 흐름

## v1 Requirements

June 7 데모에 포함되는 기능. 각 항목은 ROADMAP 기준 phase에 매핑된다.

### Main Screen

- [ ] **MAIN-01**: 메인 화면에 Pally 대기 상태와 하단 음성 입력 시작 버튼(rec)을 표시한다

### Voice (STT/TTS)

- [ ] **VOICE-01**: 사용자가 rec 버튼을 누르면 브라우저에서 마이크 권한 요청 → 녹음 Blob 생성 → FastAPI `/api/chat` 전송 → Google Cloud Speech-to-Text로 영어 발화를 텍스트화한다
- [ ] **VOICE-02**: Gemini 2.5 Flash가 생성한 영어 응답을 Google Cloud Text-to-Speech로 음성 변환하고, 클라이언트에서 음성과 말풍선 텍스트로 재생/표시한다

### Engine (5-axis + CHARACTER MATRIX)

- [ ] **ENGINE-01**: 사용자 발화 텍스트가 들어오면 rule-based 5축 분석기를 거쳐 CHARACTER MATRIX 가중합 + EMA 보정(alpha=0.7 for demo)을 적용해 캐릭터 파라미터를 산출한다. Python engine integration 방식은 Phase 1B ADR에서 확정하고 Phase 1C가 소비한다

### Pally (Canvas2D)

- [ ] **PALLY-01**: Pally는 Canvas2D Superformula 도형으로 렌더링되며 Formality / Energy / Intimacy / Humor / Curiosity 기반 캐릭터 파라미터에 따라 형태·색·표정이 실시간으로 변화한다 (부드러운 트랜지션)
- [ ] **PALLY-02**: 응답 생성 중 Pally가 thinking/loading 애니메이션을 표시한다

### Chat UI

- [ ] **CHAT-01**: 대화 화면에서 직전 발화/응답을 말풍선으로 미리 보여주고, 토글로 전체 대화 스크립트(SMS 스타일, 사용자=노란색, Pally=흰색)를 볼 수 있다

### Feedback

- [ ] **FB-01**: 대화 중 사용자의 어색한 영어 발화를 Gemini가 감지하면 한국어 힌트를 메인 화면 안의 작은 UI 요소로 즉시 표시한다 (대화 흐름 방해 최소)
- [ ] **FB-02**: `/api/chat` 응답에는 현재 발화에 대한 표현 교정, 한국어 설명, 더 자연스러운 대안 표현이 structured inline feedback payload로 포함된다. 별도 `/feedback` route/page는 만들지 않는다

### Session / Data

- [ ] **SESSION-01**: 익명 세션 ID로 Supabase `sessions` 테이블에 세션 생성, 모든 메시지는 `messages` 테이블에 `axes`/`character` JSONB와 함께 저장한다. RLS는 `session_id` 기반이다

### Deployment

- [ ] **DEPLOY-01**: 프론트엔드는 Vercel(`frontend/` root), 백엔드는 Railway(`backend/` root)에 배포되며, 모바일 브라우저에서 rec → 발화 → Pally 응답 음성 재생 → 인라인 힌트 표시 흐름이 데모 가능하다

## v2 Requirements

MVP 이후 다음 마일스톤에서 검토. 현재 roadmap에는 포함되지 않음.

### Auth & Onboarding

- **AUTH-01**: 회원가입 / 로그인 (이메일·소셜)
- **ONB-01**: 첫 진입 시 Pally 이름, 영어 레벨, 발화 스타일 사전 선택

### Long-term Personalization

- **MEM-01**: 세션 종료 시 5축 누적치를 `user_persona` 테이블에 EMA로 업데이트
- **MEM-02**: 과거 대화를 pgvector로 임베딩 저장 → RAG로 응답에 컨텍스트 주입

### Engine Evolution

- **ENGINE-02**: ML/LLM 기반 5축 분석기로 보완 또는 대체 (정확도 향상)
- **ENGINE-03**: Reddit PRAW 슬랭 데이터 파이프라인 — 학습 목적 태깅 필터링

### Feedback Expansion

- **FB-03**: 별도 피드백/리포트 화면에서 세션 전체 표현 교정 + 한국어 설명 + 더 자연스러운 대안 표현 제공
- **FB-04**: 발음/억양 평가 피드백
- **FB-05**: 주간 학습 리포트 (대화 시간/표현 다양성)

### Platform Expansion

- **PLAT-01**: 데스크탑 최적화 (현재는 모바일 우선)
- **PLAT-02**: 모바일 네이티브 앱 (React Native)

## Out of Scope

명시적 제외. 추후 재논의가 필요한 결정.

| Feature | Reason |
|---------|--------|
| OpenAI Whisper / GPT-4o / GPT-4o-mini-tts | ROADMAP 기준 MVP 벤더는 GCP 단일. Google Cloud STT/TTS + Gemini 2.5 Flash 사용. |
| 별도 `/feedback` route/page | MVP는 메인 화면 inline feedback payload만 제공. 별도 화면은 Post-MVP. |
| 회원가입 / 로그인 | MVP는 익명 `session_id`로 단순화. |
| 온보딩 / 사용자 입력 기반 Pally 이름·레벨 설정 | MVP는 `Pally` / `B1` 기본값 사용. |
| 실시간 멀티유저 대화 (1:N) | Pally는 1:1 학습 도구 포지셔닝. 멀티유저는 제품 정체성과 어긋남. |
| 로맨틱/감정 지지 챗봇 방향 | 학습 도구 포지셔닝 유지. |
| 정답형 영어 시험 모드 (TOEIC 등) | "내 말투에 반응하는 AI"라는 Core Value와 무관. 별도 제품 영역. |

## Traceability

각 v1 요구사항이 어느 phase에 매핑되는지.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MAIN-01 | Phase 1A | Pending |
| VOICE-01 | Phase 1C | Pending |
| VOICE-02 | Phase 1C | Pending |
| ENGINE-01 | Phase 1B (ADR + integration) + Phase 1C (consumer) | Pending |
| PALLY-01 | Phase 1B | Pending |
| PALLY-02 | Phase 1B | Pending |
| CHAT-01 | Phase 1A | Pending |
| FB-01 | Phase 1C | Pending |
| FB-02 | Phase 1C | Pending |
| SESSION-01 | Phase 0 (types) + Phase 1C (schema/RLS) | Pending |
| DEPLOY-01 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11 ✓
- Unmapped: 0 ✓

**Phase distribution:**
- Phase 0 (Foundation): SESSION-01 partial (minimal UI/session type foundation)
- Phase 1A (FE Screens & Audio Shell): 2 requirements (MAIN-01, CHAT-01) + browser audio shell for VOICE integration
- Phase 1B (Pally Canvas2D + Engine ADR): 3 requirements (ENGINE-01 ADR/integration, PALLY-01, PALLY-02)
- Phase 1C (Voice + Inline Feedback Backend + Schema): 6 requirements (VOICE-01, VOICE-02, ENGINE-01 consumer, FB-01, FB-02, SESSION-01 schema/RLS)
- Phase 2 (Integration & Demo): 1 requirement (DEPLOY-01) + real FE/BE wiring

---

*Requirements defined: 2026-05-21*
*Last updated: 2026-05-21 — synchronized to ROADMAP.md*
