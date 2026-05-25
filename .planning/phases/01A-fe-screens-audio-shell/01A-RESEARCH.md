# Phase 1A: FE Screens & Audio Shell — Research

**Researched:** 2026-05-25
**Domain:** Next.js 14 App Router + MediaRecorder UX shell + Figma → React (mock transport, mobile 402px)
**Confidence:** HIGH (stack/patterns), MEDIUM (iOS Safari MIME details — verified through MDN + caniuse but real-device verification deferred to Phase 2 per CONTEXT D-05)

## Summary

Phase 1A is a **mock-only frontend** built on the stack Phase 0 already shipped: Next.js 14.2.35 App Router + React 18 + Tailwind + Pretendard. There are **no new dependencies needed** — CONTEXT.md locked the design decisions (single mock function, fixed 800ms latency, useReducer-style state machine, implicit permission, MediaRecorder MIME auto-detect, 402px viewport). The research questions are mostly "which standard pattern" not "which library."

The main technical risk is **MediaRecorder MIME-type handling on iOS Safari** — Safari 14.1+ supports MediaRecorder but does NOT support `audio/webm` (Chrome/Firefox standard); it supports `audio/mp4`. The CONTEXT.md D-05 fallback order (`audio/webm;codecs=opus` → `audio/mp4`) is the correct one. Real STT compatibility verification stays in Phase 2.

The second risk is the **Phase 2 swap point discipline**: every chat data path must funnel through `mockChat()` in `frontend/lib/mocks/chat-mock.ts`. The plan must enforce this — if any component does direct fixture mocking elsewhere, Phase 2 wiring breaks. Wire types must live in `frontend/lib/types/chat.ts` and mirror Phase 1C's Pydantic shapes **exactly** (verified from `backend/main.py` lines 84-106).

**Primary recommendation:** Single client page (`'use client'` on `frontend/app/page.tsx`), `useReducer` state machine, MediaRecorder MIME detection + 30s `setTimeout` auto-stop, mock fixture as a single canned response. Keep `frontend/components/pally/` untouched (1B owned). Place `<PallyPlaceholder />` as a local component inside `frontend/components/chat/` (NOT in `pally/`) — 1B replaces the import path in one line.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

**A. Mock Transport**
- **D-01:** Single export `mockChat(req: ChatRequest): Promise<ChatResponse>` at `frontend/lib/mocks/chat-mock.ts`. Phase 2 swap point = this one call site → `fetch(NEXT_PUBLIC_BACKEND_URL + '/api/chat')`.
- **D-02:** Wire types match Phase 1C shape exactly. Request `{ utterance: string, session_id: string, level: 'B1' }`. Response `{ status, transcript, reply, tts_audio (base64 mp3), axes, character, character_labels, hint_ko: { hint, expression } }`. 1A receives `tts_audio` but **does not play it** (Phase 2).
- **D-03:** Canned fixture **1 only** — `transcript: req.utterance` (echo), `reply: "What a bummer! But don't be too sad."`, `axes`/`character` = 0 defaults, `hint_ko` = short Figma-tone sample.
- **D-04:** Latency **fixed 800ms** (`await new Promise(r => setTimeout(r, 800))`). No jitter, no error simulation in 1A.

**B. Audio Capture & Playback**
- **D-05:** start / stop only. MediaRecorder API, MIME detection: `MediaRecorder.isTypeSupported('audio/webm;codecs=opus')` first, fallback `audio/mp4`.
- **D-06:** Permission **implicit** — first rec-button tap calls `getUserMedia()`. No pre-permission CTA / explainer screen.
- **D-07:** Permission denied → back to idle + small toast/inline "마이크 권한이 필요해요". No deep link to settings.
- **D-08:** Max 30s recording — `MediaRecorder.stop()` called automatically. **No min duration check** (mock just echoes if too short).
- **D-09:** Recording Blob is **not used** in mock flow — only triggers `mockChat()`. Phase 2 wires Blob → FormData upload.
- **D-10:** TTS **not played** in 1A. UI sits in "speaking" for ~1.5s then returns to idle.

**C. Pally Placeholder + State Coverage**
- **D-11:** Pally area (262×262) = static SVG placeholder (Figma Star4 spike). `frontend/components/pally/` is **1B owned, 1A does not create files inside it**. 1A uses a local `<PallyPlaceholder />` component or inlined SVG.
- **D-12:** TalkButton states (visual): `idle` = orange mic | `recording`/`processing`/`speaking` = red disc + white square | `error` = same as idle + inline message.
- **D-13:** State machine: `idle → (tap, perm OK) → recording → (tap stop / 30s auto) → processing → (mockChat 800ms) → speaking → (1.5s) → idle`. Permission denied → idle + toast.
- **D-14:** Error handling = **permission-denied** + **generic catch-all** only. Generic error UI = inline "다시 한 번 말해주세요".
- **D-15:** All other state coverage (offline, mic-too-short/long, low-confidence, splash, streak) = **deferred to Senior Plan Phase B/C/D**.

**D. Session Lifecycle + Nav**
- **D-16:** `session_id` = UUID v4 via `crypto.randomUUID()` on first client mount, stored at `localStorage['pally:sessionId']`. SSR-safe — must access only inside `useEffect`.
- **D-17:** New-chat UX **not implemented in 1A**. Bottom nav 5 tabs **all visual only, disabled**, tapping does nothing (no toast).
- **D-18:** On refresh, message list starts **empty** (no localStorage message restoration). Only sessionId persists.

### Claude's Discretion
- Component directory structure (kept page-level state in `app/page.tsx`; presentational components in `frontend/components/chat/`, `frontend/components/audio/`, `frontend/components/nav/`)
- State management — `useReducer` (CONTEXT.md recommendation, agreed below in §Architecture)
- Tailwind class grouping / extract thresholds
- Star4 SVG export approach (inline JSX SVG recommended — single placeholder file, no `public/` asset needed)
- MIME detection fallback order (locked by D-05 above)
- localStorage key prefix (`pally:*` recommended; only one key in 1A: `pally:sessionId`)
- 5-tab disabled visualization (Figma as-is — Figma already shows them at full opacity; use `aria-disabled` + no click handler, not `opacity-50`)
- Chat bubble ↔ history view transition (slide-down per Figma motion section)
- mockChat catch-all (try/catch wrapper around reducer dispatch — never thrown to client per CLAUDE.md §7)

### Deferred Ideas (OUT OF SCOPE)
- Splash screen 1.5s, responsive (other viewport widths), error states 4-kind design, mic-permission friendly copy, speaking-state morph + waveform, WCAG AA contrast audit, shadow tokens, motion easing tokens, typewriter reveal, haptic, sound, app icon, character expression library, onboarding, dashboard, settings, dark mode, tablet, native wrapper, 5-tab nav routing, new-chat (+) action, message persistence, STT-fail / too-short-or-long / background-noise / low-confidence / offline states, `Axes` / `CharacterParams` types and Canvas2D renderer (Phase 1B), real `/api/chat` / STT upload / TTS playback (Phase 2).

---

## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|-----------------------------------|------------------|
| **MAIN-01** | 메인 화면에 Pally 대기 상태와 하단 음성 입력 시작 버튼(rec)을 표시한다 | Single `app/page.tsx` client component renders 3 zones (top chat bubble / center PallyPlaceholder / bottom TalkButton + GNB). 5-state TalkButton driven by useReducer. See §Architecture Patterns + §Code Examples. |
| **CHAT-01** | 대화 화면에서 직전 발화/응답을 말풍선으로 미리 보여주고, 토글로 전체 대화 스크립트(SMS 스타일, 사용자=teal "YOU"/Pally=orange "Pally")를 볼 수 있다 | Top chat bubble pulls `state.messages.at(-1)` and `.at(-2)`. Chevron toggle opens full-sheet history pulled from `state.messages`. Speaker color tokens already in DESIGN.md (teal `#00c3d0` / orange `#fe9012`). Sender label = 12px caption per DESIGN.md decisions log. See §Architecture Patterns. |

---

## Project Constraints (from CLAUDE.md)

**Directives the planner MUST honor:**

1. **TS strict, no `any`** — If unavoidable, add `// TODO: 사유`. (§7)
2. **Server Components default; `'use client'` only when needed** — Main page WILL need it (state + MediaRecorder + crypto.randomUUID). Subcomponents that don't need state can stay server components (e.g., static GNB icons, static empty-state text). (§7)
3. **Tailwind + `cn()` only — no string concatenation for classes.** `cn()` already exists at `frontend/lib/utils.ts` (clsx + tailwind-merge). (§7)
4. **Named exports preferred. Default exports only for page/layout/route handlers.** (§7)
5. **Zod boundary validation on external inputs.** For 1A this means validating mockChat response shape if the planner wants to be defensive — but since mock is internal, can skip. Phase 2 will need real Zod schema. **Recommendation:** Define the chat wire types in `frontend/lib/types/chat.ts` as plain TS types in 1A, **plus** an exported Zod schema that 1A doesn't enforce but Phase 2 can drop in immediately. Cheap insurance.
6. **No empty `catch {}` / no `|| {}` / no `?? []` silent fallbacks.** Catch-all in mockChat callsite must dispatch error state, not swallow. (§6 #3, §10 NEVER)
7. **No `git add .` — file-by-file staging.** (§7, §10 NEVER)
8. **No emojis in code or commit messages.** (§10 NEVER)
9. **No `mcp__claude-in-chrome__*` — use Playwright MCP or `/browse` for E2E.** (§10 NEVER)
10. **Directory boundaries:** 1A touches only `frontend/` outside `frontend/components/pally/`, `frontend/app/dev/pally/`, `frontend/lib/types/character.ts` (1B owned). `backend/`, `ai/`, `supabase/migrations/*` are 1C owned — **not modified**. (§1)
11. **E2E verification:** Mobile width — for 1A this means **Figma 402px** per CONTEXT.md (CLAUDE.md still mentions 360px globally; the recent commit `a2c2bb4` locked 402px for this phase). Use `/browse` or Playwright MCP, not synthetic screenshots. (§5)
12. **No README.md / ARCHITECTURE.md auto-generation.** (§10 NEVER)
13. **`feedback` separate page forbidden.** MVP inline payload only. (§10 NEVER) — 1A does not use `hint_ko` UI; that's a Phase 2 concern, but mock still returns it so type stays correct.
14. **No OpenAI / Whisper / GPT-4o references.** GCP only. (§10 NEVER) — N/A for 1A but worth noting in mock fixture (don't write "OpenAI" anywhere).

---

## Standard Stack

### Core (already installed — verified from `frontend/package.json`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `next` | 14.2.35 | App Router, RSC | [VERIFIED: package.json] Already installed in Phase 0 |
| `react` | ^18 | UI runtime | [VERIFIED: package.json] |
| `tailwindcss` | ^3.4.1 | Styling | [VERIFIED: package.json] |
| `pretendard` | ^1.3.9 | Korean font | [VERIFIED: package.json] Imported in `layout.tsx` |
| `clsx` + `tailwind-merge` | 2.1.1 / 3.6.0 | `cn()` helper | [VERIFIED: `frontend/lib/utils.ts`] |

### Browser APIs (no install — platform standard)

| API | Purpose | Notes |
|-----|---------|-------|
| `MediaRecorder` | Audio capture | [CITED: developer.mozilla.org/en-US/docs/Web/API/MediaRecorder] Baseline since ~2020 in Chrome/Firefox; Safari 14.1+ supports it but MIME differs. |
| `navigator.mediaDevices.getUserMedia()` | Mic permission + stream | Returns Promise; rejects with `NotAllowedError` on denial. [CITED: developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia] |
| `crypto.randomUUID()` | sessionId | Available in all modern browsers since 2022. Also available in Node ≥ 14.17 / 16+ — safe server-side too, BUT D-16 mandates client-only via `useEffect`. [CITED: developer.mozilla.org/en-US/docs/Web/API/Crypto/randomUUID] |
| `localStorage` | Persistent sessionId | SSR-unsafe — only inside `useEffect`. |

### What we are NOT adding

| Considered | Decision | Reason |
|------------|----------|--------|
| `zustand` / `jotai` / Redux | **Skip** | Single screen, single state machine. `useReducer` is the standard React primitive for this exact shape. CONTEXT.md suggests `useReducer`. |
| `framer-motion` | **Skip for 1A** | Senior plan defers motion polish to Phase B/C. Tailwind transitions suffice for chevron toggle + bubble fade. Adding framer-motion now without a polish budget = dead weight. |
| `zod` runtime install | **Skip for 1A install** | Already in CLAUDE.md (§7) — but mock returns canned data, no real boundary. **Recommend:** define types only in 1A. Phase 2 plan will install zod and add schemas. |
| `react-hot-toast` / `sonner` | **Skip** | One toast scenario (permission denied). A 20-line inline component is simpler and Tailwind-styleable. |
| `uuid` package | **Skip** | `crypto.randomUUID()` is native and available. No need for the 4-byte lib. |
| `pretendard` for SVG | N/A | Already loaded in layout. |

**Version verification (NPM registry not consulted in this session — `package.json` is canonical for installed versions, and we are not adding new packages):**
- Next.js 14.2.35: `[VERIFIED: package.json]` — published 2024-Q4 era, current latest for the 14.x line as of session. We are NOT upgrading to 15 in 1A.
- React 18: `[VERIFIED: package.json]` — Phase 0 chose 18 over 19; matches Next 14.

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Already exists — DO NOT touch (Pretendard import)
│   ├── page.tsx                # 1A REWRITES this — main 'use client' page
│   ├── globals.css             # Already exists
│   └── api/health/route.ts     # Already exists (Phase 0) — DO NOT touch
├── components/
│   ├── audio/
│   │   └── TalkButton.tsx      # 5 visual states (idle/recording/processing/speaking/error)
│   ├── chat/
│   │   ├── ChatBubble.tsx      # Top current-turn bubble
│   │   ├── HistorySheet.tsx    # Full history overlay
│   │   ├── HistoryRow.tsx      # One YOU/Pally row in history (SMS style)
│   │   └── PallyPlaceholder.tsx # Static Star4 SVG (NOT in components/pally/ — that's 1B)
│   ├── nav/
│   │   └── BottomNav.tsx       # 5 disabled tabs
│   └── ui/
│       └── Toast.tsx           # Inline permission-denied toast
├── lib/
│   ├── utils.ts                # Already exists (cn())
│   ├── types/
│   │   ├── message.ts          # Already exists — REUSE
│   │   ├── session.ts          # Already exists — REUSE
│   │   └── chat.ts             # NEW — ChatRequest / ChatResponse mirror of Phase 1C
│   ├── audio/
│   │   ├── pickMimeType.ts     # MediaRecorder MIME selection
│   │   └── useRecorder.ts      # Hook: getUserMedia + MediaRecorder + 30s auto-stop
│   ├── mocks/
│   │   └── chat-mock.ts        # SINGLE swap point: mockChat()
│   └── state/
│       └── conversation.ts     # useReducer state + action types
└── public/
    └── (no new assets needed — Star4 inline as JSX SVG)
```

**Why this layout:**
- Single-route app, but separating `chat/` `audio/` `nav/` makes the diff for Phase 2 (where audio/ gets the real upload) localized.
- `lib/audio/` separated from `components/audio/` because the recorder hook is logic, not UI.
- `lib/mocks/chat-mock.ts` is the ONE swap point. Plan must enforce: no other file may construct fake chat responses.
- `components/pally/` directory is NOT created here — Phase 1B owns that namespace. `PallyPlaceholder` lives under `components/chat/` so the boundary is unambiguous.

### Pattern 1: 'use client' Boundary

**What:** Top-level page is a client component; small static subcomponents can stay as server components when they have no props from client state.
**When:** `app/page.tsx` needs `'use client'` because it owns useReducer, useEffect (localStorage), and MediaRecorder. The static `<BottomNav />` (5 disabled icons, no state) could technically be a server component imported into the client page — Next.js 14 App Router supports server→client component composition. **However**, in practice for 1A, simpler is to make everything under `components/` a client component (they're tiny and don't benefit from RSC). Keep `layout.tsx` as the only RSC.

**Recommendation:** `'use client'` directive at top of `app/page.tsx` and at top of `components/audio/TalkButton.tsx`, `components/chat/HistorySheet.tsx`. Other components inherit client-ness via composition.

### Pattern 2: useReducer State Machine

**What:** Single reducer manages conversation state, recorder state, and UI mode.
**When:** Any state shape with discriminated unions across 5+ states. Classic case.

**Example:**
```typescript
// frontend/lib/state/conversation.ts
import type { Message } from '@/lib/types/message';

export type RecState =
  | { kind: 'idle' }
  | { kind: 'recording'; startedAt: number }
  | { kind: 'processing' }
  | { kind: 'speaking' }
  | { kind: 'error'; reason: 'permission-denied' | 'generic'; message: string };

export interface ConversationState {
  sessionId: string | null;       // null until useEffect mount
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
      return { ...state, rec: { kind: 'error', reason: action.reason, message: action.message } };
    case 'history/toggle':
      return { ...state, historyOpen: !state.historyOpen };
    default: {
      const exhaustive: never = action;
      throw new Error(`Unhandled action: ${JSON.stringify(exhaustive)}`);
    }
  }
}
```

The `never` exhaustiveness check satisfies TS strict mode.

### Pattern 3: MediaRecorder MIME Detection

**What:** Probe supported MIME types in order before constructing MediaRecorder.
**When:** Any MediaRecorder usage that must work across Chrome + Safari.

```typescript
// frontend/lib/audio/pickMimeType.ts
const CANDIDATES = [
  'audio/webm;codecs=opus',   // Chrome/Firefox/Edge — best
  'audio/webm',                // Chrome/Firefox/Edge fallback
  'audio/mp4',                 // Safari (iOS/macOS)
  'audio/mp4;codecs=mp4a.40.2',// Safari with codec
] as const;

export function pickMimeType(): string | null {
  if (typeof MediaRecorder === 'undefined') return null;
  for (const mime of CANDIDATES) {
    if (MediaRecorder.isTypeSupported(mime)) return mime;
  }
  return null; // signals "no supported format" — bail to error state
}
```

### Pattern 4: useRecorder Hook

**What:** Encapsulate getUserMedia + MediaRecorder + 30s auto-stop + cleanup.

```typescript
// frontend/lib/audio/useRecorder.ts
'use client';
import { useCallback, useRef } from 'react';
import { pickMimeType } from './pickMimeType';

const MAX_DURATION_MS = 30_000;

export interface RecorderHandlers {
  onStart: () => void;
  onStop: (blob: Blob | null) => void;
  onPermissionDenied: () => void;
  onError: (message: string) => void;
}

export function useRecorder(handlers: RecorderHandlers) {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stop = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const r = recorderRef.current;
    if (r && r.state !== 'inactive') {
      r.stop();
    }
  }, []);

  const start = useCallback(async () => {
    const mime = pickMimeType();
    if (!mime) {
      handlers.onError('이 브라우저는 음성 녹음을 지원하지 않아요.');
      return;
    }

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      // NotAllowedError = denial; NotFoundError = no mic; both → user-facing path
      const name = (err as DOMException).name;
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        handlers.onPermissionDenied();
      } else {
        handlers.onError('마이크에 접근할 수 없어요.');
      }
      return;
    }
    streamRef.current = stream;

    const recorder = new MediaRecorder(stream, { mimeType: mime });
    recorderRef.current = recorder;
    chunksRef.current = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = () => {
      const blob = chunksRef.current.length
        ? new Blob(chunksRef.current, { type: mime })
        : null;
      // Stop tracks to release the mic indicator
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      recorderRef.current = null;
      handlers.onStop(blob);
    };

    recorder.start();
    handlers.onStart();

    timerRef.current = window.setTimeout(() => {
      stop();
    }, MAX_DURATION_MS);
  }, [handlers, stop]);

  return { start, stop };
}
```

**Notes:**
- Stream tracks are stopped on `onstop` to remove the browser's red recording indicator.
- The hook does NOT manage React state — that's the reducer's job. Callbacks bridge.
- `MediaRecorder.start()` without timeslice arg fires `ondataavailable` once on stop — sufficient since 1A doesn't stream chunks.

### Pattern 5: Mock Transport (Single Swap Point)

```typescript
// frontend/lib/mocks/chat-mock.ts
import type { ChatRequest, ChatResponse } from '@/lib/types/chat';

const FIXED_LATENCY_MS = 800;

const FIXTURE: Omit<ChatResponse, 'transcript'> = {
  status: 'ok',
  reply: "What a bummer! But don't be too sad.",
  tts_audio: null,
  axes: { Formality: 0, Energy: 0, Intimacy: 0, Humor: 0, Curiosity: 0 },
  character: { tone_casual: 0, energy_level: 0, humor_level: 0 },
  character_labels: { tone: 'neutral', energy: 'calm', humor: 'mild' },
  hint_ko: { hint: '자연스러운 표현이에요!', expression: 'Keep it up!' },
};

export async function mockChat(req: ChatRequest): Promise<ChatResponse> {
  await new Promise<void>((resolve) => setTimeout(resolve, FIXED_LATENCY_MS));
  return {
    ...FIXTURE,
    transcript: req.utterance, // echo
  };
}
```

**Phase 2 swap:** Replace this file's contents (or the import at call site) with `fetch(NEXT_PUBLIC_BACKEND_URL + '/api/chat', { method: 'POST', body: ... })`. Everything else stays the same.

### Pattern 6: SSR-safe sessionId

```typescript
// Inside app/page.tsx body (client component)
useEffect(() => {
  const KEY = 'pally:sessionId';
  let id = window.localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(KEY, id);
  }
  dispatch({ type: 'sessionId/set', id });
}, []);
```

State stays `null` during the first render → `mockChat` cannot be called until sessionId is set. Render the TalkButton as disabled until then (one-frame visual; negligible).

### Anti-Patterns to Avoid

- **Mocking inside components.** Every chat call MUST go through `mockChat()`. Component-local fixtures (e.g., a useState with a hardcoded message array) break the Phase 2 swap.
- **Reading `localStorage` at module top-level or inside the render body.** Crashes during SSR. Only inside `useEffect`.
- **`useEffect(() => { ... }, [])` with browser-only globals not gated.** Even though `useEffect` only runs client-side, lint rules may complain. Pattern above is correct.
- **Importing from `frontend/components/pally/*` or `frontend/lib/types/character.ts`.** 1B owned. 1A places `PallyPlaceholder` in `components/chat/`.
- **`MediaRecorder.start(1000)` (timeslice) for 1A.** Not needed; we want the whole blob on stop. Adds complexity.
- **Constructing `new Audio()` for tts_audio playback.** Explicitly out of scope (D-10). Don't add the code.
- **Persisting messages to localStorage.** D-18 forbids it.
- **`opacity-50` on disabled nav tabs.** DESIGN.md decisions log says Figma renders them at full opacity for visual consistency. Use `aria-disabled="true"` + no onClick + `cursor-default`.
- **`React.lazy` / dynamic import for any component in 1A.** Single screen, all components are loaded upfront. Don't over-engineer.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation | Manual byte construction or installing `uuid` package | `crypto.randomUUID()` | Native, RFC4122-compliant, available in all target browsers. [CITED: developer.mozilla.org/en-US/docs/Web/API/Crypto/randomUUID] |
| MIME-type guessing | Hardcoded `audio/webm` | `MediaRecorder.isTypeSupported()` probe | Safari doesn't support webm; will silently fail to record. |
| Class name conditionals | `` `btn ${active ? 'on' : ''}` `` | `cn()` from `lib/utils.ts` | Already installed (clsx + tailwind-merge). CLAUDE.md §7 forbids string concat. |
| State management | Multiple `useState` calls with manual coordination | `useReducer` with discriminated-union state | Discriminated unions catch impossible state transitions at compile time. |
| Recording duration limit | Polling `Date.now()` in a 100ms interval | `setTimeout(stop, 30_000)` registered at start | One-shot timer. Clear on early stop. |
| Permission detection | `navigator.permissions.query({name:'microphone'})` first | Just call `getUserMedia()` directly and catch `NotAllowedError` | CONTEXT D-06 says implicit permission. permissions.query has its own Safari quirks. |

**Key insight:** Phase 1A is intentionally minimal. Resist any urge to add libraries — every dependency added now is one Phase 2 has to vet.

---

## Common Pitfalls

### Pitfall 1: iOS Safari MediaRecorder MIME mismatch
**What goes wrong:** Code hardcodes `audio/webm`; on iOS Safari, `MediaRecorder` throws `NotSupportedError` at construction.
**Why it happens:** WebM is Google's container; Apple doesn't ship it. Safari supports MP4 with AAC.
**How to avoid:** Always probe via `MediaRecorder.isTypeSupported()` before constructing. The candidate order in §Pattern 3 covers Chrome/Firefox/Edge first, Safari second.
**Warning signs:** "Tested on Chrome desktop, ships on iPhone Safari, breaks." 1A's UAT must include real iOS Safari or at least Safari macOS (which has the same constraint).
**Confidence:** HIGH [CITED: developer.mozilla.org/en-US/docs/Web/API/MediaRecorder/isTypeSupported — documents that supported types vary by UA]

### Pitfall 2: `useEffect` re-running getUserMedia on every render
**What goes wrong:** Putting `start()` inside a useEffect tied to a state value retriggers permission prompts.
**Why it happens:** Misunderstanding of effect dependencies.
**How to avoid:** `useRecorder().start` is a useCallback. It's called from the TalkButton's onClick, NOT from a useEffect.

### Pitfall 3: localStorage access during SSR crashes the page
**What goes wrong:** `localStorage.getItem(...)` at the top of a client component body, or in a state initializer, executes on the server during hydration. `localStorage` is undefined → ReferenceError → render fails.
**Why it happens:** Next.js App Router still server-renders client components for hydration.
**How to avoid:** Wrap in `useEffect`. Initial state is `null`; effect populates it on mount.
**Confidence:** HIGH [CITED: nextjs.org/docs — App Router SSR semantics]

### Pitfall 4: Forgetting to release MediaStream tracks
**What goes wrong:** After stop, the browser still shows the red recording indicator until the tab closes; on some systems the mic LED stays on.
**Why it happens:** Stopping MediaRecorder doesn't stop the underlying MediaStream.
**How to avoid:** Call `stream.getTracks().forEach(t => t.stop())` in `onstop`. Pattern 4 above does this.

### Pitfall 5: 30s timer not cleared on early stop
**What goes wrong:** User taps stop at 5s → recording stops → 25s later the timeout fires and calls `recorder.stop()` on a recorder that's already inactive → DOMException.
**Why it happens:** Forgetting to clear the timeout in the stop path.
**How to avoid:** Pattern 4's `stop()` clears `timerRef`. The `MediaRecorder.stop()` call also guards with `state !== 'inactive'`.

### Pitfall 6: Hydration mismatch from `crypto.randomUUID()`
**What goes wrong:** Putting `crypto.randomUUID()` in initial state generates a different UUID server-side vs client-side → React hydration warning.
**Why it happens:** Module-level or render-time randomness in SSR.
**How to avoid:** Only call inside `useEffect`. Initial state for sessionId is `null`. TalkButton renders as disabled until set.

### Pitfall 7: Silent permission denial when user dismisses the prompt
**What goes wrong:** Some browsers don't reject the getUserMedia Promise immediately when the user dismisses (vs explicitly denies) the prompt — they leave it pending.
**Why it happens:** Browser UX inconsistency.
**How to avoid:** Not a 1A problem — user explicitly clicks denied → `NotAllowedError`. If the user just ignores the prompt, the rec button stays in "starting" indefinitely. Acceptable for 1A per the simplification mandate. Phase 2 can add a 5s timeout watchdog.

### Pitfall 8: `tts_audio` field handling in mock
**What goes wrong:** Mock sets `tts_audio: ""` (empty string) and frontend code tries to base64-decode it.
**Why it happens:** Confusion between "field absent" and "field empty".
**How to avoid:** Phase 1C's Python model uses `Optional[str] = None`. Mock fixture uses `null` (TS) to match. 1A doesn't read this field anyway, but Phase 2 will.

---

## Code Examples

### Wire Type Definitions (NEW file)

```typescript
// frontend/lib/types/chat.ts
// MUST MATCH backend/main.py ChatRequest / ChatResponse exactly.
// Phase 1C source of truth — do not re-shape.

import type { Level } from './session';

export interface ChatRequest {
  utterance: string;
  session_id: string;
  level: Level; // 'A2' | 'B1' | 'B2' | 'C1' — 1A always sends 'B1'
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
  tts_audio: string | null;     // base64 MP3 or null
  axes: Axes;
  character: CharacterParams;
  character_labels: CharacterLabels;
  hint_ko: InlineHintKo | null;
}
```

**Note on overlap with Phase 1B types:** `Axes` and `CharacterParams` are stated to live in `frontend/lib/types/character.ts` (1B owned) per ROADMAP Phase 1B SC #5. To avoid stepping on 1B, **1A defines its own minimal versions inside `chat.ts`** (or as `unknown`/object shape) since 1A doesn't render character morph. Two options for the planner:
- **Option A (recommended):** Define `Axes` and `CharacterParams` inline in `chat.ts` as the wire shape. When 1B merges its `character.ts`, Phase 2 reconciles (likely just re-exports from `character.ts`).
- **Option B:** Use `Record<string, number>` placeholders in `chat.ts` and let 1B replace them. Less type safety but zero overlap risk.

Discretion call. Option A gives better DX; the reconciliation is one import line at Phase 2 merge.

### app/page.tsx skeleton

```typescript
'use client';
import { useEffect, useReducer } from 'react';
import { reducer, initialState } from '@/lib/state/conversation';
import { useRecorder } from '@/lib/audio/useRecorder';
import { mockChat } from '@/lib/mocks/chat-mock';
import { ChatBubble } from '@/components/chat/ChatBubble';
import { HistorySheet } from '@/components/chat/HistorySheet';
import { PallyPlaceholder } from '@/components/chat/PallyPlaceholder';
import { TalkButton } from '@/components/audio/TalkButton';
import { BottomNav } from '@/components/nav/BottomNav';
import { Toast } from '@/components/ui/Toast';

const SESSION_KEY = 'pally:sessionId';

export default function Page() {
  const [state, dispatch] = useReducer(reducer, initialState);

  // sessionId bootstrap (SSR-safe)
  useEffect(() => {
    let id = window.localStorage.getItem(SESSION_KEY);
    if (!id) {
      id = crypto.randomUUID();
      window.localStorage.setItem(SESSION_KEY, id);
    }
    dispatch({ type: 'sessionId/set', id });
  }, []);

  // speaking → idle after 1.5s
  useEffect(() => {
    if (state.rec.kind !== 'speaking') return;
    const t = window.setTimeout(() => dispatch({ type: 'rec/speakingDone' }), 1500);
    return () => window.clearTimeout(t);
  }, [state.rec.kind]);

  const recorder = useRecorder({
    onStart: () => dispatch({ type: 'rec/start' }),
    onStop: async (_blob) => {
      // Blob ignored in 1A (D-09); Phase 2 will FormData this.
      dispatch({ type: 'rec/stop' });
      if (!state.sessionId) {
        dispatch({ type: 'rec/error', reason: 'generic', message: '세션이 준비되지 않았어요.' });
        return;
      }
      try {
        const resp = await mockChat({
          utterance: 'mock user utterance',
          session_id: state.sessionId,
          level: 'B1',
        });
        const userMsg = { id: crypto.randomUUID(), sessionId: state.sessionId, role: 'user' as const, transcript: resp.transcript, createdAt: new Date().toISOString() };
        const pallyMsg = { id: crypto.randomUUID(), sessionId: state.sessionId, role: 'pally' as const, transcript: resp.reply, createdAt: new Date().toISOString() };
        dispatch({ type: 'rec/processed', userMsg, pallyMsg });
      } catch (err) {
        // No silent swallow — surface as generic error per D-14
        const msg = err instanceof Error ? err.message : '응답을 받지 못했어요.';
        dispatch({ type: 'rec/error', reason: 'generic', message: msg });
      }
    },
    onPermissionDenied: () => dispatch({ type: 'rec/error', reason: 'permission-denied', message: '마이크 권한이 필요해요' }),
    onError: (message) => dispatch({ type: 'rec/error', reason: 'generic', message }),
  });

  // ... render: top bubble + Pally + TalkButton + GNB + Toast + HistorySheet
}
```

(Note: the literal `'mock user utterance'` above is illustrative; planner should decide what utterance text to send to mock — since fixture echoes, anything works. Could be a fixed string per the 1-fixture rule.)

---

## Runtime State Inventory

Not applicable — Phase 1A is a greenfield UI build, not a rename/refactor/migration phase. No prior renamed string or stored data to audit.

Single state-like consideration: `localStorage['pally:sessionId']`. There is no prior key to migrate from (Phase 0 didn't write any localStorage). Plan creates it fresh.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pages Router `_app.tsx` + `getInitialProps` | App Router + Server Components + `'use client'` | Next 13.4 (May 2023) | This project is App Router from Phase 0. |
| Manual UUID via byte arrays / `uuid` lib | `crypto.randomUUID()` | Baseline browser 2022 | Skip the dep. |
| Multiple `useState` per concern | `useReducer` with discriminated unions | React 16.8+ stabilized pattern | Better TS exhaustiveness. |
| `audio/wav` raw recording | `audio/webm;codecs=opus` (Chrome) / `audio/mp4` (Safari) | MediaRecorder maturity ~2020 | Smaller files, but cross-browser MIME requires probe. |

**Not deprecated but worth noting:**
- `framer-motion` and `motion` (the rebrand) are NOT needed for 1A. Senior plan Phase B/C adds motion polish.
- React 19 / Next 15 — out of scope; Phase 0 chose React 18 / Next 14.2.35.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `'mock user utterance'` placeholder text in mockChat call is acceptable since fixture echoes verbatim. | §Code Examples (page.tsx skeleton) | Low — visible only in echo'd transcript bubble. Planner can pick any literal. |
| A2 | `getUserMedia` Promise reliably rejects with `NotAllowedError` on user denial across iOS Safari 14.1+, Chrome, Firefox. | §Pattern 4, §Pitfall 7 | Medium — Safari quirks may leave the prompt-dismiss case as a pending Promise. Acceptable per CONTEXT.md "간단하게" mandate; Phase 2 can add watchdog. |
| A3 | `audio/mp4` is the correct Safari MediaRecorder MIME (verified via MDN as of training, not re-checked in this session). | §Standard Stack, §Pitfall 1 | Low — well-established. Worst case, the candidate list includes both `audio/mp4` and `audio/mp4;codecs=mp4a.40.2` so probe succeeds. |
| A4 | Defining `Axes` / `CharacterParams` inline in `chat.ts` instead of waiting for 1B's `character.ts` will not cause a merge conflict because 1A's types are wire-format only. | §Code Examples + Architecture | Low — planner can flag this for Phase 2 reconciliation as a one-liner re-export. |
| A5 | iOS Safari 14.1+ supports `MediaRecorder` at all (a 2024-era assumption based on MDN). | §Standard Stack | Medium-Low — well-documented but not re-verified. If wrong for an older Safari, 1A falls into the "no supported MIME" branch and shows the generic error. |
| A6 | The 1B-owned directory `frontend/components/pally/` does not yet exist on the branch (1B parallel work may have made it). | §Architecture | Low — verified `frontend/components/` does not exist yet on `gsd/phase-1a-fe-audio-shell` branch as of this session. 1A creates `components/` for the first time. If 1B merges first, planner must check before adding. |
| A7 | The Phase 1C mock fixture for `character` defaults (all zeros) and `character_labels` (`'neutral' / 'calm' / 'mild'`) won't clash with 1B's expected label vocabulary. | §Pattern 5 | Low — 1A doesn't render these labels; mock can use any strings. 1B determines real labels via `describe_character()` in `ai/matrix_engine.py`. |

---

## Open Questions

1. **What utterance string does mockChat get called with in 1A?**
   - What we know: Mock echoes `transcript: req.utterance`. There's no real STT, so something must be passed.
   - What's unclear: Planner choice — a fixed demo phrase (e.g., `"I had no lunch — I'm on a diet"` from Figma), or empty string, or a counter ("Mock turn 1", "Mock turn 2").
   - Recommendation: Use the Figma sample `"I had no lunch — I'm on a diet"` so the demo screenshot matches Figma. Easy to revisit.

2. **Does the `<PallyPlaceholder />` need to be visually accurate to Figma's Star4, or can it be a simpler placeholder shape?**
   - What we know: D-11 says "Figma의 Star4 spike 도형을 export한 SVG 1개". 1B replaces it with Canvas2D anyway.
   - What's unclear: Time budget — Star4 exact export vs. quick approximation.
   - Recommendation: Use Figma MCP `mcp__figma__get_design_context` on the Group 7 node to extract the Star4 SVG once, paste inline. Cost ~10 min, looks correct.

3. **Empty-state copy line break.** Senior plan A4 specifies `"오늘은 어떤 이야기를 해볼까요?\n마이크를 눌러 영어로 말해보세요"`. Single string with `\n` or two `<p>` elements?
   - Recommendation: Two `<p>` elements for accessibility (screen readers handle separately) and easier per-line styling. The first line larger (`text-subtitle-sb`), the second smaller (`text-caption-1` muted).

4. **Should the disabled BottomNav have any `aria-*` attributes?**
   - What we know: D-17 says nothing happens on tap. CLAUDE.md doesn't mandate WCAG for 1A (Senior plan defers A11y to Phase B/C).
   - Recommendation: Minimum `aria-disabled="true"` and no `onClick`. No focus-trap. Acceptable for demo.

5. **Where exactly does the chevron live, and what does it look like opened vs closed?**
   - Figma references: top chat bubble (427:2197) + chevron toggle.
   - Recommendation: Planner extracts the chevron icon via Figma MCP during execution; not a research-phase concern.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | `next dev` | ✓ (assumed — Phase 0 ran) | — | — |
| npm | install | ✓ (assumed — Phase 0 ran) | — | — |
| Browser with MediaRecorder | E2E mobile test | ✓ (Chrome desktop / Safari macOS / iOS Safari 14.1+) | — | — |
| Figma MCP | Pull Star4 SVG + ComponentSet | ✓ (per `<system-reminder>` MCP block) | — | Hand-trace from screenshot |
| Playwright MCP or `/browse` | E2E verification at 402px | ✓ (CLAUDE.md §5 references both) | — | Manual iPhone test |

No external services. No DB. No new package installs in 1A. **No env vars needed** — `NEXT_PUBLIC_BACKEND_URL` is already set in Vercel for Phase 2 future use; 1A doesn't read it.

No blocking missing dependencies.

---

## Validation Architecture

**Note:** `.planning/config.json` does not exist in this repo (verified). Treat `nyquist_validation` as **enabled** per default behavior — but the project has no test framework set up yet. The honest answer: **Phase 1A is mock-only UI and the team's practice (CLAUDE.md §5) is E2E verification via `/browse` or Playwright MCP at 402px on mobile**, not unit tests.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None installed |
| Config file | None |
| Quick run command | `cd frontend && npx tsc --noEmit` (type check) |
| Full suite command | `cd frontend && npm run build` (build check) + Playwright MCP E2E |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAIN-01 | Main screen renders Pally + rec button at 402px | manual / E2E (Playwright MCP) | `npm run build` + browse 402px | manual only |
| MAIN-01 | Rec button cycles idle → recording → processing → speaking → idle | manual / E2E | Playwright MCP recording | manual only |
| CHAT-01 | Top chat bubble shows last turn, chevron toggles history sheet | manual / E2E | Playwright MCP click + assert | manual only |
| CHAT-01 | SMS history: YOU=teal label / Pally=orange label | visual diff vs Figma | manual screenshot compare | manual only |

### Sampling Rate
- **Per task commit:** `cd frontend && npx tsc --noEmit && npm run lint`
- **Per wave merge:** `cd frontend && npm run build`
- **Phase gate:** Playwright MCP or `/browse` E2E at 402px through full state machine.

### Wave 0 Gaps
- [ ] No test framework setup needed for 1A — CLAUDE.md §5 explicitly says "타입체크/유닛테스트 통과만으로 검증 완료 처리 금지". E2E manual verification is the project norm.
- [ ] Adding Jest/Vitest now would be scope creep — defer to a future test-infrastructure phase.

*(Sufficient — type check + build + Playwright/browse covers the phase. No new tooling required.)*

---

## Security Domain

Phase 1A is mock-only frontend, no auth, no real network calls, no user data persisted (except a randomly-generated UUID in localStorage that has no PII).

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | partial | UUID v4 sessionId via `crypto.randomUUID()` (cryptographically random per Web Crypto spec). Stored in localStorage. Not a security boundary in 1A (no PII, no auth). Phase 2/1C is where RLS enforces it. |
| V4 Access Control | no | — |
| V5 Input Validation | low | Mock input is fully internal. The plan should still define `chat.ts` types so Phase 2 has a Zod boundary to bolt onto. |
| V6 Cryptography | no | — (`crypto.randomUUID()` is the only crypto, native and correct) |
| V12 File / Resource (microphone) | yes | `getUserMedia({ audio: true })` requests user consent via browser UI — standard pattern. No 1A-specific control needed. |

### Known Threat Patterns for Next.js Client + MediaRecorder

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via injected message content | Tampering | React auto-escapes — never use `dangerouslySetInnerHTML` for message text. (No instances proposed.) |
| MIME confusion in MediaRecorder | DoS / Info Disclosure | Probe before construction (Pattern 3). |
| Permission prompt fatigue | (UX, not security) | D-06 implicit prompt only on first tap — natural. |
| localStorage XSS extraction | Info Disclosure | sessionId has no PII; even if exfiltrated, the worst is the attacker resumes someone else's anonymous conversation. Acceptable for MVP. |

**No security-blocking items for 1A.** `/gsd-secure-phase` is unlikely to find issues since there's no auth/RLS code in this phase.

---

## Sources

### Primary (HIGH confidence)
- `/Users/clairelee/Desktop/claude-project/capstone-latest/.planning/phases/01A-fe-screens-audio-shell/01A-CONTEXT.md` — the locked decisions
- `/Users/clairelee/Desktop/claude-project/capstone-latest/.planning/REQUIREMENTS.md` — MAIN-01, CHAT-01
- `/Users/clairelee/Desktop/claude-project/capstone-latest/.planning/STATE.md` — Phase 1C wire format
- `/Users/clairelee/Desktop/claude-project/capstone-latest/.planning/ROADMAP.md` — Phase 1A SC
- `/Users/clairelee/Desktop/claude-project/capstone-latest/CLAUDE.md` — Code rules, error handling, NEVER/ALWAYS
- `/Users/clairelee/Desktop/claude-project/capstone-latest/DESIGN.md` — color/typography/spacing/motion tokens
- `/Users/clairelee/Desktop/claude-project/capstone-latest/frontend/lib/types/message.ts` — Phase 0 Message type
- `/Users/clairelee/Desktop/claude-project/capstone-latest/frontend/lib/types/session.ts` — Phase 0 Session + Level types
- `/Users/clairelee/Desktop/claude-project/capstone-latest/frontend/tailwind.config.ts` — Tailwind config + typography tokens
- `/Users/clairelee/Desktop/claude-project/capstone-latest/frontend/app/layout.tsx` — Pretendard import
- `/Users/clairelee/Desktop/claude-project/capstone-latest/frontend/app/page.tsx` — current placeholder
- `/Users/clairelee/Desktop/claude-project/capstone-latest/frontend/package.json` — installed deps (Next 14.2.35, React 18)
- `/Users/clairelee/Desktop/claude-project/capstone-latest/frontend/lib/utils.ts` — existing `cn()`
- `/Users/clairelee/Desktop/claude-project/capstone-latest/frontend/lib/supabase/client.ts` — Phase 0 anon client (1A does not use)
- `/Users/clairelee/Desktop/claude-project/capstone-latest/backend/main.py` (lines 84-106, 516-624) — Phase 1C `/api/chat` request/response models (source of truth for mock wire format)
- `/Users/clairelee/Desktop/claude-project/capstone-latest/docs/plan/2026-05-25-senior-design-elevation.md` — state coverage, deferred items, Pretendard limitations

### Secondary (MEDIUM confidence — from training, not re-verified this session)
- MDN `MediaRecorder.isTypeSupported()` — MIME types vary by UA, must probe
- MDN `MediaDevices.getUserMedia()` — Promise rejection with `NotAllowedError` on denial
- MDN `Crypto.randomUUID()` — modern browser availability
- Next.js App Router SSR semantics — `'use client'` boundary, localStorage gated by useEffect

### Tertiary (LOW confidence — none used; CONTEXT.md already locks design decisions)
- N/A — no WebSearch performed. CONTEXT.md provides explicit decisions; only verified facts and project files used.

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — All versions verified from `package.json`. No new deps proposed.
- **Architecture (useReducer, file layout, mock pattern):** HIGH — Standard React + Next App Router patterns. CONTEXT.md endorses useReducer.
- **MediaRecorder pattern:** MEDIUM — Code patterns are correct per MDN documentation (training-data confidence). Real iOS Safari verification deferred to Phase 2 per D-05 simplicity mandate.
- **Pitfalls:** HIGH — Each pitfall sourced from MDN, Next.js docs, or React docs.
- **Phase 1C wire format match:** HIGH — Verified by reading `backend/main.py` directly this session.
- **Figma node ID mapping:** HIGH — IDs match between CONTEXT.md and additional_context block.

**Research date:** 2026-05-25
**Valid until:** 2026-06-07 (demo deadline) — stable patterns, no fast-moving deps.
