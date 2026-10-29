-- 오늘의 표현(daily expression) — 그날 그 사용자가 받은 표현 1개를 고정.
-- 표현 카탈로그와 매칭 패턴은 ai/daily_expression.py 에 있고, 여기엔 "누가 언제
-- 어떤 표현을 받았는지"만 남긴다. 매일 다시 뽑지 않고 고정해야 하는 이유는 둘이다.
--   (1) 레벨(profiles.english_level)을 하루 중간에 바꾸면 표현이 갈려서, 이미
--       연습해 둔 표현의 Task 달성이 풀린다.
--   (2) 카탈로그에 표현을 추가 배포하면 레벨별 순서가 밀려, 배포 순간 그날 모든
--       사용자의 표현이 바뀐다. 이쪽이 레벨 변경보다 훨씬 자주 일어난다.
-- 쓰기는 service role(서버)만 한다 — daily_task_snapshots 와 같은 정책 모양.
-- forward-only.

create table if not exists daily_expression_snapshots (
  user_id      uuid not null references auth.users (id) on delete cascade,
  date_kst     date not null,
  expr_id      text not null,
  generated_at timestamptz not null default now(),
  primary key (user_id, date_kst)
);

alter table daily_expression_snapshots enable row level security;

drop policy if exists daily_expression_snapshots_select_own on daily_expression_snapshots;
create policy daily_expression_snapshots_select_own on daily_expression_snapshots
  for select using (auth.uid() = user_id);
