-- Conversation rows are written only by the backend (service_role), which checks
-- ownership, quota and completion state. The owner-scoped INSERT/UPDATE/DELETE
-- policies on sessions let a signed-in user PATCH any column of their own rows
-- through PostgREST with the public anon key: axes_contribution (the cumulative
-- Pally axes), ended_at/created_at (achievements and streaks), reopen_count.
-- A malformed axes_contribution also made the user's own home and turns fail.
-- The frontend never writes these tables directly (it only calls supabase.auth).
-- Owner-scoped SELECT stays for any read-only client use.
revoke insert, update, delete on public.sessions from public, anon, authenticated;
grant insert, update, delete on public.sessions to service_role;

-- Same reasoning for messages: deleting own rows before /complete changed the
-- conversation's vote input. Account/history deletion runs through the backend.
revoke delete on public.messages from public, anon, authenticated;
grant delete on public.messages to service_role;

-- reserve_turn is already service_role-only. release_turn was never revoked, so
-- any client could call it; it is SECURITY INVOKER and blocked by RLS today, but
-- one future UPDATE policy on usage_daily would turn it into a quota reset.
revoke all on function public.release_turn(uuid, date) from public, anon, authenticated;
grant execute on function public.release_turn(uuid, date) to service_role;
