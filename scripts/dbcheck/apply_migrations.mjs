// 운영과 같은 순서로 전체 마이그레이션을 실제 Postgres(PGlite)에 적용한다.
// Supabase 전용 객체(auth 스키마, auth.uid(), service_role 롤)는 PGlite 에 없으므로
// 최소한으로 흉내 내고, 그 사실을 결과에 명시한다.
import { PGlite } from '@electric-sql/pglite';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';

// 이 스크립트 위치 기준 — 어느 PC 에서 받아도 그대로 돈다.
const DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '../../supabase/migrations');
const db = await new PGlite();

// Supabase 가 기본 제공하는 것들 — 여기서는 스텁이다. 실제 동작은 운영에서 확인해야 한다.
await db.exec(`
  create schema if not exists auth;
  create table auth.users (id uuid primary key, email text);
  create or replace function auth.uid() returns uuid language sql stable as $$ select current_setting('test.uid', true)::uuid $$;
  create or replace function auth.role() returns text language sql stable as $$ select coalesce(current_setting('test.role', true),'authenticated') $$;
  do $$ begin
    if not exists (select 1 from pg_roles where rolname='service_role') then create role service_role; end if;
    if not exists (select 1 from pg_roles where rolname='authenticated') then create role authenticated; end if;
    if not exists (select 1 from pg_roles where rolname='anon') then create role anon; end if;
  end $$;
`);

const files = readdirSync(DIR).filter((f) => f.endsWith('.sql')).sort();
let ok = 0;
for (const file of files) {
  const sql = readFileSync(path.join(DIR, file), 'utf8');
  try {
    await db.exec(sql);
    ok += 1;
    console.log(`  OK   ${file}`);
  } catch (error) {
    console.log(`  FAIL ${file}\n       ${String(error.message).split('\n')[0]}`);
  }
}
console.log(`\n적용: ${ok}/${files.length}`);

// 음성 Energy 가 만든 것들이 실제로 생겼는지 확인
const q = async (sql) => (await db.query(sql)).rows;
console.log('\n=== voice_energy 객체 확인 ===');
console.log('  테이블   :', (await q(
  `select table_name from information_schema.tables where table_schema='public' and table_name like 'voice_energy%' order by 1`
)).map((r) => r.table_name).join(', ') || '없음');
console.log('  messages 컬럼:', (await q(
  `select column_name from information_schema.columns where table_schema='public' and table_name='messages' and column_name like 'voice_energy%' order by 1`
)).map((r) => r.column_name).join(', ') || '없음');
console.log('  함수     :', (await q(
  `select proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and proname like '%voice_energy%' or proname='complete_conversation_with_energy' order by 1`
)).map((r) => r.proname).join(', ') || '없음');
console.log('  트리거   :', (await q(
  `select tgname from pg_trigger where not tgisinternal and tgname like '%voice_energy%'`
)).map((r) => r.tgname).join(', ') || '없음');
console.log('  인덱스   :', (await q(
  `select indexname from pg_indexes where schemaname='public' and indexname like '%voice_energy%'`
)).map((r) => r.indexname).join(', ') || '없음');
console.log('  RLS 정책 :', (await q(
  `select policyname from pg_policies where schemaname='public' and tablename like 'voice_energy%' order by 1`
)).map((r) => r.policyname).join(', ') || '없음');

await db.close();
