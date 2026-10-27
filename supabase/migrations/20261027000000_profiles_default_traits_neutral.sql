-- 신규 가입자 기본 성향 태그를 새 기본 Pally(Intimacy 0, 나머지 4축 50)에 맞춘다.
-- forward-only. 20260922000000_profiles_default_traits.sql 은 수정하지 않는다.
--
-- 새 기본 5축(frontend DEFAULT_AXES, backend _INITIAL_AXES): Intimacy 0, Humor 50,
-- Energy 50, Curiosity 50, Formality 50. 태그 규칙(0~33 / 34~66 / 67~100)을 적용하면
-- acquaint · funny · lively · curious · casual 이다.

-- 1) 신규 가입자 기본값.
alter table profiles
  alter column traits set default array['acquaint', 'funny', 'lively', 'curious', 'casual']::text[];

-- 2) 아직 발화가 있는 대화를 끝낸 적이 없는 사용자 중 옛 기본값을 그대로 가진 사용자는
--    새 기본값으로 교정한다. 대화 기록이 있는 사용자의 태그는 건드리지 않는다.
update profiles p
set traits = array['acquaint', 'funny', 'lively', 'curious', 'casual']::text[],
    updated_at = now()
where p.traits = array['acquaint', 'serious', 'calm', 'indifferent', 'casual']::text[]
  and not exists (
    select 1
    from sessions s
    join messages m on m.session_id = s.id
    where s.user_id = p.id
      and s.ended_at is not null
      and m.role = 'user'
      and m.axes is not null
  );
