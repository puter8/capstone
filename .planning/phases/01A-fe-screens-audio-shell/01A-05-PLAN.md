---
phase: 01A
plan: 05
type: execute
wave: 3
depends_on: ["01A-01", "01A-02", "01A-03", "01A-04"]
files_modified:
  - frontend/app/page.tsx
autonomous: false
requirements: [MAIN-01, CHAT-01]
must_haves:
  truths:
    - "Visiting / at 402px shows the empty-state Korean heading, the Pally 262×262 placeholder, the orange TalkButton, and the 5-tab BottomNav — all in one viewport"
    - "Tapping TalkButton transitions idle → recording (red disc) → (tap or 30s) → processing → speaking → idle within ≤ 2.4s on a normal browser (800ms mock + 1500ms speaking hold + UI overhead)"
    - "After one successful mock turn, the top ChatBubble shows YOU: <utterance> and Pally: \"What a bummer! But don't be too sad.\""
    - "Tapping the chevron opens HistorySheet showing the just-completed turn as SMS-style rows; tapping the backdrop or handle closes it"
    - "Permission denial surfaces \"마이크 권한이 필요해요\" toast, auto-dismisses in 4s, recorder returns to idle"
    - "sessionId is persisted in localStorage under key 'pally:sessionId' and reused across refresh"
    - "BottomNav 5 tabs render but tapping does nothing (no navigation, no toast)"
  artifacts:
    - path: "frontend/app/page.tsx"
      provides: "Main conversation screen — assembles all Wave-2 components, owns the reducer, wires the recorder, bootstraps sessionId"
      contains: "useReducer"
      min_lines: 80
  key_links:
    - from: "frontend/app/page.tsx"
      to: "frontend/lib/state/conversation.ts"
      via: "useReducer(reducer, initialState)"
      pattern: "useReducer\\(reducer"
    - from: "frontend/app/page.tsx"
      to: "frontend/lib/mocks/chat-mock.ts"
      via: "mockChat({utterance, session_id, level})"
      pattern: "mockChat"
    - from: "frontend/app/page.tsx"
      to: "frontend/lib/audio/useRecorder.ts"
      via: "useRecorder({onStart, onStop, onPermissionDenied, onError})"
      pattern: "useRecorder"
    - from: "frontend/app/page.tsx"
      to: "localStorage 'pally:sessionId'"
      via: "useEffect bootstrap (SSR-safe)"
      pattern: "pally:sessionId"
---

<objective>
Wave 3 — Main page assembly + E2E verification.
Plans 01~04이 만든 모든 조각(토큰, 타입, reducer, mock, MIME helper, useRecorder, TalkButton, PallyPlaceholder, ChatBubble, HistoryRow, HistorySheet, BottomNav, Toast)을 `frontend/app/page.tsx` 하나의 client component로 조립한다. RESEARCH § "app/page.tsx skeleton" 패턴 그대로.

Purpose: Phase 1A의 4가지 Success Criteria (ROADMAP)를 한 화면에서 만족시킨다. mock 흐름 (rec → 녹음 → 800ms → speaking → idle)이 처음부터 끝까지 동작하고, 모바일 402px 뷰포트에서 사람 검증으로 확인한다.

Output: page.tsx (전체 main screen). E2E 검증 checkpoint로 마무리.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md
@.planning/phases/01A-fe-screens-audio-shell/01A-RESEARCH.md
@.planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md
@frontend/lib/state/conversation.ts
@frontend/lib/audio/useRecorder.ts
@frontend/lib/mocks/chat-mock.ts
@frontend/lib/types/message.ts
@frontend/lib/types/chat.ts
@frontend/components/audio/TalkButton.tsx
@frontend/components/chat/PallyPlaceholder.tsx
@frontend/components/chat/ChatBubble.tsx
@frontend/components/chat/HistorySheet.tsx
@frontend/components/nav/BottomNav.tsx
@frontend/components/ui/Toast.tsx
</context>

<interfaces>
<!-- All Plan 02/03/04 outputs are now imports here -->

```typescript
// State
import { reducer, initialState } from '@/lib/state/conversation';
// Recorder
import { useRecorder } from '@/lib/audio/useRecorder';
// Mock transport (SINGLE swap point per D-01)
import { mockChat } from '@/lib/mocks/chat-mock';
// Types
import type { Message } from '@/lib/types/message';
// Components
import { TalkButton } from '@/components/audio/TalkButton';
import { PallyPlaceholder } from '@/components/chat/PallyPlaceholder';
import { ChatBubble } from '@/components/chat/ChatBubble';
import { HistorySheet } from '@/components/chat/HistorySheet';
import { BottomNav } from '@/components/nav/BottomNav';
import { Toast } from '@/components/ui/Toast';
```

<!-- Layout zones (UI-SPEC § Component Inventory + DESIGN.md § Layout) -->
<!--
  Three zones inside max-w-[402px] container, padded bottom-16 (above fixed BottomNav):

  Zone 1 (top):    ChatBubble (or empty state inside it)
                   + Toast (when rec.kind === 'error')
  Zone 2 (center): PallyPlaceholder, vertically centered
  Zone 3 (bottom): TalkButton, ~96px above BottomNav (sticky via flex layout)

  HistorySheet: fixed overlay, z-40, rendered only when historyOpen === true
  BottomNav:    fixed bottom-0, z-30
-->

<!-- Locked utterance text (UI-SPEC § Copywriting Contract → Mock chat fixture) -->
<!-- "I had no lunch — I'm on a diet" (Figma sample; matches RESEARCH Open Q #1 recommendation) -->
</interfaces>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Assemble main conversation screen in frontend/app/page.tsx</name>
  <files>frontend/app/page.tsx</files>
  <read_first>
    - frontend/app/page.tsx (current — Phase 0 placeholder, only renders <main>Pally</main>)
    - frontend/lib/state/conversation.ts (Plan 02 Task 2 — reducer + Action variants)
    - frontend/lib/audio/useRecorder.ts (Plan 03 Task 1 — handler shape)
    - frontend/lib/mocks/chat-mock.ts (Plan 02 Task 3 — single fixture, 800ms latency)
    - frontend/lib/types/message.ts (Message shape for dispatching rec/processed)
    - .planning/phases/01A-fe-screens-audio-shell/01A-RESEARCH.md § "app/page.tsx skeleton" (reference impl)
    - .planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md § D-16 (sessionId bootstrap pattern)
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § "Component Inventory" (layout zones) + § "Interaction Timing" (1500ms speaking hold)
  </read_first>
  <action>
    Replace the entire contents of `frontend/app/page.tsx` with the main conversation screen. The file MUST be a client component (`'use client'`), use `useReducer(reducer, initialState)`, bootstrap sessionId in `useEffect` (SSR-safe per RESEARCH Pitfall 3 + Pitfall 6), drive the recorder via `useRecorder`, and render all 6 components from Plan 03/04.

    Locked utterance text per UI-SPEC § Copywriting Contract: `"I had no lunch — I'm on a diet"` — matches Figma sample.

    Locked sessionId localStorage key per D-16: `'pally:sessionId'`.

    Locked speaking-hold per D-10/D-13: 1500ms after `rec/processed`, then dispatch `rec/speakingDone`.

    ```tsx
    'use client';

    import { useEffect, useReducer } from 'react';
    import { reducer, initialState } from '@/lib/state/conversation';
    import { useRecorder } from '@/lib/audio/useRecorder';
    import { mockChat } from '@/lib/mocks/chat-mock';
    import type { Message } from '@/lib/types/message';
    import { TalkButton } from '@/components/audio/TalkButton';
    import { PallyPlaceholder } from '@/components/chat/PallyPlaceholder';
    import { ChatBubble } from '@/components/chat/ChatBubble';
    import { HistorySheet } from '@/components/chat/HistorySheet';
    import { BottomNav } from '@/components/nav/BottomNav';
    import { Toast } from '@/components/ui/Toast';

    // localStorage key — Plan 1A is the only writer (D-16). 'pally:*' prefix per RESEARCH Discretion.
    const SESSION_KEY = 'pally:sessionId';

    // 1500ms speaking hold per CONTEXT D-10 + D-13 + UI-SPEC § Interaction Timing.
    // 1A does not play TTS; the speaking state simulates the period when audio
    // *would* be playing. Phase 2 replaces with real <audio> duration.
    const SPEAKING_HOLD_MS = 1500;

    // Locked utterance for the mock per UI-SPEC § Copywriting Contract → "Mock chat fixture".
    // Matches the Figma sample so a demo screenshot lines up.
    const MOCK_UTTERANCE = "I had no lunch — I'm on a diet";

    export default function Page() {
      const [state, dispatch] = useReducer(reducer, initialState);

      // Bootstrap sessionId (D-16). SSR-safe — only touches localStorage inside useEffect.
      useEffect(() => {
        let id = window.localStorage.getItem(SESSION_KEY);
        if (!id) {
          id = crypto.randomUUID();
          window.localStorage.setItem(SESSION_KEY, id);
        }
        dispatch({ type: 'sessionId/set', id });
      }, []);

      // Auto-transition speaking → idle after 1500ms (D-10).
      useEffect(() => {
        if (state.rec.kind !== 'speaking') return;
        const t = window.setTimeout(() => {
          dispatch({ type: 'rec/speakingDone' });
        }, SPEAKING_HOLD_MS);
        return () => window.clearTimeout(t);
      }, [state.rec.kind]);

      const recorder = useRecorder({
        onStart: () => {
          dispatch({ type: 'rec/start' });
        },
        onStop: async (_blob) => {
          // The Blob is intentionally ignored in 1A (D-09). Phase 2 will FormData this.
          dispatch({ type: 'rec/stop' });

          // SessionId must exist by now (bootstrap ran on mount). Surface explicitly otherwise.
          const sid = state.sessionId;
          if (!sid) {
            dispatch({
              type: 'rec/error',
              reason: 'generic',
              message: '세션이 준비되지 않았어요.',
            });
            return;
          }

          try {
            const resp = await mockChat({
              utterance: MOCK_UTTERANCE,
              session_id: sid,
              level: 'B1',
            });
            const now = new Date().toISOString();
            const userMsg: Message = {
              id: crypto.randomUUID(),
              sessionId: sid,
              role: 'user',
              transcript: resp.transcript,
              createdAt: now,
            };
            const pallyMsg: Message = {
              id: crypto.randomUUID(),
              sessionId: sid,
              role: 'pally',
              transcript: resp.reply,
              createdAt: now,
            };
            dispatch({ type: 'rec/processed', userMsg, pallyMsg });
          } catch (err) {
            // No silent swallow — CLAUDE.md §7. Surface generic Korean message;
            // do NOT forward raw err.message to the UI to avoid leaking implementation details.
            // eslint-disable-next-line no-console
            console.error('mockChat failed:', err);
            dispatch({
              type: 'rec/error',
              reason: 'generic',
              message: '다시 한 번 말해주세요',
            });
          }
        },
        onPermissionDenied: () => {
          dispatch({
            type: 'rec/error',
            reason: 'permission-denied',
            message: '마이크 권한이 필요해요',
          });
        },
        onError: (message) => {
          dispatch({
            type: 'rec/error',
            reason: 'generic',
            message,
          });
        },
      });

      // sessionId not yet bootstrapped → TalkButton disabled for the first frame.
      const buttonDisabled = state.sessionId === null;

      return (
        <main className="relative mx-auto w-full max-w-[402px] min-h-screen bg-surface flex flex-col">
          {/* Zone 1: Top — ChatBubble */}
          <div className="px-4 pt-6">
            <ChatBubble
              messages={state.messages}
              historyOpen={state.historyOpen}
              onToggleHistory={() => dispatch({ type: 'history/toggle' })}
            />
          </div>

          {/* Zone 2: Center — Pally placeholder, vertically centered */}
          <div className="flex-1 flex items-center justify-center">
            <PallyPlaceholder />
          </div>

          {/* Zone 3: Bottom — Toast (when error) + TalkButton, padded above BottomNav */}
          <div className="px-4 pb-24 flex flex-col items-center gap-3">
            <Toast
              message={state.rec.kind === 'error' ? state.rec.message : ''}
              visible={state.rec.kind === 'error'}
              onDismiss={() => dispatch({ type: 'rec/dismissError' })}
            />
            <TalkButton
              rec={state.rec}
              disabled={buttonDisabled}
              onPressStart={() => {
                void recorder.start();
              }}
              onPressStop={() => {
                recorder.stop();
              }}
            />
          </div>

          {/* Fixed bottom nav — 5 disabled tabs */}
          <BottomNav />

          {/* History sheet overlay — rendered only when open */}
          <HistorySheet
            open={state.historyOpen}
            messages={state.messages}
            onClose={() => dispatch({ type: 'history/toggle' })}
          />
        </main>
      );
    }
    ```

    Constraints:
    - `'use client'` first non-comment line.
    - `export default function Page()` — page files MUST use default export per CLAUDE.md §7.
    - NO call to `fetch`. NO reference to `NEXT_PUBLIC_BACKEND_URL`. NO `new Audio()` (D-10 forbids TTS playback in 1A).
    - NO inline mocks — every chat call goes through `mockChat()` import.
    - All localStorage access wrapped in `useEffect` (Pitfall 3 + 6).
    - Empty catch forbidden — the try/catch wraps `mockChat` and dispatches `rec/error` with a fixed Korean string. The raw error is `console.error`ed but NOT forwarded to UI (defense). The `eslint-disable-next-line no-console` comment is acceptable here because this is the explicit error-surfacing path the spec requires.
    - `void recorder.start()` — fire-and-forget; recorder routes failures through handler callbacks.
    - The TalkButton receives `disabled={buttonDisabled}` so the user can't click during the first-frame sessionId race.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F "'use client'" app/page.tsx && grep -F "export default function Page" app/page.tsx && grep -F "useReducer(reducer, initialState)" app/page.tsx && grep -F "import { mockChat } from '@/lib/mocks/chat-mock'" app/page.tsx && grep -F "import { useRecorder } from '@/lib/audio/useRecorder'" app/page.tsx && grep -F "'pally:sessionId'" app/page.tsx && grep -F "SPEAKING_HOLD_MS = 1500" app/page.tsx && grep -F "I had no lunch — I'm on a diet" app/page.tsx && grep -F "마이크 권한이 필요해요" app/page.tsx && grep -F "다시 한 번 말해주세요" app/page.tsx && ! grep -F "NEXT_PUBLIC_BACKEND_URL" app/page.tsx && ! grep -F "new Audio(" app/page.tsx && ! grep -F "fetch(" app/page.tsx && cd /Users/clairelee/Desktop/claude-project/capstone-latest/frontend && npm run build 2>&1 | tail -15</automated>
  </verify>
  <done>page.tsx assembles all Wave-2 components, owns the reducer + recorder, bootstraps sessionId in useEffect, dispatches Korean error strings on denial/generic failure, does NOT play TTS, does NOT call fetch, builds clean.</done>
  <acceptance_criteria>
    - File `frontend/app/page.tsx` starts with `'use client';`
    - Contains `export default function Page()`
    - Contains `useReducer(reducer, initialState)`
    - Contains the import `import { mockChat } from '@/lib/mocks/chat-mock'`
    - Contains the import `import { useRecorder } from '@/lib/audio/useRecorder'`
    - Contains the literal `'pally:sessionId'`
    - Contains the constant `SPEAKING_HOLD_MS = 1500`
    - Contains the literal `"I had no lunch — I'm on a diet"` (Figma fixture)
    - Contains the literal `'마이크 권한이 필요해요'` (permission denial copy)
    - Contains the literal `'다시 한 번 말해주세요'` (generic error copy)
    - Contains `crypto.randomUUID()` (called only inside useEffect / handler — not at module scope)
    - Contains `window.localStorage` inside a `useEffect` (Pitfall 3 SSR guard)
    - File contains zero occurrences of `NEXT_PUBLIC_BACKEND_URL` (real backend wiring is Phase 2)
    - File contains zero occurrences of `new Audio(` (TTS playback forbidden by D-10)
    - File contains zero occurrences of `fetch(` (only mockChat is the data path)
    - File contains zero occurrences of the literal token `any` (`grep -w any` returns no matches)
    - `cd frontend && npx tsc --noEmit` exits 0
    - `cd frontend && npm run build` exits 0 with no warnings
    - File line count ≥ 80
  </acceptance_criteria>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Mobile 402px E2E verification (Playwright MCP or /browse)</name>
  <files>frontend/app/page.tsx (verification target — no edits in this task)</files>
  <read_first>
    - frontend/app/page.tsx (Task 1 output)
    - .planning/ROADMAP.md § "Phase 1A: FE Screens & Audio Shell" Success Criteria #1-4 (the 4 outcomes this task gates)
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § "Visual Reference" Figma frame IDs for cross-checking screenshots
  </read_first>
  <what-built>
    The entire Phase 1A surface is now wired:
    - Main page renders empty state at first load
    - Tapping the TalkButton goes idle → recording (red disc + ring) → processing/speaking → idle
    - After one turn, ChatBubble shows YOU + Pally transcripts
    - Chevron toggles HistorySheet with SMS-style rows
    - BottomNav shows 5 disabled tabs (홈/히스토리/새 대화/랭킹/내 정보), center FAB is black not orange
    - Permission denial surfaces "마이크 권한이 필요해요" toast (auto-dismiss 4s)
    - sessionId persists across refresh in localStorage
  </what-built>
  <how-to-verify>
    Use Playwright MCP (or `/browse` headed) — synthetic device 402×844 (iPhone 12/13/14 logical width).
    Start dev server (if not running): `cd frontend && npm run dev` (background).

    1. **Empty state at 402px:**
       - Open http://localhost:3000 in a 402px viewport
       - Snapshot — assert the heading "오늘은 어떤 이야기를 해볼까요?" is visible
       - Assert the subtitle "마이크를 눌러 영어로 말해보세요" is visible
       - Assert the Pally placeholder SVG is centered (262×262)
       - Assert the orange TalkButton disc is visible at the bottom
       - Assert the BottomNav shows all 5 labels: 홈, 히스토리, 새 대화, 랭킹, 내 정보
       - Confirm: page does NOT scroll (everything fits in viewport at 402×844)

    2. **Mock turn happy path:**
       - Click the TalkButton
       - Allow microphone permission in the browser prompt
       - Expect: disc turns red (recording) with red 22%-opacity outer ring
       - Wait ~3 seconds, then click TalkButton again to stop
       - Expect: state moves through processing → speaking → idle within ~2.4s (800ms mock + 1500ms speaking hold)
       - Expect: ChatBubble now shows "YOU I had no lunch — I'm on a diet" (teal label) AND "Pally What a bummer! But don't be too sad." (orange label)
       - Browser DevTools → Application → Local Storage: confirm `pally:sessionId` key contains a UUID

    3. **History sheet toggle:**
       - Click the chevron in the ChatBubble
       - Expect: HistorySheet overlay slides down, showing both messages as SMS-style rows with proper YOU=teal / Pally=orange labels
       - Click backdrop or handle → sheet closes

    4. **Permission denial:**
       - Browser: revoke microphone permission (chrome://settings/content/microphone → block localhost)
       - Refresh page, click TalkButton
       - Expect: deny prompt OR direct denial
       - Expect: Toast appears with "마이크 권한이 필요해요"
       - Expect: Toast auto-dismisses after 4s
       - Expect: TalkButton returns to idle (orange)

    5. **BottomNav inertness:**
       - Click each of the 5 BottomNav tabs in turn
       - Expect: nothing happens — no navigation, no toast, no console errors
       - Expect: 새 대화 (+) FAB is BLACK (#1a1a1a), NOT orange

    6. **sessionId persistence:**
       - Note the UUID in localStorage
       - Refresh the page
       - Expect: same UUID still in localStorage
       - Expect: ChatBubble back to empty state (D-18: no message persistence in 1A)

    Take screenshots of states 1, 2 (after turn), 3 (history open), 4 (toast visible) and attach to the SUMMARY.

    Run `cd frontend && npm run build` one more time to confirm production build succeeds.

    If any step fails — STOP and surface the issue. Do NOT mark this task done unless every step above passes.
  </how-to-verify>
  <action>
    Execute the 6 verification steps above via Playwright MCP (`mcp__playwright__*`) or the project `/browse` headed mode.

    Sequence:
    1. Spawn dev server: `cd frontend && npm run dev` (run in background).
    2. For each of steps 1-6 above, use Playwright to navigate, snapshot, and assert. Record screenshots into `.planning/phases/01A-fe-screens-audio-shell/screenshots/01A-step{N}.png` (or similar).
    3. If any expectation fails, stop and surface the failure with the exact step number + symptom. Do NOT amend the production code from inside this checkpoint task — instead, report to the user, who decides whether to revise Plan 03/04/05 and re-execute.
    4. After all 6 steps pass, also run `cd frontend && npm run build` one final time and capture the tail of the output.
    5. Wait for the user signal "approved" before marking this task complete.
  </action>
  <verify>
    <automated>cd frontend && npm run build 2>&1 | tail -10 && ls .planning/phases/01A-fe-screens-audio-shell/screenshots/ 2>/dev/null</automated>
  </verify>
  <done>All 6 verification steps pass with screenshots attached; production build still succeeds; user has typed "approved".</done>
  <acceptance_criteria>
    - All 6 verification steps documented in <how-to-verify> pass (no Korean copy missing, no scroll, mock cycle completes within ~2.4s, history sheet toggles, permission denial surfaces correct toast, BottomNav inert, sessionId persists)
    - Screenshots captured for at least steps 1, 2 (after turn), 3 (history open), 4 (toast visible)
    - `cd frontend && npm run build` exits 0
    - User has explicitly typed "approved" in the resume signal
  </acceptance_criteria>
  <resume-signal>Type "approved" with attached screenshots, or describe the failing step (which of 1-6, exact symptom) to revise.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User → Browser → MediaRecorder | Mic permission gate. |
| Browser → localStorage | sessionId persistence (no PII, low value). |
| In-process mock | Data path stays inside the bundle. Phase 2 swaps this for a real network call and the boundary moves to fetch. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01A-05-01 | Information Disclosure | Raw error message from mockChat surfaced to UI | mitigate | The page.tsx catch block dispatches the fixed Korean string `'다시 한 번 말해주세요'` (not `err.message`); the raw exception is logged via `console.error` only, server/dev console. Acceptance grep verifies. |
| T-01A-05-02 | Tampering | localStorage tampering switches sessionId to attacker-controlled value | accept | sessionId is opaque + has no PII + no auth. Worst case is the attacker resumes someone else's anonymous demo turn. Acceptable for MVP per RESEARCH § Security Domain. |
| T-01A-05-03 | DoS | speaking-state timeout leaked on rapid rec spam | mitigate | useEffect cleanup returns `window.clearTimeout(t)`. Verified via grep in Plan 03 Task 1 and Plan 04 Task 1; pattern reused here. |
| T-01A-05-04 | DoS | sessionId bootstrap race — first click before useEffect fires → mockChat called with null sid | mitigate | `buttonDisabled = state.sessionId === null` propagated to TalkButton; user cannot click during the bootstrap frame. |
| T-01A-05-05 | Repudiation | Hydration mismatch from `crypto.randomUUID()` at module scope | mitigate | Per Pitfall 6, `randomUUID` is called only inside `useEffect` and handler bodies (verified by grep — it must NOT appear in `initialState` or any module-level constant). |
| T-01A-05-06 | XSS | Mock fixture text rendered into ChatBubble | accept | All fixture strings are compile-time constants. React auto-escapes. No `dangerouslySetInnerHTML`. |
| T-01A-05-07 | Information Disclosure | Microphone permission persists across refresh, browser indicator stays on | mitigate | `useRecorder.onstop` releases tracks (Plan 03 Task 1 acceptance verifies). |
</threat_model>

<verification>
- `cd frontend && npx tsc --noEmit` passes
- `cd frontend && npm run build` passes
- Manual Playwright/`/browse` checks 1–6 in the Task 2 checkpoint all pass
- `grep -r "fetch(" frontend/app frontend/components frontend/lib 2>/dev/null | grep -v node_modules` returns no matches (mock-only)
- `grep -r "new Audio(" frontend/app frontend/components frontend/lib 2>/dev/null | grep -v node_modules` returns no matches (no TTS playback in 1A)
- `grep -r "NEXT_PUBLIC_BACKEND_URL" frontend/app frontend/components frontend/lib 2>/dev/null | grep -v node_modules` returns no matches (Phase 2 wiring)
- `test ! -d frontend/components/pally` exits 0 (Phase 1B namespace untouched)
- `test ! -d frontend/app/dev` exits 0 (Phase 1B `app/dev/pally` namespace untouched)
- `test ! -f frontend/lib/types/character.ts` exits 0 (Phase 1B namespace untouched)
</verification>

<success_criteria>
1. ROADMAP Phase 1A SC #1: 모바일 폭 ~402px에서 메인 화면이 보인다 (Pally placeholder + rec 버튼 + 5탭 BottomNav). ✓ (Playwright step 1)
2. ROADMAP Phase 1A SC #2: 상단 영역이 chevron 토글 가능, 펼치면 이전 발화 내용 표시. ✓ (Playwright step 3)
3. ROADMAP Phase 1A SC #3: Phase 0 UI 타입(Message/Session) import + mock 데이터로 화면 동작 검증. ✓ (Plan 02 + page.tsx Task 1)
4. ROADMAP Phase 1A SC #4: rec 버튼은 idle → recording → processing → speaking → idle/error 상태 cycle; 브라우저 권한 요청, 녹음 Blob 생성 동작; 실제 `NEXT_PUBLIC_BACKEND_URL` 연결은 Phase 2. ✓ (Playwright step 2 + 4)
5. `npm run build` succeeds without warnings.
6. No file inside `frontend/components/pally/`, `frontend/app/dev/`, no `frontend/lib/types/character.ts`, no edits in `backend/` / `ai/` / `supabase/` (directory boundary check).
</success_criteria>

<output>
After completion, create `.planning/phases/01A-fe-screens-audio-shell/01A-05-SUMMARY.md` summarizing:
- All 4 ROADMAP Phase 1A SCs cleared with Playwright evidence
- Files created (full list)
- The single swap point (`frontend/lib/mocks/chat-mock.ts mockChat`) for Phase 2 hand-off
- Known deferred items (Senior plan Phase B/C/D), reproduced from CONTEXT § Deferred Ideas
</output>
