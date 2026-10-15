// 마이그레이션이 "적용된다"가 아니라 "동작한다"를 확인한다.
// plpgsql 은 생성 시 본문을 검증하지 않으므로, 함수는 호출해 봐야 깨짐이 드러난다.
import { PGlite } from '@electric-sql/pglite';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';

// 이 스크립트 위치 기준 — 어느 PC 에서 받아도 그대로 돈다.
const DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '../../supabase/migrations');
const db = await new PGlite();
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
for (const f of readdirSync(DIR).filter((f) => f.endsWith('.sql')).sort()) {
  await db.exec(readFileSync(path.join(DIR, f), 'utf8'));
}

const results = [];
const check = (name, passed, detail = '') => {
  results.push([name, passed]);
  console.log(`  [${passed ? 'PASS' : 'FAIL'}] ${name}${passed ? '' : `\n         -> ${detail}`}`);
};
const q = async (sql, params = []) => (await db.query(sql, params)).rows;

const USER = '11111111-1111-1111-1111-111111111111';
const OTHER = '22222222-2222-2222-2222-222222222222';
await q(`insert into auth.users(id,email) values ($1,'a@x.com'),($2,'b@x.com')`, [USER, OTHER]);
await q(`insert into public.profiles(id,display_name,english_level,onboarding_completed)
         values ($1,'a','A2',true),($2,'b','A2',true)`, [USER, OTHER]);

const newSession = async (user) => (await q(
  `insert into public.sessions(user_id,character_name,level) values ($1,'Pally','A2') returning id`, [user]
))[0].id;

// 발화 하나를 저장한다. voice_energy 가 있으면 작업 큐에 올라간다.
const addTurn = async (session, user, axes, energy, epoch = 0) => (await q(
  `insert into public.messages(session_id,role,transcript,axes,voice_energy,voice_energy_epoch)
   values ($1,'user','hi',$2::jsonb,$3::jsonb,$4) returning id`,
  [session, JSON.stringify(axes), energy === null ? null : JSON.stringify(energy), epoch]
))[0].id;

const AXES = { Formality: 40, Energy: 50, Intimacy: 30, Humor: 20, Curiosity: 60 };
const pending = (n) => ({ status: 'pending', audio_base64: 'AAAA', audio_sha256: `sha${n}` });
const ready = (range) => ({ status: 'ready', range_st: range, method: 'pitch-range-fold-v1' });

console.log('\n1. 기준(baseline) 저장');
const measurements = JSON.stringify([{ range_st: 2.0 }, { range_st: 2.2 }, { range_st: 2.3 }]);
const saved = await q(`select public.save_voice_energy_baseline($1,$2,$3::jsonb,$4) as row`,
  [USER, 2.16, measurements, 'pitch-range-fold-v1']);
check('기준 저장되고 값이 돌아옴', saved[0].row?.range_st === 2.16, JSON.stringify(saved[0].row));
const again = await q(`select public.save_voice_energy_baseline($1,$2,$3::jsonb,$4) as row`,
  [USER, 9.99, measurements, 'pitch-range-fold-v1']);
check('재등록해도 첫 기준을 덮어쓰지 않음', again[0].row?.range_st === 2.16, JSON.stringify(again[0].row));

console.log('\n2. 작업 큐 (claim / finish)');
const session = await newSession(USER);
const turn = await addTurn(session, USER, AXES, pending(1));
const claimed = await q(`select id, voice_energy->>'status' as status,
                                voice_energy->>'claim_token' as token from public.claim_voice_energy_job()`);
check('pending 작업을 claim 하면 processing 으로', claimed[0]?.status === 'processing', JSON.stringify(claimed));
const empty = await q(`select id from public.claim_voice_energy_job()`);
check('이미 잡힌 작업은 다시 claim 되지 않음', empty.length === 0, JSON.stringify(empty));
const wrongToken = await q(`select public.finish_voice_energy_job($1,$2,$3::jsonb) as ok`,
  [turn, OTHER, JSON.stringify(ready(4.9))]);
check('잘못된 claim_token 으로 완료 불가', wrongToken[0].ok === false, JSON.stringify(wrongToken));
await q(`select public.finish_voice_energy_job($1,$2,$3::jsonb) as ok`,
  [turn, claimed[0].token, JSON.stringify({ ...ready(4.9), audio_base64: 'AAAA' })]);
const after = await q(`select voice_energy from public.messages where id=$1`, [turn]);
check('완료 시 원음(audio_base64)이 제거됨',
  after[0].voice_energy.audio_base64 === undefined && after[0].voice_energy.status === 'ready',
  JSON.stringify(after[0].voice_energy));
const badResult = await db.query(`select public.finish_voice_energy_job($1,$2,$3::jsonb)`,
  [turn, claimed[0].token, JSON.stringify({ status: 'whatever' })]).then(() => null).catch((e) => e.message);
check('허용되지 않은 status 는 거부', String(badResult).includes('invalid_voice_energy_result'), String(badResult));

console.log('\n3. 회차(epoch) 검증 트리거');
const closed = await newSession(USER);
await q(`update public.sessions set ended_at=now() where id=$1`, [closed]);
const intoClosed = await db.query(
  `insert into public.messages(session_id,role,transcript,voice_energy,voice_energy_epoch)
   values ($1,'user','late','{"status":"pending"}'::jsonb,0)`, [closed]
).then(() => null).catch((e) => e.message);
check('끝난 대화에는 작업을 넣을 수 없음', String(intoClosed).includes('conversation_closed'), String(intoClosed));
const live = await newSession(USER);
const wrongEpoch = await db.query(
  `insert into public.messages(session_id,role,transcript,voice_energy,voice_energy_epoch)
   values ($1,'user','x','{"status":"pending"}'::jsonb,7)`, [live]
).then(() => null).catch((e) => e.message);
check('회차가 어긋나면 거부', String(wrongEpoch).includes('conversation_closed'), String(wrongEpoch));

console.log('\n4. 종료 집계 (complete_conversation_with_energy)');
// 유효 발화 1개뿐 → 5개 미만이라 이전 값을 유지해야 한다.
const few = await q(`select public.complete_conversation_with_energy($1,$2,0) as row`, [session, USER]);
const fewEnergy = few[0].row.energy;
check('유효 발화 5개 미만이면 retained',
  fewEnergy.status === 'retained' && fewEnergy.reason === 'insufficient_valid_clips',
  JSON.stringify(fewEnergy));
check('이전 Energy(최초 50)를 유지', few[0].row.current_axes.Energy === 50, JSON.stringify(few[0].row.current_axes));

// 유효 발화 5개 → 계산이 돌아야 한다. 기준 2.16, 중앙값 4.92 → delta 2.76 → 50+27.6=77.6 → 80
const full = await newSession(USER);
for (const r of [4.90, 4.91, 4.92, 4.93, 4.94]) {
  const id = await addTurn(full, USER, AXES, pending(r));
  const c = await q(`select voice_energy->>'claim_token' as token from public.claim_voice_energy_job()`);
  await q(`select public.finish_voice_energy_job($1,$2,$3::jsonb)`, [id, c[0].token, JSON.stringify(ready(r))]);
}
const done = await q(`select public.complete_conversation_with_energy($1,$2,0) as row`, [full, USER]);
const energy = done[0].row.energy;
check('유효 발화 5개면 ready', energy.status === 'ready' && energy.reason === null, JSON.stringify(energy));
check('문서 실측과 같은 점수(기준 2.16 / 중앙값 4.92 → 80)',
  energy.score === 80 && done[0].row.current_axes.Energy === 80,
  `score=${energy.score} range=${energy.range_st} delta=${energy.delta_st}`);
check('종료와 동시에 ended_at 이 기록됨', Boolean(done[0].row.ended_at), JSON.stringify(done[0].row.ended_at));

console.log('\n5. 멱등성 / 피드백 연계');
const repeat = await q(`select public.complete_conversation_with_energy($1,$2,0) as row`, [full, USER]);
check('재호출해도 같은 점수(스냅샷 재사용)', repeat[0].row.energy.score === 80, JSON.stringify(repeat[0].row.energy));
const snapCount = await q(`select count(*)::int as n from public.voice_energy_snapshots where session_id=$1`, [full]);
check('스냅샷이 중복 생성되지 않음', snapCount[0].n === 1, JSON.stringify(snapCount));
const marked = await q(
  `select count(*)::int as n from public.messages where session_id=$1 and role='user' and feedback_requested_at is not null`,
  [full]);
check('기존 피드백 표시 로직이 그대로 돈다', marked[0].n === 5, JSON.stringify(marked));

console.log('\n6. 타인 접근');
const stolen = await db.query(`select public.complete_conversation_with_energy($1,$2,0)`, [full, OTHER])
  .then(() => null).catch((e) => e.message);
check('남의 대화는 종료할 수 없음', String(stolen).includes('conversation_not_found'), String(stolen));

const passed = results.filter(([, p]) => p).length;
console.log(`\n${'='.repeat(56)}\n  합계 ${passed}/${results.length}`);
await db.close();
process.exit(passed === results.length ? 0 : 1);
