-- Mark the exact saved user turns requested by /complete. App and database
-- clocks must never decide whether a resumed turn is eligible for review.
alter table public.messages
  add column if not exists feedback_requested_at timestamptz;

create index if not exists messages_pending_session_feedback_idx
  on public.messages (id, session_id)
  where role = 'user' and feedback is null and feedback_requested_at is not null;

-- Message writes already go through the backend's ownership/quota checks.
-- Prevent direct client inserts or resetting feedback/markers from scheduling
-- unmetered model calls. Existing owner-scoped SELECT/DELETE policies remain.
revoke insert, update on public.messages from public, anon, authenticated;
grant insert, update on public.messages to service_role;

create or replace function public.complete_conversation_with_feedback(
  p_conversation_id uuid,
  p_user_id uuid,
  p_expected_reopen_count integer
) returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_session public.sessions%rowtype;
  v_now timestamptz := clock_timestamp();
begin
  select * into v_session from public.sessions
  where id = p_conversation_id and user_id = p_user_id
  for update;
  if not found then
    raise exception 'conversation_not_found' using errcode = 'P0002';
  end if;
  if v_session.reopen_count <> p_expected_reopen_count then
    raise exception 'conversation_changed' using errcode = 'P0001';
  end if;

  update public.sessions
  set ended_at = coalesce(ended_at, v_now)
  where id = p_conversation_id
  returning * into v_session;

  update public.messages
  set feedback_requested_at = v_now
  where session_id = p_conversation_id and role = 'user'
    and feedback is null and feedback_requested_at is null;

  return to_jsonb(v_session);
end;
$$;

revoke all on function public.complete_conversation_with_feedback(uuid, uuid, integer)
  from public, anon, authenticated;
grant execute on function public.complete_conversation_with_feedback(uuid, uuid, integer)
  to service_role;

-- Serialize saving a user/reply pair against closing its session. The bulk
-- insert holds this row lock until both messages commit. If close wins, the
-- late turn fails and the backend refunds its quota reservation.
create or replace function public.require_active_session_for_user_message()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_ended_at timestamptz;
begin
  if new.role = 'user' then
    select ended_at into v_ended_at from public.sessions
    where id = new.session_id for update;
    if found and v_ended_at is not null then
      raise exception 'conversation_closed' using errcode = 'P0001';
    end if;
  end if;
  return new;
end;
$$;

revoke all on function public.require_active_session_for_user_message()
  from public, anon, authenticated;

create trigger messages_require_active_session
  before insert on public.messages
  for each row execute function public.require_active_session_for_user_message();
