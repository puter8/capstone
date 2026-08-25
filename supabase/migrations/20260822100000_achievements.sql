-- 5주차 Achievements: 일일 Task 선택 고정 + Streak.
-- forward-only. 완료 판정은 서버가 계산하고, 여기엔 "그날 선택된 3개"와 "그날 자격 여부"만 저장.

-- 그날 결정적으로 선택된 3개 task id (같은 날 안 바뀌게 고정).
create table if not exists daily_task_snapshots (
  user_id      uuid not null references auth.users (id) on delete cascade,
  date_kst     date not null,
  task_ids     text[] not null,               -- 정확히 3개
  generated_at timestamptz not null default now(),
  primary key (user_id, date_kst)
);
alter table daily_task_snapshots enable row level security;
drop policy if exists daily_task_snapshots_select_own on daily_task_snapshots;
create policy daily_task_snapshots_select_own on daily_task_snapshots
  for select using (auth.uid() = user_id);

-- 그날 3개 모두 완료(qualified) 여부 — Streak 계산의 원천.
create table if not exists streak_days (
  user_id   uuid not null references auth.users (id) on delete cascade,
  date_kst  date not null,
  qualified boolean not null default false,
  primary key (user_id, date_kst)
);
alter table streak_days enable row level security;
drop policy if exists streak_days_select_own on streak_days;
create policy streak_days_select_own on streak_days
  for select using (auth.uid() = user_id);
