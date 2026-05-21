# Roadmap: Pally — CharaShift MVP

**Created:** 2026-05-21
**Demo deadline:** 2026-06-07 (17 days)
**Granularity:** coarse (5 phases, parallel-friendly)
**Team:** 3 developers (이찬희 / 백은혜 / 김민주) building in parallel after Phase 0
**LLM vendor:** GCP Vertex AI (Gemini 2.5) — OpenAI 사용 안 함

## Core Value Alignment

**"내 영어 발화 스타일에 반응하는 Pally."**

Every phase exists to make the core loop (사용자 발화 → 5축 분석 → Pally 시각·말투 변화) demoable on a mobile browser by June 7. Phase 0 unblocks parallel work with minimal foundation; Phases 1A/1B/1C are the three slices of the core loop built simultaneously; Phase 2 stitches them into the demo flow.

## Phases

- [ ] **Phase 0: Foundation (Minimal)** — Next.js 스캐폴드 + 공유 타입 + `.env.example` + Supabase 클라이언트 + Tailwind. 1A/1B/1C가 즉시 시작할 수 있게 최소만 (이찬희, 0.5일)
- [ ] **Phase 1A: FE Screens & Feedback UI** — 랜딩 + 대화 + `/feedback` 페이지 UI (이찬희)
- [ ] **Phase 1B: Pally Canvas2D + Python Engine Integration** — Superformula 렌더러 + 5축 엔진 통합 ADR (백은혜)
- [ ] **Phase 1C: Voice + Feedback Backend + Supabase Schema** — Vertex AI Gemini로 `/api/chat`, `/api/feedback` + Supabase 테이블/RLS (김민주)
- [ ] **Phase 2: Integration & Demo Polish** — End-to-end wiring, Vercel deploy, demo rehearsal (전원)

## Phase Details

### Phase 0: Foundation (Minimal)
**Goal**: A/B/C 세 개발자가 본인 phase 첫 task부터 충돌 없이 병렬로 시작할 수 있도록 최소 공유 인프라만 깐다.
**Depends on**: Nothing (first phase)
**Owner**: 이찬희 (단독)
**Requirements**: SESSION-01
**Success Criteria** (what must be TRUE):
  1. 로컬에서 `npm run dev` 한 번으로 Next.js 14 App Router 앱을 띄울 수 있고, `/api/health`가 200을 반환한다
  2. `lib/types/`에 5축(`Axes`), 캐릭터 파라미터(`CharacterParams`), 메시지(`Message`), 세션(`Session`) 타입이 정의되어 있어 A/B/C 모두가 import해서 쓸 수 있다
  3. `lib/supabase/client.ts`(anon 키)가 작성되어 있고, 실제 Supabase 프로젝트 URL/anon key로 연결만 확인된다 (server.ts와 테이블은 Phase 1C에서 추가)
  4. `.env.example`에 GCP Vertex AI 키 (`GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`) / Supabase URL / anon key / service role / Reddit / DATABASE_URL 항목이 모두 명시되어 있다
  5. Tailwind CSS + `cn()` 유틸이 동작하고, 루트 page가 빈 placeholder만 렌더한다

**Plans**: TBD (1 plan, 1 wave)
**Estimated effort**: 0.5 day (2026-05-21 오후 ~ 2026-05-22 오전)
**UI hint**: minimal (scaffold만)

---

### Phase 1A: FE Screens & Feedback UI
**Goal**: 사용자가 모바일 브라우저에서 보게 될 모든 화면(랜딩·대화·피드백)이 시각적으로 완성되고, Phase 0에서 정의한 API 계약에 맞춰 호출 준비가 되어 있다.
**Depends on**: Phase 0
**Owner**: 이찬희 (FE · 디자인)
**Requirements**: MAIN-01, CHAT-01
**Success Criteria** (what must be TRUE):
  1. 모바일 폭(~360px)에서 랜딩 화면에 Pally 영역(placeholder OK) + rec 버튼이 보이고, rec 버튼을 누르면 대화 화면으로 전환된다
  2. 대화 화면에서 직전 발화/응답이 말풍선으로 표시되고, 토글로 SMS 스타일 전체 스크립트(사용자=노란색, Pally=흰색)를 열고 닫을 수 있다
  3. `/feedback` 페이지가 세션 ID 기반으로 진입 가능하고, 빈 상태/로딩/결과 3가지 상태가 렌더링된다
  4. 모든 화면이 Phase 0에서 정의한 API 응답 타입을 import해서 사용하고, mock 데이터로 화면 동작이 검증된다
  5. "AI 캐릭터와 대화 중" 라벨이 대화 화면에 상시 노출된다 (과몰입 방지)
**Plans**: TBD
**Estimated effort**: 5 days (parallel with 1B/1C)
**UI hint**: yes

---

### Phase 1B: Pally Canvas2D + Python Engine Integration
**Goal**: Canvas2D Superformula로 렌더링된 Pally가 캐릭터 파라미터 변화에 부드럽게 반응하고, 응답 대기 중에는 생각 애니메이션을 보여준다. 또한 5축 Python 엔진 통합 방식이 ADR로 확정되어 1C가 그 결정을 따를 수 있게 한다.
**Depends on**: Phase 0
**Owner**: 백은혜 (AI · 데이터)
**Requirements**: PALLY-01, PALLY-02, ENGINE-01 (engine integration portion)
**Success Criteria** (what must be TRUE):
  1. Python 엔진(`ai/analyzer.py` + `matrix_engine.py`) 통합 방식이 `docs/adr/0001-python-engine-integration.md`로 확정되어 있고 (TS 포팅 / Vercel Python serverless / subprocess / 외부 Python 서비스 중 1개), 결정된 방식으로 Next.js API route에서 샘플 문장을 입력하면 5축 점수 + CHARACTER MATRIX가 JSON으로 반환된다
  2. Canvas2D 컴포넌트가 Pally를 Superformula 도형으로 렌더링하고, 60fps에 근접하게 동작한다 (모바일 브라우저 기준)
  3. `tone_casual` / `energy_level` / `humor_level` 값을 외부에서 주입하면 Pally의 형태·색·표정이 ~300ms 안에 부드럽게 트랜지션된다 (튐 없음)
  4. "thinking" 상태가 true가 되면 Pally가 식별 가능한 로딩/생각 애니메이션을 보여주고, false가 되면 idle로 복귀한다
  5. 데모용 컨트롤 페이지에서 슬라이더로 각 축을 움직여 시각 변화를 즉시 확인할 수 있다
  6. Phase 0에서 정의한 `CharacterParams` 타입을 그대로 받아 렌더링한다 (별도 변환 레이어 없음)

**Plans**: TBD
**Estimated effort**: 5 days (parallel with 1A/1C)
**UI hint**: yes
**Task order**: ENGINE-01 ADR을 첫날 안에 끝낸다 (1C가 이 ADR을 critical input으로 기다림).

---

### Phase 1C: Voice + Feedback Backend + Supabase Schema
**Goal**: 사용자의 음성 입력이 Vertex AI Gemini로 텍스트화 → 5축 분석 → 응답 생성 → TTS까지 흐르고, 종료 후·대화 중 피드백이 동작한다. 또한 본 phase에서 사용할 Supabase `sessions`/`messages` 테이블 + `session_id` 기반 RLS를 정의한다.
**Depends on**: Phase 0 (scaffold + types + Supabase client), Phase 1B (Python 엔진 통합 ADR)
**Owner**: 김민주 (BE · Supabase)
**Requirements**: VOICE-01, VOICE-02, ENGINE-01, FB-01, FB-02, SESSION-01 (schema portion)
**LLM 벤더**: GCP Vertex AI 단일. SDK = `@google-cloud/vertexai`. STT = Gemini 2.5 native audio input, 응답 생성 = Gemini 2.5, TTS = Vertex Text-to-Speech, 인라인 한국어 힌트 = Gemini 2.5 structured output.
**Success Criteria** (what must be TRUE):
  1. Supabase에 `sessions` / `messages` 테이블이 `session_id` 기반 RLS와 함께 마이그레이션으로 생성되어 있고, 익명 세션 ID(클라이언트 UUID)로 insert/select가 정책 검사를 통과한다. `messages` 테이블은 `axes`(jsonb), `character`(jsonb), `transcript`(text), `role` 컬럼을 포함한다. `lib/supabase/server.ts`(service role, `'server-only'` import)도 본 phase에서 추가
  2. 사용자가 마이크로 영어 한 문장을 말하면 Gemini가 오디오를 직접 받아 텍스트화(STT)하고, 그 텍스트가 5축 분석 + CHARACTER MATRIX + EMA 보정을 거친 캐릭터 파라미터로 변환되어 응답 페이로드에 포함된다
  3. 같은 호출 흐름에서 Gemini가 영어 응답 텍스트를 생성하고, Vertex TTS가 그 텍스트를 음성으로 변환해 (스트리밍 또는 청크 단위로) 클라이언트에 도착한다
  4. 대화 중 Gemini가 어색한 영어 발화를 감지하면 한국어 힌트가 응답에 포함되고, 클라이언트는 이를 작은 UI 요소로 표시할 수 있는 형태(텍스트 + 위치)로 받는다
  5. 세션 종료 후 `/api/feedback` 호출 시 Gemini가 세션 전체 메시지를 일괄 분석해 표현 교정·한국어 설명·자연스러운 대안을 JSON으로 반환한다
  6. 모든 외부 API 호출은 서버 측에서만 이루어지며 (`service_role` / GCP 서비스 어카운트 JSON이 클라이언트 번들에 포함되지 않음), 호출 결과는 `messages` 테이블에 `axes`/`character` JSONB와 함께 저장된다
**Plans**: TBD
**Estimated effort**: 6 days (parallel with 1A/1B)
**Task order**: Supabase 마이그레이션 → Gemini STT(오디오 입력) → 1B ADR 도착 후 엔진 호출 → 응답 생성/TTS → `/api/feedback`.

---

### Phase 2: Integration & Demo Polish
**Goal**: 세 슬라이스가 하나의 흐름으로 합쳐져 Vercel 배포 URL에서 모바일로 데모 가능한 상태가 된다.
**Depends on**: Phase 1A, Phase 1B, Phase 1C
**Owner**: 전원
**Requirements**: DEPLOY-01
**Success Criteria** (what must be TRUE):
  1. Vercel main 브랜치에 push하면 자동 배포되고, 배포 URL을 모바일 브라우저(~360px)에서 열어 랜딩→rec→대화→피드백 전체 흐름이 끊김 없이 동작한다
  2. PRD의 3가지 데모 케이스(casual / formal / 대화 중 페르소나 드리프트) 각각에 대해 Pally의 시각·말투가 눈에 띄게 다르게 반응한다 (rehearsal 1회 이상 완료)
  3. 한 세션의 모든 메시지가 Supabase `messages`에 `axes`/`character` JSONB와 함께 저장되어 있고, `/feedback` 페이지가 해당 세션 ID로 결과를 보여준다
  4. STT/응답/TTS 평균 지연이 데모 가능 수준이며, 에러 시에는 사용자에게 명시적 메시지가 표시된다 (silent fail 없음)
  5. 발표자가 데모 디바이스 + 백업 디바이스 2대에서 동일 흐름을 재현했고, 알려진 에지 케이스 목록이 문서화되어 있다
**Plans**: TBD
**Estimated effort**: 3 days (2026-06-04 → 2026-06-06, 데모 전일 버퍼 1일 포함)
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Foundation | 0/? | Not started | - |
| 1A. FE Screens & Feedback UI | 0/? | Not started | - |
| 1B. Pally Canvas2D + Engine ADR | 0/? | Not started | - |
| 1C. Voice + Feedback BE + Schema | 0/? | Not started | - |
| 2. Integration & Demo Polish | 0/? | Not started | - |

## Coverage Validation

**v1 requirements:** 11 total
**Mapped:** 11 / 11 ✓
**Orphans:** 0

| Requirement | Phase |
|-------------|-------|
| MAIN-01 | Phase 1A |
| VOICE-01 | Phase 1C |
| VOICE-02 | Phase 1C |
| ENGINE-01 | Phase 1B (ADR + integration) + Phase 1C (consumer) |
| PALLY-01 | Phase 1B |
| PALLY-02 | Phase 1B |
| CHAT-01 | Phase 1A |
| FB-01 | Phase 1C |
| FB-02 | Phase 1C |
| SESSION-01 | Phase 0 (types) + Phase 1C (schema/RLS) |
| DEPLOY-01 | Phase 2 |

## Parallelization Plan

```
        Phase 0 (Foundation, 0.5d, 이찬희)
                         |
        +----------------+----------------+
        |                |                |
   Phase 1A (5d)   Phase 1B (5d)    Phase 1C (6d)
   (이찬희)         (백은혜)          (김민주)
        |                |                |
        |          ADR D+1 ──────► 1C uses ADR
        |                |                |
        +----------------+----------------+
                         |
                Phase 2 (Integration, 3d, 전원)
                         |
                  2026-06-07 demo
```

**Timeline check:** 0.5 (Foundation) + 6 (longest parallel slice = 1C) + 3 (Integration) = **9.5 days of critical path**, leaving ~7.5 days of buffer in the 17-day window.

**Branch strategy:** Each parallel phase on its own feature branch (`gsd/phase-1a-fe-screens`, `gsd/phase-1b-pally-canvas`, `gsd/phase-1c-voice-backend`), merged into `main` before Phase 2 starts.

---

*Roadmap created: 2026-05-21*
*Last updated: 2026-05-21 — Phase 0 minimized, OpenAI replaced with GCP Vertex AI, Supabase schema moved to Phase 1C, Python engine ADR moved to Phase 1B*
