# Pally 현재 모습을 프로필에 저장

기준: 2026-10-07 KST, main `b8e1af8` 위 `feat/profile-saved-current-axes`.
선행 문서: [홈 Pally 기준 통일과 홈 재진입 로딩](2026-10-06-home-pally-profile-axes.md).

## 문제

홈 Pally는 `_carried_over_axes`가 "발화가 있는 가장 최근에 끝낸 대화의 최종 5축"을 매번 다시 계산한 값(프로필 `current_axes`)으로 그렸다. 가장 최근에 끝낸 대화를 History에서 이어 하면 그 대화가 "끝난 대화"에서 빠져 서버가 이전 대화의 값을 돌려주고, 이어 하는 동안 Pally의 색·모양이 바뀌었다(Intimacy가 색을 정하므로 30에서 20으로 바뀌며 연두에서 민트로 달라졌다). 종료하면 원래 값으로 돌아왔다. 예전 구현(완료 대화 목록)에도 같은 현상이 있었다.

## 결정

대화를 끝낼 때 마이페이지 태그(`profiles.traits`)와 같은 요청으로 `profiles.current_axes`를 저장하고, 홈·태그·다음 대화의 출발점이 저장값 하나를 읽는다. 이어 하기는 저장값을 건드리지 않는다.

- `profiles.current_axes jsonb` 추가(null 허용, 객체만 허용). null은 "말을 한 대화를 끝낸 적이 없음"이며 프로필 응답에서 `_INITIAL_AXES`로 내려간다.
- `_refresh_profile_traits`: 태그와 `current_axes`를 한 번에 저장한다. 발화가 없는 대화는 건드리지 않는다.
- `_carried_over_axes`: 대화를 훑는 쿼리 대신 `profiles.current_axes`를 읽는다. 대화 수와 무관하게 한 번에 읽는다.
- `DELETE /api/conversations`: `current_axes`를 비워 홈 Pally가 첫 모습으로 돌아간다.
- 프론트 변경 없음(`database.types.ts`만 갱신).

## 마이그레이션과 배포 순서

`supabase/migrations/20261007000000_profiles_current_axes.sql`: 칸 추가 + 기존 사용자 값 채우기(발화가 있는 가장 최근에 **끝낸** 대화의 마지막 사용자 발화 5축, 반복 실행 가능).

1. 칸 추가·값 채우기를 먼저 적용한다(추가만 하므로 구 서버는 영향이 없다). 2026-10-07 운영에 적용했다. 사용자 12명 중 6명이 채워졌고 모두 5축을 가진 객체다.
2. 서버를 배포한다.
3. 1~2 사이에 구 서버가 끝낸 대화는 `current_axes`를 갱신하지 못하므로, 배포 직후 값 채우기를 한 번 더 실행한다(같은 SQL, 결과 동일).

## 검증

- 백엔드 CI 명령 그대로 298개 통과(저장값을 읽는지, 종료 시 태그와 모습이 함께 저장되는지, 기록 삭제가 모습을 비우는지, null이 첫 Pally로 내려가는지), `ruff --select E9,F63,F7,F82`·compileall 통과.
- 운영 DB: 적용 전 읽기 전용으로 대상 6명과 구 규칙과의 차이 1명을 확인했고, 적용 후 6명 모두 유효한 객체이며 5축 키 누락이 없다. 칸 추가 후에도 구 서버의 `/api/profile`·`/api/usage`가 200으로 응답했다.
- `database.types.ts`는 Supabase가 생성한 타입과 `profiles` 블록이 일치한다.

## 배포 후 확인

- 가장 최근에 끝낸 대화를 이어 하는 동안 홈 Pally 색·모양이 바뀌지 않는지, 종료하면 그 대화의 값으로 갱신되는지.
- 대화 종료 후 프로필 `current_axes`가 방금 끝낸 대화의 마지막 발화 값과 일치하는지.
- 기록 삭제 직후 홈 Pally가 첫 모습(50/30/20/10/15)으로 돌아오는지(되돌릴 수 없는 작업이라 별도 승인 후 확인).
