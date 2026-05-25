---
phase: 01A
plan: 03
type: execute
wave: 2
depends_on: ["01A-01", "01A-02"]
files_modified:
  - frontend/lib/audio/useRecorder.ts
  - frontend/components/audio/TalkButton.tsx
autonomous: true
requirements: [MAIN-01]
must_haves:
  truths:
    - "useRecorder hook requests mic permission via getUserMedia, starts MediaRecorder, auto-stops at 30s, releases MediaStream tracks on stop"
    - "useRecorder routes NotAllowedError to onPermissionDenied callback, other errors to onError callback — no silent swallow"
    - "TalkButton renders 5 distinct visual mappings (idle=orange mic, recording/processing/speaking=red square, error=orange mic) driven by RecState discriminated union"
    - "TalkButton press toggles between idle→recording→idle via dispatched actions; no internal state inside the button"
    - "TalkButton aria-label changes per state (녹음 시작 / 녹음 정지 / 처리 중 / Pally가 응답 중)"
  artifacts:
    - path: "frontend/lib/audio/useRecorder.ts"
      provides: "useRecorder hook — getUserMedia + MediaRecorder + 30s auto-stop + cleanup"
      exports: ["useRecorder", "RecorderHandlers"]
    - path: "frontend/components/audio/TalkButton.tsx"
      provides: "5-state visual mic toggle (96px disc + 132px decorative ring + drop shadow)"
      exports: ["TalkButton"]
  key_links:
    - from: "frontend/lib/audio/useRecorder.ts"
      to: "frontend/lib/audio/pickMimeType.ts"
      via: "named import"
      pattern: "from './pickMimeType'"
    - from: "frontend/components/audio/TalkButton.tsx"
      to: "frontend/lib/state/conversation.ts"
      via: "import type RecState"
      pattern: "from '@/lib/state/conversation'"
---

<objective>
Wave 2 — Audio shell (recorder hook + TalkButton visual).
Plan 02의 reducer/types/mock/MIME 위에 실제 brower audio capture를 wire하고, CONTEXT.md D-12의 5-state TalkButton 시각을 React로 옮긴다. MediaRecorder 권한 흐름과 30s auto-stop, MediaStream cleanup이 핵심.

Purpose: Plan 05가 `<TalkButton rec={state.rec} onPressStart={...} onPressStop={...} />`만 import하면 끝나도록, Audio 동작 전체를 두 파일로 캡슐화한다. RESEARCH §Pattern 4 (useRecorder hook)와 UI-SPEC § Component Inventory의 TalkButton spec을 결합.

Output: useRecorder hook (logic) + TalkButton component (presentation). 둘 다 'use client' 필요.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md
@.planning/phases/01A-fe-screens-audio-shell/01A-RESEARCH.md
@.planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md
@DESIGN.md
@frontend/lib/utils.ts
@frontend/lib/audio/pickMimeType.ts
@frontend/lib/state/conversation.ts
</context>

<interfaces>
<!-- Inputs from Plan 01 + 02 (must exist before this plan starts) -->

From frontend/lib/audio/pickMimeType.ts (Plan 02 Task 4):
```typescript
export function pickMimeType(): string | null;
```

From frontend/lib/state/conversation.ts (Plan 02 Task 2):
```typescript
export type RecState =
  | { kind: 'idle' }
  | { kind: 'recording'; startedAt: number }
  | { kind: 'processing' }
  | { kind: 'speaking' }
  | { kind: 'error'; reason: 'permission-denied' | 'generic'; message: string };
```

From frontend/lib/utils.ts (Phase 0):
```typescript
export function cn(...inputs: ClassValue[]): string;
```

From frontend/tailwind.config.ts (Plan 01):
- Color tokens: primary, primary-soft, error, surface-raised, fab, etc.
- All Pretendard fontSize tokens.

<!-- TalkButton visual contract (UI-SPEC § Component Inventory + DESIGN.md decisions log) -->
<!--
  Outer ring (decorative, not a hit target):
    - idle:      132×132, orange (primary) at 18% opacity
    - recording: 132×132, error (red) at 22% opacity (same size as idle per DESIGN.md 2026-05-25)
    - speaking/processing: same as recording
    - error: same visual as idle
  Primary disc (hit target):
    - 96×96, full bleed
    - idle: bg-primary (#fe9012), white mic-icon SVG centered
    - recording/processing/speaking: bg-error (#ef4444), white rounded square (radius 6) centered
    - error: bg-primary, white mic-icon (same as idle)
  Drop shadow: subtle elevation; use Tailwind `shadow-lg` analogue
  aria-label: per state — UI-SPEC § Copywriting Contract → "Primary CTA (TalkButton)"
  Press feedback: scale 0.95 over 150ms (DESIGN.md § Motion)
-->
</interfaces>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Build useRecorder hook at frontend/lib/audio/useRecorder.ts</name>
  <files>frontend/lib/audio/useRecorder.ts</files>
  <read_first>
    - frontend/lib/audio/pickMimeType.ts (Plan 02 — for import)
    - .planning/phases/01A-fe-screens-audio-shell/01A-RESEARCH.md § "Pattern 4: useRecorder Hook" (verbatim reference) + § "Pitfall 4 (release tracks)" + § "Pitfall 5 (clear timer)"
    - .planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md § D-05, D-06, D-07, D-08, D-09
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § "Copywriting Contract → Error and permission states" (Korean strings)
  </read_first>
  <action>
    Create new file `frontend/lib/audio/useRecorder.ts`. Implement per RESEARCH § Pattern 4, with the following constraints honored verbatim:
    - **D-06**: permission is requested implicitly via `getUserMedia({ audio: true })` on the first call to `start()` — no pre-permission UI flow.
    - **D-07**: `NotAllowedError` / `PermissionDeniedError` fires `onPermissionDenied()`. Other errors fire `onError(message)` with the Korean strings from UI-SPEC.
    - **D-08**: 30-second auto-stop via `setTimeout` registered at recorder start; cleared on early stop.
    - **D-09**: The recorded `Blob` is passed to `onStop(blob)` but the caller (Plan 05) will ignore it in 1A. Phase 2 will use it.
    - **Pitfall 4**: `stream.getTracks().forEach(t => t.stop())` is called inside the `onstop` handler so the browser's red recording indicator clears.
    - **Pitfall 5**: `stop()` clears the 30-s timer before calling `MediaRecorder.stop()` to avoid double-stop DOMException.
    - **CLAUDE.md §7**: no empty `catch {}`, no `|| {}` / `?? []` silent fallback, no `any`.

    File contents (`'use client'` directive at top because the hook touches browser APIs):

    ```typescript
    'use client';

    import { useCallback, useRef } from 'react';
    import { pickMimeType } from './pickMimeType';

    // 30s cap per CONTEXT D-08. Long enough for a single conversational turn,
    // short enough to bound MediaRecorder memory + abuse.
    const MAX_DURATION_MS = 30_000;

    // Inline copy per UI-SPEC § Copywriting Contract → "Error and permission states"
    const ERR_NO_MIME = '이 브라우저는 음성 녹음을 지원하지 않아요.';
    const ERR_MIC_ACCESS = '마이크에 접근할 수 없어요.';

    export interface RecorderHandlers {
      onStart: () => void;
      onStop: (blob: Blob | null) => void;
      onPermissionDenied: () => void;
      onError: (message: string) => void;
    }

    export interface RecorderControls {
      start: () => Promise<void>;
      stop: () => void;
    }

    export function useRecorder(handlers: RecorderHandlers): RecorderControls {
      const recorderRef = useRef<MediaRecorder | null>(null);
      const chunksRef = useRef<Blob[]>([]);
      const timerRef = useRef<number | null>(null);
      const streamRef = useRef<MediaStream | null>(null);
      const mimeRef = useRef<string | null>(null);

      const stop = useCallback((): void => {
        if (timerRef.current !== null) {
          window.clearTimeout(timerRef.current);
          timerRef.current = null;
        }
        const r = recorderRef.current;
        if (r && r.state !== 'inactive') {
          r.stop();
        }
      }, []);

      const start = useCallback(async (): Promise<void> => {
        const mime = pickMimeType();
        if (!mime) {
          handlers.onError(ERR_NO_MIME);
          return;
        }
        mimeRef.current = mime;

        let stream: MediaStream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (err) {
          // Surface — never swallow (CLAUDE.md §7).
          const name = err instanceof DOMException ? err.name : '';
          if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
            handlers.onPermissionDenied();
          } else {
            handlers.onError(ERR_MIC_ACCESS);
          }
          return;
        }
        streamRef.current = stream;

        const recorder = new MediaRecorder(stream, { mimeType: mime });
        recorderRef.current = recorder;
        chunksRef.current = [];

        recorder.ondataavailable = (e: BlobEvent) => {
          if (e.data.size > 0) {
            chunksRef.current.push(e.data);
          }
        };

        recorder.onstop = () => {
          const captured = chunksRef.current;
          const finalMime = mimeRef.current ?? mime;
          const blob = captured.length > 0 ? new Blob(captured, { type: finalMime }) : null;

          // Pitfall 4: stop tracks so the browser mic indicator clears.
          const s = streamRef.current;
          if (s) {
            for (const t of s.getTracks()) {
              t.stop();
            }
          }
          streamRef.current = null;
          recorderRef.current = null;
          chunksRef.current = [];

          handlers.onStop(blob);
        };

        recorder.start();
        handlers.onStart();

        // 30s auto-stop (D-08). Cleared by stop() if user taps early (Pitfall 5).
        timerRef.current = window.setTimeout(() => {
          stop();
        }, MAX_DURATION_MS);
      }, [handlers, stop]);

      return { start, stop };
    }
    ```

    Constraints:
    - Do not `useEffect` to auto-start. Caller (Plan 05's TalkButton onClick) drives start/stop.
    - Do not throw out of `start`/`stop`. All paths go through handler callbacks.
    - No `any`. `err` is narrowed via `instanceof DOMException`.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F "'use client'" lib/audio/useRecorder.ts && grep -F "export function useRecorder" lib/audio/useRecorder.ts && grep -F "export interface RecorderHandlers" lib/audio/useRecorder.ts && grep -F "MAX_DURATION_MS = 30_000" lib/audio/useRecorder.ts && grep -F "NotAllowedError" lib/audio/useRecorder.ts && grep -F "getTracks()" lib/audio/useRecorder.ts && grep -F "this browser" lib/audio/useRecorder.ts; test $? -ne 0 || (echo "Korean error string check failed" && false) && grep -F "이 브라우저는 음성 녹음을 지원하지 않아요." lib/audio/useRecorder.ts && grep -F "마이크에 접근할 수 없어요." lib/audio/useRecorder.ts</automated>
  </verify>
  <done>useRecorder.ts exports the hook + RecorderHandlers interface, properly cleans up MediaStream tracks and the 30s timer, routes denial vs other errors through distinct callbacks, no silent swallow, tsc passes.</done>
  <acceptance_criteria>
    - File `frontend/lib/audio/useRecorder.ts` exists with `'use client'` as the first non-comment line
    - Contains `export function useRecorder(handlers: RecorderHandlers): RecorderControls`
    - Contains `export interface RecorderHandlers` with exactly 4 callbacks: `onStart`, `onStop`, `onPermissionDenied`, `onError`
    - Contains the constant `MAX_DURATION_MS = 30_000`
    - Contains string `'NotAllowedError'` and `'PermissionDeniedError'`
    - Contains `navigator.mediaDevices.getUserMedia({ audio: true })`
    - Contains `s.getTracks()` (or `stream.getTracks()`) followed by `.stop()` — verifies Pitfall 4 fix
    - Contains the exact Korean strings `'이 브라우저는 음성 녹음을 지원하지 않아요.'` and `'마이크에 접근할 수 없어요.'`
    - Contains `import { pickMimeType } from './pickMimeType'`
    - Contains zero occurrences of empty `catch {}` (grep regex `catch\s*\(\s*\)\s*\{\s*\}` and `catch\s*\{\s*\}` return no matches)
    - Contains zero occurrences of the literal token `any` (`grep -w any` returns no matches)
    - Contains `window.clearTimeout(timerRef.current)` (Pitfall 5 fix)
    - `cd frontend && npx tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto" tdd="false">
  <name>Task 2: TalkButton component at frontend/components/audio/TalkButton.tsx (5 visual states, 96px disc + 132px ring)</name>
  <files>frontend/components/audio/TalkButton.tsx</files>
  <read_first>
    - frontend/lib/state/conversation.ts (Plan 02 — for RecState type)
    - frontend/lib/utils.ts (for cn helper)
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § "Component Inventory → TalkButton" + § "Color → reserved-for list" + § "Copywriting Contract → Primary CTA (TalkButton)"
    - DESIGN.md § Decisions Log (2026-05-25 entries for "Mic idle", "Recording (stop) button", "Mic idle ring vs Recording pulse ring 동일 사이즈")
    - .planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md § D-12
  </read_first>
  <action>
    Create new directory `frontend/components/audio/` and new file `frontend/components/audio/TalkButton.tsx`. Implement the 5-state visual mapping per CONTEXT D-12 and UI-SPEC.

    **Props contract:**
    ```typescript
    interface TalkButtonProps {
      rec: RecState;                          // from conversation reducer
      disabled?: boolean;                     // true while sessionId is bootstrapping
      onPressStart: () => void;               // wired to useRecorder.start in Plan 05
      onPressStop: () => void;                // wired to useRecorder.stop in Plan 05
    }
    ```

    The component is stateless re: rec — `rec` flows in from the parent reducer. The button decides which handler to call by inspecting `rec.kind`:
    - `idle` or `error` → onPressStart
    - `recording` → onPressStop
    - `processing` or `speaking` → no-op (button is non-interactive in those states; visually same as recording per D-12, but pointer-events disabled to prevent double-fire)

    **Visual mapping (verbatim from UI-SPEC § Color reserved-for list + DESIGN.md decisions log 2026-05-25):**

    | rec.kind | Outer ring (132×132) | Disc (96×96) | Inner icon |
    |----------|----------------------|--------------|------------|
    | idle | `bg-primary/18` (orange 18%) | `bg-primary` | white mic SVG |
    | recording | `bg-error/22` (red 22%) | `bg-error` | white rounded-square (radius 6) |
    | processing | same as recording | same as recording | same as recording |
    | speaking | same as recording | same as recording | same as recording |
    | error | same as idle | same as idle | same as idle |

    Touch target = 96px disc (D-12; UI-SPEC § Spacing). Use `aria-label` from this map (UI-SPEC § Copywriting Contract):

    ```typescript
    const ARIA: Record<RecState['kind'], string> = {
      idle: '녹음 시작',
      recording: '녹음 정지',
      processing: '처리 중',
      speaking: 'Pally가 응답 중',
      error: '녹음 시작',
    };
    ```

    Press feedback: `active:scale-95 transition-transform duration-150` (DESIGN.md § Motion "Mic press: scale 0.95, 150ms" + UI-SPEC § Interaction Timing — magic number comment required).

    **Implementation skeleton:**
    ```tsx
    'use client';

    import { cn } from '@/lib/utils';
    import type { RecState } from '@/lib/state/conversation';

    export interface TalkButtonProps {
      rec: RecState;
      disabled?: boolean;
      onPressStart: () => void;
      onPressStop: () => void;
    }

    // aria-labels per UI-SPEC § Copywriting Contract → Primary CTA (TalkButton).
    const ARIA: Record<RecState['kind'], string> = {
      idle: '녹음 시작',
      recording: '녹음 정지',
      processing: '처리 중',
      speaking: 'Pally가 응답 중',
      error: '녹음 시작',
    };

    function MicIcon() {
      // 24x24 white mic icon — pulled to match Figma TalkButton ComponentSet 441:30, state=idle.
      return (
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3z"
            fill="#ffffff"
          />
          <path
            d="M5 11a7 7 0 0 0 14 0M12 18v3"
            stroke="#ffffff"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      );
    }

    function StopIcon() {
      // 20x20 white rounded square (radius 6) — Figma state=thinking.
      return (
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
          <rect x="2" y="2" width="18" height="18" rx="6" fill="#ffffff" />
        </svg>
      );
    }

    export function TalkButton({ rec, disabled = false, onPressStart, onPressStop }: TalkButtonProps) {
      const isRecordingFamily = rec.kind === 'recording' || rec.kind === 'processing' || rec.kind === 'speaking';
      const isInteractive = !disabled && (rec.kind === 'idle' || rec.kind === 'error' || rec.kind === 'recording');

      // Ring color: red family while recording/processing/speaking, otherwise orange.
      const ringClass = isRecordingFamily
        ? 'bg-error/[0.22]'
        : 'bg-primary/[0.18]';
      // Disc fill: red while recording-family, orange otherwise.
      const discClass = isRecordingFamily ? 'bg-error' : 'bg-primary';

      const handleClick = () => {
        if (!isInteractive) return;
        if (rec.kind === 'recording') {
          onPressStop();
        } else {
          onPressStart();
        }
      };

      return (
        <div className="relative flex items-center justify-center">
          {/* Decorative outer ring — 132x132, not a hit target */}
          <div
            aria-hidden="true"
            className={cn(
              'absolute rounded-full',
              'w-[132px] h-[132px]',
              ringClass,
            )}
          />
          {/* Primary disc — 96x96 hit target */}
          <button
            type="button"
            aria-label={ARIA[rec.kind]}
            aria-disabled={!isInteractive}
            disabled={!isInteractive}
            onClick={handleClick}
            className={cn(
              'relative flex items-center justify-center',
              'w-24 h-24 rounded-full',           // 96x96 disc
              discClass,
              'shadow-lg',
              // Press feedback: scale 0.95 over 150ms (DESIGN.md § Motion / UI-SPEC § Interaction Timing).
              'transition-transform duration-150 active:scale-95',
              'disabled:cursor-default',
            )}
          >
            {isRecordingFamily ? <StopIcon /> : <MicIcon />}
          </button>
        </div>
      );
    }
    ```

    Constraints:
    - `'use client'` at top (button is interactive).
    - Named export only — `export function TalkButton`.
    - **No `opacity-50`** on disabled — UI-SPEC § Anti-Patterns #5 forbids it for BottomNav, and the same principle applies (use cursor + aria-disabled).
    - **No hardcoded hex in className** — `bg-primary` / `bg-error`, not `bg-[#fe9012]`. The 18% / 22% opacity ring uses Tailwind arbitrary alpha syntax `bg-primary/[0.18]` (this IS allowed — it's a token + opacity, not raw hex).
    - **Inline SVG OK** — RESEARCH § Standard Stack says no `lucide-react` install.
    - The "processing"/"speaking" branch is visually identical to "recording" per D-12 but the disc is non-interactive (`disabled` prop) so the user can't double-fire onPressStop.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F "'use client'" components/audio/TalkButton.tsx && grep -F "export function TalkButton" components/audio/TalkButton.tsx && grep -F "녹음 시작" components/audio/TalkButton.tsx && grep -F "녹음 정지" components/audio/TalkButton.tsx && grep -F "처리 중" components/audio/TalkButton.tsx && grep -F "Pally가 응답 중" components/audio/TalkButton.tsx && grep -F "bg-primary" components/audio/TalkButton.tsx && grep -F "bg-error" components/audio/TalkButton.tsx && grep -F "w-24 h-24" components/audio/TalkButton.tsx && grep -F "active:scale-95" components/audio/TalkButton.tsx && ! grep -F "#fe9012" components/audio/TalkButton.tsx && ! grep -F "#ef4444" components/audio/TalkButton.tsx && ! grep -F "opacity-50" components/audio/TalkButton.tsx</automated>
  </verify>
  <done>TalkButton.tsx renders 5 visual variants driven by `rec.kind`, all 4 aria-labels present, 96px disc + 132px ring, press scale 0.95, no inline hex, no opacity-50; tsc passes.</done>
  <acceptance_criteria>
    - File `frontend/components/audio/TalkButton.tsx` exists with `'use client'` directive
    - Contains `export function TalkButton(`
    - Contains `import type { RecState } from '@/lib/state/conversation'`
    - Contains `import { cn } from '@/lib/utils'`
    - Contains all 4 distinct aria-label strings: `'녹음 시작'`, `'녹음 정지'`, `'처리 중'`, `'Pally가 응답 중'`
    - Contains the literal `w-24 h-24` (96px disc per UI-SPEC § Spacing)
    - Contains the literal `w-[132px] h-[132px]` (132px decorative ring)
    - Contains `bg-primary` and `bg-error` (uses Tailwind tokens, not raw hex)
    - Contains `active:scale-95` and `duration-150` (DESIGN.md motion)
    - Contains `shadow-lg`
    - File contains zero occurrences of raw hex literals `#fe9012` or `#ef4444` (color tokens enforce)
    - File contains zero occurrences of `opacity-50` (UI-SPEC § Anti-Patterns #5)
    - File contains zero occurrences of `export default`
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
| Browser ⇄ Mic | `getUserMedia({ audio: true })` triggers the OS-level permission prompt. User consent is the access gate. |
| MediaRecorder → App | Captured audio Blob is held in component memory only; 1A does not transmit or persist it. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01A-03-01 | Information Disclosure | MediaStream tracks not stopped → mic indicator persists, recording leaks beyond UI intent | mitigate | useRecorder.onstop calls `stream.getTracks().forEach(t => t.stop())` (Pitfall 4 fix). Acceptance grep verifies. |
| T-01A-03-02 | DoS | 30s timer fires after early stop → double `MediaRecorder.stop()` throws DOMException | mitigate | `stop()` clears `timerRef` before calling MediaRecorder.stop and guards on `state !== 'inactive'` (Pitfall 5). |
| T-01A-03-03 | Tampering | Empty error catch swallows browser denial silently | mitigate | `try/catch` in `start()` routes `NotAllowedError` to `onPermissionDenied` and other errors to `onError(message)` — no empty catch. Acceptance grep verifies. |
| T-01A-03-04 | Repudiation | Pressing TalkButton during processing fires duplicate `onPressStop` → race | mitigate | `isInteractive` guard returns early for processing/speaking states; `disabled` attribute also set. |
| T-01A-03-05 | Spoofing | Untrusted text in aria-label | accept | All 4 aria-label strings are compile-time Korean literals from UI-SPEC. No user input. |
| T-01A-03-06 | Information Disclosure | MediaRecorder error name leaked into UI message | mitigate | `useRecorder.start()` maps known error names to fixed Korean strings; the raw `err.message` is never forwarded to the UI handler. |
</threat_model>

<verification>
- `cd frontend && npx tsc --noEmit` passes
- `cd frontend && npm run build` passes
- Manual verification deferred to Plan 05 E2E (Playwright on 402px viewport at idle/recording state)
- No imports from `frontend/components/pally/*` or `frontend/lib/types/character.ts`
</verification>

<success_criteria>
1. `useRecorder` hook compiles + handles permission denial, MIME unsupported, generic error, 30s auto-stop, MediaStream cleanup.
2. TalkButton renders 5 visual states driven by `RecState.kind`, 96px disc + 132px ring, no raw hex, no opacity-50.
3. aria-labels match all 5 RecState kinds.
4. `npm run build` succeeds.
</success_criteria>

<output>
After completion, create `.planning/phases/01A-fe-screens-audio-shell/01A-03-SUMMARY.md`
</output>
