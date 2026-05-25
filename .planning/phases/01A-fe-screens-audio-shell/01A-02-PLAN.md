---
phase: 01A
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/lib/types/chat.ts
  - frontend/lib/state/conversation.ts
  - frontend/lib/mocks/chat-mock.ts
  - frontend/lib/audio/pickMimeType.ts
autonomous: true
requirements: [MAIN-01, CHAT-01]
must_haves:
  truths:
    - "All wire types for /api/chat exist in TS and match Phase 1C Pydantic shape exactly (status / transcript / reply / tts_audio / axes / character / character_labels / hint_ko)"
    - "There is exactly ONE mock chat function (`mockChat`) — Phase 2's swap point"
    - "The reducer state machine covers all 5 rec states (idle / recording / processing / speaking / error) with discriminated unions; no unreachable state is constructible at compile time"
    - "MIME-type probe returns audio/webm;codecs=opus on Chrome/Firefox, audio/mp4 on Safari, null when nothing supported"
  artifacts:
    - path: "frontend/lib/types/chat.ts"
      provides: "ChatRequest / ChatResponse / Axes / CharacterParams / CharacterLabels / InlineHintKo TS types — mirrors Phase 1C backend/main.py exactly"
      exports: ["ChatRequest", "ChatResponse", "Axes", "CharacterParams", "CharacterLabels", "InlineHintKo"]
    - path: "frontend/lib/state/conversation.ts"
      provides: "RecState / ConversationState / Action discriminated unions + reducer + initialState"
      exports: ["RecState", "ConversationState", "Action", "reducer", "initialState"]
    - path: "frontend/lib/mocks/chat-mock.ts"
      provides: "Single export mockChat(req) — fixed 800ms latency, single Figma-sourced fixture"
      exports: ["mockChat"]
    - path: "frontend/lib/audio/pickMimeType.ts"
      provides: "MIME-type probe returning the first supported MediaRecorder MIME or null"
      exports: ["pickMimeType"]
  key_links:
    - from: "frontend/lib/mocks/chat-mock.ts"
      to: "frontend/lib/types/chat.ts"
      via: "import type"
      pattern: "import type \\{[^}]*ChatRequest[^}]*ChatResponse"
    - from: "frontend/lib/state/conversation.ts"
      to: "frontend/lib/types/message.ts"
      via: "import type Message"
      pattern: "from '@/lib/types/message'"
---

<objective>
Wave 1 foundation (parallel to Plan 01) — shared types + mock transport + reducer + MIME probe.
Phase 1A의 데이터 흐름 backbone을 만든다. 모든 후속 UI plan들이 import할 wire types, useReducer state machine, single-swap-point mock, MediaRecorder MIME helper를 한 번에 wire한다.

Purpose: 후속 plan(03 audio, 04 chat surfaces, 05 page assembly)이 type/state/transport 코드를 흩어 만들지 않고 이 4개 파일에서 import만 하도록 한다. CONTEXT.md D-01 "mock 함수는 단일 export"와 RESEARCH.md "every chat call MUST go through mockChat()"이 핵심 invariant.

Output: 4개 신규 파일 (types/chat.ts, state/conversation.ts, mocks/chat-mock.ts, audio/pickMimeType.ts). 모두 named export, TS strict 통과.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md
@.planning/phases/01A-fe-screens-audio-shell/01A-RESEARCH.md
@.planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md
@frontend/lib/types/message.ts
@frontend/lib/types/session.ts
@frontend/lib/utils.ts
</context>

<interfaces>
<!-- Existing Phase 0 types (consumed by this plan — do not modify) -->

From frontend/lib/types/message.ts:
```typescript
export type MessageRole = 'user' | 'pally';
export interface Message {
  id: string;
  sessionId: string;
  role: MessageRole;
  transcript: string;
  createdAt: string; // ISO 8601
}
```

From frontend/lib/types/session.ts:
```typescript
export type Level = 'A2' | 'B1' | 'B2' | 'C1';
export interface Session {
  id: string;
  characterName: string;
  level: Level;
  createdAt: string;
  endedAt?: string;
}
```

<!-- Phase 1C wire format (backend/main.py — SOURCE OF TRUTH, mirrored here verbatim) -->
<!--
  POST /api/chat
  Request: { utterance: str, session_id: str, level: 'A2' | 'B1' | 'B2' | 'C1' }
  Response: {
    status: str,
    transcript: str,
    reply: str,
    tts_audio: Optional[str],          // base64 mp3 OR null
    axes: { Formality, Energy, Intimacy, Humor, Curiosity: number },
    character: { tone_casual, energy_level, humor_level: number },
    character_labels: { tone, energy, humor: string },
    hint_ko: { hint: str, expression: str } | null
  }
-->

<!-- NOTE on Phase 1B boundary -->
<!-- Phase 1B owns frontend/lib/types/character.ts (Axes + CharacterParams). Plan 02 -->
<!-- defines minimal wire-format copies INSIDE chat.ts (per RESEARCH Option A). When 1B -->
<!-- merges its character.ts, Phase 2 reconciles via re-export. 1A does NOT create -->
<!-- frontend/lib/types/character.ts. -->

<!-- Locked fixture text (UI-SPEC § Copywriting Contract → "Mock chat fixture") -->
<!--
  reply (EN):                "What a bummer! But don't be too sad."
  hint_ko.hint (KO):         "자연스러운 표현이에요!"
  hint_ko.expression (EN):   "Keep it up!"
  default axes/character:    all zeros
  character_labels:          { tone: 'neutral', energy: 'calm', humor: 'mild' }
-->
</interfaces>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Define wire types in frontend/lib/types/chat.ts</name>
  <files>frontend/lib/types/chat.ts</files>
  <read_first>
    - frontend/lib/types/session.ts (for `Level` re-import)
    - .planning/phases/01A-fe-screens-audio-shell/01A-RESEARCH.md § "Wire Type Definitions" section (locked shape)
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § "Copywriting Contract → Mock chat fixture" (fixture values)
  </read_first>
  <action>
    Create new file `frontend/lib/types/chat.ts` (the file does not exist yet — verified by `ls frontend/lib/types/` showing only message.ts + session.ts). Contents — all `export`s are named (no default):

    ```typescript
    /**
     * Phase 1A wire types for POST /api/chat.
     *
     * SOURCE OF TRUTH: backend/main.py (Phase 1C Pydantic models).
     * Any shape divergence breaks the Phase 2 mock-to-real swap, so this file
     * mirrors backend/main.py exactly. Re-shape only when Phase 1C ships a change.
     *
     * Note on Axes / CharacterParams: Phase 1B owns frontend/lib/types/character.ts
     * (per .planning/ROADMAP.md Phase 1B SC #5). 1A intentionally defines its own
     * wire-shape copies here so 1A can compile without waiting for 1B. When 1B
     * merges, Phase 2 will re-export from character.ts in one line.
     */

    import type { Level } from './session';

    export interface ChatRequest {
      utterance: string;
      session_id: string;
      level: Level;
    }

    export interface Axes {
      Formality: number;
      Energy: number;
      Intimacy: number;
      Humor: number;
      Curiosity: number;
    }

    export interface CharacterParams {
      tone_casual: number;
      energy_level: number;
      humor_level: number;
    }

    export interface CharacterLabels {
      tone: string;
      energy: string;
      humor: string;
    }

    export interface InlineHintKo {
      hint: string;
      expression: string;
    }

    export interface ChatResponse {
      status: string;
      transcript: string;
      reply: string;
      tts_audio: string | null;
      axes: Axes;
      character: CharacterParams;
      character_labels: CharacterLabels;
      hint_ko: InlineHintKo | null;
    }
    ```

    Constraints:
    - **No `any`.** No `unknown`. TS strict.
    - Field names use `snake_case` for wire fields (`session_id`, `tts_audio`, `hint_ko`) per Phase 1C Pydantic models.
    - Internal-only Korean comment OK only if needed; existing file uses English comments per CLAUDE.md §7.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F 'export interface ChatRequest' lib/types/chat.ts && grep -F 'export interface ChatResponse' lib/types/chat.ts && grep -F 'tts_audio: string | null' lib/types/chat.ts && grep -F "import type { Level } from './session'" lib/types/chat.ts</automated>
  </verify>
  <done>chat.ts exports the six interfaces with the exact shape above; tsc passes.</done>
  <acceptance_criteria>
    - File `frontend/lib/types/chat.ts` exists
    - Contains `export interface ChatRequest` with fields `utterance: string`, `session_id: string`, `level: Level`
    - Contains `export interface ChatResponse` with all 8 fields: `status`, `transcript`, `reply`, `tts_audio: string | null`, `axes: Axes`, `character: CharacterParams`, `character_labels: CharacterLabels`, `hint_ko: InlineHintKo | null`
    - Contains the four interfaces `Axes`, `CharacterParams`, `CharacterLabels`, `InlineHintKo`
    - `Axes` has exactly 5 fields (Formality, Energy, Intimacy, Humor, Curiosity) all `number`
    - `CharacterParams` has exactly 3 fields (tone_casual, energy_level, humor_level) all `number`
    - `import type { Level } from './session'` is present
    - File contains zero occurrences of the literal token `any` (`grep -w any` returns no matches)
    - `cd frontend && npx tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Build useReducer state machine in frontend/lib/state/conversation.ts</name>
  <files>frontend/lib/state/conversation.ts</files>
  <read_first>
    - frontend/lib/types/message.ts (for Message import)
    - .planning/phases/01A-fe-screens-audio-shell/01A-RESEARCH.md § "Pattern 2: useReducer State Machine" (full reference impl)
    - .planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md § D-12, D-13, D-14 (state machine transitions)
  </read_first>
  <action>
    Create new directory `frontend/lib/state/` and new file `frontend/lib/state/conversation.ts`. Implement the reducer described in RESEARCH §Pattern 2, verbatim (already vetted against TS strict). per D-12 (5 states), D-13 (transitions), D-14 (error reasons = 'permission-denied' | 'generic').

    ```typescript
    /**
     * Phase 1A — conversation state machine.
     *
     * Single reducer covers:
     *   1. sessionId bootstrap (set once on first client mount per D-16)
     *   2. Rec state transitions per D-13:
     *        idle → recording → processing → speaking → idle
     *        idle → error (permission-denied | generic) → (next tap) → idle
     *   3. History sheet visibility (CHAT-01 chevron toggle)
     *
     * All states are discriminated unions so TS exhaustiveness catches missing
     * transitions at compile time.
     */

    import type { Message } from '@/lib/types/message';

    export type RecState =
      | { kind: 'idle' }
      | { kind: 'recording'; startedAt: number }
      | { kind: 'processing' }
      | { kind: 'speaking' }
      | { kind: 'error'; reason: 'permission-denied' | 'generic'; message: string };

    export interface ConversationState {
      sessionId: string | null;
      messages: Message[];
      rec: RecState;
      historyOpen: boolean;
    }

    export type Action =
      | { type: 'sessionId/set'; id: string }
      | { type: 'rec/start' }
      | { type: 'rec/stop' }
      | { type: 'rec/processed'; userMsg: Message; pallyMsg: Message }
      | { type: 'rec/speakingDone' }
      | { type: 'rec/error'; reason: 'permission-denied' | 'generic'; message: string }
      | { type: 'rec/dismissError' }
      | { type: 'history/toggle' };

    export const initialState: ConversationState = {
      sessionId: null,
      messages: [],
      rec: { kind: 'idle' },
      historyOpen: false,
    };

    export function reducer(state: ConversationState, action: Action): ConversationState {
      switch (action.type) {
        case 'sessionId/set':
          return { ...state, sessionId: action.id };
        case 'rec/start':
          return { ...state, rec: { kind: 'recording', startedAt: Date.now() } };
        case 'rec/stop':
          return { ...state, rec: { kind: 'processing' } };
        case 'rec/processed':
          return {
            ...state,
            messages: [...state.messages, action.userMsg, action.pallyMsg],
            rec: { kind: 'speaking' },
          };
        case 'rec/speakingDone':
          return { ...state, rec: { kind: 'idle' } };
        case 'rec/error':
          return {
            ...state,
            rec: { kind: 'error', reason: action.reason, message: action.message },
          };
        case 'rec/dismissError':
          // Tap-to-dismiss returns to idle without altering messages
          return state.rec.kind === 'error' ? { ...state, rec: { kind: 'idle' } } : state;
        case 'history/toggle':
          return { ...state, historyOpen: !state.historyOpen };
        default: {
          // Exhaustiveness — fails the build if a new Action variant is added without a case
          const exhaustive: never = action;
          throw new Error(`Unhandled conversation action: ${JSON.stringify(exhaustive)}`);
        }
      }
    }
    ```

    Constraints:
    - No `any`, no silent fallback (no `?? {}` / `|| []`) — empty error swallow forbidden per CLAUDE.md §7 / §10.
    - Use `import type` for Message (TS verbatimModuleSyntax-friendly).
    - The default-case `never` assertion satisfies CLAUDE.md "TS strict mode, no `any`" rule.
    - The 'rec/dismissError' action is an addition vs RESEARCH (covers the UI-SPEC § Copywriting Contract toast tap-to-dismiss requirement); keep it.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F "export type RecState" lib/state/conversation.ts && grep -F "export interface ConversationState" lib/state/conversation.ts && grep -F "export type Action" lib/state/conversation.ts && grep -F "export function reducer" lib/state/conversation.ts && grep -F "export const initialState" lib/state/conversation.ts && grep -F "const exhaustive: never = action" lib/state/conversation.ts</automated>
  </verify>
  <done>conversation.ts exports the 5 expected symbols (RecState, ConversationState, Action, initialState, reducer) with the exhaustive never default branch; tsc passes.</done>
  <acceptance_criteria>
    - File `frontend/lib/state/conversation.ts` exists
    - Contains `export type RecState =` with all 5 kinds: `'idle'`, `'recording'`, `'processing'`, `'speaking'`, `'error'`
    - Contains `export interface ConversationState` with exactly 4 fields: `sessionId: string | null`, `messages: Message[]`, `rec: RecState`, `historyOpen: boolean`
    - Contains `export type Action =` with all 8 action types listed in the action block above (including `'rec/dismissError'`)
    - Contains `export function reducer(state: ConversationState, action: Action): ConversationState`
    - Contains `export const initialState: ConversationState =` with `sessionId: null`, empty messages, `rec: { kind: 'idle' }`, `historyOpen: false`
    - Default switch branch contains `const exhaustive: never = action` (TS exhaustiveness guard)
    - File contains zero occurrences of the literal token `any` (`grep -w any` returns no matches)
    - `cd frontend && npx tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Implement single-swap mock at frontend/lib/mocks/chat-mock.ts</name>
  <files>frontend/lib/mocks/chat-mock.ts</files>
  <read_first>
    - frontend/lib/types/chat.ts (Task 1 output — for ChatRequest/ChatResponse types)
    - .planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md § D-01, D-02, D-03, D-04 (mock contract)
    - .planning/phases/01A-fe-screens-audio-shell/01A-UI-SPEC.md § "Copywriting Contract → Mock chat fixture" (exact fixture values)
  </read_first>
  <action>
    Create new directory `frontend/lib/mocks/` and new file `frontend/lib/mocks/chat-mock.ts`. Implement the single-export mock function per D-01 (single function), D-02 (wire shape match), D-03 (1 canned fixture), D-04 (fixed 800ms latency).

    ```typescript
    /**
     * Phase 1A — Mock transport for /api/chat.
     *
     * SINGLE SWAP POINT (per CONTEXT D-01):
     *   Phase 2 replaces the body of `mockChat` with:
     *     const r = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/chat`, ...);
     *     return r.json() as ChatResponse;
     *   No other file in the codebase may construct a ChatResponse — only this one.
     *
     * Contract (locked, per CONTEXT D-02 → D-04 + UI-SPEC Copywriting Contract):
     *   - latency: fixed 800ms, no jitter
     *   - reply: "What a bummer! But don't be too sad." (Figma sample)
     *   - hint_ko: { hint: "자연스러운 표현이에요!", expression: "Keep it up!" }
     *   - axes / character: all zeros (1A does not render character morph)
     *   - character_labels: neutral / calm / mild
     *   - tts_audio: null (1A does not play TTS per D-10)
     *   - transcript: echoes req.utterance verbatim
     */

    import type { ChatRequest, ChatResponse } from '@/lib/types/chat';

    // Fixed 800ms — matches plausible Phase-1C E2E latency for deterministic demo
    // screen recordings (per CONTEXT D-04). Do NOT add jitter in 1A.
    const FIXED_LATENCY_MS = 800;

    const FIXTURE: Omit<ChatResponse, 'transcript'> = {
      status: 'ok',
      reply: "What a bummer! But don't be too sad.",
      tts_audio: null,
      axes: {
        Formality: 0,
        Energy: 0,
        Intimacy: 0,
        Humor: 0,
        Curiosity: 0,
      },
      character: {
        tone_casual: 0,
        energy_level: 0,
        humor_level: 0,
      },
      character_labels: {
        tone: 'neutral',
        energy: 'calm',
        humor: 'mild',
      },
      hint_ko: {
        hint: '자연스러운 표현이에요!',
        expression: 'Keep it up!',
      },
    };

    export async function mockChat(req: ChatRequest): Promise<ChatResponse> {
      await new Promise<void>((resolve) => setTimeout(resolve, FIXED_LATENCY_MS));
      return {
        ...FIXTURE,
        transcript: req.utterance, // echo
      };
    }
    ```

    Constraints:
    - Single named export `mockChat`. No default export. No other functions exported.
    - Fixture is `const`. Do not mutate.
    - Latency literal is the named constant `FIXED_LATENCY_MS` with a comment citing D-04 (UI-SPEC § Anti-Patterns #7 forbids magic numbers without comments).
    - No `Math.random()`, no error throw paths inside mockChat (1A mock is success-only per D-04 / D-14).
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F "export async function mockChat" lib/mocks/chat-mock.ts && grep -F "FIXED_LATENCY_MS = 800" lib/mocks/chat-mock.ts && grep -F "What a bummer! But don't be too sad." lib/mocks/chat-mock.ts && grep -F "자연스러운 표현이에요!" lib/mocks/chat-mock.ts && ! grep -F "Math.random" lib/mocks/chat-mock.ts && ! grep -F "export default" lib/mocks/chat-mock.ts</automated>
  </verify>
  <done>chat-mock.ts exports exactly one named function `mockChat`, fixed 800ms latency, fixture matches the locked Figma copy + UI-SPEC contract; tsc passes; no random/jitter/default-export.</done>
  <acceptance_criteria>
    - File `frontend/lib/mocks/chat-mock.ts` exists
    - Contains `export async function mockChat(req: ChatRequest): Promise<ChatResponse>`
    - Contains the constant `FIXED_LATENCY_MS = 800`
    - Contains the exact literal `"What a bummer! But don't be too sad."`
    - Contains the exact literal `'자연스러운 표현이에요!'`
    - Contains the exact literal `'Keep it up!'`
    - Contains `tts_audio: null` (1A does not play TTS)
    - `axes` fixture has all 5 fields set to literal 0 (`Formality: 0`, `Energy: 0`, `Intimacy: 0`, `Humor: 0`, `Curiosity: 0`)
    - `character` fixture has 3 fields set to literal 0
    - `character_labels` has tone='neutral', energy='calm', humor='mild'
    - File contains zero occurrences of `Math.random`
    - File contains zero occurrences of `export default`
    - File contains zero occurrences of the literal token `any` (`grep -w any` returns no matches)
    - `import type { ChatRequest, ChatResponse } from '@/lib/types/chat'` present
    - `cd frontend && npx tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto" tdd="false">
  <name>Task 4: MediaRecorder MIME-type probe at frontend/lib/audio/pickMimeType.ts</name>
  <files>frontend/lib/audio/pickMimeType.ts</files>
  <read_first>
    - .planning/phases/01A-fe-screens-audio-shell/01A-RESEARCH.md § "Pattern 3: MediaRecorder MIME Detection" (verbatim helper) + § "Pitfall 1: iOS Safari MediaRecorder MIME mismatch"
    - .planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md § D-05 (probe order)
  </read_first>
  <action>
    Create new directory `frontend/lib/audio/` and new file `frontend/lib/audio/pickMimeType.ts`. Implement the probe per D-05 (webm;codecs=opus first, mp4 fallback).

    ```typescript
    /**
     * Phase 1A — MediaRecorder MIME-type probe.
     *
     * Chrome / Firefox / Edge support audio/webm (Opus codec); iOS Safari 14.1+
     * only supports audio/mp4. Hardcoding either fails on the other.
     *
     * Probe order locked by CONTEXT D-05 + RESEARCH Pattern 3. Returns the first
     * supported MIME or null when nothing is supported (caller surfaces a
     * "이 브라우저는 음성 녹음을 지원하지 않아요." inline error per UI-SPEC
     * § Copywriting Contract → "Error and permission states").
     */

    const CANDIDATES = [
      'audio/webm;codecs=opus',       // Chrome / Firefox / Edge — preferred
      'audio/webm',                    // Chrome / Firefox / Edge — fallback
      'audio/mp4',                     // Safari (iOS + macOS)
      'audio/mp4;codecs=mp4a.40.2',    // Safari — explicit AAC
    ] as const;

    export function pickMimeType(): string | null {
      if (typeof MediaRecorder === 'undefined') {
        return null;
      }
      for (const mime of CANDIDATES) {
        if (MediaRecorder.isTypeSupported(mime)) {
          return mime;
        }
      }
      return null;
    }
    ```

    Constraints:
    - Function MUST guard `typeof MediaRecorder === 'undefined'` so SSR import does not crash (RESEARCH § Pitfall 3 analog for MediaRecorder).
    - Candidate array ordered exactly as above (D-05 lock).
    - No `any`, no fallback to a hardcoded MIME — return `null` if nothing supported.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && grep -F "export function pickMimeType(): string | null" lib/audio/pickMimeType.ts && grep -F "audio/webm;codecs=opus" lib/audio/pickMimeType.ts && grep -F "audio/mp4" lib/audio/pickMimeType.ts && grep -F "typeof MediaRecorder === 'undefined'" lib/audio/pickMimeType.ts</automated>
  </verify>
  <done>pickMimeType.ts exports a single function probing candidates in the locked order, SSR-safe via undefined guard, returns string | null; tsc passes.</done>
  <acceptance_criteria>
    - File `frontend/lib/audio/pickMimeType.ts` exists
    - Contains `export function pickMimeType(): string | null`
    - Contains all 4 candidate strings: `'audio/webm;codecs=opus'`, `'audio/webm'`, `'audio/mp4'`, `'audio/mp4;codecs=mp4a.40.2'`
    - First candidate in CANDIDATES array is `'audio/webm;codecs=opus'` (D-05 lock)
    - Contains the SSR guard `typeof MediaRecorder === 'undefined'`
    - Uses `MediaRecorder.isTypeSupported(mime)` to probe
    - Returns `null` when no candidate is supported (not a fallback hardcoded MIME)
    - File contains zero occurrences of the literal token `any` (`grep -w any` returns no matches)
    - `cd frontend && npx tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Mock → UI | mockChat is an internal-only data source; no untrusted input crosses here in 1A. Phase 2 replaces with `fetch(NEXT_PUBLIC_BACKEND_URL/api/chat)` and the boundary becomes browser → backend. |
| Browser API → Reducer | MediaRecorder error names (`NotAllowedError`, etc.) flow into reducer Action payloads via handlers (wired in Plan 03). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01A-02-01 | Tampering | mockChat fixture content | accept | Fixture is a build-time constant — no user input. When Phase 2 swaps to real fetch, Zod validation will be added at that boundary. |
| T-01A-02-02 | Spoofing | wire types snake_case vs Phase 1C | mitigate | Field names `session_id`, `tts_audio`, `hint_ko` match `backend/main.py` verbatim (verified by Task 1 acceptance grep). If 1C changes shape, Phase 2 reconciliation catches it via TS compile error. |
| T-01A-02-03 | Information Disclosure | reducer error messages | mitigate | Reducer stores user-facing Korean strings only (`마이크 권한이 필요해요`, `다시 한 번 말해주세요`). Plan 03 ensures raw exception messages from MediaRecorder are NOT propagated to UI. |
| T-01A-02-04 | DoS | pickMimeType SSR safety | mitigate | `typeof MediaRecorder === 'undefined'` guard returns null instead of throwing during Next.js server render. |
</threat_model>

<verification>
- `cd frontend && npx tsc --noEmit` passes after all 4 files exist
- `cd frontend && npm run build` passes (verified by Plan 05 wave gate)
- No file imports from `frontend/components/pally/*` or `frontend/lib/types/character.ts` (Phase 1B namespace)
- No file imports from `backend/`, `ai/`, `supabase/`
- `grep -r "Math.random" frontend/lib/` returns no matches (mock is deterministic)
- `grep -rE "any( |;|\\)|>)" frontend/lib/types/chat.ts frontend/lib/state/conversation.ts frontend/lib/mocks/chat-mock.ts frontend/lib/audio/pickMimeType.ts` shows no `any` usage (TS strict invariant)
</verification>

<success_criteria>
1. `frontend/lib/types/chat.ts` exports 6 interfaces matching Phase 1C wire shape exactly.
2. `frontend/lib/state/conversation.ts` exports reducer + initialState + 3 types covering all 5 rec states with exhaustive never-default.
3. `frontend/lib/mocks/chat-mock.ts` exports exactly one function `mockChat`, fixed 800ms, Figma-locked fixture.
4. `frontend/lib/audio/pickMimeType.ts` exports SSR-safe probe with the locked candidate order.
5. `npm run build` succeeds.
</success_criteria>

<output>
After completion, create `.planning/phases/01A-fe-screens-audio-shell/01A-02-SUMMARY.md`
</output>
