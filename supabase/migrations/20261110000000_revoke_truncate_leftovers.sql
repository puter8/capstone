-- Leftovers from the initial `grant all` on these tables. 20261005200000 and
-- 20261106000000 took back the DML, but REFERENCES, TRIGGER and TRUNCATE stayed.
--
-- TRUNCATE is the one that matters: it empties a table without consulting RLS, so
-- the owner-scoped policies on sessions and messages do not apply to it. PostgREST
-- only issues SELECT/INSERT/UPDATE/DELETE and RPC, and no SECURITY INVOKER function
-- truncates, so nothing can reach it with the anon key today. This is the same kind
-- of unreachable leftover that release_turn was, closed for the same reason.
--
-- REFERENCES and TRIGGER go with it: both let a client attach something to a table
-- only the backend writes. Reads are unaffected - anon and authenticated already
-- hold no SELECT on either table.
revoke truncate, references, trigger on public.sessions, public.messages
  from public, anon, authenticated;
