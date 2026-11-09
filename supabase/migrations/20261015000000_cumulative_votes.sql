-- 닮아가는 Pally: 대화 하나 = 한 표.
-- 턴마다 분석기 원점수(raw_axes)를, 대화를 끝낼 때 그 평균(axes_contribution)을 남겨
-- 누적을 끝낸 대화들의 표에서 다시 계산한다. 다시 연 대화는 자기 표만 바뀌고,
-- 동시에 끝낸 두 대화가 서로의 반영을 덮어쓰지 않는다.
-- axes_contribution = {"mean": {5축 평균} | null, "turns": int, "first_completed_at": timestamptz | null}
-- (null = 다시 연 적 없음 -> ended_at 이 처음 끝낸 시각. 다시 열 때 ended_at 을 옮겨 적는다)
-- 표는 종료 RPC 직전에 서버(service role)가 쓴다.
-- 두 테이블 모두 이미 RLS 가 켜져 있고 기존 정책이 행 단위로 그대로 적용된다.
alter table public.messages add column if not exists raw_axes jsonb;
alter table public.sessions add column if not exists axes_contribution jsonb;
