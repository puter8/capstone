-- 5주차 quota: 무료 사용자 일일 turn 사용량 + 원자적 차감.
-- forward-only. 기존 마이그레이션은 수정하지 않는다.

-- 일일 사용량 (KST 날짜 bucket).
create table if not exists usage_daily (
  user_id    uuid not null references auth.users (id) on delete cascade,
  date_kst   date not null,
  used_turns integer not null default 0,
  primary key (user_id, date_kst)
);

alter table usage_daily enable row level security;

-- 본인 것만 조회 (쓰기는 service_role 만).
drop policy if exists usage_daily_select_own on usage_daily;
create policy usage_daily_select_own on usage_daily
  for select using (auth.uid() = user_id);

-- 원자적 예약: used < limit 이면 +1 하고 새 값 반환, 아니면 -1 (소진).
-- INSERT..ON CONFLICT DO UPDATE 는 충돌 행을 잠그므로 동시 요청이 직렬화된다 →
-- "둘 다 마지막 1개 통과" race 를 방지한다.
create or replace function reserve_turn(p_user_id uuid, p_date date, p_limit int)
returns int
language plpgsql
as $$
declare
  new_used int;
begin
  insert into usage_daily (user_id, date_kst, used_turns)
  values (p_user_id, p_date, 1)
  on conflict (user_id, date_kst)
    do update set used_turns = usage_daily.used_turns + 1
    where usage_daily.used_turns < p_limit
  returning used_turns into new_used;

  if new_used is null then
    return -1;  -- 한도 도달 (update 스킵됨)
  end if;
  return new_used;
end;
$$;

-- 예약 롤백: turn 이 실패(STT 무음/실패, AI 실패)해 차감을 취소할 때. 0 미만으로 안 내려감.
create or replace function release_turn(p_user_id uuid, p_date date)
returns void
language plpgsql
as $$
begin
  update usage_daily
    set used_turns = greatest(used_turns - 1, 0)
    where user_id = p_user_id and date_kst = p_date;
end;
$$;
