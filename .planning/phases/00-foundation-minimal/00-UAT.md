---
status: complete
phase: 00-foundation-minimal
source: 00-01-SUMMARY.md
started: 2026-05-21T00:00:00Z
updated: 2026-05-22T13:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: From clean state, `cd frontend && npm run dev` boots Next.js on port 3000 within ~10s with no errors in terminal (no module-not-found, no missing-env crash, no port conflicts).
result: pass

### 2. Home Page Renders "Pally"
expected: With dev server running, open http://localhost:3000 in a browser. Page renders the literal text "Pally" with Tailwind padding (`p-4`) and small text size (`text-sm`). No console errors, no hydration warnings. This exercises the full Tailwind + `cn()` + `@/*` alias chain (SC#5).
result: pass

### 3. /api/health Returns ok:true
expected: With dev server running, `curl http://localhost:3000/api/health` returns HTTP 200 with body exactly `{"ok":true}` (SC#1). No extra fields, no trailing data.
result: pass
evidence: |
  curl http://localhost:3000/api/health
  → HTTP 200, body: {"ok":true}

### 4. Supabase Connection Check
expected: From `frontend/`, run `npm run check:supabase`. Script loads `.env.local`, makes a real HTTP roundtrip to the Supabase project (`orhodalbxhbzlvjsqalu`), and prints "Supabase reachable" then exits 0 (SC#3). Failure modes: missing env crashes loudly; bad URL/key prints an error instead of silently passing.
result: pass
evidence: |
  cd frontend && npm run check:supabase
  → "Supabase reachable. user: null" (exit 0)

### 5. Env Files Not Tracked by Git
expected: Run `git ls-files | grep .env.local` in repo root. Output is empty (no `.env.local` files committed anywhere). Both `frontend/.env.local` and `backend/.env.local` exist locally but are gitignored. Root `.env.local` no longer exists (D-14 per-service routing). T-1/T-2 mitigation visible (SC#4).
result: pass
evidence: |
  git ls-files | grep .env.local → empty
  ls frontend/.env.local backend/.env.local → both present (290B, 466B)
  ls .env.local at repo root → no matches (D-14 confirmed)
  git check-ignore -v → both gitignored (frontend/.gitignore:29, .gitignore:12)

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — all tests passed]
