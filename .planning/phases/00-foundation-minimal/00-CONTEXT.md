# Phase 0: Foundation (Minimal) - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Owner:** 이찬희 (단독, 0.5일)

<domain>
## Phase Boundary

1A/1B/1C 세 개발자가 본인 phase 첫 task부터 충돌 없이 병렬로 시작할 수 있도록 `frontend/` 최소 공유 인프라만 깐다.

**범위 안:**
- Next.js 14 App Router 스캐폴드 (`frontend/`)
- 최소 UI 타입 (`Message`, `Session`)
- Supabase anon 클라이언트 (`frontend/lib/supabase/client.ts`)
- `frontend/.env.example` (3개 키)
- Tailwind + `cn()` 유틸
- `frontend/app/page.tsx` placeholder
- `/api/health` 200 반환
- 루트 `.env.local` 정리

**범위 밖 (다른 phase로):**
- `Axes` / `CharacterParams` 타입 → Phase 1B
- Supabase `sessions` / `messages` 테이블 + RLS → Phase 1C
- `backend/` 변경 → Phase 1C
- 실제 화면 UI → Phase 1A
- ADR `docs/adr/0001-python-engine-integration.md` → Phase 1B

</domain>

<decisions>
## Implementation Decisions

### Scaffolding

- **D-01:** 패키지 매니저는 **npm**. `cd frontend && npm install && npm run dev`로 통일.
- **D-02:** **src/ 디렉토리 미사용**. `frontend/app/`, `frontend/lib/`, `frontend/components/`를 `frontend/` 바로 아래에 둠. ROADMAP Phase 0 SC와 CLAUDE.md §1 소유권 표(`frontend/components/pally/`, `frontend/app/dev/pally/`, `frontend/lib/types/character.ts`)와 일치.
- **D-03:** import alias **`@/*`** (Next.js 기본, shadcn 관례). `@/lib/types/message`, `@/lib/supabase/client` 형태.
- **D-04:** **Next.js 기본 ESLint만**. Prettier / lint-staged / husky는 Phase 0에서 추가 안 함 (스코프 보호). 이후 phase에서 필요하면 별도 결정.

### Type Shapes (frontend/lib/types/)

- **D-05:** **`Message`** 인터페이스 필드: `id: string`, `sessionId: string`, `role: 'user' | 'pally'`, `transcript: string`, `createdAt: string` (ISO).
  - `axes` / `character` 필드는 **포함하지 않음** — Phase 1B가 `character.ts`에서 `Axes` / `CharacterParams` 정의 후 추가.
  - role은 `'user' | 'assistant'` 대신 도메인 친화적 `'user' | 'pally'` 채택.
  - 텍스트 필드는 `content` 대신 **`transcript`** — Phase 1C `messages.transcript` 컬럼명과 일치하여 wire-format 변환 비용 0.
- **D-06:** **`Session`** 인터페이스 필드: `id: string`, `characterName: string`, `level: 'A2' | 'B1' | 'B2' | 'C1'`, `createdAt: string`, `endedAt?: string`.
  - `level`은 literal union으로 잠금 (ROADMAP Phase 1C SC#1 명시).
  - MVP 기본값(`Pally` / `B1`)은 1C가 Supabase row 생성 시 채움. Phase 0 타입은 채우지 않고 모양만 정의.
- **D-07:** 명명 규칙: **TS는 camelCase**, Supabase row는 snake_case. 경계에서 변환 (supabase-js 응답을 camelCase로 매핑하거나 인라인 변환). 변환 유틸 작성 여부는 Phase 1A가 mock 데이터 만들 때 자체 결정.
- **D-08:** 날짜는 **ISO string**. JS Date 객체 미사용 (JSON wire format 통일).

### /api/health

- **D-09:** **단순 `{ ok: true }`** 200 반환. 외부 의존(Supabase ping 등) **없음**. Vercel/Railway 헬스 프로브 비용 0.
- **D-10:** Supabase 연결 확인(SC#3)은 **별도 스크립트** (`frontend/scripts/check-supabase.ts` 같은 이름, 정확 경로는 plan 단계에서). health endpoint와 책임 분리.

### Env Files

- **D-11:** **`frontend/.env.example`** 만들고, 키는 정확히 3개: `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **D-12:** 루트 `.env.local` 처리:
  - Supabase URL / anon key → **`frontend/.env.local`로 이동**.
  - **OpenAI key 삭제** (MVP는 GCP 전용). PM(최윤서)에게 해당 OpenAI key revoke 여부 확인 요청.
  - 루트 `.env.local` 파일 **삭제**.
  - 이 작업은 Phase 0 plan에 포함.
- **D-13:** `frontend/.env.local` (실제 dev 값) 함께 생성. `.gitignore`에 `.env.local`이 이미 포함되어 있어 커밋 안 됨. 이찬희가 `npm run dev`를 바로 돌릴 수 있도록.

### Claude's Discretion

다음은 plan/researcher가 표준 관행으로 결정:
- `cn()` 유틸 위치 — shadcn 관례인 `frontend/lib/utils.ts` 기본 추천 (`@/lib/utils`).
- Tailwind 버전 — `create-next-app --tailwind` 기본값 (v3 권장, v4는 아직 안정성 검증 필요).
- `Message` / `Session` 파일 분리 vs 단일 — 가독성 기준. `frontend/lib/types/message.ts`, `frontend/lib/types/session.ts` 분리 추천하나 `index.ts` 통합도 무방.
- `frontend/app/page.tsx` placeholder 내용 — 비어 있어도 OK, 또는 "Pally" 텍스트 정도. 1A가 즉시 덮어쓸 예정.
- `create-next-app` 추가 플래그 — `--ts --tailwind --app --no-src-dir --import-alias '@/*' --eslint --use-npm`.

### Folded Todos

해당 없음 (todo match-phase 결과 0건).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 0 Scope
- `.planning/ROADMAP.md` § Phase 0 — Success Criteria 1~5, Repo Layout 섹션
- `.planning/REQUIREMENTS.md` § SESSION-01, Traceability 표 (Phase 0 = types only)
- `.planning/PROJECT.md` § Constraints (Mobile-first, Tech stack), Key Decisions (monorepo split, Phase 0 minimal foundation)

### Team Conventions
- `CLAUDE.md` § 1 (Phase Ownership), § 6 (Code Rules — TypeScript/Next.js, Git), § 9 (NEVER/ALWAYS)
- `docs/shared/SETUP.md` § 1-3 (Local tools, MCP, GCP — Phase 0 셋업 전제)

### Existing Assets (참조용, Phase 0에서 수정 금지)
- `backend/main.py` — Phase 1C 영역, Phase 0에서 손대지 않음
- `ai/analyzer.py`, `ai/matrix_engine.py` — Phase 1B가 소비할 validated assets
- `assets/visualizer.html` — Canvas2D 프로토타입 (Phase 1B 참조)

### No External Specs
- ADR `docs/adr/0001-python-engine-integration.md` — 아직 작성 안 됨 (Phase 1B 산출물)
- `docs/code-convention.md` — 아직 없음 (CLAUDE.md §10에 참조되어 있지만 미작성). Phase 0 범위 밖.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`backend/main.py`**: 이미 존재 (Phase 1C 영역). Phase 0에서 import / 수정 / 호출 모두 금지. 1C가 GCP STT/TTS/Gemini로 재작성 예정.
- **`ai/analyzer.py` + `ai/matrix_engine.py`**: validated rule-based 5축 엔진. Phase 0과 직접 연결 없음. 1B 통합 ADR이 활용.
- **`assets/visualizer.html`**: Canvas2D Superformula 프로토타입. 1B가 React 컴포넌트로 포팅 시 참조.

### Established Patterns
- **모노레포 분리**: `frontend/` (Vercel) · `backend/` (Railway) · `ai/` (Python 공유). Phase 0은 `frontend/` 안에서만 작업.
- **Vercel Root Directory = `frontend/`**: `cd frontend && npm run dev` 한 줄로 dev 서버. Vercel 배포는 main 브랜치 push만으로 자동.
- **TS strict 모드 · Tailwind · App Router · Server Components 기본** — CLAUDE.md §6 코드 룰 그대로 적용.

### Integration Points
- Phase 1A: `frontend/components/`, `frontend/app/page.tsx`(덮어쓰기), `frontend/lib/types/message.ts`/`session.ts` import.
- Phase 1B: `frontend/components/pally/`, `frontend/app/dev/pally/`, `frontend/lib/types/character.ts`(추가). 김민주 소유.
- Phase 1C: `frontend/lib/supabase/client.ts`(anon)는 Phase 0 산출, server client(`server.ts`)와 마이그레이션은 1C가 추가. `frontend/.env.local`에 `NEXT_PUBLIC_BACKEND_URL`을 1C 배포 후 Railway URL로 갱신.

### Constraints (코드베이스에서 발견)
- **루트 `.env.local`에 OpenAI key 잔존** — out-of-scope 키. 보안 위험 (key revoke 필요 여부 PM 확인).
- **루트 `README.md` 존재 (`@`로 표시된 큰 파일)** — Phase 0에서 손대지 않음. 향후 monorepo overview 갱신은 별도 phase.
- **`docs/adr/` 비어 있음** — Phase 1B가 첫 ADR 작성.

</code_context>

<specifics>
## Specific Ideas

- **Pally 도메인 친화 명명**: Message.role을 `'user' | 'pally'`로 잠금 (LLM 관례 `'assistant'` 대신). 이후 UI/팀 커뮤니케이션 일관성을 위해.
- **wire-format 합 일치**: Phase 1C가 Supabase에 작성할 `messages.transcript` 컬럼명과 Phase 0 TS 타입의 `transcript` 필드명 통일. 변환 레이어 없이 직결.
- **EMA 데모 가중치**: ROADMAP에 `alpha = 0.7 for demo` 명시. Phase 0에서는 사용 안 함 (1B/1C에서 소비).

</specifics>

<deferred>
## Deferred Ideas

- **Prettier + lint-staged + husky 설정** — Phase 0 스코프 보호로 제외. Phase 2 demo polish 또는 별도 cleanup phase에서 도입 검토.
- **`docs/code-convention.md` 작성** — CLAUDE.md §10에 참조되어 있으나 미작성. Phase 0 범위 밖, PM이 별도 처리.
- **루트 `.env.example` 또는 monorepo 차원 secret 관리** — ROADMAP이 명시적으로 "루트 .env.example 두지 않음" 결정. v2에서 doppler/1password 같은 secret manager 도입 시 재검토.
- **`Axes` / `CharacterParams` 타입 정의** — Phase 1B에서 김민주가 `ai/analyzer.py`, `matrix_engine.py` 실제 출력 모양 기반으로 정의 (`frontend/lib/types/character.ts`).
- **Supabase `sessions` / `messages` 테이블 + RLS 마이그레이션** — Phase 1C에서 백은혜 담당.
- **`backend/main.py`의 OpenAI 의존 정리** — 현재 `backend/`는 Phase 1C가 GCP로 재작성 예정이므로 Phase 0에서 손대지 않음.

### Reviewed Todos (not folded)
해당 없음.

</deferred>

---

*Phase: 00-foundation-minimal*
*Context gathered: 2026-05-21*
