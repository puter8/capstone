-- turn 중복 저장 방지: 같은 conversation(session)에서 같은 Idempotency-Key로
-- 재시도가 와도 turn이 두 번 저장되지 않게 한다.
-- turn = user 메시지 + pally 메시지. 식별 키는 user 메시지 행에만 저장한다.
-- forward-only. 기존 sessions/messages 마이그레이션은 수정하지 않는다.

alter table messages add column if not exists idempotency_key text;

create unique index if not exists messages_session_idem_uniq
  on messages (session_id, idempotency_key)
  where idempotency_key is not null;
