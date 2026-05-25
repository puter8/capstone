---
phase: 01A-fe-screens-audio-shell
plan: 03
subsystem: ui
tags: [react, hooks, mediarecorder, audio, tailwind, talkbutton, accessibility]

requires:
  - phase: 01A-fe-screens-audio-shell
    provides: "design tokens (primary/error/shadow), Tailwind config (Plan 01)"
  - phase: 01A-fe-screens-audio-shell
    provides: "RecState discriminated union, pickMimeType MIME probe (Plan 02)"
provides:
  - "useRecorder hook (getUserMedia + MediaRecorder + 30s auto-stop + track cleanup)"
  - "TalkButton 5-state visual component (96px disc + 132px ring) wired to RecState"
affects: [01A-05 (main screen composition that imports TalkButton + useRecorder)]

tech-stack:
  added: []
  patterns:
    - "Hook-of-callbacks: useRecorder accepts RecorderHandlers, never throws, never swallows"
    - "Component-of-state: TalkButton is stateless re: rec, parent reducer owns transitions"
    - "Tailwind token discipline: bg-primary / bg-error / bg-primary/[0.18], no raw hex in JSX"

key-files:
  created:
    - "frontend/lib/audio/useRecorder.ts"
    - "frontend/components/audio/TalkButton.tsx"
  modified: []

key-decisions:
  - "useRecorder accepts handlers (onStart/onStop/onPermissionDenied/onError) rather than returning state — keeps the reducer in conversation.ts as the single source of rec state"
  - "TalkButton disables the disc during processing/speaking (visually identical to recording) to prevent double-fire of onPressStop while async work is in flight"
  - "30s auto-stop timer is cleared inside stop() BEFORE calling MediaRecorder.stop() (Pitfall 5) to avoid double-stop DOMException"
  - "MediaStream tracks released inside MediaRecorder.onstop (Pitfall 4) so the browser red mic indicator clears synchronously with UI"

patterns-established:
  - "Browser-API hooks: 'use client' at top, useRef for all mutable handles, useCallback for stable controls, no useEffect auto-start (caller drives)"
  - "Permission-aware error routing: DOMException.name === 'NotAllowedError' | 'PermissionDeniedError' → onPermissionDenied; all other errors → onError(fixed Korean string). Raw err.message is never forwarded to UI (T-01A-03-06)"

requirements-completed: [MAIN-01]

duration: ~18min
completed: 2026-05-25
---

# Phase 01A Plan 03: Audio Shell (useRecorder + TalkButton) Summary

**MediaRecorder hook with 30s auto-stop and 5-state TalkButton wired to RecState, all CONTEXT D-05~D-12 + RESEARCH Pitfall 4/5 mitigations applied.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-25T07:18:00Z (approx, plan launch)
- **Completed:** 2026-05-25T07:36:25Z
- **Tasks:** 2
- **Files modified:** 2 (both new)

## Accomplishments

- `useRecorder` hook that requests mic via `getUserMedia`, picks a supported MIME via the Plan 02 probe, drives `MediaRecorder`, auto-stops at 30s, and releases `MediaStream` tracks on stop so the browser mic indicator clears.
- Permission denial cleanly separated from generic mic errors — `onPermissionDenied` vs `onError(fixed Korean string)`. No empty catch, no silent fallback.
- `TalkButton` renders the 5-state mic visual from CONTEXT D-12: orange disc + mic icon for `idle`/`error`, red disc + rounded stop square for `recording`/`processing`/`speaking`. Processing/speaking share the recording visual but the disc is disabled to prevent double-fire of `onPressStop` while async work is in flight.
- All 4 distinct Korean aria-labels (`녹음 시작`, `녹음 정지`, `처리 중`, `Pally가 응답 중`) wired off `rec.kind`.
- 132px decorative ring + 96px hit-target disc (`w-24 h-24`) + `shadow-lg` elevation, `active:scale-95 duration-150` press feedback per DESIGN.md § Motion.
- `npx tsc --noEmit` and `npm run build` both pass.

## Task Commits

Each task was committed atomically (parallel worktree — `--no-verify` on all commits):

1. **Task 1: useRecorder hook at frontend/lib/audio/useRecorder.ts** — `5c0917c` (feat)
2. **Task 2: TalkButton component at frontend/components/audio/TalkButton.tsx** — `e041068` (feat)

## Files Created/Modified

- `frontend/lib/audio/useRecorder.ts` (created) — Hook returning `{ start, stop }`. Permission/MIME/timer/cleanup all handled. Imports `pickMimeType` from Plan 02.
- `frontend/components/audio/TalkButton.tsx` (created) — 5-state visual mic toggle. Imports `RecState` (type-only) from `@/lib/state/conversation` and `cn` from `@/lib/utils`. Inline SVGs (no `lucide-react`).

## Decisions Made

- **Handlers vs returned state:** `useRecorder` takes callbacks rather than returning current rec state. The conversation reducer (Plan 02) is the single source of truth; Plan 05 will dispatch from the handlers.
- **Processing/speaking disable disc:** Visually identical to recording per D-12, but `disabled` is set so a second tap can't fire `onPressStop` twice during async work (mitigates T-01A-03-04 in the threat model).
- **MAX_DURATION_MS as module-private constant** (not a hook prop) — D-08 specifies 30s and Phase 2 will tighten/loosen it across the whole app, not per call site.
- **`for...of` over `forEach` when releasing tracks** — avoids the implicit `void`-callback shape; clearer linear ordering during cleanup.

## Deviations from Plan

None — plan executed exactly as written. The plan's `<action>` block included a verbatim code skeleton; both files implement it 1:1 with the constraints (no `any`, no empty catch, no silent fallback, no raw hex, no `opacity-50`).

## Issues Encountered

- **`frontend/node_modules` missing in this worktree.** The worktree was fresh, so `npx tsc --noEmit` initially refused (npx tried to fetch tsc from the registry). Resolved by running `npm install` once; lockfile was already committed so no new lockfile drift. Both `tsc --noEmit` and `next build` then passed cleanly.

## User Setup Required

None — no external service configuration.

## Threat Model Verification

All `mitigate` dispositions in the plan's `<threat_model>` are implemented:

| Threat ID | Mitigation | Verified |
|-----------|------------|----------|
| T-01A-03-01 | `stream.getTracks().forEach(t => t.stop())` inside `onstop` | grep + code review |
| T-01A-03-02 | `stop()` clears `timerRef` and guards `state !== 'inactive'` before `MediaRecorder.stop()` | grep + code review |
| T-01A-03-03 | `try/catch` routes `NotAllowedError`/`PermissionDeniedError` to `onPermissionDenied`, everything else to `onError(fixed Korean string)` | grep + code review |
| T-01A-03-04 | `isInteractive` guard + `disabled` attribute on disc during processing/speaking | code review |
| T-01A-03-05 | All 4 aria-label strings are compile-time literals (no user input) | code review |
| T-01A-03-06 | Raw `err.message` never forwarded to UI; only fixed Korean strings | code review |

## Next Phase Readiness

- Plan 05 can now `import { useRecorder } from '@/lib/audio/useRecorder'` and `import { TalkButton } from '@/components/audio/TalkButton'` and wire them to the conversation reducer with no further audio work needed.
- No imports from `frontend/components/pally/*` or `frontend/lib/types/character.ts` — Phase 1B owner boundary preserved.

## Self-Check: PASSED

- `frontend/lib/audio/useRecorder.ts` — FOUND
- `frontend/components/audio/TalkButton.tsx` — FOUND
- Commit `5c0917c` — FOUND
- Commit `e041068` — FOUND

---
*Phase: 01A-fe-screens-audio-shell*
*Completed: 2026-05-25*
