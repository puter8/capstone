# STATE: Pally — CharaShift MVP

**Last updated:** 2026-05-21 (initialization)

## Project Reference

- **Core Value:** 내 영어 발화 스타일에 반응하는 Pally — 5축 분석 → Pally 시각·말투 변화 루프
- **Demo deadline:** 2026-06-07 (17 days remaining)
- **Current focus:** Phase 0 — Foundation (shared infra so A/B/C can build in parallel)
- **Source-of-truth docs:** `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `docs/mvp/PRD.md`, `docs/mvp/2026-05-midterm-qa.md`

## Current Position

- **Milestone:** MVP v1 (June 7 demo)
- **Phase:** Phase 0 — Foundation
- **Plan:** Not yet planned (`/gsd-plan-phase 0` to generate)
- **Status:** Not started
- **Progress:** ▱▱▱▱▱▱▱▱▱▱ 0 / 5 phases complete

| Phase | Status | Notes |
|-------|--------|-------|
| 0. Foundation | Not started | Critical: Python engine integration decision (ADR) |
| 1A. FE Screens & Feedback UI | Not started | Parallel, developer A |
| 1B. Pally Canvas2D Character | Not started | Parallel, developer B |
| 1C. Voice + Feedback Backend | Not started | Parallel, developer C |
| 2. Integration & Demo Polish | Not started | Depends on 1A + 1B + 1C |

## Performance Metrics

- **Requirements coverage:** 11/11 v1 requirements mapped to phases ✓
- **Critical path:** ~12 days (3 + 6 + 3); buffer ~5 days
- **Team utilization plan:** 3 developers × ~5–6d parallel slice = max throughput inside the window
- **Plans completed:** 0
- **Plans pending:** 5 phases × TBD plans

## Accumulated Context

### Key Decisions Logged

> Authoritative list lives in `.planning/PROJECT.md` "Key Decisions". Mirror here only when state changes.

- Single Vercel + Supabase stack (no FastAPI/Railway) — Pending validation in Phase 0/2
- Rule-based 5축 only for MVP — Pending validation in Phase 1C
- Dual feedback track (Gemini inline + OpenAI batch) — Pending validation in Phase 1C
- Mobile-first, anonymous sessions, no onboarding — Pending validation in Phase 2
- 5축 drives both Canvas2D visuals (1B) and GPT-4o tone prompt (1C) — Pending validation in Phase 2
- Next.js app at repo root (option A) — Pending validation in Phase 0
- Python 엔진(`ai/`) 통합 방식은 Phase 0 ADR에서 결정 — **Open, blocking Phase 1C**

### Outstanding Todos / Open Questions

- [ ] **Phase 0 — Python engine integration**: 4 후보 비교 (TS 포팅 / Vercel Python serverless / subprocess / 외부 Python 서비스) → ADR
- [ ] **Phase 0 — Supabase project**: 새 프로젝트 프로비저닝 + RLS 정책 확정 (`session_id` 기반)
- [ ] **Phase 0 — Env keys**: OpenAI, Gemini, Supabase 키 발급/등록 (사용자 확인 필요)
- [ ] **Phase 1C — Streaming strategy**: GPT-4o 텍스트 + gpt-4o-mini-tts 오디오 동시 스트리밍 방식 결정 (SSE vs ReadableStream)
- [ ] **Phase 2 — Demo device**: 데모용 모바일 디바이스 + 백업 디바이스 확정 + 네트워크 환경 사전 확인

### Blockers

- 없음 (initialization 시점). Phase 0 시작 시 외부 API 키 확보가 첫 게이트.

## Session Continuity

### Recent Sessions

| Date | Phase | Outcome |
|------|-------|---------|
| 2026-05-21 | Init | PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md created. 11/11 v1 requirements mapped to 5 phases. |

### Next Action

`/gsd-plan-phase 0` — Phase 0 (Foundation) 실행 계획 수립. 가장 시급한 결정: Python 엔진 통합 방식 ADR.

### Hand-off Notes

- Phase 0가 끝나기 전에는 A/B/C 병렬 빌드 시작 금지 (공유 타입·API 계약·DB 스키마가 합의되지 않은 상태에서 병렬 시작하면 통합 시 충돌 폭발).
- Phase 1A/1B/1C는 별도 feature branch에서 작업. 머지 순서는 1C → 1B → 1A 권장 (BE 계약 안정화 → 시각 컴포넌트 → 화면 통합).
- Phase 2는 반드시 모바일 실기기에서 검증. desktop emulator만으로 종료 처리 금지 (PROJECT.md 제약 사항).

---

*State initialized: 2026-05-21*
