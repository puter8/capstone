-- Opt-in within-speaker pitch range. No external calls or visual mapping changes.
alter table public.messages add column if not exists voice_energy jsonb;
alter table public.messages add column if not exists voice_energy_epoch integer;
create index messages_voice_energy_pending on public.messages(id)
 where voice_energy->>'status' in ('pending','processing');

create table public.voice_energy_baselines (
 user_id uuid primary key references auth.users(id) on delete cascade,
 range_st double precision not null check(range_st >= 0 and range_st < 'Infinity'::float8),
 measurements jsonb not null check(jsonb_array_length(measurements)=3),
 method text not null check(method='pitch-range-fold-v1'),
 created_at timestamptz not null default clock_timestamp()
);
create table public.voice_energy_snapshots (
 session_id uuid not null references public.sessions(id) on delete cascade,
 epoch integer not null check(epoch>=0),
 user_id uuid not null references auth.users(id) on delete cascade,
 current_axes jsonb not null,
 energy jsonb not null,
 created_at timestamptz not null default clock_timestamp(),
 primary key(session_id,epoch)
);
alter table public.voice_energy_baselines enable row level security;
alter table public.voice_energy_snapshots enable row level security;
create policy voice_baseline_owner_read on public.voice_energy_baselines for select to authenticated using(user_id=auth.uid());
create policy voice_snapshot_owner_read on public.voice_energy_snapshots for select to authenticated using(user_id=auth.uid());
revoke all on public.voice_energy_baselines,public.voice_energy_snapshots from public,anon,authenticated,service_role;
grant select on public.voice_energy_baselines,public.voice_energy_snapshots to authenticated;
grant select,insert,delete on public.voice_energy_baselines,public.voice_energy_snapshots to service_role;

create function public.save_voice_energy_baseline(p_user_id uuid,p_range_st double precision,p_measurements jsonb,p_method text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare v public.voice_energy_baselines%rowtype;
begin
 insert into public.voice_energy_baselines(user_id,range_st,measurements,method)
 values(p_user_id,p_range_st,p_measurements,p_method) on conflict(user_id) do nothing;
 select * into v from public.voice_energy_baselines where user_id=p_user_id;
 return to_jsonb(v);
end; $$;

-- Existing closed-session guard remains. This additional guard closes the
-- close/reopen gap between the application's check and its INSERT.
create function public.guard_voice_energy_epoch() returns trigger
language plpgsql security definer set search_path='' as $$
declare s public.sessions%rowtype;
begin
 if new.role='user' and new.voice_energy is not null then
  select * into s from public.sessions where id=new.session_id for update;
  if s.ended_at is not null or new.voice_energy_epoch is distinct from s.reopen_count then
   raise exception 'conversation_closed' using errcode='P0001';
  end if;
 end if;
 return new;
end; $$;
create trigger messages_voice_energy_epoch before insert on public.messages
for each row execute function public.guard_voice_energy_epoch();

create function public.claim_voice_energy_job() returns setof public.messages
language plpgsql security definer set search_path='' as $$
declare v_id uuid;
begin
 select id into v_id from public.messages
 where role='user' and (voice_energy->>'status'='pending'
 or (voice_energy->>'status'='processing' and (voice_energy->>'lease_until')::timestamptz < clock_timestamp()))
 order by created_at,id for update skip locked limit 1;
 if v_id is null then return; end if;
 return query update public.messages set voice_energy=voice_energy || jsonb_build_object(
 'status','processing','claim_token',gen_random_uuid(),'lease_until',clock_timestamp()+interval '5 minutes')
 where id=v_id returning *;
end; $$;

create function public.finish_voice_energy_job(p_message_id uuid,p_token uuid,p_result jsonb)
returns boolean language plpgsql security definer set search_path='' as $$
declare n integer;
begin
 if p_result->>'status' not in ('ready','missing','error') or p_result->>'status' is null then
  raise exception 'invalid_voice_energy_result';
 end if;
 update public.messages set voice_energy=p_result-'audio_base64'-'claim_token'-'lease_until'
 where id=p_message_id and voice_energy->>'status'='processing' and voice_energy->>'claim_token'=p_token::text;
 get diagnostics n=row_count;
 return n=1;
end; $$;

create function public.complete_conversation_with_energy(p_conversation_id uuid,p_user_id uuid,p_expected_reopen_count integer)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 s public.sessions%rowtype; snap public.voice_energy_snapshots%rowtype;
 closed jsonb; axes jsonb; previous integer:=50; baseline double precision;
 spread double precision; delta double precision; q double precision; lo integer;
 valid_count integer; pending_count integer; error_count integer; missing_count integer;
 score integer; reason text; energy jsonb;
begin
 select * into s from public.sessions where id=p_conversation_id and user_id=p_user_id for update;
 if not found then raise exception 'conversation_not_found' using errcode='P0002'; end if;
 if s.reopen_count<>p_expected_reopen_count then raise exception 'conversation_changed'; end if;
 select * into snap from public.voice_energy_snapshots where session_id=s.id and epoch=s.reopen_count;
 if found then
  return to_jsonb(s)||jsonb_build_object('current_axes',snap.current_axes,'energy',snap.energy);
 end if;
 -- Serialize per-user baseline/snapshot decisions across concurrently closed sessions.
 perform 1 from auth.users where id=p_user_id for update;
 select (current_axes->>'Energy')::integer into previous from public.voice_energy_snapshots
 where user_id=p_user_id order by created_at desc,session_id desc limit 1;
 previous:=coalesce(previous,50);
 select m.axes into axes from public.messages m where m.session_id=s.id and m.role='user' and m.axes is not null
 order by m.created_at desc,m.id desc limit 1;
 if axes is null then
  select current_axes into axes from public.voice_energy_snapshots where user_id=p_user_id order by created_at desc,session_id desc limit 1;
 end if;
 axes:=coalesce(axes,'{"Formality":50,"Energy":50,"Intimacy":50,"Humor":50,"Curiosity":50}'::jsonb);
 select range_st into baseline from public.voice_energy_baselines where user_id=p_user_id and method='pitch-range-fold-v1';
 select count(*) filter(where voice_energy->>'status'='ready'),
 count(*) filter(where voice_energy->>'status' in ('pending','processing')),
 count(*) filter(where voice_energy->>'status'='error'),
 count(*) filter(where voice_energy->>'status'='missing'),
 percentile_cont(0.5) within group(order by (voice_energy->>'range_st')::double precision)
 filter(where voice_energy->>'status'='ready')
 into valid_count,pending_count,error_count,missing_count,spread
 from public.messages where session_id=s.id and role='user' and voice_energy_epoch=s.reopen_count;
 reason:=case when pending_count>0 then 'pending_at_close' when baseline is null then 'baseline_missing'
 when valid_count<5 then 'insufficient_valid_clips' else null end;
 score:=previous;
 if reason is null then
  delta:=spread-baseline;
  q:=least(100.0,greatest(0.0,50+10*delta))/5;
  lo:=floor(q)::integer;
  score:=5*(case when q-lo<0.5 then lo when q-lo>0.5 then lo+1 when mod(lo,2)=0 then lo else lo+1 end);
 end if;
 axes:=jsonb_set(axes,'{Energy}',to_jsonb(score));
 energy:=jsonb_build_object('status',case when reason is null then 'ready' else 'retained' end,
 'score',score,'missing_reason',reason,'reason',reason,'range_st',spread,'delta_st',delta,
 'baseline_range_st',baseline,'valid_clips',valid_count,'pending_clips',pending_count,
 'error_clips',error_count,'missing_clips',missing_count,'method','pitch-range-fold-v1','epoch',s.reopen_count);
 closed:=public.complete_conversation_with_feedback(p_conversation_id,p_user_id,p_expected_reopen_count);
 insert into public.voice_energy_snapshots(session_id,epoch,user_id,current_axes,energy)
 values(s.id,s.reopen_count,p_user_id,axes,energy);
 return closed||jsonb_build_object('current_axes',axes,'energy',energy);
end; $$;

revoke all on function public.save_voice_energy_baseline(uuid,double precision,jsonb,text),public.guard_voice_energy_epoch(),
public.claim_voice_energy_job(),public.finish_voice_energy_job(uuid,uuid,jsonb),public.complete_conversation_with_energy(uuid,uuid,integer)
from public,anon,authenticated;
grant execute on function public.save_voice_energy_baseline(uuid,double precision,jsonb,text),public.claim_voice_energy_job(),
public.finish_voice_energy_job(uuid,uuid,jsonb),public.complete_conversation_with_energy(uuid,uuid,integer) to service_role;
