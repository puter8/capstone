-- Pally remembers what the user said about themselves, so the next conversation
-- starts from what it already knows. Facts are extracted in the background
-- after a conversation ends, never inside a turn.
--
-- key is a closed list, not free text. Real Gemini calls showed that a prompt
-- forbidding health conditions was ignored 5 times out of 5 (it stored
-- health_condition: depression), while a closed key list left the model no
-- category to put it in. The check constraint keeps that guarantee in the
-- database, so a later prompt change cannot quietly widen what we store.
create table public.user_memories (
  user_id uuid not null references auth.users(id) on delete cascade,
  key text not null check (key in (
    'name', 'age', 'city', 'occupation', 'workplace', 'field_of_study', 'school',
    'school_year', 'family', 'pet', 'hobby', 'skill', 'language', 'plan')),
  value text not null check (length(btrim(value)) between 1 and 200),
  -- Deleting a conversation takes away what was learned from it: history
  -- deletion must not leave derived facts behind. Account deletion cascades
  -- through user_id, the same way sessions does.
  source_session_id uuid not null references public.sessions(id) on delete cascade,
  created_at timestamptz not null default clock_timestamp(),
  -- The same fact restated in a later conversation is not a new row. A changed
  -- fact (a new major, a new city) is, and the reader keeps the newest.
  primary key (user_id, key, value)
);

-- The only read path: one user's facts, newest first.
create index user_memories_user_recent_idx
  on public.user_memories(user_id, created_at desc);

alter table public.user_memories enable row level security;
create policy user_memories_owner_read on public.user_memories
  for select to authenticated using (user_id = auth.uid());
revoke all on public.user_memories from public, anon, authenticated, service_role;
grant select on public.user_memories to authenticated;
grant select, insert, delete on public.user_memories to service_role;

-- The prompt block for the conversation, built once when the conversation is
-- created. A turn already reads its session row, so injecting memory costs it
-- no extra round trip, and the facts cannot change mid-conversation: extraction
-- runs after a conversation ends.
alter table public.sessions add column if not exists memory_prompt text;
