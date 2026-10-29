# 마이그레이션 검증 (실제 Postgres, 공유 DB 없이)

공유 Supabase 를 건드리지 않고 마이그레이션을 검증한다. PGlite(WASM Postgres)를
쓰므로 Docker 도 서버 설치도 필요 없다.

```bash
cd scripts/dbcheck
npm install @electric-sql/pglite
node apply_migrations.mjs             # 마이그레이션 전체가 순서대로 적용되는지
node voice_energy_scenarios.mjs       # 음성 Energy 가 실제로 동작하는지 (18종)
node daily_expression_scenarios.mjs   # 오늘의 표현 snapshot 모양·제약·연쇄삭제 (9종)
```

`apply_migrations.mjs` 는 "적용되는가"만 본다. plpgsql 은 생성 시 본문을 검증하지
않으므로, 함수가 깨져 있어도 생성은 성공한다. `voice_energy_scenarios.mjs` 가
함수를 실제로 호출해 동작을 확인하는 쪽이다.

## 한계

Supabase 가 제공하는 것들(`auth` 스키마, `auth.uid()`, `auth.role()`,
`service_role`/`authenticated`/`anon` 롤)은 여기 없어서 최소한으로 흉내 낸다.
따라서 **RLS 정책이 실제로 걸러내는지는 이 환경에서 확인되지 않는다** — 정책이
생성되는 것까지만 본다. 실제 차단 여부는 배포된 환경에 anon key 로 직접 쏘는
`scripts/verify_security.py` 의 RLS 4종에서 확인한다.
