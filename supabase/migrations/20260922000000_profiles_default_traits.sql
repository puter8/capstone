-- 신규 가입자 기본 성향 태그를 홈 화면의 기본 Pally 모습과 맞추고,
-- 옛 기본값이 남은 기존 사용자 태그를 교정한다.
-- forward-only. 기존 20260812000000_profiles_traits_updated_at.sql 은 수정하지 않는다.
--
-- 기존 기본값(bestie·ridiculous·lively·curious·blunt)은 Figma 예시 문구라,
-- 신규 가입자가 보는 Pally(frontend DEFAULT_AXES: Intimacy 20, Humor 10, Energy 30,
-- Curiosity 15, Formality 50)와 태그가 맞지 않았다.

-- 1) 신규 가입자 기본값: DEFAULT_AXES 에 태그 규칙(0~33 / 34~66 / 67~100)을 적용한 값.
alter table profiles
  alter column traits set default array['acquaint', 'serious', 'calm', 'indifferent', 'casual']::text[];

-- 2) 이미 대화를 끝낸 기록이 있는 사용자: 백엔드가 대화 종료 시 계산하는 것과 같은 기준
--    (가장 최근에 끝낸 대화 중 발화가 있는 대화의 최종 5축)으로 태그를 채운다.
--    구간 라벨은 backend/main.py 의 _TRAIT_TIERS 와 같다. 일회성 교정이라 SQL 로 옮겨 적는다.
with latest as (
  select distinct on (s.user_id) s.user_id, m.axes
  from sessions s
  join messages m on m.session_id = s.id
  where s.ended_at is not null
    and m.role = 'user'
    and m.axes is not null
  order by s.user_id, s.created_at desc, m.created_at desc
)
update profiles p
set traits = array[
      case when (l.axes->>'Intimacy')::numeric  <= 33 then 'acquaint'
           when (l.axes->>'Intimacy')::numeric  <= 66 then 'buddy'    else 'bestie' end,
      case when (l.axes->>'Humor')::numeric     <= 33 then 'serious'
           when (l.axes->>'Humor')::numeric     <= 66 then 'funny'    else 'ridiculous' end,
      case when (l.axes->>'Energy')::numeric    <= 33 then 'calm'
           when (l.axes->>'Energy')::numeric    <= 66 then 'lively'   else 'energetic' end,
      case when (l.axes->>'Curiosity')::numeric <= 33 then 'indifferent'
           when (l.axes->>'Curiosity')::numeric <= 66 then 'curious'  else 'inquisitive' end,
      case when (l.axes->>'Formality')::numeric <= 33 then 'blunt'
           when (l.axes->>'Formality')::numeric <= 66 then 'casual'   else 'formal' end
    ]::text[],
    updated_at = now()
from latest l
where p.id = l.user_id
  and p.traits = array['bestie', 'ridiculous', 'lively', 'curious', 'blunt']::text[];

-- 3) 아직 발화가 있는 대화를 끝낸 적이 없는 사용자: 새 기본값으로 교정한다.
update profiles p
set traits = array['acquaint', 'serious', 'calm', 'indifferent', 'casual']::text[],
    updated_at = now()
where p.traits = array['bestie', 'ridiculous', 'lively', 'curious', 'blunt']::text[]
  and not exists (
    select 1
    from sessions s
    join messages m on m.session_id = s.id
    where s.user_id = p.id
      and s.ended_at is not null
      and m.role = 'user'
      and m.axes is not null
  );
