---
phase: 01A-fe-screens-audio-shell
plan: 02
subsystem: ui
tags: [typescript, next.js, react, mediarecorder, mock-transport, useReducer, wire-types]

requires:
  - phase: 00-foundation-minimal
    provides: frontend/lib/types/{message,session}.ts (Message, Level), tailwind.config.ts tokens, Pretendard Variable
  - phase: 01C-voice-feedback-backend
    provides: /api/chat Pydantic response shape (status / transcript / reply / tts_audio / axes / character / character_labels / hint_ko)
provides:
  - ChatRequest / ChatResponse / Axes / CharacterParams / CharacterLabels / InlineHintKo TS interfaces
  - ConversationState + RecState (5 states) + 8 Action discriminated unions + reducer + initialState
  - Single-swap mockChat() with 800ms fixed latency and Figma-locked fixture
  - SSR-safe pickMimeType() probe (webm;codecs=opus → webm → mp4 → mp4 AAC → null)
affects:
  - 01A-03 (useRecorder + TalkButton — consumes pickMimeType + reducer)
  - 01A-04 (chat surfaces — consumes ConversationState + Message)
  - 01A-05 (page.tsx assembly — consumes everything + mockChat)
  - phase 2 (real /api/chat swap — replace mockChat body with fetch)

tech-stack:
  added: []
  patterns:
    - "Wire-type mirror: frontend types snake_case 1:1 with backend Pydantic for swap-without-translation"
    - "useReducer state machine with discriminated-union exhaustiveness ('never' default branch)"
    - "Single-export mock as Phase-2 swap point (no other ChatResponse construction in codebase)"
    - "SSR-safe browser-API guards via typeof X === 'undefined' before access"

key-files:
  created:
    - frontend/lib/types/chat.ts
    - frontend/lib/state/conversation.ts
    - frontend/lib/mocks/chat-mock.ts
    - frontend/lib/audio/pickMimeType.ts
  modified: []

key-decisions:
  - "1A defines wire-shape copies of Axes / CharacterParams inline (not character.ts) so 1A can compile without waiting on Phase 1B; Phase 2 will re-export from 1B character.ts in one line"
  - "rec/dismissError action added beyond RESEARCH spec to satisfy UI-SPEC toast tap-to-dismiss"
  - "Fixed 800ms latency, no jitter — deterministic for demo screen recordings (CONTEXT D-04)"
  - "Probe returns null instead of falling back to a hardcoded MIME — caller surfaces explicit Korean unsupported-browser toast"

patterns-established:
  - "TS strict + zero `any`: all 4 files contain zero `any` literal tokens (verified by grep)"
  - "Reducer exhaustiveness: default switch branch uses `const exhaustive: never = action` to fail compile on new Action variants"
  - "Wire boundary: snake_case fields in chat.ts mirror backend/main.py — diff with backend types is the swap-correctness gate"

requirements-completed: [MAIN-01, CHAT-01]

duration: 5min
completed: 2026-05-25
---

# Phase 01A Plan 02: Wire Types + Reducer + Mock + MIME Probe Summary

**Phase 1A data-flow backbone: 4 new files providing wire types mirroring Phase 1C `/api/chat`, a useReducer state machine covering all 5 rec states with exhaustive `never` default, a single-export `mockChat` (800ms fixed latency, Figma-locked fixture), and an SSR-safe MediaRecorder MIME probe.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-25 (worktree session)
- **Completed:** 2026-05-25
- **Tasks:** 4 / 4
- **Files created:** 4
- **Files modified:** 0

## Accomplishments

- **Wire-shape parity with Phase 1C.** `frontend/lib/types/chat.ts` declares `ChatRequest`, `ChatResponse`, `Axes`, `CharacterParams`, `CharacterLabels`, `InlineHintKo` with snake_case fields matching `backend/main.py` verbatim — Phase 2's swap requires no field renaming.
- **State machine ready for Plan 03 + 04.** `frontend/lib/state/conversation.ts` exports `RecState` (5 discriminated kinds), `ConversationState`, 8 `Action` variants, `reducer`, and `initialState`. Default branch uses `const exhaustive: never = action` so adding a new Action variant without a case statement fails the build.
- **Single Phase-2 swap point established.** `frontend/lib/mocks/chat-mock.ts` exports exactly one function `mockChat`; no `Math.random`, no `export default`, no other ChatResponse construction in the repo. Body replacement with `fetch()` is the entire Phase 2 wiring change.
- **iOS Safari + Chrome covered.** `frontend/lib/audio/pickMimeType.ts` probes 4 candidates in CONTEXT D-05 lock order with an SSR `typeof MediaRecorder === 'undefined'` guard. Returns null (caller's responsibility) instead of a silent hardcoded fallback.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire types in lib/types/chat.ts** — `b7d3512` (feat)
2. **Task 2: Reducer in lib/state/conversation.ts** — `2a7ff63` (feat)
3. **Task 3: mockChat in lib/mocks/chat-mock.ts** — `699d76d` (feat)
4. **Task 4: pickMimeType in lib/audio/pickMimeType.ts** — `0f46e6e` (feat)

## Files Created/Modified

- `frontend/lib/types/chat.ts` — 6 interfaces (ChatRequest, ChatResponse, Axes, CharacterParams, CharacterLabels, InlineHintKo) mirroring Phase 1C wire shape exactly, Level imported from session.ts
- `frontend/lib/state/conversation.ts` — RecState discriminated union (5 kinds) + ConversationState + Action (8 variants) + reducer + initialState, exhaustive never default branch
- `frontend/lib/mocks/chat-mock.ts` — Single named export `mockChat(req): Promise<ChatResponse>`, FIXED_LATENCY_MS=800, Figma-locked fixture (`"What a bummer! But don't be too sad."`, `자연스러운 표현이에요!`, `Keep it up!`), all axes/character zero, tts_audio null
- `frontend/lib/audio/pickMimeType.ts` — `pickMimeType(): string | null`, CANDIDATES = `['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/mp4;codecs=mp4a.40.2']`, SSR guard

## Decisions Made

- **`rec/dismissError` action added vs RESEARCH spec.** UI-SPEC §Copywriting Contract requires tap-to-dismiss for the inline toast; the action zeroes the error back to idle without altering messages. This is explicitly called out in the plan body (Task 2 Constraints note).
- **Wire-shape copies live inline in chat.ts, not character.ts.** Phase 1B owns `frontend/lib/types/character.ts` and 1A must not write into it. Phase 2 will reconcile via re-export. The chat.ts comment block documents this lock for the reconciliation agent.
- **`pickMimeType()` returns null on failure rather than a hardcoded MIME.** CLAUDE.md §6 #3 forbids silent fallback; the caller (Plan 03) is expected to surface the Korean unsupported-browser inline toast per UI-SPEC.

## Deviations from Plan

None — plan executed exactly as written.

(Note: `npm install` was required at the start to populate `frontend/node_modules/` for `tsc` to resolve. This is a worktree-setup step, not a code deviation, and `package.json` / `package-lock.json` were not modified.)

## Issues Encountered

- **Worktree branch base mismatch.** The orchestrator's expected base hint (`c1f18db`) was an ancestor of the actual Phase 1A branch tip (`a597528` — the commit that ships the 5 PLAN.md files). The worktree HEAD was instead at `60709ad` (post-1B `main`). Resolved with `git reset --hard a597528` (Phase 1A branch tip) before reading the plan. No code lost. Recorded here so the orchestrator can update its base-hint logic if needed.
- **`typescript` not pre-installed in worktree node_modules.** Ran `npm install` once to populate `frontend/node_modules/`; `package-lock.json` was unchanged.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Wave 1 (Plan 02) backbone is ready for Wave 2 consumers:

- **Plan 01A-03 (useRecorder + TalkButton):** imports `pickMimeType` from `lib/audio/`, imports `reducer` / `RecState` / `Action` from `lib/state/conversation`.
- **Plan 01A-04 (chat surfaces):** imports `ConversationState` + `Message` + reducer dispatch.
- **Plan 01A-05 (page.tsx assembly):** imports `mockChat`, `reducer`, `initialState`, ties everything to the main screen.

No blockers. All verification + success criteria pass:

- `cd frontend && npx tsc --noEmit` → exit 0
- `cd frontend && npm run build` → ✓ Compiled successfully, 6 static pages generated
- `grep -rE 'any( |;|\)|>)' lib/{types/chat,state/conversation,mocks/chat-mock,audio/pickMimeType}.ts` → no matches
- `grep -r "Math.random" frontend/lib/` → no matches

## Self-Check: PASSED

- FOUND: `frontend/lib/types/chat.ts`
- FOUND: `frontend/lib/state/conversation.ts`
- FOUND: `frontend/lib/mocks/chat-mock.ts`
- FOUND: `frontend/lib/audio/pickMimeType.ts`
- FOUND commit: `b7d3512` (Task 1)
- FOUND commit: `2a7ff63` (Task 2)
- FOUND commit: `699d76d` (Task 3)
- FOUND commit: `0f46e6e` (Task 4)

---

*Phase: 01A-fe-screens-audio-shell*
*Plan: 02*
*Completed: 2026-05-25*
