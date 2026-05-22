# Phase 0: Foundation (Minimal) - Research

**Researched:** 2026-05-21
**Domain:** Next.js 14 App Router scaffold, Tailwind v3, Supabase anon client, env hygiene
**Confidence:** HIGH

## Summary

Phase 0 is a 0.5-day mechanical scaffold inside `frontend/`. All consequential decisions are already locked in CONTEXT.md (D-01 ~ D-13). Research scope is therefore narrow: confirm the exact `create-next-app@14` invocation, version pins it produces, the Tailwind v3 + `cn()` shadcn pattern, the cheapest Supabase "connection-only" verification when no tables exist, and the safe order-of-operations for the root `.env.local` cleanup (which contains more keys than CONTEXT.md anticipated).

**Primary recommendation:**
1. Delete `frontend/.gitkeep` before scaffolding (`create-next-app` aborts on a non-empty target dir, and `.gitkeep` is not in its `validFiles` allowlist).
2. Run `npx create-next-app@14 frontend --ts --tailwind --app --no-src-dir --import-alias '@/*' --eslint --use-npm`.
3. Add `clsx@^2` + `tailwind-merge@^3` + `@supabase/supabase-js@^2` on top.
4. Migrate root `.env.local` → `frontend/.env.local` keeping ONLY the two `NEXT_PUBLIC_SUPABASE_*` keys; everything else stays root-deleted with PM confirmation (more keys than CONTEXT.md saw — see §Common Pitfalls).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Package manager = **npm**. `cd frontend && npm install && npm run dev`.
- **D-02:** **No `src/` directory**. `frontend/app/`, `frontend/lib/`, `frontend/components/` live directly under `frontend/`.
- **D-03:** Import alias **`@/*`** (Next.js default). E.g. `@/lib/types/message`, `@/lib/supabase/client`.
- **D-04:** **Next.js default ESLint only**. No Prettier / lint-staged / husky in Phase 0.
- **D-05:** `Message` = `{ id: string; sessionId: string; role: 'user' | 'pally'; transcript: string; createdAt: string }`. NO `axes` / `character` fields (Phase 1B adds those). Field name is `transcript` (not `content`) to match Phase 1C Supabase column.
- **D-06:** `Session` = `{ id: string; characterName: string; level: 'A2' | 'B1' | 'B2' | 'C1'; createdAt: string; endedAt?: string }`. `level` is a literal union.
- **D-07:** TS = camelCase, Supabase = snake_case. Convert at boundary. No conversion utility in Phase 0 (1A decides if mock data needs one).
- **D-08:** Dates as ISO strings only. No `Date` objects on the wire.
- **D-09:** `/api/health` returns `{ ok: true }` with HTTP 200. **No external deps** (no Supabase ping inside).
- **D-10:** Supabase connection verification = **separate one-off script** (e.g. `frontend/scripts/check-supabase.ts`). Decoupled from `/api/health`.
- **D-11:** `frontend/.env.example` with exactly 3 keys: `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **D-12:** Migrate root `.env.local` Supabase URL/anon → `frontend/.env.local`. **Delete OpenAI key**. PM (최윤서) confirms OpenAI key revoke. Delete the root `.env.local` file itself.
- **D-13:** Also create `frontend/.env.local` (gitignored, real dev values) so 이찬희 can run `npm run dev` immediately.

### Claude's Discretion

- `cn()` location = **`frontend/lib/utils.ts`** (shadcn convention, imported as `@/lib/utils`).
- Tailwind version = **v3 (3.4.x)**, NOT v4. Reason: `create-next-app@14 --tailwind` installs `tailwindcss@^3.4.1` by default; v4 changes config model and is unnecessary risk for a 0.5-day scaffold.
- `Message` / `Session` file layout = **separate files** (`lib/types/message.ts`, `lib/types/session.ts`). Each export is named and small; aligns with Phase 1B adding `lib/types/character.ts` as a third sibling. No `lib/types/index.ts` barrel — direct imports only.
- `frontend/app/page.tsx` placeholder content = a single `<main>` with text `"Pally"` and no styling beyond a Tailwind utility class (proves Tailwind compiles).
- Exact `create-next-app` flags = `--ts --tailwind --app --no-src-dir --import-alias '@/*' --eslint --use-npm`.

### Deferred Ideas (OUT OF SCOPE)

- Prettier + lint-staged + husky — Phase 2 or later cleanup.
- `docs/code-convention.md` — PM separate task.
- Root `.env.example` or monorepo secret manager — explicitly excluded by ROADMAP.
- `Axes` / `CharacterParams` types — Phase 1B (`frontend/lib/types/character.ts`).
- Supabase `sessions` / `messages` tables + RLS — Phase 1C.
- `backend/main.py` OpenAI dependency cleanup — Phase 1C will rewrite `backend/` for GCP.
- `frontend/lib/supabase/server.ts` (service-role server client) — Phase 1C.
- `ai/` Python work — Phase 1B.
- `assets/visualizer.html` — Phase 1B reference only.
- Root `README.md` — untouched in Phase 0.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SESSION-01 | "익명 세션 ID로 Supabase `sessions` 테이블에 세션 생성, 모든 메시지는 `messages` 테이블에 axes/character JSONB와 함께 저장한다. RLS는 session_id 기반이다." (REQUIREMENTS.md) | Phase 0 covers only the **TS type contract** half: `Message` + `Session` shapes (D-05, D-06) so 1A can mock-render and 1C can later persist with `transcript`/`session_id`/`character_name`/`level` column names that already match. Schema + RLS = Phase 1C. Traceability table confirms: "SESSION-01: Phase 0 (types) + Phase 1C (schema/RLS)". |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

The planner MUST enforce these in every task:

- §5 #4 / §9 NEVER: **`git add .` forbidden**. Each commit stages files by name.
- §9 NEVER: **No emojis** in code or commit messages.
- §9 NEVER: **No README.md / ARCHITECTURE.md auto-generation** unless explicitly requested. (Phase 0 produces PLAN/REVIEW/etc. via gsd, but no spontaneous docs.)
- §6 Git: Branch = `gsd/phase-0-foundation-minimal` (per template, slug from `phase_slug`). Commits in imperative mood, ≤72 chars, explain *why*.
- §6 TypeScript: **strict mode**, `any` forbidden (TODO with reason if unavoidable), comments + identifiers in English.
- §6 Next.js: Server Components by default; `'use client'` only when interaction/hooks/browser API required.
- §9 NEVER: **Commit `.env*`** (or GCP JSON or Supabase service_role). Phase 0 *moves* `.env.local` files — they must never be staged. `.gitignore` already covers `.env.local` (verified — line 11: `.env.local`).
- §9 NEVER: **Empty `catch {}`, silent fallback `|| {}` / `?? []`**. The `check-supabase.ts` script must let errors propagate with descriptive messages.
- §3 (external API): The Supabase connection check IS an external API call. Plan must specify the actual HTTP call performed and its expected response shape, not just "supabase client constructs without throwing."

## Standard Stack

### Core (installed by `create-next-app@14 --ts --tailwind --eslint`)

| Library | Version (verified 2026-05-21) | Purpose | Source |
|---------|------|---------|--------|
| `next` | `14.2.35` (latest of v14 line) | App Router framework | [VERIFIED: `npm view next@14 version`] |
| `react` | `^18` | UI library | [VERIFIED: create-next-app v14.2.35 source `templates/index.ts`] |
| `react-dom` | `^18` | DOM renderer | [VERIFIED: same source] |
| `typescript` | `^5` | TS compiler | [VERIFIED: same source] |
| `@types/node` | `^20` | Node typings | [VERIFIED: same source] |
| `@types/react` | `^18` | React typings | [VERIFIED: same source] |
| `@types/react-dom` | `^18` | React DOM typings | [VERIFIED: same source] |
| `tailwindcss` | `^3.4.1` (latest patch: `3.4.19`) | Utility CSS | [VERIFIED: create-next-app v14.2.35 source + `npm view tailwindcss@3 version`] |
| `postcss` | `^8` | CSS pipeline | [VERIFIED: same source] |
| `eslint` | `^8` | Linter | [VERIFIED: same source] |
| `eslint-config-next` | `14.2.35` | Next.js ESLint preset | [VERIFIED: same source — pinned to Next version] |

### Added on top (Phase 0 explicit installs)

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| `@supabase/supabase-js` | `^2.106.1` | Anon client for `lib/supabase/client.ts` (D-10 connection check) | [VERIFIED: `npm view @supabase/supabase-js version` = 2.106.1] |
| `clsx` | `^2.1.1` | Conditional className builder for `cn()` | [VERIFIED: `npm view clsx version` = 2.1.1] |
| `tailwind-merge` | `^3.6.0` | Tailwind class conflict resolver inside `cn()` | [VERIFIED: `npm view tailwind-merge version` = 3.6.0] |

### NOT installed (explicitly out of scope per CONTEXT/D-04)

| Skipped | Why |
|---------|-----|
| `@supabase/ssr` | Adds `createBrowserClient`/`createServerClient` cookie machinery for auth SSR. Phase 0 has no auth; D-10 only needs a one-off connection check. `@supabase/supabase-js` is sufficient and matches CONTEXT.md wording. 1C may add `@supabase/ssr` later. |
| `autoprefixer` | Not in `create-next-app@14` default deps. Tailwind v3's PostCSS pipeline handles prefixing internally. [VERIFIED: postcss.config.mjs template only loads `tailwindcss` plugin.] |
| `prettier`, `husky`, `lint-staged` | D-04 explicit defer. |
| `zod` | Mentioned by CLAUDE.md §6 for "external input validation" — but Phase 0 has no external input (health endpoint is static, type files are static, `check-supabase.ts` only reads env). Defer to 1A/1C. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@supabase/supabase-js` | `@supabase/ssr` (`createBrowserClient`) | Supabase now recommends `@supabase/ssr` for App Router projects that need SSR auth ([CITED: supabase.com/docs/guides/auth/server-side/creating-a-client]). Phase 0 has neither auth nor SSR — extra dep is noise. CONTEXT.md says "anon client", which `supabase-js` covers directly. Decision: stay with `supabase-js`. |
| `tailwindcss@^4` | `tailwindcss@^3.4.1` | v4 (`4.3.0` latest) changes the config model (`@theme` directive in CSS, no `tailwind.config.ts`). `create-next-app@14 --tailwind` still generates v3 config files. CONTEXT Claude's Discretion explicitly prefers v3. Decision: v3. |
| Single `lib/types/index.ts` barrel | Separate `message.ts` + `session.ts` | Barrel imports re-export everything and complicate tree-shaking + circular-dep diagnosis. Separate files match the eventual `character.ts` sibling Phase 1B adds. Decision: separate. |

**Installation commands (after scaffold succeeds):**
```bash
cd frontend
npm install @supabase/supabase-js clsx tailwind-merge
```

## Architecture Patterns

### Recommended Project Structure (post-scaffold)

```
frontend/
├── app/
│   ├── api/
│   │   └── health/
│   │       └── route.ts          # GET /api/health → { ok: true }
│   ├── layout.tsx                # scaffold default (Server Component)
│   ├── page.tsx                  # placeholder "Pally" text (Server Component)
│   └── globals.css               # scaffold default (Tailwind directives)
├── lib/
│   ├── supabase/
│   │   └── client.ts             # createClient(URL, anon key) — D-10
│   ├── types/
│   │   ├── message.ts            # D-05
│   │   └── session.ts            # D-06
│   └── utils.ts                  # cn() — shadcn pattern
├── scripts/
│   └── check-supabase.ts         # one-off connection verifier — D-10
├── .env.example                  # 3 keys only — D-11
├── .env.local                    # real dev values, gitignored — D-13
├── next.config.mjs               # scaffold default
├── postcss.config.mjs            # scaffold default
├── tailwind.config.ts            # scaffold default (already includes app/, components/, pages/)
├── tsconfig.json                 # scaffold default with strict:true, paths: { "@/*": ["./*"] }
├── package.json
└── .eslintrc.json
```

The scaffold generates `components/` only if you opt into shadcn — `create-next-app` does **not** create `components/` by itself. Phase 0 leaves `components/` absent; 1A and 1B create it as needed.

### Pattern 1: App Router Route Handler (D-09 health endpoint)

**What:** A `route.ts` exporting an HTTP method handler in App Router.
**When to use:** Webhooks, health probes, third-party callbacks. Not for mutations (those use Server Actions per CLAUDE.md §6).
**Example:**
```typescript
// frontend/app/api/health/route.ts
// Source: Next.js App Router Route Handler convention
// [CITED: nextjs.org/docs/app/api-reference/file-conventions/route]
export const dynamic = 'force-static'; // health probe is constant; cache-friendly for Vercel

export function GET(): Response {
  return Response.json({ ok: true });
}
```

Notes:
- Named export `GET` (HTTP verb in uppercase). Default exports are not used for route handlers.
- `Response.json()` is the idiomatic helper. Status 200 is the default.
- `dynamic = 'force-static'` is optional but signals to Vercel that no per-request work is needed. CONTEXT.md D-09 explicitly forbids external deps inside this handler.

### Pattern 2: shadcn `cn()` utility

**What:** Conditional Tailwind class composition with conflict-aware merging.
**When to use:** Any component that conditionally applies Tailwind classes (CLAUDE.md §6 forbids string concatenation).
**Example:**
```typescript
// frontend/lib/utils.ts
// Source: shadcn/ui canonical lib/utils.ts
// [CITED: ui.shadcn.com/docs/installation/manual]
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

Phase 0 will not consume `cn()` (placeholder `page.tsx` is one-line). It exists so 1A/1B can import `@/lib/utils` without each adding their own variant.

### Pattern 3: Supabase anon browser client (D-10)

**What:** A module-level singleton `createClient` instance with anon credentials.
**When to use:** Client Components or scripts that read public data / call public APIs. No auth, no cookies, no service role.
**Example:**
```typescript
// frontend/lib/supabase/client.ts
// Source: @supabase/supabase-js v2 README; matches CLAUDE.md §6 (client = anon key)
// [CITED: github.com/supabase/supabase-js]
import { createClient } from '@supabase/supabase-js';

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  throw new Error(
    'Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. Check frontend/.env.local.',
  );
}

export const supabase = createClient(url, anonKey);
```

Notes:
- Throwing at module load surfaces missing config immediately (CLAUDE.md §9: crash beats silent fallback). Do NOT use `?? ''`.
- Plain `createClient` from `supabase-js` is correct for Phase 0; switch to `@supabase/ssr` only when 1C adds auth/SSR (out of scope here).
- This file is imported by both the eventual UI code AND `scripts/check-supabase.ts`.

### Pattern 4: One-off connection verification script (D-10)

**What:** A standalone TypeScript script that proves the URL + anon key reach a real Supabase instance, without depending on any table existing yet.
**Example:**
```typescript
// frontend/scripts/check-supabase.ts
// Verifies NEXT_PUBLIC_SUPABASE_URL + NEXT_PUBLIC_SUPABASE_ANON_KEY reach a live project.
// Uses GoTrue /auth/v1/user — a no-table endpoint that returns { user: null } for an anon JWT.
// [CITED: supabase.com/docs/reference/javascript/auth-getuser]
import { supabase } from '../lib/supabase/client';

async function main(): Promise<void> {
  const { data, error } = await supabase.auth.getUser();
  if (error && error.status !== 401) {
    // 401 is expected for a fresh anon client — it proves the endpoint replied.
    // Anything else (network, DNS, bad URL) is a real failure — let it crash.
    throw error;
  }
  console.log('Supabase reachable. user:', data.user);
}

main().catch((err) => {
  console.error('Supabase connection check FAILED:', err);
  process.exit(1);
});
```

Run with: `npx tsx frontend/scripts/check-supabase.ts` (add `tsx` as devDep, or invoke via `node --experimental-strip-types` on Node 22+ — we have Node 24.14, so `node --experimental-strip-types frontend/scripts/check-supabase.ts` works). **Recommendation:** add `tsx@^4` as devDep for stability and one `npm run check:supabase` script.

Why `auth.getUser()` and not a table read: there are no tables yet (Phase 1C creates them). `auth.getUser()` is a real HTTP round-trip to `/auth/v1/user` on the Supabase project — it confirms URL + key + network reachability without requiring any schema. A successful "user is null" response (or 401 for an unauthenticated anon JWT) means the connection works.

### Pattern 5: TS type files (D-05, D-06)

```typescript
// frontend/lib/types/message.ts
export type MessageRole = 'user' | 'pally';

export interface Message {
  id: string;
  sessionId: string;
  role: MessageRole;
  transcript: string;
  createdAt: string; // ISO 8601
}
```

```typescript
// frontend/lib/types/session.ts
export type Level = 'A2' | 'B1' | 'B2' | 'C1';

export interface Session {
  id: string;
  characterName: string;
  level: Level;
  createdAt: string;   // ISO 8601
  endedAt?: string;    // ISO 8601
}
```

Notes:
- `MessageRole` and `Level` are exported separately so 1A/1B/1C can narrow without re-declaring literals (DRY).
- All `string` IDs — no branded types in Phase 0 (overkill for MVP).
- `interface` over `type` because future Phase 1B may want to extend (`Message` gaining `axes`/`character` is a real possibility; declaration merging is easier with `interface`).

### Anti-Patterns to Avoid

- **Barrel export `lib/types/index.ts`:** Creates implicit coupling, breaks tree-shaking, hides what's exported. Use direct imports.
- **`Date` objects on the type:** D-08 mandates ISO strings. Never type `createdAt: Date`.
- **`?? ''` on env vars:** Silent fallback (CLAUDE.md §9). Throw explicitly.
- **Adding `/api/health` Supabase ping:** D-09 forbids. Vercel/Railway poll this endpoint; external deps inside make the probe lie about app health.
- **Default-exporting `cn`, `supabase`, types:** CLAUDE.md §6 requires named exports except for pages/layouts/route handlers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Conditional Tailwind classes | Template-string `${cond ? 'a' : 'b'}` concat | `cn()` (clsx + tailwind-merge) | Tailwind class conflicts (e.g., `p-2 p-4`) aren't resolved by string concat; `tailwind-merge` keeps the later one. CLAUDE.md §6 explicitly forbids string concat. |
| Next.js scaffold | Hand-written `next.config`, `tsconfig`, ESLint, Tailwind PostCSS plugin chain | `create-next-app@14 --ts --tailwind --eslint` | The defaults are battle-tested and match Vercel's deployment expectations. Hand-rolling is 100% downside. |
| Supabase client construction | Re-implementing JWT signing / fetch wrappers | `@supabase/supabase-js` `createClient` | Singleton, retry logic, realtime, future auth — all already there. |
| Env var validation | Optional chaining + ad-hoc checks scattered around | Module-load `throw new Error(...)` at the single boundary in `lib/supabase/client.ts` | One place to fail loudly; downstream code can trust the env exists. (Heavier validation via `zod`/`@t3-oss/env-nextjs` is overkill for 3 keys in Phase 0.) |

**Key insight:** Phase 0 is small enough that "don't hand-roll" mostly means "let `create-next-app` do its job and add three small libs on top." The temptation to over-customize at scaffold time is the real risk.

## Runtime State Inventory

**Trigger:** Phase 0 includes a rename/cleanup component — moving keys out of root `.env.local` and deleting it. Below is the inventory.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | None — Phase 0 has no DB writes. (Supabase project itself stores nothing for Phase 0 because no tables exist yet.) | None — verified by reading ROADMAP Phase 0 SC; tables = Phase 1C. |
| **Live service config** | Vercel Root Directory and env vars referencing the (not-yet-created) `frontend/` will be configured by 이찬희 outside Phase 0 commits. **PM-side action:** PM (최윤서) must confirm OpenAI API key revocation in OpenAI dashboard (key currently in root `.env.local` line `OPENAI_API_KEY=...`). | Plan must include a checklist item: "Confirm with PM that OpenAI key has been revoked at platform.openai.com before deleting the local copy." |
| **OS-registered state** | None. No daemons, no services, no scheduled tasks reference Phase 0 artifacts. | None — verified by `ls .planning/phases/` and absence of any `launchd` / `systemd` / Task Scheduler integration. |
| **Secrets and env vars** | Root `.env.local` (uncommitted, gitignored) contains **8 keys**, not the 2 CONTEXT.md anticipated: `OPENAI_API_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`, `DATABASE_URL`. See §Common Pitfalls Pitfall 4. | Plan must (a) preserve the two `NEXT_PUBLIC_SUPABASE_*` values into `frontend/.env.local`, (b) capture and decide on each of the other 6 (most likely all stay deleted or move to `backend/.env` later — but the decision is per-key and needs PM input). |
| **Build artifacts / installed packages** | None — `frontend/` contains only `.gitkeep`. No `node_modules`, no `.next/`, no compiled output. | None. |

**Canonical question:** *After every file is updated, what runtime systems still have the old string cached, stored, or registered?*
**Answer:** Only the OpenAI account itself — that key string is live at OpenAI until PM revokes it. Local deletion of the file does not revoke the credential server-side.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js (≥20) | `create-next-app`, `npm`, all dev tooling | yes | 24.14.0 | — |
| npm | D-01 package manager | yes | 11.9.0 | — |
| `npx` | Running `create-next-app` | yes | 11.9.0 | — |
| Network access to npm registry | Installing scaffold deps | yes (verified — `npm view next version` returned `16.2.6`) | — | — |
| Network access to `*.supabase.co` | `check-supabase.ts` actual ping | not verified at research time | — | If unreachable, script throws and Phase 0 SC#3 fails — investigate before scaffolding |
| Supabase project URL + anon key (real values) | D-13 `frontend/.env.local` real dev values | yes — both already in root `.env.local` (to be migrated, D-12) | — | — |
| `tsx` (TS script runner) | `scripts/check-supabase.ts` invocation | no | — | Use `node --experimental-strip-types` (Node 24.14 supports). Recommended: add `tsx@^4` as devDep for stability. |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** `tsx` — fallback exists, but installing it is one extra `npm install -D tsx` line in the plan.

## Common Pitfalls

### Pitfall 1: `create-next-app` aborts because `frontend/` is not empty
**What goes wrong:** Running `npx create-next-app@14 frontend ...` exits with `The directory frontend contains files that could conflict: .gitkeep` and bails.
**Why it happens:** `create-next-app`'s `isFolderEmpty()` allowlist is hard-coded; `.gitkeep` is not on it (only `.gitignore`, `.git`, `.DS_Store`, etc. are). [VERIFIED: read `create-next-app@14.2.35/helpers/is-folder-empty.ts`]
**How to avoid:** Delete `frontend/.gitkeep` (and any `.DS_Store`) before scaffolding. Stage that deletion as part of the same commit that lands the scaffold.
**Warning signs:** Error message lists conflicting files in red.

### Pitfall 2: `create-next-app` written to monorepo root by mistake
**What goes wrong:** Running it without a target directory creates the app at the current working directory (project root) and pollutes the monorepo.
**How to avoid:** Always pass `frontend` as the project-directory argument. Verify CWD = project root before running. Plan task should be `cd <project root> && npx create-next-app@14 frontend ...`.

### Pitfall 3: Default Tailwind `content` glob misses `components/` because we don't create one yet
**What goes wrong:** Scaffolded `tailwind.config.ts` content glob includes `./components/**/*` (and `./pages/**` we won't use, and `./app/**`). That's fine — Tailwind silently ignores non-existent directories. Phase 1A/1B will add `components/`.
**How to avoid:** No action. Leave the default config untouched. [VERIFIED: read `create-next-app@14.2.35/templates/app-tw/ts/tailwind.config.ts`]

### Pitfall 4: Root `.env.local` has 6 unexpected extra keys (NOT just OpenAI)
**What goes wrong:** CONTEXT.md D-12 mentions migrating Supabase keys and deleting one OpenAI key. The actual root `.env.local` contains 8 keys total: `OPENAI_API_KEY`, the two `NEXT_PUBLIC_SUPABASE_*`, **`SUPABASE_SERVICE_ROLE_KEY`** (server-only, never goes to frontend!), **`REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`/`REDDIT_USER_AGENT`** (presumably for the v2 Reddit PRAW slang pipeline `ENGINE-03` in REQUIREMENTS.md — out of scope for MVP), and **`DATABASE_URL`** (likely points to Supabase Postgres direct connection).
**Why it happens:** The file was hand-maintained before phase planning began.
**How to avoid:**
1. Before deleting, **dump the keys via the redaction command** (`grep -E '^[A-Z_]+=' .env.local | sed 's/=.*/=<redacted>/'`) and capture the list in the plan.
2. Per-key decision matrix the plan must include:
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` → **move** to `frontend/.env.local` (D-12).
   - `SUPABASE_SERVICE_ROLE_KEY` → **stash for Phase 1C `backend/.env`** (Notion private page per SETUP.md §5). Do NOT put in `frontend/.env.local` (CLAUDE.md §6: service_role is server-only, never imported in client code).
   - `OPENAI_API_KEY` → **delete + PM revoke** (D-12).
   - `REDDIT_*` (3 keys), `DATABASE_URL` → **defer per-key decision to PM**. They are not in any MVP requirement. Suggested treatment: stash in Notion, delete from disk, revisit in v2 (`ENGINE-03`).
3. Only after all 8 keys are accounted for, delete root `.env.local`.
4. Confirm `.gitignore` line 11 (`.env.local`) still covers both root and `frontend/.env.local` — it does (glob is unanchored). [VERIFIED: read `.gitignore`]
**Warning signs:** Treating "Supabase migration" as a 2-key operation will lose the other 6 silently.

### Pitfall 5: Putting Supabase ping inside `/api/health`
**What goes wrong:** Vercel + Railway poll `/api/health` for load-balancer signaling. If Supabase is briefly down, health goes red and traffic gets rerouted (or instance gets killed) even though the app itself is fine.
**Why it happens:** Intuition says "health check should check dependencies."
**How to avoid:** D-09 forbids it. Keep `/api/health` static. Use `scripts/check-supabase.ts` for one-time verification; if a runtime liveness check is ever needed for Supabase, that's a separate endpoint with its own SLO.

### Pitfall 6: `tsconfig.json` "@/*" path lands at `./*` not `./src/*`
**What goes wrong:** With D-02 `--no-src-dir`, the alias resolves from `frontend/` root, so `@/lib/utils` → `frontend/lib/utils.ts`. If someone copies a tsconfig snippet from a `src/`-style project, imports break.
**How to avoid:** Trust the `create-next-app` output. [VERIFIED: with `--no-src-dir`, `tsconfig.json` paths = `{ "@/*": ["./*"] }`.] Do not hand-edit `paths`.

### Pitfall 7: Forgetting `next-env.d.ts` is auto-generated and should be committed
**What goes wrong:** Developer sees `next-env.d.ts` is generated and adds it to `.gitignore`, breaking TS in CI.
**How to avoid:** Next.js documents this file as committed. Default `.gitignore` from `create-next-app` does NOT exclude it. Leave alone.

### Pitfall 8: Running `npm run dev` from project root instead of `frontend/`
**What goes wrong:** No `package.json` at root — fails confusingly.
**How to avoid:** All Phase 0 dev/build commands run from `frontend/`. Vercel Root Directory = `frontend/` (ROADMAP §Repo Layout, CLAUDE.md §7). Document this in PLAN.md verification steps.

## Code Examples

(All examples in §Architecture Patterns above are verified. Repeating them here would duplicate.)

## State of the Art

| Old Approach | Current Approach (2026-05) | When Changed | Impact for Phase 0 |
|--------------|------------------|--------------|--------|
| Next.js Pages Router | **App Router** | Next 13.4 stable (May 2023) | We're already on App Router — no decision needed. |
| `@supabase/auth-helpers-nextjs` | `@supabase/ssr` for SSR auth | mid-2024 | Out of scope for Phase 0 (no auth). 1C may revisit. |
| Tailwind v3 config in `tailwind.config.ts` | Tailwind v4 `@theme` in CSS | Tailwind 4.0 (early 2025) | We stay on v3 (CONTEXT discretion). v4 migration is a separate future phase. |
| Anon/service_role API keys | New "publishable" / "secret" keys | Supabase 2025 (legacy keys deprecated end of 2026) | [CITED: supabase.com/docs/guides/api/api-keys] Anon keys still work for the demo timeline (June 7, 2026). Migration can be a v2 task. |
| `npx create-next-app` Tailwind = v3 | Likely v4 in `create-next-app@15`+ | Next 15 generation | We pin `create-next-app@14` explicitly to keep v3 defaults. |

**Deprecated / outdated to avoid:**
- `@supabase/auth-helpers-nextjs` — replaced by `@supabase/ssr`; don't reach for it.
- `pages/api/health.ts` style routing — App Router uses `app/api/health/route.ts`.
- `getServerSideProps` etc. — App Router uses Server Components / Route Handlers / Server Actions.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Root `.env.local` `DATABASE_URL` and `REDDIT_*` keys are not used by any MVP code path. | Pitfall 4 / Runtime State Inventory | Low. They aren't referenced by `backend/main.py` filenames in scope, and no MVP requirement (REQUIREMENTS.md v1) uses them. Still, PM should confirm before deletion — plan includes that confirmation step. |
| A2 | Supabase anon key in root `.env.local` matches the SETUP.md `puter8/capstone` project (`orhodalbxhbzlvjsqalu`). | D-12 migration | If mismatched, `check-supabase.ts` will fail loudly. Plan's verification step catches this. |
| A3 | `tsx@^4` is acceptable as a small dev-only dep for running the connection-check script. | Pattern 4 | Trivial. Fallback: `node --experimental-strip-types`. |
| A4 | The dev (`이찬희`) is on macOS/Linux (not Windows-only) — `pbcopy`, POSIX-quoted flags work. | Implicit | Low — `npm` and `npx` cross-platform, but plan should not assume `pbcopy`. |
| A5 | OpenAI key in root `.env.local` is the same key already known to PM (i.e., PM can revoke it without further sleuthing). | D-12 | If unknown provenance, the revoke conversation gets harder. Plan step: 이찬희 shares the key prefix (first 7 chars) with PM, PM identifies + revokes. |

## Validation Architecture

**Skipped:** `.planning/config.json` has `workflow.nyquist_validation = false`. Per researcher rules, this section is omitted. Phase 0 verification relies on the hand-written checks below in §Verification Commands.

## Verification Commands

For the planner to embed as acceptance criteria on individual tasks. All assume CWD = project root unless noted.

| Goal | Command | Expected |
|------|---------|----------|
| Confirm Node ≥20 | `node --version` | `v20.*` or higher (have `v24.14.0`) |
| Scaffold succeeds | `ls frontend/package.json && ls frontend/tsconfig.json && ls frontend/tailwind.config.ts && ls frontend/app/page.tsx && ls frontend/postcss.config.mjs` | All five files exist |
| Type check clean | `cd frontend && npx tsc --noEmit` | Exit 0, zero errors |
| ESLint clean (default config) | `cd frontend && npm run lint` | Exit 0 |
| Dev server boots | `cd frontend && npm run dev` (run in background, then curl) | `curl -fsS http://localhost:3000/api/health` returns `{"ok":true}` with HTTP 200 |
| Health endpoint via Next.js build (prod) | `cd frontend && npm run build && npm run start &` then `curl -fsS http://localhost:3000/api/health` | `{"ok":true}` |
| Tailwind compiled | `cd frontend && curl -fsS http://localhost:3000/ \| grep -q 'class='` | non-empty (page renders with class attributes) |
| Supabase connection real | `cd frontend && npx tsx scripts/check-supabase.ts` | exits 0, prints `Supabase reachable. user: null` |
| Root `.env.local` deleted | `ls /Users/clairelee/Desktop/claude-project/capstone-latest/.env.local 2>&1` | `No such file or directory` |
| `frontend/.env.local` exists, gitignored | `ls frontend/.env.local && git check-ignore frontend/.env.local` | file exists, command exits 0 |
| `.env.example` has exactly 3 keys | `grep -cE '^[A-Z_]+=' frontend/.env.example` | `3` |
| No `.env*` staged | `git status --porcelain \| grep -E '\\.env' \|\| true` | empty (no env files appear in `git status`) |
| Type files in place | `ls frontend/lib/types/message.ts frontend/lib/types/session.ts frontend/lib/supabase/client.ts frontend/lib/utils.ts` | all four exist |
| `cn()` exports compile | `cd frontend && node -e "require('./.next/server/...').cn"` — too brittle; instead: `cd frontend && npx tsc --noEmit` covers it | exit 0 |

## Security Domain

`.planning/config.json` does not have `security_enforcement: false` (key absent — treat as enabled per researcher rules).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control for Phase 0 |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in Phase 0 or MVP (anonymous sessions only). |
| V3 Session Management | no | Same. |
| V4 Access Control | no | Same; Supabase RLS is Phase 1C. |
| V5 Input Validation | no | No external input handled (health endpoint is static, types are static). 1A/1C revisit with `zod`. |
| V6 Cryptography | no | No crypto code. Never hand-roll — when 1C signs/verifies, it uses Supabase's libraries. |
| V7 Error Handling | yes | CLAUDE.md §5 #3 + §9 enforce: no `catch {}`, no silent fallback. Errors crash with descriptive messages. |
| V8 Data Protection | yes | `.env*` never committed. `service_role` key never enters `frontend/`. Pitfall 4 above is the key concrete risk. |
| V14 Configuration | yes | Default Next.js + Tailwind + ESLint config; no custom hardening yet. `frontend/.gitignore` (from `create-next-app`) covers `.env*`, `.next/`, `node_modules/`. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation for Phase 0 |
|---------|--------|---------------------|
| Secret leakage via `.env` commit | Information Disclosure | `.gitignore` line 11 covers `.env.local`; staged-secret guard rule in CLAUDE.md §9; plan tasks stage files by name (CLAUDE.md §5 #4). |
| Service-role key shipped to client bundle | Information Disclosure | `service_role` key from root `.env.local` is **stashed for Phase 1C `backend/`**, NOT migrated to `frontend/`. Pattern 3 only reads `NEXT_PUBLIC_*` env vars. |
| Health endpoint information disclosure | Information Disclosure | `{ ok: true }` only — no version string, no env data. D-09 enforces. |
| Supabase anon key in client bundle | (None — by design) | `NEXT_PUBLIC_*` is the canonical Supabase pattern; protection lives in RLS policies (Phase 1C). |

## Open Questions (RESOLVED)

1. **Are the 6 non-Supabase, non-OpenAI keys in root `.env.local` safe to delete?**
   - What we know: `OPENAI_API_KEY` (delete), `SUPABASE_SERVICE_ROLE_KEY` (move to Phase 1C `backend/.env` Notion stash), `REDDIT_*` (3 keys — likely from `ENGINE-03` v2 work, not MVP), `DATABASE_URL` (likely Supabase direct Postgres).
   - What's unclear: whether `DATABASE_URL` or `REDDIT_*` are actively referenced by any local script not in scope here.
   - Recommendation: Plan inserts a single human-loop checkpoint where 이찬희 confirms with PM whether to (a) discard all 4 unknowns, (b) stash them in Notion under "deferred MVP credentials", or (c) some per-key mix. Default to (b) — safer.
   - **RESOLVED (D-14):** Per-key `env_routing_table` — `SUPABASE_SERVICE_ROLE_KEY` + `DATABASE_URL` + `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` + `REDDIT_USER_AGENT` → `backend/.env.local`; `OPENAI_API_KEY` → delete + PM (최윤서) revoke at platform.openai.com; `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` → `frontend/.env.local`. Root `.env.local` deleted after all 8 keys placed.

2. **`tsx` vs `node --experimental-strip-types` for `check-supabase.ts`?**
   - What we know: Node 24.14 supports `--experimental-strip-types`; `tsx@^4` is mainstream.
   - What's unclear: team preference; PM may want minimal devDeps.
   - Recommendation: Add `tsx` as devDep + a `package.json` script `"check:supabase": "tsx scripts/check-supabase.ts"`. Cleaner and reproducible.
   - **RESOLVED (D-15):** `tsx@^4` as devDependency + `"check:supabase": "tsx scripts/check-supabase.ts"` script in `frontend/package.json`.

3. **Should `frontend/app/page.tsx` placeholder use the Tailwind `cn()` import at all?**
   - What we know: Doing so proves the whole chain compiles (Tailwind directive in `globals.css` + `cn()` from `lib/utils` + alias `@/lib/utils`).
   - What's unclear: 1A will rewrite this file immediately.
   - Recommendation: Yes — render `<main className={cn('p-4 text-sm')}>Pally</main>`. Proves end-to-end wiring in <60s for free. Even if 1A overwrites, the throw-away test confirmed Phase 0 SC#5.
   - **RESOLVED (D-16):** `frontend/app/page.tsx` renders `<main className={cn('p-4 text-sm')}>Pally</main>` — exercises the full Tailwind + `cn()` chain at scaffold time. Phase 1A overwrites Day 1.

## Sources

### Primary (HIGH confidence)
- `create-next-app@14.2.35` source: [`templates/index.ts`](https://github.com/vercel/next.js/blob/v14.2.35/packages/create-next-app/templates/index.ts) — definitive dep versions (verified via `gh api`)
- `create-next-app@14.2.35` source: [`helpers/is-folder-empty.ts`](https://github.com/vercel/next.js/blob/v14.2.35/packages/create-next-app/helpers/is-folder-empty.ts) — `.gitkeep` pitfall (verified)
- `create-next-app@14.2.35` template: [`templates/app-tw/ts/tailwind.config.ts`](https://github.com/vercel/next.js/blob/v14.2.35/packages/create-next-app/templates/app-tw/ts/tailwind.config.ts) (verified)
- `npm view next@14`, `npm view @supabase/supabase-js`, `npm view tailwindcss@3`, `npm view clsx`, `npm view tailwind-merge` — version verification (2026-05-21)
- [shadcn/ui Manual Installation](https://ui.shadcn.com/docs/installation/manual) — `cn()` canonical pattern
- [Supabase: Creating a Supabase client for SSR](https://supabase.com/docs/guides/auth/server-side/creating-a-client) — confirms `@supabase/ssr` is for SSR/auth scenarios, not Phase 0's anon-only use
- `.planning/ROADMAP.md` Phase 0 § Success Criteria 1-5 + Repo Layout
- `.planning/REQUIREMENTS.md` SESSION-01 + Traceability table
- `CLAUDE.md` §1 / §5 / §6 / §7 / §9 (team conventions, NEVER/ALWAYS)
- `docs/shared/SETUP.md` §1-5 (local toolchain, env vars)
- `.planning/phases/00-foundation-minimal/00-CONTEXT.md` — locked decisions D-01 ~ D-13

### Secondary (MEDIUM confidence)
- [DEV: "cn" utility function in shadcn-ui/ui](https://dev.to/ramunarasinga/cn-utility-function-in-shadcn-uiui-3c4k) — corroborates shadcn `cn()` pattern
- [Next.js docs: create-next-app CLI](https://nextjs.org/docs/app/api-reference/cli/create-next-app) — flag reference (cross-checked against `--help` output)

### Tertiary (LOW confidence)
- General-purpose 2026 Next.js setup blog posts — used only to spot-check that v3 Tailwind + Next 14 + npm is still a viable combo. None influence a load-bearing claim.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — every version pin verified against `npm view` and `create-next-app@14.2.35` source on 2026-05-21.
- Architecture: **HIGH** — patterns are official (Route Handler) or canonical (shadcn `cn()`, supabase-js `createClient`).
- Pitfalls: **HIGH** — Pitfalls 1 and 4 verified empirically (`is-folder-empty.ts` read; `.env.local` keys enumerated by redacted grep).
- Open questions: **MEDIUM** — questions 1 and 3 need human confirmation; question 2 is a small style choice.

**Research date:** 2026-05-21
**Valid until:** 2026-06-20 (~30 days; demo is 2026-06-07 so the entire MVP runs within this window). Tailwind v4 default in `create-next-app@15` will eventually invalidate the Tailwind-v3 assumption, but we pin `create-next-app@14` explicitly.
