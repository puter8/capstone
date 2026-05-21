# STATE: Pally — CharaShift MVP

**Last updated:** 2026-05-21 (synchronized to ROADMAP.md)

## Project Reference

- **Core Value:** 내 영어 발화 스타일에 반응하는 Pally — 5축 분석 → Pally 시각·말투 변화 루프
- **Demo deadline:** 2026-06-07 (17 days from roadmap creation)
- **Current focus:** Phase 0 — Foundation (minimal frontend scaffold so 1A/1B/1C can build in parallel)
- **Planning source of truth:** `.planning/ROADMAP.md`
- **Synchronized planning docs:** `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`
- **Background docs only:** `docs/mvp/PRD.md`, `docs/mvp/2026-05-midterm-qa.md`

## Current Position

- **Milestone:** MVP v1 (June 7 demo)
- **Phase:** Phase 0 — Foundation (Minimal)
- **Plan:** Not yet planned (`/gsd-plan-phase 0` to generate)
- **Status:** Not started
- **Progress:** ▱▱▱▱▱ 0 / 5 phases complete

| Phase | Status | Notes |
|-------|--------|-------|
| 0. Foundation (Minimal) | Not started | Next.js scaffold in `frontend/`, minimal UI types, Supabase anon client, Tailwind, env example |
| 1A. FE Screens & Audio Shell | Not started | Parallel after Phase 0; 메인 화면 + rec/audio mock transport |
| 1B. Pally Canvas2D + Python Engine Integration | Not started | Parallel after Phase 0; Pally renderer + character types + D+1 engine ADR |
| 1C. Voice + Inline Feedback Backend + Supabase Schema | Not started | Parallel after Phase 0; FastAPI `/api/chat`, GCP STT/TTS/Gemini, Supabase schema/RLS |
| 2. Integration & Demo Polish | Not started | Depends on 1A + 1B + 1C; Vercel/Railway real wiring + mobile rehearsal |

## Performance Metrics

- **Requirements coverage:** 11/11 v1 requirements mapped to phases ✓
- **Critical path:** 0.5d Phase 0 + 6d longest parallel slice + 3d integration = ~9.5 days
- **Buffer:** ~7.5 days inside the 17-day window
- **Team utilization plan:** 3 developers build 1A/1B/1C in parallel after Phase 0
- **Plans completed:** 0
- **Plans pending:** 5 phases × TBD plans

## Accumulated Context

### Key Decisions Logged

> Authoritative list lives in `.planning/PROJECT.md` "Key Decisions". Mirror here only when state changes.

- Monorepo split: `frontend/` (Vercel), `backend/` (Railway FastAPI), `ai/` (Python engine) — Accepted
- LLM/voice vendor: GCP only (Gemini 2.5 Flash + Google Cloud STT/TTS), no OpenAI in MVP — Accepted
- `/feedback` UI removed from MVP; feedback is inline structured payload from `/api/chat` — Accepted
- Phase 0 is minimal foundation only; Supabase schema/RLS moves to Phase 1C — Accepted
- Python engine integration ADR moves to Phase 1B and must be available D+1 for 1C — Accepted
- 1A/1B/1C remain parallel; 1C consumes only the D+1 ADR, not full 1B completion — Accepted
- 김민주 owns `ai/`, `frontend/components/pally/`, `frontend/app/dev/pally/`, `frontend/lib/types/character.ts` — Accepted
- MVP uses rule-based 5-axis engine with EMA alpha=0.7 for visible demo response — Accepted
- No onboarding in MVP; sessions use default `character_name = 'Pally'`, `level = 'B1'` — Accepted

### Outstanding Todos / Open Questions

- [ ] **Phase 0 — frontend scaffold**: Create Next.js 14 App Router under `frontend/`, Tailwind, `cn()`, placeholder `frontend/app/page.tsx`, `/api/health`
- [ ] **Phase 0 — minimal UI types**: Define only `Message` and `Session` for 1A mock UI. Do not define `Axes`/`CharacterParams` yet
- [ ] **Phase 0 — Supabase client/env**: Add `frontend/lib/supabase/client.ts` and `frontend/.env.example` with frontend keys only
- [ ] **Phase 1A — audio shell**: Browser permission request, recording Blob, mock transport, sample/mock audio playback, state machine
- [ ] **Phase 1B — Python engine ADR**: Decide FastAPI direct import / subprocess / external Python service / TS port; produce `docs/adr/0001-python-engine-integration.md` by D+1
- [ ] **Phase 1C — GCP preflight**: Before implementation, perform real Google Cloud STT/TTS/Gemini test calls and confirm response shape/latency
- [ ] **Phase 1C — Supabase schema**: Create `sessions`/`messages` tables with `session_id` RLS, `character_name`, `level`, `axes`, `character`
- [ ] **Phase 2 — mobile demo**: Verify deployed Vercel + Railway URLs on demo device and backup device

### Blockers

- No active blocker at planning level.
- Phase 1C will need GCP service account credentials, Supabase URL/service role, and Railway environment setup before real integration can pass.

## Session Continuity

### Recent Sessions

| Date | Phase | Outcome |
|------|-------|---------|
| 2026-05-21 | Init | Initial PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md created. |
| 2026-05-21 | Roadmap review | ROADMAP.md updated to GCP-only, Vercel/Railway split, `/feedback` UI removed, 1A audio shell + 1C backend + Phase 2 wiring split, 1A/1B/1C parallelism preserved. |
| 2026-05-21 | Planning sync | PROJECT.md, REQUIREMENTS.md, STATE.md synchronized to ROADMAP.md. |

### Next Action

`/gsd-plan-phase 0` — Phase 0 (Foundation Minimal) 실행 계획 수립.

### Hand-off Notes

- Phase 0가 끝나면 1A/1B/1C를 병렬 시작한다. 1C는 1B 전체 머지를 기다리지 않고 D+1 engine ADR만 받아 진행한다.
- 1A와 1B 모두 `frontend/`를 만지므로 ownership을 지킨다: 1A는 메인 화면/audio shell, 1B는 Pally renderer/demo/type file.
- Phase 1C는 FastAPI/Python 기준이다. Node `@google-cloud/*` 패키지나 Next.js API route 백엔드 구현으로 되돌리지 않는다.
- Phase 2는 mock audio transport를 실제 Railway `/api/chat`으로 교체하고, 모바일 실기기에서 녹음 Blob 업로드 + TTS 재생까지 검증한다.
- `/feedback` route/page는 MVP에서 만들지 않는다. 한국어 힌트/피드백은 메인 화면 inline payload로만 처리한다.

---

*State initialized: 2026-05-21*
*Last synchronized: 2026-05-21 — ROADMAP.md is the baseline*
