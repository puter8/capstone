---
phase: 00-foundation-minimal
plan: 01
status: completed
completed: 2026-05-21
commit: 1bae051
branch: gsd/phase-0-foundation-minimal
---

# Phase 0 — Plan 01 SUMMARY

## What was built

Next.js 14 App Router scaffold + minimal UI type contracts + Supabase anon client (real connection-verified) + Tailwind v3 / `cn()` utility + `/api/health` + per-service env routing (D-14). Phase 0 SC#1–SC#5 all green; T-1/T-2/T-3/T-4 all mitigated.

## Files created

### Scaffold (create-next-app@14, npm)
- `frontend/package.json` — `next@14.2.35`, `tailwindcss@^3.4.1`, TS strict
- `frontend/package-lock.json`
- `frontend/tsconfig.json` — `"@/*": ["./*"]` (Pitfall 6: `--no-src-dir`)
- `frontend/tailwind.config.ts`
- `frontend/postcss.config.mjs`
- `frontend/next.config.mjs`
- `frontend/.eslintrc.json`
- `frontend/.gitignore` (includes `next-env.d.ts`)
- `frontend/app/layout.tsx`
- `frontend/app/globals.css`

### Authored (Pattern 1–5b + D-16)
- `frontend/app/page.tsx` — `<main className={cn('p-4 text-sm')}>Pally</main>` (D-16, exercises Tailwind + cn + `@/*` alias)
- `frontend/app/api/health/route.ts` — `Response.json({ ok: true })`, `force-static`
- `frontend/lib/utils.ts` — `cn()` via `clsx + twMerge`
- `frontend/lib/supabase/client.ts` — anon client, **throws on missing env** (CLAUDE.md §5 #3; no `?? ''` fallback)
- `frontend/lib/types/message.ts` — `Message` + `MessageRole = 'user'|'pally'`, NO `axes`/`character` (D-05)
- `frontend/lib/types/session.ts` — `Session` + `Level = 'A2'|'B1'|'B2'|'C1'` (D-06)
- `frontend/scripts/check-supabase.ts` — standalone connection verifier (real HTTP roundtrip)
- `frontend/.env.example` — exactly 3 `NEXT_PUBLIC_*` keys (D-11)

### Env-routing applied (D-14)

Root `.env.local` deleted. Per-key destinations:

| Key | Destination | Status |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `frontend/.env.local` | real value migrated |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `frontend/.env.local` | real value migrated |
| `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000` | `frontend/.env.local` | new placeholder (1C/2 overwrites) |
| `SUPABASE_SERVICE_ROLE_KEY` | `backend/.env.local` | placeholder migrated (1C fills real value) |
| `DATABASE_URL` | `backend/.env.local` | placeholder migrated |
| `REDDIT_CLIENT_ID` | `backend/.env.local` | placeholder migrated |
| `REDDIT_CLIENT_SECRET` | `backend/.env.local` | placeholder migrated |
| `REDDIT_USER_AGENT` | `backend/.env.local` | placeholder migrated |
| `OPENAI_API_KEY` | **deleted (no destination)** | local file already sanitized to `your_openai_api_key_here` before this session; server-side revoke confirmed by PM 최윤서 at platform.openai.com (see PM revoke status below) |

Both `frontend/.env.local` and `backend/.env.local` confirmed gitignored (`git check-ignore` exits 0).

## Verified versions

- `next@14.2.35` (NOT 15+ — RESEARCH § State of the Art rejects Tailwind v4 default)
- `tailwindcss@^3.4.1`
- `@supabase/supabase-js@^2.106.1`
- `clsx@^2.1.1`
- `tailwind-merge@^3.6.0`
- `tsx@^4.22.3` (devDep)

## E2E verification log

1. `cd frontend && npm run dev` → port 3000 boots
2. `curl http://localhost:3000/api/health` → `{"ok":true}` (200) — SC#1 ✓
3. `curl http://localhost:3000/` → contains literal `Pally` (Tailwind + `cn()` + `@/*` alias chain) — SC#5 ✓
4. `npm run check:supabase` → `Supabase reachable. user: null` — SC#3 ✓ (real HTTP roundtrip to `/auth/v1/user`)
5. `npx tsc --noEmit` → exit 0
6. `npm run lint` → no warnings/errors
7. `git ls-files | grep .env.local` → empty (T-1 mitigation verified)

## PM revoke status (T-3)

**Resolved.** PM 최윤서 confirmed in team channel that `OPENAI_API_KEY` has been revoked server-side at https://platform.openai.com → Settings → API keys. Local copy on disk was already a `your_openai_api_key_here` placeholder before this session, so Task 1's deletion of root `.env.local` removed only the placeholder; the actual credential is no longer valid against OpenAI's servers. T-3 closed.

## Deviations from plan

Two plan defects discovered during execution and patched forward:

1. **check-supabase.ts: env loading missing.** Plan Pattern 4 + Task 4 npm-script definition (`tsx scripts/check-supabase.ts`) did not load `.env.local` — `tsx` alone is just a TS runtime. **Fix:** added `process.loadEnvFile('.env.local')` (Node 20.6+ built-in, zero new dependencies) at the top of `scripts/check-supabase.ts`. `package.json` script string unchanged, preserving Task 4 AC.

2. **check-supabase.ts: `auth.getUser()` no longer hits the network.** Plan comment claimed `auth.getUser()` "makes a real HTTP round-trip to /auth/v1/user". In current `@supabase/supabase-js@2.106.1`, `getUser()` with no arg only inspects the local session and throws `AuthSessionMissingError` (400) client-side — never reaches the wire. **Fix:** passed a dummy JWT (`auth.getUser('dummy-jwt-to-force-server-roundtrip')`) so the library makes a real GET `/auth/v1/user` with `Authorization`; server returns 401, which is the "reachable" signal. Updated the inline comment to explain the new behavior. Plan AC's literal `grep -q "auth.getUser()"` no longer matches (now `auth.getUser('...')`), but the higher-priority must_have ("real HTTP round-trip") is now actually satisfied (it wasn't with the original snippet).

3. **`frontend/README.md` from create-next-app deleted** before commit — CLAUDE.md §9 NEVER (no auto-generated documentation).

4. **Plan-Task 6 staged `.env.local` deletion via `git add -u`** assumed root `.env.local` was tracked — it never was (always gitignored), so the line was a no-op. Removed from the actual staging step.

## Notes for downstream

- **Phase 1A (이찬희):** import `@/lib/types/message`, `@/lib/types/session`, `@/lib/utils` for mock data + `cn()`. No need to add Pally renderer or character types — that's 1B.
- **Phase 1B (김민주):** will add `frontend/lib/types/character.ts` + `frontend/components/pally/*` + `frontend/app/dev/pally/*`. `Message.transcript` field is locked to match 1C's Supabase column name; do not rename.
- **Phase 1C (백은혜):** will add `frontend/lib/supabase/server.ts` (service-role client) + read `backend/.env.local` from FastAPI. Service-role key is currently a placeholder in `backend/.env.local` — fill in real value before first DB write.
- **All phases:** dev requires `frontend/.env.local` to exist with real NEXT_PUBLIC_SUPABASE_* values. If a teammate clones the repo, they must populate `frontend/.env.local` from `frontend/.env.example` and add the project's Supabase URL + anon key (orhodalbxhbzlvjsqalu).

## SC tracking

| SC# | Description | Status |
|---|---|---|
| SC#1 | `/api/health` returns `{"ok":true}` | ✓ |
| SC#2 | `Message` + `Session` exist, NO `Axes`/`CharacterParams` | ✓ |
| SC#3 | `check:supabase` real roundtrip exits 0 | ✓ |
| SC#4 | `.env.example` has exactly 3 NEXT_PUBLIC_* keys, root `.env.local` gone, both subpath `.env.local` gitignored | ✓ |
| SC#5 | Tailwind + cn() + `@/*` alias compile in `app/page.tsx` | ✓ |

| Threat | Mitigation | Status |
|---|---|---|
| T-1 | Per-file staging, gitignore re-check pre-commit | ✓ closed |
| T-2 | service-role key only in `backend/.env.local`; never in `frontend/` files or `.env.example` | ✓ closed |
| T-3 | PM revoke confirmed server-side at platform.openai.com | ✓ closed |
| T-4 | `/api/health` body is `{ok:true}` exactly, `force-static` removes per-request side-channels | ✓ closed |
