# Requirements: Pally — CharaShift MVP

**Defined:** 2026-05-21
**Core Value:** 내 영어 발화 스타일에 반응하는 Pally — 5축 분석이 Pally의 시각·말투 변화로 즉시 이어지는 흐름

## v1 Requirements

June 7 데모에 포함되는 기능. 각 항목은 정확히 하나의 roadmap phase에 매핑된다.

### Main Screen

- [ ] **MAIN-01**: 메인 화면에 Pally 대기 상태(아이들 애니메이션) 표시 + 하단 음성 입력 시작 버튼(rec)

### Voice (STT/TTS)

- [ ] **VOICE-01**: 사용자가 rec 버튼을 누르면 마이크 권한 요청 → OpenAI Whisper로 영어 발화를 텍스트화한다
- [ ] **VOICE-02**: GPT-4o가 생성한 영어 응답을 GPT-4o-mini-tts로 음성 출력하며 동시에 말풍선에 텍스트로 표시한다

### Engine (5-axis + CHARACTER MATRIX)

- [ ] **ENGINE-01**: 사용자 발화 텍스트가 들어오면 rule-based 5축 분석기를 거쳐 CHARACTER MATRIX 가중합 + EMA 보정을 적용해 캐릭터 파라미터(tone_casual, energy_level, humor_level)를 산출한다 (서버에서 실행)

### Pally (Canvas2D)

- [ ] **PALLY-01**: Pally는 Canvas2D Superformula 도형으로 렌더링되며 캐릭터 파라미터(tone_casual / energy_level / humor_level)에 따라 형태·색·표정이 실시간으로 변화한다 (부드러운 트랜지션)
- [ ] **PALLY-02**: GPT-4o 응답을 기다리는 동안 Pally가 "생각 중" 로딩 애니메이션을 표시한다

### Chat UI

- [ ] **CHAT-01**: 대화 화면에서 직전 발화/응답을 말풍선으로 미리 보여주고, 토글로 전체 대화 스크립트(SMS 스타일, 사용자=노란색, Pally=흰색)를 볼 수 있다

### Feedback

- [ ] **FB-01**: 대화 중 사용자의 어색한 영어 발화를 Gemini가 감지하면 한국어 힌트를 작은 UI 요소로 즉시 표시한다 (대화 흐름 방해 최소)
- [ ] **FB-02**: 대화 종료 후 `/feedback` 페이지에서 LLM이 세션 전체를 일괄 분석해 표현 교정 + 한국어 설명 + 더 자연스러운 대안 표현을 제시한다

### Session / Data

- [ ] **SESSION-01**: 익명 세션 ID로 Supabase `sessions` 테이블에 세션 생성, 모든 메시지는 `messages` 테이블에 `axes`/`character` JSONB와 함께 저장 (RLS는 `session_id` 기반)

### Deployment

- [ ] **DEPLOY-01**: 메인 브랜치 push 시 Vercel에 자동 배포되며, 모바일 브라우저에서 배포 URL로 데모 가능 (~360px 폭 정상 동작)

## v2 Requirements

MVP 이후 다음 마일스톤에서 검토. 현재 roadmap에는 포함되지 않음.

### Auth & Onboarding

- **AUTH-01**: 회원가입 / 로그인 (이메일·소셜)
- **ONB-01**: 첫 진입 시 발화 스타일 사전 선택 (캐주얼/격식/탐구형) — 콜드 스타트 완화

### Long-term Personalization

- **MEM-01**: 세션 종료 시 5축 누적치를 `user_persona` 테이블에 EMA로 업데이트
- **MEM-02**: 과거 대화를 pgvector로 임베딩 저장 → RAG로 응답에 컨텍스트 주입

### Engine Evolution

- **ENGINE-02**: ML/LLM 기반 5축 분석기로 보완 또는 대체 (정확도 향상)
- **ENGINE-03**: Reddit PRAW 슬랭 데이터 파이프라인 — 학습 목적 태깅 필터링

### Feedback Expansion

- **FB-03**: 발음/억양 평가 피드백
- **FB-04**: 주간 학습 리포트 (대화 시간/표현 다양성) — 과몰입 방지 넛지 포함

### Platform Expansion

- **PLAT-01**: 데스크탑 최적화 (현재는 모바일 우선)
- **PLAT-02**: 모바일 네이티브 앱 (React Native)

## Out of Scope

명시적 제외. 추후 재논의가 필요한 결정.

| Feature | Reason |
|---------|--------|
| 별도 FastAPI 백엔드 + Railway 배포 | 17일 timeline에서 배포·디버깅 부담 최소화. Next.js API routes로 통합. |
| 실시간 멀티유저 대화 (1:N) | Pally는 1:1 학습 도구 포지셔닝. 멀티유저는 제품 정체성과 어긋남. |
| 로맨틱/감정 지지 챗봇 방향 | 학습 도구 포지셔닝 유지 — 시스템 프롬프트 레벨에서 차단 (Character.AI/Replika 사례 회피) |
| 정답형 영어 시험 모드 (TOEIC 등) | "내 말투에 반응하는 AI"라는 Core Value와 무관. 별도 제품 영역. |

## Traceability

각 v1 요구사항이 어느 phase에 매핑되는지. Roadmap 생성 시 채워짐.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MAIN-01 | TBD | Pending |
| VOICE-01 | TBD | Pending |
| VOICE-02 | TBD | Pending |
| ENGINE-01 | TBD | Pending |
| PALLY-01 | TBD | Pending |
| PALLY-02 | TBD | Pending |
| CHAT-01 | TBD | Pending |
| FB-01 | TBD | Pending |
| FB-02 | TBD | Pending |
| SESSION-01 | TBD | Pending |
| DEPLOY-01 | TBD | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 0 (roadmap 생성 시 채워짐)
- Unmapped: 11 ⚠️ (roadmap 단계에서 0으로 만들어야 함)

---
*Requirements defined: 2026-05-21*
*Last updated: 2026-05-21 after initialization*
