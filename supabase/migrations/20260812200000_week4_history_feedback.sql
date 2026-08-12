-- 4주차: History/상세 조회 + feedback 저장 + 대화 reopen 지원.
-- forward-only. 기존 마이그레이션은 수정하지 않는다.

-- feedback: 해당 turn(user 메시지 행)에 연결해 저장. 생성은 AI, 저장/조회는 backend.
-- FeedbackItem[] JSON: [{ "original", "corrected", "explanation_ko" }, ...]
alter table messages add column if not exists feedback jsonb;

-- reopen: 완료된 대화를 같은 id 로 재개할 때 이력 보존용.
alter table sessions add column if not exists reopened_at timestamptz;
alter table sessions add column if not exists reopen_count integer not null default 0;
