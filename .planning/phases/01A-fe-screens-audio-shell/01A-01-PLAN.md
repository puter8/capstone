---
phase: 01A
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/tailwind.config.ts
  - frontend/app/globals.css
  - frontend/app/layout.tsx
autonomous: true
requirements: [MAIN-01]
must_haves:
  truths:
    - "Tailwind config exposes the Phase 1A color tokens (surface, surface-raised, primary, primary-soft, accent, error, text, text-muted, icon, border) as utility classes"
    - "Page background is the warm cream (#fcf9f6) — visible on mobile"
    - "Pretendard Variable is the active font family across body text"
    - "Viewport meta locks initial-scale=1 with maximum-scale=1 so iOS Safari does not auto-zoom on focus"
  artifacts:
    - path: "frontend/tailwind.config.ts"
      provides: "Color tokens in theme.extend.colors matching DESIGN.md + 01A-UI-SPEC.md"
      contains: "primary"
    - path: "frontend/app/globals.css"
      provides: "Cream surface as html/body background — replaces light/dark CSS vars"
      contains: "#fcf9f6"
    - path: "frontend/app/layout.tsx"
      provides: "Korean lang + viewport meta + Pally metadata + font-sans body"
      contains: "Pally"
  key_links:
    - from: "frontend/tailwind.config.ts"
      to: "any JSX className"
      via: "Tailwind JIT generation"
      pattern: "bg-surface|bg-primary|text-accent|text-error|border-border"
    - from: "frontend/app/layout.tsx"
      to: "all pages"
      via: "App Router root layout"
      pattern: "html lang=\"ko\""
---

<objective>
Wave 1 foundation — Tailwind 토큰 + layout shell.
Phase 1A의 모든 후속 plan(02~05)이 의존하는 컬러 시스템과 layout 베이스를 깐다. DESIGN.md `Implementation Status` ⏳ 상태인 color/spacing 토큰을 `tailwind.config.ts`에 wire하고, `globals.css`의 light/dark CSS vars(현재 흰 배경/검정 텍스트)를 Pally cream surface로 교체한다. `app/layout.tsx`의 placeholder metadata(`"Create Next App"`)를 Pally 메타데이터로 교체하고 모바일 viewport meta를 추가한다.

Purpose: 후속 plan들이 hardcoded hex(`#fe9012` 등) 없이 `bg-primary`, `text-accent` 같은 토큰으로 작업할 수 있게 한다. UI-SPEC § Anti-Patterns #2가 "inline raw hex in JSX 금지"를 명시하므로 이 plan 없이 다른 plan을 시작하면 anti-pattern violation 발생.

Output: tailwind.config.ts 토큰 확장, cream surface가 적용된 globals.css, Pally metadata + viewport meta가 적용된 layout.tsx.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md
@.planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md
@DESIGN.md
@frontend/tailwind.config.ts
@frontend/app/globals.css
@frontend/app/layout.tsx
</context>

<interfaces>
<!-- Existing Tailwind config (frontend/tailwind.config.ts) -->
<!-- fontFamily.sans = Pretendard Variable + fallback chain (LOCKED, do NOT touch) -->
<!-- fontSize tokens: title-1 / title-2 / subtitle-sb / subtitle / body-sb / body / body-2-sb / body-2 / button-1..4 / caption-1 / caption-2 (LOCKED, do NOT add new sizes) -->
<!-- Existing theme.extend.colors: { background: var(--background), foreground: var(--foreground) } — REMOVE these two and add the Phase 1A palette below -->

<!-- Color tokens to add (verbatim hex from DESIGN.md § Color + 01A-UI-SPEC.md § Color) -->
<!--
  surface         = #fcf9f6   (warm cream, page background)
  surface-raised  = #ffffff   (bubble + history sheet)
  primary         = #fe9012   (Pally orange — accent 10%)
  primary-soft    = #ffb84a   (history stripe + future hover)
  accent          = #00c3d0   (YOU teal label only)
  text            = #1a1a1a   (body text)
  text-secondary  = #212529   (reserved)
  text-muted      = #6b7280   (timestamps, muted captions, BottomNav inactive labels)
  icon            = #33363f   (BottomNav inactive icons)
  border          = #e5e0d8   (BottomNav top border + history panel edges)
  success         = #10b981
  warning         = #f59e0b
  error           = #ef4444   (recording disc + inline generic error)
  fab             = #1a1a1a   (BottomNav center + disc — distinct from active orange)
-->
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add Phase 1A color tokens to Tailwind config</name>
  <files>frontend/tailwind.config.ts</files>
  <read_first>
    - frontend/tailwind.config.ts (current state — Phase 0 shipped fontFamily.sans + 15 fontSize tokens; do not modify those)
    - DESIGN.md § Color (hex values authoritative)
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § Color (60/30/10 split + reserved-for list)
  </read_first>
  <action>
    `frontend/tailwind.config.ts`의 `theme.extend.colors`에서 기존 `{ background: var(--background), foreground: var(--foreground) }` 두 줄을 **제거하고**, 다음 14개 token을 추가한다. 모든 값은 `<interfaces>` 블록의 hex와 정확히 일치해야 한다 (DESIGN.md verbatim). per D-12, D-14.

    ```typescript
    colors: {
      surface: "#fcf9f6",
      "surface-raised": "#ffffff",
      primary: "#fe9012",
      "primary-soft": "#ffb84a",
      accent: "#00c3d0",
      text: "#1a1a1a",
      "text-secondary": "#212529",
      "text-muted": "#6b7280",
      icon: "#33363f",
      border: "#e5e0d8",
      success: "#10b981",
      warning: "#f59e0b",
      error: "#ef4444",
      fab: "#1a1a1a",
    },
    ```

    `fontFamily.sans` 블록과 `fontSize` 블록(15개 token) 은 **건드리지 않는다** — Phase 0가 lock했고 1A-UI-SPEC § Typography가 "1A는 zero new sizes"를 명시한다. `plugins: []`도 그대로.

    완료 후 `cd frontend && npx tsc --noEmit` 가 통과해야 한다 (config 파일 자체도 TS strict 대상). 새 의존성 설치 없음.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F '"#fe9012"' tailwind.config.ts && grep -F '"#fcf9f6"' tailwind.config.ts && grep -F '"#00c3d0"' tailwind.config.ts && grep -F '"#ef4444"' tailwind.config.ts && ! grep -F 'var(--background)' tailwind.config.ts && ! grep -F 'var(--foreground)' tailwind.config.ts</automated>
  </verify>
  <done>tailwind.config.ts contains all 14 color tokens with exact hex; the legacy `background`/`foreground` CSS-var entries are removed; tsc passes.</done>
  <acceptance_criteria>
    - `frontend/tailwind.config.ts` contains the literal strings `"#fcf9f6"`, `"#fe9012"`, `"#ffb84a"`, `"#00c3d0"`, `"#1a1a1a"`, `"#212529"`, `"#6b7280"`, `"#33363f"`, `"#e5e0d8"`, `"#10b981"`, `"#f59e0b"`, `"#ef4444"`, `"#ffffff"`
    - `frontend/tailwind.config.ts` does NOT contain `var(--background)` or `var(--foreground)`
    - `frontend/tailwind.config.ts` still contains the line `"Pretendard Variable"` (fontFamily.sans untouched)
    - `frontend/tailwind.config.ts` still contains `"title-1"` (fontSize.title-1 untouched)
    - `cd frontend && npx tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Replace globals.css light/dark vars with cream surface + add viewport meta and Pally metadata to layout.tsx</name>
  <files>frontend/app/globals.css, frontend/app/layout.tsx</files>
  <read_first>
    - frontend/app/globals.css (current — has prefers-color-scheme dark block that conflicts with "Dark mode out of scope for MVP" decision in DESIGN.md)
    - frontend/app/layout.tsx (current — title "Create Next App", description "Generated by create next app" placeholder)
    - DESIGN.md § Decisions Log entry "Dark mode out of scope for MVP"
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § Color
  </read_first>
  <action>
    **A. `frontend/app/globals.css`** — 전체 내용을 아래로 교체. light/dark CSS vars와 `@media (prefers-color-scheme: dark)` 블록을 제거 (DESIGN.md "Dark mode out of scope for MVP"). body 배경은 `bg-surface` 토큰을 통해 적용되도록 빈 background-color rule만 남기되, Tailwind utility로 표현 가능하므로 body color/background block 자체를 삭제. `text-balance` utility는 유지.

    ```css
    @tailwind base;
    @tailwind components;
    @tailwind utilities;

    /*
     * Phase 1A: light mode only (DESIGN.md "Dark mode out of scope for MVP").
     * Page background + text colors are applied via Tailwind tokens on <body>
     * (see frontend/app/layout.tsx — `bg-surface text-text`).
     */

    @layer utilities {
      .text-balance {
        text-wrap: balance;
      }
    }
    ```

    **B. `frontend/app/layout.tsx`** — 전체 내용을 아래로 교체. (1) metadata title/description을 Pally로 교체, (2) viewport export를 추가 (Next 14 App Router pattern — iOS Safari focus zoom 방지), (3) body className에 `bg-surface text-text font-sans antialiased` 적용. Pretendard CSS import는 유지 (Phase 0 lock).

    ```typescript
    import type { Metadata, Viewport } from "next";
    import "pretendard/dist/web/variable/pretendardvariable.css";
    import "./globals.css";

    export const metadata: Metadata = {
      title: "Pally",
      description: "내 영어 발화 스타일에 반응하는 Pally — 한국인 영어학습자를 위한 음성 회화 동반자",
    };

    // Mobile viewport lock — Figma 402px target (per 01A-CONTEXT.md + commit a2c2bb4).
    // maximumScale=1 prevents iOS Safari from auto-zooming when MediaRecorder
    // permission prompts or input focus events fire.
    export const viewport: Viewport = {
      width: "device-width",
      initialScale: 1,
      maximumScale: 1,
      userScalable: false,
    };

    export default function RootLayout({
      children,
    }: Readonly<{
      children: React.ReactNode;
    }>) {
      return (
        <html lang="ko">
          <body className="bg-surface text-text font-sans antialiased min-h-screen">
            {children}
          </body>
        </html>
      );
    }
    ```

    완료 후 `cd frontend && npm run build` 가 통과해야 한다.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F 'title: "Pally"' app/layout.tsx && grep -F 'maximumScale: 1' app/layout.tsx && grep -F 'bg-surface text-text font-sans antialiased' app/layout.tsx && ! grep -F 'prefers-color-scheme' app/globals.css && ! grep -F '--background' app/globals.css && cd /Users/clairelee/Desktop/claude-project/capstone-latest/frontend && npm run build 2>&1 | tail -20</automated>
  </verify>
  <done>globals.css has no dark-mode block and no CSS vars; layout.tsx exports metadata with title "Pally", a viewport export with maximumScale 1, and the body uses bg-surface/text-text/font-sans Tailwind classes; `npm run build` succeeds.</done>
  <acceptance_criteria>
    - `frontend/app/globals.css` contains `@tailwind base;`, `@tailwind components;`, `@tailwind utilities;`, `.text-balance` utility
    - `frontend/app/globals.css` does NOT contain `prefers-color-scheme`, does NOT contain `--background`, does NOT contain `--foreground`
    - `frontend/app/layout.tsx` exports `metadata` with `title: "Pally"`
    - `frontend/app/layout.tsx` exports `viewport` of type `Viewport` with `maximumScale: 1` and `userScalable: false`
    - `frontend/app/layout.tsx` body has `className="bg-surface text-text font-sans antialiased min-h-screen"`
    - `frontend/app/layout.tsx` still imports `pretendard/dist/web/variable/pretendardvariable.css` (Phase 0 lock)
    - `frontend/app/layout.tsx` still uses `<html lang="ko">`
    - `cd frontend && npx tsc --noEmit` exits 0
    - `cd frontend && npm run build` exits 0 with no Tailwind warnings about unknown classes
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Build → Browser | Tailwind config + globals.css are compiled at build time; no runtime input. |
| Layout → All pages | Root layout metadata + viewport flow to every page render. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01A-01-01 | Information Disclosure | layout.tsx metadata | accept | metadata fields contain only the product name and Korean tagline — no PII, no secret. Acceptable. |
| T-01A-01-02 | Tampering | globals.css | accept | Build-time artifact only. No user-controlled input flows in. |
| T-01A-01-03 | Denial of Service | viewport maximumScale=1 (a11y consideration) | accept | `userScalable: false` is required to prevent iOS Safari mic-permission auto-zoom (CONTEXT.md "간단하게" mandate). A11y trade-off acknowledged; Senior plan Phase B/C will revisit. |
</threat_model>

<verification>
- `cd frontend && npx tsc --noEmit` passes
- `cd frontend && npm run build` passes
- A trivial JSX snippet using `className="bg-primary"` would render orange (verified at Plan 05 E2E via Playwright)
- No dark-mode CSS shipped
</verification>

<success_criteria>
1. tailwind.config.ts exposes 14 color tokens (surface / surface-raised / primary / primary-soft / accent / text / text-secondary / text-muted / icon / border / success / warning / error / fab) with exact DESIGN.md hex values.
2. globals.css is dark-mode-free and CSS-var-free.
3. layout.tsx has Pally metadata, Viewport export with `maximumScale: 1`, and body classed `bg-surface text-text font-sans antialiased min-h-screen`.
4. `npm run build` succeeds without warnings.
</success_criteria>

<output>
After completion, create `.planning/phases/01A-fe-screens-audio-shell/01A-01-SUMMARY.md`
</output>
