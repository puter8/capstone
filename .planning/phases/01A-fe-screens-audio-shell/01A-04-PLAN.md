---
phase: 01A
plan: 04
type: execute
wave: 2
depends_on: ["01A-01", "01A-02"]
files_modified:
  - frontend/components/chat/PallyPlaceholder.tsx
  - frontend/components/chat/ChatBubble.tsx
  - frontend/components/chat/HistoryRow.tsx
  - frontend/components/chat/HistorySheet.tsx
  - frontend/components/nav/BottomNav.tsx
  - frontend/components/ui/Toast.tsx
autonomous: true
requirements: [MAIN-01, CHAT-01]
must_haves:
  truths:
    - "PallyPlaceholder renders a 262×262 inline SVG Star4 shape — it does NOT live in frontend/components/pally/ (that's Phase 1B's namespace)"
    - "ChatBubble shows the empty-state Korean copy (24px heading + 16px subtitle) when messages.length === 0, or the latest user+pally turn when messages exist, with a chevron toggle"
    - "HistorySheet renders messages chronologically as SMS-style rows, YOU label teal / Pally label orange (CHAT-01 contract)"
    - "BottomNav renders 5 tabs (홈 / 히스토리 / 새 대화 / 랭킹 / 내 정보), the center `+` is a 56px black disc, NOT orange, and all tabs are aria-disabled with no onClick"
    - "Toast surfaces error.message above the TalkButton zone, auto-dismisses after 4s, tap-to-dismiss"
  artifacts:
    - path: "frontend/components/chat/PallyPlaceholder.tsx"
      provides: "Static 262×262 inline SVG of Figma Star4 spike — Phase 1B replacement target"
      exports: ["PallyPlaceholder"]
    - path: "frontend/components/chat/ChatBubble.tsx"
      provides: "Top zone bubble — empty state OR last turn + chevron toggle"
      exports: ["ChatBubble"]
    - path: "frontend/components/chat/HistoryRow.tsx"
      provides: "Single SMS-style row (sender label + transcript + timestamp)"
      exports: ["HistoryRow"]
    - path: "frontend/components/chat/HistorySheet.tsx"
      provides: "Full-sheet overlay listing all messages with 4×40 panel handle + orange stripe"
      exports: ["HistorySheet"]
    - path: "frontend/components/nav/BottomNav.tsx"
      provides: "5-tab disabled nav (홈 / 히스토리 / 새 대화 FAB / 랭킹 / 내 정보)"
      exports: ["BottomNav"]
    - path: "frontend/components/ui/Toast.tsx"
      provides: "Inline error toast above TalkButton — 4s auto-dismiss + tap-to-dismiss"
      exports: ["Toast"]
  key_links:
    - from: "frontend/components/chat/ChatBubble.tsx"
      to: "frontend/lib/types/message.ts"
      via: "import type Message"
      pattern: "from '@/lib/types/message'"
    - from: "frontend/components/chat/HistorySheet.tsx"
      to: "frontend/components/chat/HistoryRow.tsx"
      via: "named import"
      pattern: "from './HistoryRow'"
    - from: "frontend/components/ui/Toast.tsx"
      to: "consumer (Plan 05 page.tsx)"
      via: "onDismiss prop dispatched to reducer 'rec/dismissError'"
      pattern: "onDismiss"
---

<objective>
Wave 2 — Chat surfaces (parallel to Plan 03 audio shell).
CHAT-01 + MAIN-01의 시각 요소 전체. PallyPlaceholder, top ChatBubble (chevron + empty state), HistorySheet (SMS rows + drag handle + orange stripe), BottomNav (5 disabled tabs), Toast (error 표시). 모두 stateless / props-driven — state는 Plan 05 page에서 reducer를 통해 주입.

Purpose: Plan 03이 audio 영역을 소유하는 동안, 이 plan은 chat surface 영역을 소유 (file-level 충돌 0). Plan 05에서 두 영역이 만나면 메인 페이지 조립이 import만 하면 끝.

Output: 6개 components, 모두 named export, 모두 `'use client'` (Toast + HistorySheet은 setTimeout 사용; ChatBubble + BottomNav + PallyPlaceholder는 inert presentational이지만 일관성을 위해 client 처리), TS strict 통과.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md
@.planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md
@.planning/phases/01A-fe-screens-audio-shell/01A-RESEARCH.md
@DESIGN.md
@frontend/lib/utils.ts
@frontend/lib/types/message.ts
</context>

<interfaces>
<!-- Existing types (consumed) -->

From frontend/lib/types/message.ts:
```typescript
export type MessageRole = 'user' | 'pally';
export interface Message {
  id: string;
  sessionId: string;
  role: MessageRole;
  transcript: string;
  createdAt: string;
}
```

From frontend/lib/utils.ts:
```typescript
export function cn(...inputs: ClassValue[]): string;
```

<!-- New component prop contracts (declared by THIS plan, consumed by Plan 05) -->

```typescript
// PallyPlaceholder: static, no props
export function PallyPlaceholder(): JSX.Element;

// ChatBubble: empty-state when messages is empty, otherwise show last user+pally turn + chevron
export interface ChatBubbleProps {
  messages: readonly Message[];
  historyOpen: boolean;
  onToggleHistory: () => void;
}
export function ChatBubble(props: ChatBubbleProps): JSX.Element;

// HistoryRow: SMS row
export interface HistoryRowProps {
  message: Message;
}
export function HistoryRow(props: HistoryRowProps): JSX.Element;

// HistorySheet: full overlay; slide-down when open
export interface HistorySheetProps {
  open: boolean;
  messages: readonly Message[];
  onClose: () => void;
}
export function HistorySheet(props: HistorySheetProps): JSX.Element;

// BottomNav: 5 disabled tabs, no interactive props
export function BottomNav(): JSX.Element;

// Toast: error display, auto-dismiss + tap-to-dismiss
export interface ToastProps {
  message: string;
  visible: boolean;
  onDismiss: () => void;
}
export function Toast(props: ToastProps): JSX.Element;
```

<!-- UI-SPEC locked copy + colors (reproduced for self-contained reference) -->
<!--
  Empty state heading:    "오늘은 어떤 이야기를 해볼까요?"      text-title-1, text-text
  Empty state subtitle:   "마이크를 눌러 영어로 말해보세요"    text-body, text-text-muted

  Sender labels:
    YOU  → bg-transparent text-accent text-body-2-sb     (#00c3d0 teal)
    Pally → bg-transparent text-primary text-body-2-sb   (#fe9012 orange)

  BottomNav labels (11px Regular = text-caption-2):
    홈 / 히스토리 / 새 대화 / 랭킹 / 내 정보
  BottomNav surface: bg-surface, border-t border-border (1px), upward soft shadow (DESIGN.md decisions log)
  BottomNav `+` (center, index 2): w-14 h-14 (56px) bg-fab disc + white cross + caption-2 muted label
  BottomNav tab hit area: 64×56 (UI-SPEC § Spacing)

  HistorySheet handle: 4×40 px gray rounded bar at top of panel (DESIGN.md decisions log 2026-05-25)
  HistorySheet bottom: 13px h-[13px] bg-primary-soft stripe (panel ≤ 605px tall)

  Toast surface: bg-surface-raised border border-border rounded-lg (radius 8 = rounded-md? UI-SPEC says radius.sm = 8 → rounded-lg in Tailwind default scale is 8px)
  Toast typography: text-body for permission strings; text-caption-1 + text-error for "다시 한 번 말해주세요" — but THIS Toast component is generic and just uses text-body. Plan 05 chooses content per error.reason.
  Toast auto-dismiss: 4000ms (UI-SPEC § Interaction Timing — magic-number comment required)
-->
</interfaces>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Static SVG PallyPlaceholder + Toast (small components, batched)</name>
  <files>frontend/components/chat/PallyPlaceholder.tsx, frontend/components/ui/Toast.tsx</files>
  <read_first>
    - .planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md § D-11 (PallyPlaceholder boundary — NOT in components/pally/)
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § "Component Inventory → PallyPlaceholder, Toast" + § "Interaction Timing" (4000ms toast)
    - .planning/phases/01A-fe-screens-audio-shell/01A-RESEARCH.md § "Open Questions #2" (Star4 SVG — inline JSX with simplified spike shape acceptable; 1B replaces with Canvas2D anyway)
  </read_first>
  <action>
    Create two small components in parallel files.

    **A. `frontend/components/chat/PallyPlaceholder.tsx`** — 262×262 inline SVG of a Star4 spike (4-pointed/8-pointed spiked shape) in `primary` orange. Static. NO state. NO `'use client'` needed (pure SVG render).

    The component lives at `components/chat/` per D-11 — explicitly NOT in `components/pally/` (that namespace belongs to Phase 1B's Canvas2D renderer per CLAUDE.md §1).

    ```tsx
    /**
     * Phase 1A — Pally placeholder.
     *
     * D-11 / CLAUDE.md §1: This file lives at components/chat/, NOT components/pally/.
     * The components/pally/ directory is Phase 1B's namespace (Canvas2D Superformula
     * renderer). When Phase 1B ships, Plan 05's page.tsx swaps the import in one line.
     *
     * Visual: 262×262 box containing an inline SVG approximation of the Figma "Star4"
     * spike (8-point soft spike, primary orange fill). Exact Figma export via
     * mcp__figma__get_design_context on Group 7 is acceptable but not required —
     * Phase 1B will overwrite this entirely.
     */

    export function PallyPlaceholder() {
      return (
        <div
          className="w-[262px] h-[262px] flex items-center justify-center"
          aria-hidden="true"
        >
          <svg
            viewBox="0 0 262 262"
            width="262"
            height="262"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Star4 spike approximation — 8 outer points alternating with inner radii */}
            <path
              d="
                M131 0
                L160 80
                L240 60
                L195 130
                L262 161
                L181 178
                L200 252
                L131 215
                L62 252
                L81 178
                L0 161
                L67 130
                L22 60
                L102 80 Z
              "
              fill="#fe9012"
            />
          </svg>
        </div>
      );
    }
    ```

    Note: the literal `#fe9012` here is the only acceptable raw-hex usage in 1A — it's inside an SVG `fill` attribute and the SVG fill cannot reference Tailwind tokens. UI-SPEC § Anti-Patterns #2 forbids inline hex **in JSX className**; SVG attribute fill is a separate channel. Add a comment justifying this:

    ```
    {/* primary token (#fe9012) — SVG fill cannot reference Tailwind tokens */}
    ```

    **B. `frontend/components/ui/Toast.tsx`** — generic inline toast above TalkButton, 4s auto-dismiss + tap-to-dismiss. `'use client'` because of setTimeout.

    ```tsx
    'use client';

    import { useEffect } from 'react';
    import { cn } from '@/lib/utils';

    // 4000ms per UI-SPEC § Interaction Timing — "long enough to read 1 Korean line
    // at calm pace, short enough to clear before the user re-attempts".
    const AUTO_DISMISS_MS = 4000;

    export interface ToastProps {
      message: string;
      visible: boolean;
      onDismiss: () => void;
    }

    export function Toast({ message, visible, onDismiss }: ToastProps) {
      useEffect(() => {
        if (!visible) return;
        const t = window.setTimeout(onDismiss, AUTO_DISMISS_MS);
        return () => window.clearTimeout(t);
      }, [visible, onDismiss]);

      if (!visible) return null;

      return (
        <button
          type="button"
          onClick={onDismiss}
          className={cn(
            'block w-full max-w-[320px] mx-auto',
            'bg-surface-raised border border-border rounded-lg',
            'px-4 py-2',
            'text-body text-text-muted text-left',
            'shadow-lg',
            'transition-opacity duration-200',
          )}
          aria-live="polite"
        >
          {message}
        </button>
      );
    }
    ```

    Constraints:
    - PallyPlaceholder size literal `w-[262px] h-[262px]` is allowed — UI-SPEC § Spacing notes it as a touch-target exception, 262 is a multiple of 4, and the Figma Group 7 lock fixes this dimension.
    - Toast uses `bg-surface-raised` + `border-border` tokens, no inline hex in className.
    - Auto-dismiss timer cleaned up on unmount/visibility change.
    - No empty catch, no silent fallback.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F "export function PallyPlaceholder" components/chat/PallyPlaceholder.tsx && grep -F 'w-[262px] h-[262px]' components/chat/PallyPlaceholder.tsx && grep -F "#fe9012" components/chat/PallyPlaceholder.tsx && test ! -d components/pally && grep -F "'use client'" components/ui/Toast.tsx && grep -F "export function Toast" components/ui/Toast.tsx && grep -F "AUTO_DISMISS_MS = 4000" components/ui/Toast.tsx && grep -F "bg-surface-raised" components/ui/Toast.tsx && grep -F "border-border" components/ui/Toast.tsx && grep -F 'aria-live="polite"' components/ui/Toast.tsx</automated>
  </verify>
  <done>PallyPlaceholder.tsx renders a 262×262 SVG with primary orange fill (raw hex only inside SVG fill attr); Toast.tsx auto-dismisses after 4s with cleanup; both files placed at correct paths and pass tsc.</done>
  <acceptance_criteria>
    - File `frontend/components/chat/PallyPlaceholder.tsx` exists
    - File `frontend/components/chat/PallyPlaceholder.tsx` contains the literal `w-[262px] h-[262px]`
    - File `frontend/components/chat/PallyPlaceholder.tsx` contains `<svg`
    - File `frontend/components/chat/PallyPlaceholder.tsx` contains `#fe9012` (Pally orange, inside SVG fill attribute)
    - Directory `frontend/components/pally/` does NOT exist (Phase 1B namespace — `test ! -d frontend/components/pally` exits 0)
    - File `frontend/components/ui/Toast.tsx` exists with `'use client'`
    - File `frontend/components/ui/Toast.tsx` contains `export function Toast(`
    - File `frontend/components/ui/Toast.tsx` contains `AUTO_DISMISS_MS = 4000`
    - File `frontend/components/ui/Toast.tsx` contains `bg-surface-raised` and `border-border` (token usage, not raw hex)
    - File `frontend/components/ui/Toast.tsx` contains `window.clearTimeout` (cleanup)
    - Both files contain zero occurrences of the literal token `any` (`grep -w any` returns no matches)
    - `cd frontend && npx tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto" tdd="false">
  <name>Task 2: ChatBubble (empty state + last turn + chevron toggle)</name>
  <files>frontend/components/chat/ChatBubble.tsx</files>
  <read_first>
    - frontend/lib/types/message.ts (for Message type)
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § "Copywriting Contract → Empty state" + § "Component Inventory → ChatBubble" + § "Color → reserved-for list" (YOU=accent teal, Pally=primary orange)
    - .planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md (D-18: empty on refresh — no localStorage restoration)
    - DESIGN.md § Decisions Log "Empty state 한국어로 전환"
  </read_first>
  <action>
    Create `frontend/components/chat/ChatBubble.tsx`. Top-zone surface — when no messages, shows empty state heading + subtitle. When messages exist, shows the latest user transcript (`messages.at(-2)`, if user role) and latest Pally reply (`messages.at(-1)`, if pally role). Chevron icon (down when closed, up when historyOpen) toggles HistorySheet via `onToggleHistory`.

    ```tsx
    'use client';

    import { cn } from '@/lib/utils';
    import type { Message } from '@/lib/types/message';

    export interface ChatBubbleProps {
      messages: readonly Message[];
      historyOpen: boolean;
      onToggleHistory: () => void;
    }

    function SenderLabel({ role }: { role: Message['role'] }) {
      if (role === 'user') {
        return <span className="text-accent text-body-2-sb">YOU</span>;
      }
      return <span className="text-primary text-body-2-sb">Pally</span>;
    }

    function Chevron({ open }: { open: boolean }) {
      // 16x16 chevron — down when closed (open=false), up when open=true.
      return (
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          aria-hidden="true"
          className={cn('transition-transform duration-200', open ? 'rotate-180' : 'rotate-0')}
        >
          <path
            d="M3 6l5 5 5-5"
            stroke="#6b7280"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
        </svg>
      );
    }

    export function ChatBubble({ messages, historyOpen, onToggleHistory }: ChatBubbleProps) {
      const isEmpty = messages.length === 0;
      // Last Pally reply is the latest entry; last user turn is the one before.
      const lastPally = !isEmpty ? messages.at(-1) : undefined;
      const lastUser = !isEmpty ? messages.at(-2) : undefined;

      return (
        <section
          className={cn(
            'mx-auto w-full max-w-[370px]',
            'bg-surface-raised rounded-2xl border border-border',
            'px-4 py-3',
            'shadow-sm',
          )}
          aria-label="대화"
        >
          {isEmpty ? (
            // Empty state per UI-SPEC Copywriting Contract — two <p> for screen-reader correctness (RESEARCH §Open Q #3).
            <div className="py-6 text-center">
              <p className="text-title-1 text-text">오늘은 어떤 이야기를 해볼까요?</p>
              <p className="text-body text-text-muted mt-2">마이크를 눌러 영어로 말해보세요</p>
            </div>
          ) : (
            <div className="space-y-2">
              {lastUser && lastUser.role === 'user' && (
                <p className="text-body text-text">
                  <SenderLabel role="user" />
                  <span className="ml-2">{lastUser.transcript}</span>
                </p>
              )}
              {lastPally && lastPally.role === 'pally' && (
                <p className="text-subtitle-sb text-text">
                  <SenderLabel role="pally" />
                  <span className="ml-2">{lastPally.transcript}</span>
                </p>
              )}
            </div>
          )}

          <button
            type="button"
            onClick={onToggleHistory}
            aria-label={historyOpen ? '대화 기록 닫기' : '대화 기록 열기'}
            aria-expanded={historyOpen}
            className="mx-auto mt-2 flex items-center justify-center w-full h-6 rounded-md hover:bg-surface"
          >
            <Chevron open={historyOpen} />
          </button>
        </section>
      );
    }
    ```

    Constraints:
    - `'use client'` because of onClick + transitions.
    - Sender labels: `YOU` text-accent (teal), `Pally` text-primary (orange) — UI-SPEC § Color reserved-for list locks this.
    - Empty-state heading uses `text-title-1` (24px), subtitle uses `text-body` (16px) + `text-text-muted` — UI-SPEC § Typography active subset.
    - The chevron stroke hex `#6b7280` corresponds to `text-muted` token; we use raw hex inside SVG stroke since SVG attrs can't reference Tailwind tokens. Add an inline comment.
    - `.at(-1)` is ES2022 array method — supported by Next 14 / React 18 / TS 5.
    - No external libraries.
    - `readonly Message[]` accepted in props for safety.
    - DO NOT render the `hint_ko` field — Phase 2 surfaces it (UI-SPEC § Anti-Patterns #9 forbids reading hint_ko in 1A UI).
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F "'use client'" components/chat/ChatBubble.tsx && grep -F "export function ChatBubble" components/chat/ChatBubble.tsx && grep -F "오늘은 어떤 이야기를 해볼까요?" components/chat/ChatBubble.tsx && grep -F "마이크를 눌러 영어로 말해보세요" components/chat/ChatBubble.tsx && grep -F "text-accent" components/chat/ChatBubble.tsx && grep -F "text-primary" components/chat/ChatBubble.tsx && grep -F "text-title-1" components/chat/ChatBubble.tsx && grep -F "aria-expanded" components/chat/ChatBubble.tsx && ! grep -F "hint_ko" components/chat/ChatBubble.tsx</automated>
  </verify>
  <done>ChatBubble renders empty state OR last turn correctly, sender labels use the locked color tokens, chevron toggles via onToggleHistory, hint_ko field never read; tsc passes.</done>
  <acceptance_criteria>
    - File `frontend/components/chat/ChatBubble.tsx` exists with `'use client'`
    - Contains `export function ChatBubble(`
    - Contains the exact Korean literal `'오늘은 어떤 이야기를 해볼까요?'`
    - Contains the exact Korean literal `'마이크를 눌러 영어로 말해보세요'`
    - Contains `text-accent` (YOU teal) and `text-primary` (Pally orange) Tailwind classes
    - Contains `text-title-1` (empty heading size lock)
    - Contains `aria-expanded` on the chevron toggle button
    - Contains `import type { Message } from '@/lib/types/message'`
    - Contains zero occurrences of `hint_ko` (UI-SPEC § Anti-Patterns #9 forbids hint_ko UI in 1A)
    - Contains zero occurrences of the literal token `any` (`grep -w any` returns no matches)
    - `cd frontend && npx tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto" tdd="false">
  <name>Task 3: HistoryRow + HistorySheet (full overlay with handle + stripe)</name>
  <files>frontend/components/chat/HistoryRow.tsx, frontend/components/chat/HistorySheet.tsx</files>
  <read_first>
    - frontend/lib/types/message.ts (for Message)
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § "Component Inventory → HistorySheet/HistoryRow" + § "Color → primary-soft stripe (13px)" + § "Interaction Timing → chat-bubble enter motion (200ms ease-out)"
    - DESIGN.md § Decisions Log "History view 주황색 stripe" + "History view에 4×40px panel handle"
  </read_first>
  <action>
    Create both files (HistorySheet imports HistoryRow). Both are `'use client'` because the sheet has open/close transitions and the row formatter calls Date.

    **A. `frontend/components/chat/HistoryRow.tsx`**

    ```tsx
    'use client';

    import { cn } from '@/lib/utils';
    import type { Message } from '@/lib/types/message';

    export interface HistoryRowProps {
      message: Message;
    }

    function formatTime(iso: string): string {
      // Hour:Minute, Korean locale ("오후 3:14" style). Defensive guard if iso invalid.
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) {
        // Surface, don't silently fall back. (CLAUDE.md §7)
        return '';
      }
      return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    }

    export function HistoryRow({ message }: HistoryRowProps) {
      const isUser = message.role === 'user';
      // Label color per UI-SPEC § Color reserved-for list: YOU=accent (teal), Pally=primary (orange).
      const labelClass = isUser ? 'text-accent' : 'text-primary';
      const labelText = isUser ? 'YOU' : 'Pally';

      return (
        <div className={cn('flex flex-col gap-1 px-4 py-3', isUser ? 'items-start' : 'items-end')}>
          <span className={cn('text-body-2-sb', labelClass)}>{labelText}</span>
          <p className={cn('text-body text-text max-w-[280px]', isUser ? 'text-left' : 'text-right')}>
            {message.transcript}
          </p>
          <span className="text-caption-1 text-text-muted">{formatTime(message.createdAt)}</span>
        </div>
      );
    }
    ```

    **B. `frontend/components/chat/HistorySheet.tsx`** — full-sheet overlay; slide-down animation when open; 4×40 handle at top; 13px primary-soft stripe at bottom. Close on backdrop tap or handle drag (1A: simple click on handle/backdrop dispatches `onClose`).

    ```tsx
    'use client';

    import { cn } from '@/lib/utils';
    import type { Message } from '@/lib/types/message';
    import { HistoryRow } from './HistoryRow';

    export interface HistorySheetProps {
      open: boolean;
      messages: readonly Message[];
      onClose: () => void;
    }

    export function HistorySheet({ open, messages, onClose }: HistorySheetProps) {
      // Render nothing when closed — no hidden DOM with a11y trap.
      if (!open) return null;

      return (
        <div className="fixed inset-0 z-40 flex flex-col" role="dialog" aria-modal="true" aria-label="대화 기록">
          {/* Backdrop — tap to close */}
          <button
            type="button"
            onClick={onClose}
            aria-label="대화 기록 닫기"
            className="absolute inset-0 bg-black/30"
          />

          {/* Panel — slide-down from top, max height 605px so the 13px stripe peeks below */}
          <section
            className={cn(
              'relative mx-auto mt-0 w-full max-w-[402px]',
              'bg-surface-raised rounded-b-2xl',
              'shadow-xl',
              'flex flex-col',
              // Slide-down feel: animate via Tailwind transition (200ms ease-out per UI-SPEC § Interaction Timing).
              'transition-transform duration-200 ease-out',
            )}
            style={{ maxHeight: '605px' }}
          >
            {/* 4x40 drag handle (DESIGN.md decisions log 2026-05-25) */}
            <button
              type="button"
              onClick={onClose}
              aria-label="대화 기록 닫기"
              className="mx-auto mt-2 mb-1 h-1 w-10 rounded-full bg-text-muted/40"
            />

            {/* Scrollable message list */}
            <div className="flex-1 overflow-y-auto px-2 py-2">
              {messages.length === 0 ? (
                <p className="text-body text-text-muted text-center py-8">아직 대화가 없어요</p>
              ) : (
                <ul className="flex flex-col">
                  {messages.map((m) => (
                    <li key={m.id}>
                      <HistoryRow message={m} />
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          {/* 13px primary-soft stripe peeking under the panel (DESIGN.md 2026-05-25) */}
          <div
            aria-hidden="true"
            className="mx-auto w-full max-w-[402px] h-[13px] bg-primary-soft"
          />
        </div>
      );
    }
    ```

    Constraints:
    - `HistoryRow` does not silently swallow invalid timestamps — returns empty string with comment.
    - `HistorySheet` returns `null` when closed (no hidden DOM with accidental focus).
    - Use `text-text-muted/40` Tailwind opacity-on-token (not raw hex).
    - 4×40 handle and 13px stripe sizes locked by DESIGN.md decisions log.
    - max-w-[402px] aligns with viewport lock.
    - `role="dialog" aria-modal="true"` for screen readers.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F "export function HistoryRow" components/chat/HistoryRow.tsx && grep -F "text-accent" components/chat/HistoryRow.tsx && grep -F "text-primary" components/chat/HistoryRow.tsx && grep -F "toLocaleTimeString('ko-KR'" components/chat/HistoryRow.tsx && grep -F "export function HistorySheet" components/chat/HistorySheet.tsx && grep -F "import { HistoryRow } from './HistoryRow'" components/chat/HistorySheet.tsx && grep -F 'role="dialog"' components/chat/HistorySheet.tsx && grep -F 'aria-modal="true"' components/chat/HistorySheet.tsx && grep -F "bg-primary-soft" components/chat/HistorySheet.tsx && grep -F 'h-[13px]' components/chat/HistorySheet.tsx && grep -F 'w-10' components/chat/HistorySheet.tsx</automated>
  </verify>
  <done>HistoryRow formats Korean time + uses YOU/Pally sender colors; HistorySheet renders dialog overlay with 4×40 handle + 13px primary-soft stripe + 402px max width; both tsc-pass.</done>
  <acceptance_criteria>
    - File `frontend/components/chat/HistoryRow.tsx` exists with `'use client'`
    - Contains `export function HistoryRow(`
    - Contains `text-accent` (YOU label) and `text-primary` (Pally label)
    - Contains `text-caption-1` and `text-text-muted` (timestamp)
    - Contains `toLocaleTimeString('ko-KR'`
    - File `frontend/components/chat/HistorySheet.tsx` exists with `'use client'`
    - Contains `export function HistorySheet(`
    - Contains `import { HistoryRow } from './HistoryRow'`
    - Contains `role="dialog"` and `aria-modal="true"`
    - Contains `bg-primary-soft` (decorative bottom stripe)
    - Contains `h-[13px]` (DESIGN.md stripe height lock)
    - Contains `w-10` (40px handle width lock per DESIGN.md 2026-05-25 "History view에 4×40px panel handle")
    - Both files contain zero occurrences of the literal token `any` (`grep -w any` returns no matches)
    - `cd frontend && npx tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto" tdd="false">
  <name>Task 4: BottomNav (5 disabled tabs, FAB center, no onClick)</name>
  <files>frontend/components/nav/BottomNav.tsx</files>
  <read_first>
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § "Component Inventory → BottomNav" + § "Color" + § "Anti-Patterns to Reject in Review" (#5 — no opacity-50)
    - .planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md § D-17 (all 5 disabled, no toast on tap)
    - DESIGN.md § Decisions Log 2026-05-25 (5 tab labels, +FAB color, navbar separator)
  </read_first>
  <action>
    Create `frontend/components/nav/BottomNav.tsx`. 5 tabs: 홈 / 히스토리 / 새 대화 (FAB, center index 2) / 랭킹 / 내 정보. **All 5 are `aria-disabled="true"` with NO onClick** (D-17: tapping does nothing). Center FAB is a 56px black disc (`bg-fab`) with white cross — NOT orange. Other tabs render 24x24 stroke icons in `text-icon` (#33363f) + caption-2 label in `text-text-muted`.

    Bar surface: `bg-surface` + top border `border-t border-border` (1px) + upward soft drop shadow.

    ```tsx
    'use client';

    import { cn } from '@/lib/utils';

    type TabId = 'home' | 'history' | 'new' | 'ranking' | 'profile';
    interface Tab {
      id: TabId;
      label: string;
      isFab: boolean;
    }

    // Korean labels locked by DESIGN.md decisions log 2026-05-25 + UI-SPEC § Copywriting Contract.
    const TABS: readonly Tab[] = [
      { id: 'home', label: '홈', isFab: false },
      { id: 'history', label: '히스토리', isFab: false },
      { id: 'new', label: '새 대화', isFab: true },
      { id: 'ranking', label: '랭킹', isFab: false },
      { id: 'profile', label: '내 정보', isFab: false },
    ];

    // 24x24 stroke icons — minimal placeholder shapes (Figma exact glyphs deferred to Phase B polish).
    function TabIcon({ id }: { id: TabId }) {
      const stroke = '#33363f'; // icon token — SVG stroke can't reference Tailwind tokens
      return (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          {id === 'home' && (
            <path d="M4 11l8-7 8 7v9a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1v-9z" stroke={stroke} strokeWidth="2" strokeLinejoin="round" />
          )}
          {id === 'history' && (
            <g stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="8" fill="none" />
              <path d="M12 7v5l3 2" />
            </g>
          )}
          {id === 'ranking' && (
            <path d="M5 21V10M12 21V4M19 21v-7" stroke={stroke} strokeWidth="2" strokeLinecap="round" />
          )}
          {id === 'profile' && (
            <g stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 21a8 8 0 0 1 16 0" />
            </g>
          )}
        </svg>
      );
    }

    export function BottomNav() {
      return (
        <nav
          aria-label="하단 내비게이션"
          className={cn(
            'fixed bottom-0 inset-x-0 z-30',
            'mx-auto w-full max-w-[402px]',
            'bg-surface border-t border-border',
            // Upward soft drop shadow per DESIGN.md "Navbar separator" decision 2026-05-25.
            'shadow-[0_-2px_10px_rgba(0,0,0,0.06)]',
          )}
        >
          <ul className="flex items-center justify-around h-16">
            {TABS.map((tab) => (
              <li key={tab.id} className="flex-1 flex justify-center">
                {tab.isFab ? (
                  // 새 대화 FAB — 56px black disc, white cross. NOT orange (DESIGN.md decisions log).
                  <div
                    aria-disabled="true"
                    aria-label={tab.label}
                    className="flex flex-col items-center gap-1 cursor-default"
                  >
                    <div className="w-14 h-14 rounded-full bg-fab flex items-center justify-center">
                      <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
                        <path d="M10 4v12M4 10h12" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                    </div>
                    <span className="text-caption-2 text-text-muted">{tab.label}</span>
                  </div>
                ) : (
                  <div
                    aria-disabled="true"
                    aria-label={tab.label}
                    className="flex flex-col items-center gap-1 cursor-default w-16 h-14 justify-center"
                  >
                    <TabIcon id={tab.id} />
                    <span className="text-caption-2 text-text-muted">{tab.label}</span>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </nav>
      );
    }
    ```

    Constraints:
    - **No onClick on any tab.** D-17 lock — tapping does nothing, not even a toast.
    - **No `opacity-50` anywhere** — UI-SPEC § Anti-Patterns #5.
    - All 5 labels exact: `홈 / 히스토리 / 새 대화 / 랭킹 / 내 정보`.
    - FAB uses `bg-fab` token (= #1a1a1a), NOT `bg-primary`.
    - Stroke hex `#33363f` and `#ffffff` inside SVG attrs are allowed (SVG attributes can't reference Tailwind tokens); document with inline comment.
    - `text-caption-2` for labels (11px Regular — locked by UI-SPEC § Typography table).
    - max-w-[402px] aligns with viewport lock.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F "export function BottomNav" components/nav/BottomNav.tsx && grep -F "'홈'" components/nav/BottomNav.tsx && grep -F "'히스토리'" components/nav/BottomNav.tsx && grep -F "'새 대화'" components/nav/BottomNav.tsx && grep -F "'랭킹'" components/nav/BottomNav.tsx && grep -F "'내 정보'" components/nav/BottomNav.tsx && grep -F "bg-fab" components/nav/BottomNav.tsx && grep -F "text-caption-2" components/nav/BottomNav.tsx && grep -F "text-text-muted" components/nav/BottomNav.tsx && ! grep -F "opacity-50" components/nav/BottomNav.tsx && ! grep -E "onClick" components/nav/BottomNav.tsx</automated>
  </verify>
  <done>BottomNav renders 5 disabled tabs in the locked Korean labels, center FAB uses bg-fab (black) not bg-primary, no onClick anywhere, no opacity-50; tsc passes.</done>
  <acceptance_criteria>
    - File `frontend/components/nav/BottomNav.tsx` exists with `'use client'`
    - Contains `export function BottomNav(`
    - Contains all 5 exact Korean labels: `'홈'`, `'히스토리'`, `'새 대화'`, `'랭킹'`, `'내 정보'`
    - Contains `bg-fab` (FAB center disc uses fab token, not primary)
    - Contains `text-caption-2` (11px label per UI-SPEC Typography)
    - Contains `text-text-muted` for inactive label color
    - Contains `border-t border-border` (separator)
    - Contains `shadow-[0_-2px_10px_rgba(0,0,0,0.06)]` (upward shadow per DESIGN.md)
    - File contains zero occurrences of `onClick` (D-17: no tap handler)
    - File contains zero occurrences of `opacity-50` (Anti-Pattern #5)
    - File contains zero occurrences of `bg-primary` for the FAB (D-17 locks black FAB)
    - File contains zero occurrences of the literal token `any` (`grep -w any` returns no matches)
    - `cd frontend && npx tsc --noEmit` exits 0
    - `cd frontend && npm run build` exits 0
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Reducer messages → ChatBubble/HistorySheet renders | `Message.transcript` flows into JSX as a text child. React auto-escapes. |
| `Date` parsing → HistoryRow timestamp | `new Date(iso)` may produce Invalid Date; the formatter surfaces that explicitly. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01A-04-01 | XSS / Tampering | ChatBubble/HistoryRow transcript render | mitigate | React's default text-node escaping is the mitigation. No `dangerouslySetInnerHTML` in any component. Acceptance grep verifies. |
| T-01A-04-02 | Information Disclosure | hint_ko field exposed to UI before Phase 2 | mitigate | ChatBubble.tsx contains zero occurrences of `hint_ko` per UI-SPEC § Anti-Patterns #9. |
| T-01A-04-03 | DoS | Toast timer leak on rapid show/hide | mitigate | useEffect cleanup returns `window.clearTimeout(t)` — verified. |
| T-01A-04-04 | Tampering | Invalid Message.createdAt → Date.parse silently NaN | mitigate | HistoryRow.formatTime checks `Number.isNaN(d.getTime())` and returns empty string instead of `"Invalid Date"` leaking — explicit, not silent. |
| T-01A-04-05 | Repudiation | Disabled BottomNav tap accidentally navigates | mitigate | Zero onClick handlers in BottomNav (acceptance grep). aria-disabled set. |
| T-01A-04-06 | Information Disclosure | localStorage XSS exfiltrates sessionId | accept | sessionId has no PII. Same threat already documented in RESEARCH § Security Domain. |
</threat_model>

<verification>
- `cd frontend && npx tsc --noEmit` passes
- `cd frontend && npm run build` passes
- No file inside `frontend/components/pally/*` was created (Phase 1B namespace — verified by `test ! -d frontend/components/pally`)
- All Korean copy locked: empty-state heading, subtitle, 5 nav labels, sender labels YOU/Pally
</verification>

<success_criteria>
1. PallyPlaceholder renders 262×262 SVG at `components/chat/`, NOT at `components/pally/`.
2. ChatBubble renders empty state or last user+pally turn with chevron toggle; uses text-accent/text-primary sender colors.
3. HistoryRow + HistorySheet render SMS-style rows, 4×40 handle, 13px primary-soft stripe, dialog a11y attrs.
4. BottomNav renders 5 disabled tabs (홈/히스토리/새 대화/랭킹/내 정보), center FAB is bg-fab (black) not orange, zero onClick handlers, zero opacity-50.
5. Toast auto-dismisses after 4s with cleanup.
6. `npm run build` succeeds.
</success_criteria>

<output>
After completion, create `.planning/phases/01A-fe-screens-audio-shell/01A-04-SUMMARY.md`
</output>
