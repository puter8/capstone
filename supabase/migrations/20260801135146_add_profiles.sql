-- profiles: Supabase Auth 사용자 확장 (온보딩 정보, 영어 레벨)
create table profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text not null default '',
  english_level text not null default 'A2'
    check (english_level in ('A2', 'B1', 'B2', 'C1')),
  onboarding_completed boolean not null default false,
  created_at timestamptz not null default now()
);

alter table profiles enable row level security;

create policy "profiles_select_own" on profiles
  for select using (auth.uid() = id);

-- INSERT/UPDATE는 의도적으로 정책을 만들지 않음.
-- authenticated 역할은 SELECT만 가능하고, 쓰기는 백엔드 API가 service_role로 처리.