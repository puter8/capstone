---
phase: 01A
plan: 01
subsystem: frontend
tags: [foundation, design-system, tokens, layout]
dependency_graph:
  requires:
    - "Phase 0 frontend scaffold (Next.js 14 App Router + Pretendard + 15 typography tokens)"
  provides:
    - "Tailwind color tokens (surface, surface-raised, primary, primary-soft, accent, text, text-secondary, text-muted, icon, border, success, warning, error, fab)"
    - "Cream surface page background applied globally on <body>"
    - "Pally product metadata (title + Korean tagline) on every route"
    - "iOS-safe mobile viewport lock (maximumScale=1, userScalable=false)"
  affects:
    - "All Phase 1A plans 02-05 (TalkButton, ChatBubble, HistorySheet, BottomNav) can now use bg-primary/text-accent/etc. without inline hex"
tech_stack:
  added: []
  patterns:
    - "Tailwind theme.extend.colors as design-token surface"
    - "Next.js 14 App Router Viewport export for mobile lock"
    - "Body-level Tailwind utilities replace globals.css CSS variables"
key_files:
  created: []
  modified:
    - frontend/tailwind.config.ts
    - frontend/app/globals.css
    - frontend/app/layout.tsx
decisions:
  - "Removed prefers-color-scheme dark block (Dark mode out of scope for MVP per DESIGN.md)"
  - "Locked userScalable=false on viewport (a11y trade-off accepted; mic permission auto-zoom prevention takes priority per CONTEXT D-06)"
  - "Body sets bg-surface text-text font-sans antialiased min-h-screen so every route inherits cream surface without per-page wiring"
metrics:
  duration_seconds: 111
  duration_human: "1m 51s"
  tasks_completed: 2
  files_modified: 3
  files_created: 0
  completed_date: "2026-05-25"
requirements: [MAIN-01]
---

# Phase 1A Plan 01: Tailwind tokens + layout shell Summary

Phase 1A foundation — wired 14 Phase 1A color tokens into Tailwind theme.extend.colors, replaced the Create-Next-App light/dark CSS variable scaffolding with a cream-surface Tailwind body shell, and locked the mobile viewport with maximumScale=1 to prevent iOS Safari auto-zoom on mic permission prompts.

## What Was Built

### Task 1 — Color tokens in Tailwind (commit `3cc4e8d`)

Added 14 color tokens to `frontend/tailwind.config.ts` under `theme.extend.colors`, removed the legacy `{ background: var(--background), foreground: var(--foreground) }` pair, and preserved the Pretendard `fontFamily.sans` chain plus all 15 typography tokens (no changes to typography per UI-SPEC "1A introduces zero new sizes").

Tokens added (hex verbatim from DESIGN.md / UI-SPEC):

| Token | Hex | Role |
|-------|-----|------|
| `surface` | `#fcf9f6` | Page background (cream) |
| `surface-raised` | `#ffffff` | Chat bubble / history sheet |
| `primary` | `#fe9012` | Pally orange — accent 10% |
| `primary-soft` | `#ffb84a` | History stripe / future hover |
| `accent` | `#00c3d0` | "YOU" teal label only |
| `text` | `#1a1a1a` | Body text |
| `text-secondary` | `#212529` | Reserved |
| `text-muted` | `#6b7280` | Timestamps / inactive labels |
| `icon` | `#33363f` | BottomNav inactive icons |
| `border` | `#e5e0d8` | BottomNav top border / panel edges |
| `success` | `#10b981` | Reserved |
| `warning` | `#f59e0b` | Reserved |
| `error` | `#ef4444` | Recording disc / inline error |
| `fab` | `#1a1a1a` | BottomNav center + disc |

Verification: `npx tsc --noEmit` exits 0, all expected hex strings present, legacy CSS-var entries gone.

### Task 2 — Cream surface + Pally layout shell (commit `221de9a`)

`frontend/app/globals.css` — collapsed to three `@tailwind` directives plus the existing `.text-balance` utility. Dropped the `:root` CSS vars (`--background`, `--foreground`) and the entire `@media (prefers-color-scheme: dark)` block since dark mode is out of scope for the June 7 demo. The body background and text color now flow through Tailwind utility classes on `<body>`, eliminating two parallel color systems.

`frontend/app/layout.tsx` — three changes:

1. `metadata`: title changed from `"Create Next App"` to `"Pally"`; description set to the Korean tagline `"내 영어 발화 스타일에 반응하는 Pally — 한국인 영어학습자를 위한 음성 회화 동반자"` (matches PROJECT.md core value).
2. New `Viewport` export with `width: "device-width"`, `initialScale: 1`, `maximumScale: 1`, `userScalable: false`. This is the Next 14 App Router pattern for separating viewport from metadata. The lock prevents iOS Safari from auto-zooming on `getUserMedia` permission prompts (CONTEXT D-06 implicit permission flow) and matches commit `a2c2bb4`'s 402px Figma viewport decision.
3. Body className: `"bg-surface text-text font-sans antialiased min-h-screen"` so every route inherits the cream background, primary text color, Pretendard font, and full-viewport height without per-page wiring. The existing Pretendard import and `<html lang="ko">` are preserved (Phase 0 lock).

Verification: `npx tsc --noEmit` exits 0; `npm run build` succeeds with no Tailwind unknown-class warnings; static page generation completes for all 7 existing routes including `/dev/pally`.

## Files Changed

| File | Change |
|------|--------|
| `frontend/tailwind.config.ts` | +16 / -2 — added 14 color tokens, removed CSS-var entries |
| `frontend/app/globals.css` | -10 / +5 — removed dark-mode block + CSS vars + body color/background rule |
| `frontend/app/layout.tsx` | +17 / -5 — Pally metadata, Viewport export, body Tailwind tokens |

## Commits

| Hash | Task | Message |
|------|------|---------|
| `3cc4e8d` | Task 1 | `feat(01A-01): wire Phase 1A color tokens into Tailwind config` |
| `221de9a` | Task 2 | `feat(01A-01): apply cream surface and Pally layout shell` |

## Verification Outcomes

- `cd frontend && npx tsc --noEmit` — exits 0
- `cd frontend && npm run build` — `✓ Compiled successfully`, `✓ Generating static pages (7/7)`, no warnings
- `grep` checks for required hex tokens — all present
- `grep` checks for forbidden artifacts (`var(--background)`, `var(--foreground)`, `prefers-color-scheme`, `--background`, `--foreground` inside globals.css) — all 0 matches
- Phase 0 contracts preserved — `"Pretendard Variable"` and `"title-1"` strings still in `tailwind.config.ts`; Pretendard CSS import still in `layout.tsx`; `<html lang="ko">` intact

Note: npm install on this worktree pulled the existing lockfile (5 vulnerabilities reported by npm audit — 1 moderate, 4 high). These pre-date this plan and are out of scope per the SCOPE BOUNDARY rule; logged here as informational only.

## Deviations from Plan

None — plan executed exactly as written. Both tasks completed in sequence, all acceptance criteria met, no auto-fix triggers fired.

## Decisions Made

- Kept `surface-raised` at pure `#ffffff` per DESIGN.md (chat bubble + history sheet fill). UI-SPEC treats this as the 30% "secondary surface" against the 60% cream.
- Body className composition order kept as `bg-surface text-text font-sans antialiased min-h-screen` to match the acceptance-criteria grep exactly. `min-h-screen` is appended (not in PLAN.md grep) to guarantee the cream surface fills the entire viewport even on short content (Task 2 plan body shows it on the same line).
- Description string includes the em-dash and Korean tagline from PROJECT.md verbatim so it remains the single source of truth for product copy at the metadata layer.

## Known Stubs

None. All tokens map to concrete hex values and the body shell is fully wired — no placeholder colors, no "coming soon" copy, no components left with empty data sources. Subsequent Phase 1A plans (02-05) will consume these tokens to build TalkButton, ChatBubble, HistorySheet, and BottomNav.

## Self-Check: PASSED

- File `frontend/tailwind.config.ts` — FOUND, contains all 14 hex tokens
- File `frontend/app/globals.css` — FOUND, free of dark-mode and CSS-var artifacts
- File `frontend/app/layout.tsx` — FOUND, contains Pally metadata + Viewport export + cream-surface body
- Commit `3cc4e8d` — FOUND in `git log`
- Commit `221de9a` — FOUND in `git log`
- `npm run build` — exited 0 with no Tailwind warnings
