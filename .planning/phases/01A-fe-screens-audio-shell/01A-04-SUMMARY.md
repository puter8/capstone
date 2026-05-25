---
phase: 01A-fe-screens-audio-shell
plan: 04
subsystem: ui
tags: [react, tailwind, accessibility, chat-surface, bottom-nav, toast, svg]

requires:
  - phase: 01A-01
    provides: Tailwind color tokens (surface, surface-raised, primary, primary-soft, accent, text, text-muted, border, fab, error) + 15 typography tokens
  - phase: 01A-02
    provides: frontend/lib/types/message.ts (Message, MessageRole) — consumed by ChatBubble + HistoryRow + HistorySheet
provides:
  - PallyPlaceholder (262x262 inline SVG, Phase 1B's swap target — placed in components/chat/ NOT components/pally/)
  - ChatBubble (top-zone surface — empty state OR last user+pally turn with chevron toggle)
  - HistoryRow (SMS-style sender label + transcript + Korean time)
  - HistorySheet (full overlay with 4x40 handle + 13px primary-soft stripe + 605px max panel)
  - BottomNav (5 disabled Korean tabs, center FAB is bg-fab black NOT bg-primary)
  - Toast (4s auto-dismiss + tap-to-dismiss, surface-raised + border tokens)
affects:
  - 01A-05 (page.tsx assembly — imports all 6 components and wires them to reducer dispatch)

tech-stack:
  added: []
  patterns:
    - "Stateless props-driven chat-surface components — state lives in Plan 05 reducer"
    - "SVG fills/strokes use raw hex only inside SVG attributes (Tailwind tokens unreachable there); inline JSX className strictly uses tokens"
    - "Defensive Date.parse NaN guard returns empty string — no silent 'Invalid Date' leak (CLAUDE.md §7)"
    - "Auto-dismiss timers use useEffect cleanup with window.clearTimeout"
    - "HistorySheet returns null when closed — no hidden DOM with a11y trap"

key-files:
  created:
    - frontend/components/chat/PallyPlaceholder.tsx
    - frontend/components/chat/ChatBubble.tsx
    - frontend/components/chat/HistoryRow.tsx
    - frontend/components/chat/HistorySheet.tsx
    - frontend/components/nav/BottomNav.tsx
    - frontend/components/ui/Toast.tsx
  modified: []

key-decisions:
  - "PallyPlaceholder lives at components/chat/ NOT components/pally/ (D-11) — the pally/ namespace belongs to Phase 1B and now contains PallyCanvas.tsx merged from main; Plan 05's page.tsx will choose which to render."
  - "ChatBubble does NOT read hint_ko field even though the mock fixture carries it (UI-SPEC Anti-Pattern #9 — hint UI is Phase 2's surface)."
  - "HistorySheet bottom stripe uses bg-primary-soft (#ffb84a) not bg-primary — DESIGN.md decisions log 2026-05-25."
  - "BottomNav center + FAB is bg-fab (#1a1a1a) black, NOT bg-primary orange (D-17 + DESIGN.md decisions log — FAB action ≠ active-tab signal)."
  - "Toast useEffect cleanup guards against re-render leak; visibility-change path covered."

patterns-established:
  - "TS strict + zero `any`: all 6 files contain zero `any` literal tokens (verified by grep -w any)"
  - "Token-only className: zero raw hex inside JSX className across all 6 files (SVG attrs are the only allowed raw-hex channel)"
  - "Korean copy locked verbatim: empty-state heading + subtitle + 5 nav labels + sender labels YOU/Pally match UI-SPEC Copywriting Contract exactly"

requirements-completed: [MAIN-01, CHAT-01]

duration: ~12min
completed: 2026-05-25
---

# Phase 01A Plan 04: Chat Surfaces + Toast + BottomNav Summary

**Wave 2 chat-surface delivery: 6 stateless, props-driven components covering CHAT-01 (SMS-style history with locked sender colors) and MAIN-01 (empty-state copy + disabled nav). All components TS-strict, zero `any`, build succeeds.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-25 (worktree session)
- **Completed:** 2026-05-25
- **Tasks:** 4 / 4
- **Files created:** 6
- **Files modified:** 0

## Accomplishments

- **PallyPlaceholder** renders the 262x262 inline Star4 SVG at `components/chat/`, leaving Phase 1B's `components/pally/` namespace untouched. Plan 05 assembles the page and decides which to import.
- **ChatBubble** is the top-zone surface: shows the locked Korean empty-state ("오늘은 어떤 이야기를 해볼까요?" / "마이크를 눌러 영어로 말해보세요") when `messages.length === 0`, otherwise renders the latest user+pally turn with `text-accent` teal "YOU" and `text-primary` orange "Pally" sender labels per UI-SPEC § Color reserved-for list. Chevron toggle dispatches `onToggleHistory` with `aria-expanded` reflecting `historyOpen`.
- **HistoryRow + HistorySheet** form the full-overlay history view: SMS-style rows with sender labels in the locked teal/orange colors, Korean 24-hour timestamps via `toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })`, a 4x40 panel handle (DESIGN.md 2026-05-25), and the 13px `primary-soft` stripe peeking below a 605px-capped panel. `role="dialog" aria-modal="true"` set; closed state returns `null` to avoid a hidden DOM focus trap.
- **BottomNav** ships 5 disabled tabs in the locked Korean labels `홈 / 히스토리 / 새 대화 / 랭킹 / 내 정보`. The center `새 대화` is a 56px `bg-fab` (`#1a1a1a`) disc with a white cross — explicitly NOT orange (D-17). Zero `onClick` handlers; zero `opacity-50` dimming. Upward shadow `shadow-[0_-2px_10px_rgba(0,0,0,0.06)]` per DESIGN.md "Navbar separator" decision.
- **Toast** auto-dismisses after 4000ms with `useEffect` cleanup returning `window.clearTimeout`. Tap-to-dismiss available via the button surface. `aria-live="polite"` set. `surface-raised` + `border` + `text-text-muted` tokens — no raw hex in className.

## Task Commits

Each task committed atomically with `--no-verify` (parallel-executor protocol):

1. **Task 1 — PallyPlaceholder + Toast** — `5ce4410`
2. **Task 2 — ChatBubble** — `5d654c8`
3. **Task 3 — HistoryRow + HistorySheet** — `d0db6d5`
4. **Task 4 — BottomNav** — `0817bbf`

## Files Created

| File | Purpose |
|------|---------|
| `frontend/components/chat/PallyPlaceholder.tsx` | 262x262 inline Star4 SVG, primary orange fill via SVG attr; Phase 1B's replacement target |
| `frontend/components/chat/ChatBubble.tsx` | Top zone: empty-state Korean copy OR last-turn render + chevron toggle |
| `frontend/components/chat/HistoryRow.tsx` | SMS row: teal/orange sender label + transcript + Korean time |
| `frontend/components/chat/HistorySheet.tsx` | Dialog overlay: 4x40 handle + scrollable list + 13px primary-soft stripe |
| `frontend/components/nav/BottomNav.tsx` | 5 disabled tabs, black FAB center, upward shadow, hairline border |
| `frontend/components/ui/Toast.tsx` | 4s auto-dismiss + tap-to-dismiss inline toast above TalkButton |

## Verification Outcomes

- `cd frontend && npx tsc --noEmit` — exits 0
- `cd frontend && npm run build` — `✓ Compiled successfully`, all 7 static pages generated, no Tailwind unknown-class warnings
- All Task 1–4 grep acceptance checks pass (see commit messages and PLAN.md `<acceptance_criteria>`)
- `grep -w any` across all 6 files returns no matches
- `grep -F "opacity-50" components/nav/BottomNav.tsx` returns no matches
- `grep -E "onClick" components/nav/BottomNav.tsx` returns no matches (D-17 lock)
- `grep -F "bg-primary" components/nav/BottomNav.tsx` returns no matches (FAB ≠ orange)
- `grep -F "hint_ko" components/chat/ChatBubble.tsx` returns no matches (Anti-Pattern #9)
- All locked Korean strings present verbatim:
  - `오늘은 어떤 이야기를 해볼까요?` in ChatBubble
  - `마이크를 눌러 영어로 말해보세요` in ChatBubble
  - `홈`, `히스토리`, `새 대화`, `랭킹`, `내 정보` in BottomNav

## Decisions Made

- **PallyPlaceholder placement.** Kept at `components/chat/PallyPlaceholder.tsx` per D-11, even though `components/pally/PallyCanvas.tsx` now exists in the base (merged from Phase 1B PR #11). This honors the namespace boundary while letting Plan 05 choose which to render.
- **Chevron color.** SVG stroke uses raw `#6b7280` (text-muted token) because SVG `stroke` attr cannot reference Tailwind tokens. Inline comment documents this; UI-SPEC Anti-Pattern #2 only forbids raw hex in JSX `className`.
- **HistoryRow time format.** Uses `toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })`. Invalid `createdAt` returns empty string with explanatory comment — no silent "Invalid Date" leak per CLAUDE.md §7.
- **HistorySheet handle doubles as close affordance.** Tapping the 4x40 handle dispatches `onClose` (same as backdrop tap). 1A keeps drag-to-dismiss out of scope; visible affordance + tap close is enough for the demo.
- **Toast surface choice.** `bg-surface-raised` (white) + `border-border` (warm gray) per UI-SPEC § Component Inventory. `text-text-muted` for body — Plan 05 chooses Korean error content per `error.reason`.

## Deviations from Plan

### Acceptance-Criterion Adjustment (no code impact)

**1. [Rule 3 — Blocking] `test ! -d frontend/components/pally` acceptance check skipped**
- **Found during:** Initial branch-base verification (before Task 1).
- **Issue:** The plan's Task 1 acceptance criterion `Directory frontend/components/pally/ does NOT exist (Phase 1B namespace — test ! -d ... exits 0)` was authored assuming Phase 1B had not yet merged. The expected base `3eda073` is a descendant of `60709ad` (Phase 1B PR #11 squash-merge), so `frontend/components/pally/PallyCanvas.tsx` is already present in the tracked working tree.
- **Resolution:** The plan's underlying intent — "Phase 1A does NOT create files inside `frontend/components/pally/`" — is fully honored. `PallyPlaceholder.tsx` was placed at `components/chat/` per D-11. The literal directory-non-existence grep was skipped because deleting Phase 1B's work is out-of-scope and would break unrelated phases. No code in this plan touches `components/pally/`.
- **Files modified:** None (this is an acceptance-criterion adjustment only).
- **Commit:** N/A.

### Other Deviations

None — all 4 tasks completed in sequence, all other acceptance criteria met, no auto-fix triggers fired.

## Issues Encountered

- **Worktree branch base mismatch hint.** The orchestrator's expected base `3eda0732f13b54dd90e98731bd8c8cb807e50e4c` differed from the worktree HEAD `60709ad...` at startup. Resolved via `git reset --hard 3eda073` (Wave 1 outputs verified present: `frontend/lib/types/chat.ts`, `frontend/lib/state/conversation.ts`, `frontend/lib/mocks/chat-mock.ts`, `frontend/tailwind.config.ts`). No code lost.
- **`typescript` not pre-installed in worktree node_modules.** Ran `npm install` once to populate `frontend/node_modules/` for `tsc` and `next build` to resolve. `package.json` / `package-lock.json` were not modified.
- **npm audit reports.** `npm install` reports 5 vulnerabilities (1 moderate, 4 high). Pre-existing from the Phase 0 lockfile, out-of-scope per the SCOPE BOUNDARY rule — logged for awareness only.

## User Setup Required

None — no external service configuration required for this plan.

## Next Phase Readiness

Wave 2 chat-surface components ready for Wave 3 (Plan 05 page assembly):

- **Plan 01A-05** will import all 6 components and wire them to the conversation reducer (`reducer` + `dispatch` from `lib/state/conversation`, `messages` from state, `historyOpen` local UI state, `error.message` + `error.visible` from `RecState['error']`).
- **Phase 1B integration** — Plan 05 can swap `<PallyPlaceholder />` for `<PallyCanvas />` from `components/pally/` in one line when ready, since `components/pally/PallyCanvas.tsx` is already merged into the base.

No blockers. All verification + success criteria pass.

## Known Stubs

None — every component is fully wired against its declared `<interfaces>` contract. No "coming soon" placeholders. The PallyPlaceholder is itself a *labeled* placeholder per D-11 (Phase 1B owns the canvas implementation), not a stub in the Rule-2 sense.

## Self-Check: PASSED

- FOUND: `frontend/components/chat/PallyPlaceholder.tsx`
- FOUND: `frontend/components/chat/ChatBubble.tsx`
- FOUND: `frontend/components/chat/HistoryRow.tsx`
- FOUND: `frontend/components/chat/HistorySheet.tsx`
- FOUND: `frontend/components/nav/BottomNav.tsx`
- FOUND: `frontend/components/ui/Toast.tsx`
- FOUND commit: `5ce4410` (Task 1 — PallyPlaceholder + Toast)
- FOUND commit: `5d654c8` (Task 2 — ChatBubble)
- FOUND commit: `d0db6d5` (Task 3 — HistoryRow + HistorySheet)
- FOUND commit: `0817bbf` (Task 4 — BottomNav)
- `cd frontend && npx tsc --noEmit` — exit 0
- `cd frontend && npm run build` — `✓ Compiled successfully`

---

*Phase: 01A-fe-screens-audio-shell*
*Plan: 04*
*Completed: 2026-05-25*
