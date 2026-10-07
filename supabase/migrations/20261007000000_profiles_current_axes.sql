-- Pally 의 "현재 모습"(5축)을 프로필에 저장한다.
-- forward-only. 칸 추가라 기존 코드·데이터에 영향이 없다 (null = 아직 말을 한 끝난 대화가 없음).
--
-- 지금까지는 홈 Pally 를 매번 "가장 최근에 끝낸 대화"에서 다시 계산했다. 지난 대화를
-- 이어 하는 동안에는 그 대화가 끝난 대화에서 빠져서 Pally 모습이 이전 대화의 것으로
-- 바뀌었다. 대화를 끝낼 때 모습을 저장하면(마이페이지 태그 profiles.traits 와 같은
-- 시점·같은 방식) 이어 하기가 모습을 건드리지 않고, 세 화면(홈·태그·다음 대화
-- 출발점)이 저장된 값 하나를 쓴다.

alter table profiles
  add column if not exists current_axes jsonb;

alter table profiles
  drop constraint if exists profiles_current_axes_object;
alter table profiles
  add constraint profiles_current_axes_object
  check (current_axes is null or jsonb_typeof(current_axes) = 'object');

-- 기존 사용자: 백엔드가 쓰던 기준과 같게 채운다 (발화가 있는 가장 최근에 '끝낸'
-- 대화의 마지막 사용자 발화 5축). 여러 번 실행해도 같은 결과다.
with latest as (
  select distinct on (s.user_id) s.user_id, m.axes
  from sessions s
  join messages m on m.session_id = s.id
  where s.ended_at is not null
    and m.role = 'user'
    and m.axes is not null
  order by s.user_id, s.ended_at desc, m.created_at desc
)
update profiles p
set current_axes = l.axes
from latest l
where p.id = l.user_id;
