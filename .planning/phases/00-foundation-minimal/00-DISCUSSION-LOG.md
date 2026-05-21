# Phase 0: Foundation (Minimal) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-21
**Phase:** 00-foundation-minimal
**Areas discussed:** Scaffolding tool & options, Minimal type shapes, /api/health behavior, Root .env.local cleanup

---

## Area Selection

| Area | Discussed |
|------|-----------|
| 스캐폴드 도구 & 옵션 | ✓ |
| 최소 타입 shape | ✓ |
| /api/health 동작 | ✓ |
| 루트 `.env.local` 정리 | ✓ |

---

## Scaffolding Tool & Options

### Q1. 패키지 매니저

| Option | Description | Selected |
|--------|-------------|----------|
| pnpm | SETUP.md에 명시. 디스크 효율/설치 속도 좋음. Vercel auto-detect. 팀원 전원 `pnpm install` 쓸 수 있어야 함 | |
| npm | Next.js 기본값, lock file 안정적, 설치 없이 바로 쓸 수 있음 | ✓ |

**Notes:** SETUP.md는 pnpm을 권장하지만, CLAUDE.md 본문 예시(`npm run build`)와 일관성 + 추가 설치 없는 선택지로 npm 채택. SETUP.md 갱신 필요할 수 있음.

### Q2. src/ 디렉토리

| Option | Description | Selected |
|--------|-------------|----------|
| src/ 없이 | Next.js 기본값. `frontend/app/`, `frontend/lib/`, `frontend/components/` 루트 바로 아래. ROADMAP과 일치 | ✓ (재확정) |
| src/ 사용 | 큰 프로젝트 관행. `frontend/src/app/`. ROADMAP 경로와 어긋남 | |

**Notes:** 초기 답변에서 "src/ 사용" 선택했으나 ROADMAP과 충돌 발견 → 두 옵션의 전체 monorepo 파일 구조와 영향 받는 문서 목록을 비교 후 **"src/ 미사용 유지"로 재확정**. ROADMAP/CLAUDE.md/PROJECT.md 수정 0건.

### Q3. Import alias

| Option | Description | Selected |
|--------|-------------|----------|
| `@/*` | Next.js 기본값, shadcn 관례 | ✓ |
| `~/*` | 일부 팀 선호 | |

### Q4. ESLint / Prettier

| Option | Description | Selected |
|--------|-------------|----------|
| Next.js 기본 ESLint만 | `create-next-app`이 깔아주는 ESLint 그대로. Phase 0 스코프에 딱 맞음 | ✓ |
| ESLint + Prettier + lint-staged | 풀 세팅. 회의/합의 필요 | |
| Prettier만 추가 | 간단하지만 도구 설치/합의 필요 | |

---

## Minimal Type Shapes

### Q1. Message.role 값

| Option | Description | Selected |
|--------|-------------|----------|
| `'user' \| 'pally'` | 도메인 친화. 프로젝트 특성(Pally 특화)과 일치 | ✓ |
| `'user' \| 'assistant'` | LLM API 관례 | |

### Q2. Message 텍스트 필드 이름

| Option | Description | Selected |
|--------|-------------|----------|
| `transcript` | Phase 1C `messages.transcript` 컬럼명과 일치. 변환 레이어 0 | ✓ |
| `content` | OpenAI/LLM API 관례. UI 친화적이나 1C 컬럼명과 불일치 | |

### Q3. Session.level 타입

| Option | Description | Selected |
|--------|-------------|----------|
| `'A2' \| 'B1' \| 'B2' \| 'C1'` literal union | ROADMAP Phase 1C SC#1이 명시한 4개 값. 타입 안전 | ✓ |
| `string` | 유연하지만 잘못된 값 들어갈 위험 | |

### Q4. Date 필드

| Option | Description | Selected |
|--------|-------------|----------|
| ISO string | JSON wire format 그대로. Supabase row 그대로 사용 가능 | ✓ |
| JS Date 객체 | UI에서 다루기 편하나 직렬화 비용 | |

### Q5. 명명 스타일 (casing)

| Option | Description | Selected |
|--------|-------------|----------|
| camelCase TS → 경계에서 변환 | JS 관례. Supabase row(snake_case)는 경계에서 변환 | ✓ |
| snake_case TS → 그대로 | 변환 없으나 JS 관례에서 벗어남 | |

### Q6. Phase 0 Message에 `axes` / `character` 자리 만들기

| Option | Description | Selected |
|--------|-------------|----------|
| 조차도 안 넣음 | id/sessionId/role/transcript/createdAt만. Phase 1B가 `character.ts`에서 `Axes`/`CharacterParams` 정의 후 추가 | ✓ |
| `axes?: unknown`, `character?: unknown` 플레이스홀더 | 1B에서 정확한 타입으로 교체. mock UI가 axes 필드 사전 고려 가능 | |

---

## /api/health Behavior

### Q1. 반환값

| Option | Description | Selected |
|--------|-------------|----------|
| 단순 `{ ok: true }` 200 | 추가 로직 없음. ROADMAP 텍스트 그대로 | ✓ |
| Supabase ping 포함 | 검증 통합. 매 호출마다 round-trip 비용 | |
| version + timestamp 메타 포함 | 배포 식별 용도. Phase 0 스코프 초과 | |

### Q2. Supabase 연결 확인(SC#3) 위치

| Option | Description | Selected |
|--------|-------------|----------|
| 별도 쓰기 스크립트 | `frontend/scripts/check-supabase.ts` 등 수동 실행. health와 책임 분리 | ✓ |
| 클라이언트 초기화 시 콘솔 로그 | env 값 존재 여부만 체크. 실제 연결 1C에서 | |
| /api/health 안에 포함 | Q1 'Supabase ping 포함' 옵션과 연동 | |

---

## Root .env.local Cleanup

### Q1. Supabase URL / anon 키 처리

| Option | Description | Selected |
|--------|-------------|----------|
| `frontend/.env.local`로 이동 + 루트 파일 삭제 | Vercel Root = `frontend/`. 로컬 dev와 배포 환경 일치 | ✓ |
| 루트 파일 통째 삭제 + 새 값 팀에 재요청 | 구 값 신뢰하지 말고 다시 받음 | |
| Phase 0 범위 밖, 그대로 둠 | 개인 작업 | |

### Q2. OpenAI key 처리

| Option | Description | Selected |
|--------|-------------|----------|
| 삭제 + 구 자격증명 폐기 PM 확인 | MVP는 GCP 전용. 로컬 삭제 + PM에 revoke 여부 확인 요청 | ✓ |
| 조용히 삭제만 | revoke는 별도 관리 | |

### Q3. `frontend/.env.local` (실제 dev 파일) 함께 생성?

| Option | Description | Selected |
|--------|-------------|----------|
| 예 | 이찬희가 즉시 `npm run dev` 가능. `.gitignore`에 이미 포함 | ✓ |
| 아니오, .env.example만 | 팀원 각자 로컬 설정 | |

---

## Cross-Area Follow-up

### src/ 결정 재검토

사용자가 "ROADMAP/CLAUDE.md를 수정하더라도 src/ 만드는 게 낫지 않을까"라고 재고함. 두 가지 옵션의 **전체 monorepo 파일 트리**(`frontend/` 안만 영향, 루트 레벨 CLAUDE.md 등은 변동 없음 명시)와 **수정 필요한 문서 목록**을 보여준 후, **"src/ 미사용 유지"**로 최종 확정.

---

## Claude's Discretion

- `cn()` 유틸 위치 — shadcn 관례 `frontend/lib/utils.ts` 추천하나 plan/researcher가 최종 결정
- Tailwind 버전 — `create-next-app --tailwind` 기본값(v3 권장)
- 타입 파일 분리 vs 통합 — 가독성 기준
- `page.tsx` placeholder 내용 — 비어 있거나 짧은 텍스트
- `create-next-app` 정확한 플래그 조합 — `--ts --tailwind --app --no-src-dir --import-alias '@/*' --eslint --use-npm`

---

## Deferred Ideas

- Prettier + lint-staged + husky 설정
- `docs/code-convention.md` 작성
- 루트 `.env.example` 또는 monorepo 차원 secret manager
- `Axes` / `CharacterParams` 타입 정의 (Phase 1B)
- Supabase 스키마 / RLS 마이그레이션 (Phase 1C)
- `backend/main.py` OpenAI 의존 정리 (Phase 1C 재작성에서 자연스럽게 처리)
