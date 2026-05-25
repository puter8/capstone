# Phase 1A: FE Screens & Audio Shell - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-25
**Phase:** 1A — FE Screens & Audio Shell
**Areas discussed:** Mock transport / Audio capture+playback / Pally placeholder + state coverage / Session lifecycle + nav tabs

---

## Pre-discussion context loaded

- `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md` § Phase 1A, `STATE.md` (1C complete)
- Phase 0 CONTEXT (`.planning/phases/00-foundation-minimal/00-CONTEXT.md`)
- `DESIGN.md` (color/typography/spacing/motion tokens)
- `docs/plan/2026-05-25-senior-design-elevation.md` (Phase A~D plan, 13 state coverage 표)
- Figma `mvp design` canvas (node 427:2173) via Figma MCP — 6 frames + TalkButton ComponentSet + GNB

## Gray Area Selection

Initial offer of 4 gray areas:
- A. Mock transport 설계
- B. Audio capture & playback 구현
- C. Pally placeholder + 1A state coverage
- D. Session lifecycle + nav tabs routing

**User's response:** "1A는 프론트만이니까 간단하게 가자" — bypass deep discussion, take simplest defaults.

## Mid-discussion clarifications from user

- "근데 1A는 프론트만 하는 거 아냐??" → confirms FE-only, no real `/api/chat` call in 1A → mock transport locked.
- "아냐 이렇게 하기로 했어. figma mcp로 봐봐" → directs to Figma file (node 427:2173). Many UI gray areas became pre-decided (5-tab nav, layout, empty copy, history toggle, bubble pattern).
- "+ 버튼은 안 눌려도 돼, 그냥 start, stop 이랑 대화 내용만 잘 뜨면 됨" → all 5 nav tabs disabled including +; core 1A = rec start/stop + conversation rendering only.

## Decisions Recorded (simple defaults, no deep Q&A)

### A. Mock Transport
- Single `mockChat()` function as Phase 2 swap point — D-01, D-02
- 1 fixed canned fixture, 800ms fixed latency, no random/jitter, no error simulation, no TTS playback — D-03, D-04

### B. Audio Capture & Playback
- MediaRecorder with browser MIME detection (webm/opus → mp4 fallback) — D-05
- Implicit permission (first rec tap), denial = toast only — D-06, D-07
- 30s max auto-stop, no min duration check — D-08
- Blob unused in mock path, TTS playback skipped in 1A — D-09, D-10

### C. Pally Placeholder + State Coverage
- Static SVG placeholder (Figma Star4 spike export), not inside `components/pally/` (1B owns) — D-11
- TalkButton states (idle/recording/processing/speaking/error) sharing 2 visual variants from Figma — D-12
- rec state machine simplified for mock-only path — D-13
- Only 2 error UIs: permission-denied + unified catch-all — D-14
- All other senior-plan states deferred — D-15

### D. Session Lifecycle + Nav Tabs
- `crypto.randomUUID()` on first client mount, localStorage `pally:sessionId` — D-16
- All 5 nav tabs (including +) visually rendered, fully disabled, no toast, no routing — D-17
- Page refresh starts empty messages list, sessionId retained — D-18

## Claude's Discretion (delegated)

- Component directory layout, state management lib choice, Tailwind class extraction, SVG export form, MediaRecorder MIME priority order, localStorage key prefix, disabled visual styling, transition animations between states.

## Deferred Ideas

All Senior Plan items not explicitly folded into 1A above — splash, 360 variant, error states 4종 polish, friendly mic permission UX, speaking morph/waveform, A11y full audit, dark mode, app icon, onboarding, dashboard, settings, multi-tab routing, message persistence to Supabase, real STT/TTS wiring (Phase 2), Phase 1B's `Axes`/`CharacterParams` and Canvas2D renderer.

## Out of Scope (different phases)

- Real `/api/chat` call, STT upload, TTS playback → Phase 2
- Pally Canvas2D renderer → Phase 1B
- Supabase migrations, RLS → done in Phase 1C
- New-chat (+) UX, other nav tabs routing → Post-MVP / Phase 2
