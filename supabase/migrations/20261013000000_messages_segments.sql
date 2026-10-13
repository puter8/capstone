-- Pally 응답의 색칠용 조각. 교정(correction) / Pally 자신의 말(own_remark) /
-- 새 표현(new_expr) / 질문(question) 으로 나뉜 구간 목록을 그대로 담는다.
-- 저장하는 이유: 새로고침하거나 History 에서 다시 열어도 같은 색으로 보여야 한다.
-- 비어 있으면(모델이 계약을 깼거나 이 기능 이전의 대화) API 는 평문만 돌려주고
-- 프론트는 지금처럼 색 없이 그린다.
-- forward-only. 기존 마이그레이션은 수정하지 않는다.

alter table public.messages add column if not exists segments jsonb;
