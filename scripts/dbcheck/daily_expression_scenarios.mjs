// 오늘의 표현 snapshot 테이블이 실제 Postgres 에서 의도대로 동작하는지 확인.
// apply_migrations.mjs 는 "적용되는가"만 보므로, 여기서 모양·제약·연쇄삭제를 직접 건드린다.
// RLS 가 실제로 걸러내는지는 이 환경에서 확인되지 않는다 (README 의 한계 참조).
//
//   cd scripts/dbcheck && node daily_expression_scenarios.mjs

import { PGlite } from '@electric-sql/pglite';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';

// 이 스크립트 위치 기준 — 어느 PC 에서 받아도 그대로 돈다 (apply_migrations.mjs 와 동일).
const MIGRATIONS = path.resolve(
  path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')),
  '../../supabase/migrations');
const TABLE = 'daily_expression_snapshots';

let pass = 0;
let fail = 0;

function check(name, ok, detail = '') {
  if (ok) {
    pass += 1;
    console.log(`  OK   ${name}`);
  } else {
    fail += 1;
    console.log(`  FAIL ${name}${detail ? ` — ${detail}` : ''}`);
  }
}

const db = await new PGlite();
// Supabase 가 기본 제공하는 것들 — 여기서는 스텁이다 (apply_migrations.mjs 와 동일).
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
for (const file of readdirSync(MIGRATIONS).filter((f) => f.endsWith('.sql')).sort()) {
  await db.exec(readFileSync(path.join(MIGRATIONS, file), 'utf8'));
}

console.log(`\n=== ${TABLE} ===`);

const cols = await db.query(
  `select column_name, is_nullable from information_schema.columns
   where table_name = $1 order by ordinal_position`, [TABLE]);
const colNames = cols.rows.map((r) => r.column_name);
check('컬럼 4개', colNames.join(',') === 'user_id,date_kst,expr_id,generated_at', colNames.join(','));
check('expr_id NOT NULL', cols.rows.find((r) => r.column_name === 'expr_id')?.is_nullable === 'NO');

const pk = await db.query(
  `select a.attname from pg_index i
   join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey)
   where i.indrelid = $1::regclass and i.indisprimary order by a.attname`, [TABLE]);
check('PK = (user_id, date_kst)', pk.rows.map((r) => r.attname).join(',') === 'date_kst,user_id');

const rls = await db.query(`select relrowsecurity from pg_class where relname = $1`, [TABLE]);
check('RLS 활성화', rls.rows[0]?.relrowsecurity === true);

const pol = await db.query(`select policyname, cmd from pg_policies where tablename = $1`, [TABLE]);
check('본인 select 정책 1개만', pol.rows.length === 1 && pol.rows[0].cmd === 'SELECT',
  JSON.stringify(pol.rows));

const user = '11111111-1111-1111-1111-111111111111';
await db.query(`insert into auth.users (id) values ($1)`, [user]);
await db.query(
  `insert into ${TABLE} (user_id, date_kst, expr_id) values ($1, '2026-10-29', 'b1-into')`, [user]);

// 같은 날 두 번째 쓰기는 새 행이 아니라 그 날의 표현을 덮어쓴다 (백엔드 upsert 경로).
await db.query(
  `insert into ${TABLE} (user_id, date_kst, expr_id) values ($1, '2026-10-29', 'b1-rather')
   on conflict (user_id, date_kst) do update set expr_id = excluded.expr_id`, [user]);
const after = await db.query(`select expr_id from ${TABLE} where user_id = $1`, [user]);
check('하루 1행 유지 + upsert 로 교체', after.rows.length === 1 && after.rows[0].expr_id === 'b1-rather',
  JSON.stringify(after.rows));

// 다른 날은 별개 행.
await db.query(
  `insert into ${TABLE} (user_id, date_kst, expr_id) values ($1, '2026-10-30', 'b1-depends')`, [user]);
const twoDays = await db.query(`select count(*)::int n from ${TABLE} where user_id = $1`, [user]);
check('날짜별로 행이 쌓인다', twoDays.rows[0].n === 2);

// 없는 사용자로는 못 넣는다 (FK).
let fkBlocked = false;
try {
  await db.query(
    `insert into ${TABLE} (user_id, date_kst, expr_id)
     values ('99999999-9999-9999-9999-999999999999', '2026-10-29', 'b1-into')`);
} catch {
  fkBlocked = true;
}
check('없는 사용자 삽입 차단', fkBlocked);

// 계정이 지워지면 함께 지워진다.
await db.query(`delete from auth.users where id = $1`, [user]);
const left = await db.query(`select count(*)::int n from ${TABLE}`);
check('계정 삭제 시 연쇄 삭제', left.rows[0].n === 0);

console.log(`\n통과: ${pass}/${pass + fail}`);
process.exit(fail === 0 ? 0 : 1);
