-- profiles: API 계약(UserProfile)에 맞춰 traits + updated_at 추가.
-- forward-only. 기존 20260801135146_add_profiles.sql 는 수정하지 않는다.

-- traits: 표시 순서대로 정확히 5개. 생성 로직(5축 → traits)은 후속(AI).
-- 지금은 Figma 기본 태그를 seed 로 채워 계약의 "정확히 5개 NOT NULL" 을 만족시킨다.
alter table profiles
  add column if not exists traits text[] not null
    default array['bestie', 'ridiculous', 'lively', 'curious', 'blunt']::text[];

alter table profiles
  add column if not exists updated_at timestamptz not null default now();

-- 계약: traits 는 항상 정확히 5개.
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'profiles_traits_len5'
  ) then
    alter table profiles
      add constraint profiles_traits_len5 check (array_length(traits, 1) = 5);
  end if;
end $$;
