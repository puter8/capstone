-- 5주차 activity-events: Achievements Daily Task 측정용 화면 이벤트 기록.
-- forward-only. 완료 평가는 서버(GET /achievements)가 하고, 여기선 "사실 이벤트"만 저장.

create table if not exists activity_events (
  user_id          uuid not null references auth.users (id) on delete cascade,
  event_id         uuid not null,                 -- 클라이언트 생성, 사용자 내 유일 (dedup 키)
  event_type       text not null,
  occurred_at      timestamptz,                   -- 클라이언트 발생 시각 (참고용)
  conversation_id  uuid,
  feedback_item_id uuid,
  received_at      timestamptz not null default now(),  -- 서버 수신 시각 (task 날짜 판정 기준)
  primary key (user_id, event_id)                 -- 재전송 dedup
);

alter table activity_events enable row level security;

drop policy if exists activity_events_select_own on activity_events;
create policy activity_events_select_own on activity_events
  for select using (auth.uid() = user_id);

-- task 완료 평가 쿼리용 (사용자 + 수신일 + 타입).
create index if not exists activity_events_user_received_idx
  on activity_events (user_id, received_at);
