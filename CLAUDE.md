# CHARACTER MATRIX — Team & AI Agent Guide

> 이 문서는 **사람 팀원**과 **AI 코딩 에이전트(Claude Code / Codex / Cursor)** 둘 다 본다.
> - 새 팀원: §0 온보딩부터 순서대로
> - AI 에이전트: §2 워크플로우부터 (각 세션 시작 시 이 파일 + `docs/code-convention.md` + `DESIGN.md` 반드시 로드)
>
> **AGENTS.md는 이 파일을 가리키는 symlink다.** Codex는 동일 내용을 본다.

---

## 0. 팀 온보딩 (처음 1회)

### 0.1 필수 도구

| 도구 | 용도 | 버전 |
|------|------|------|
| Node.js | 프론트엔드/Next.js | 20+ |
| Python | 핵심 엔진(`ai/`) | 3.10+ |
| pnpm | 패키지 매니저 | latest |
| git | 버전관리 | — |
| Claude Code (CLI) | 기본 AI 에이전트 | latest |
| Codex CLI (선택) | 보조 리뷰/검증 | latest |

### 0.2 gsd / gstack 설치

이 프로젝트는 **gsd**(메인 워크플로우) + **gstack**(보조 도구)으로 운용한다.

```bash
# gstack (gsd 스킬 포함)
git clone --depth 1 https://github.com/garrytan/gstack.git ~/gstack
cd ~/gstack && ./install.sh    # 설치 스크립트는 repo README 참조
```

설치 후 Claude Code 안에서 `/gsd-help`, `/gstack-upgrade` 가 자동완성에 뜨면 정상.

> 설치 막히면 Claire(@healthtok456)에게 정확한 명령 확인.

### 0.3 MCP 서버 등록 (전원 동일 셋업)

모든 팀원이 같은 MCP 서버를 등록해야 한다. **Claude Code 기준:**

```bash
# Supabase — DB 스키마/마이그레이션/로그 조회
claude mcp add --transport http supabase https://mcp.supabase.com/mcp

# Vercel — 배포 상태/빌드 로그
claude mcp add --transport http vercel https://mcp.vercel.com

# GitHub — PR/이슈/리뷰
claude mcp add --transport http github https://api.githubcopilot.com/mcp/

# Figma — 디자인 컨텍스트 (Figma Desktop 실행 중이어야 함)
claude mcp add --transport sse figma http://127.0.0.1:3845/sse
```

등록 후 `claude mcp list`로 4개 모두 확인.

**Codex 사용자**는 `~/.codex/config.toml`에 동일 서버 등록 (Codex 문서 참조).

### 0.4 환경 변수

```bash
cp .env.example .env.local
```

필요 키 (`.env.example` 참조):
- `OPENAI_API_KEY`
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
- `DATABASE_URL`

실제 키는 팀 공유 비밀저장소(1Password / Notion 비공개 페이지)에서 받음. 본인이 받지 못한 경우 PM(최윤서)에게 요청.

### 0.5 첫 동작 확인

```bash
python tests/test_matrix.py
```

5축 분석 + CHARACTER MATRIX 결과가 출력되면 환경 OK.

### 0.6 현재 진행 상태 파악

```
/gsd-progress
```

`.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`(있으면)를 읽고 다음 액션을 알려준다.

---

## 1. 도구 역할 분리

| 도구 | 역할 | 주요 명령 |
|------|------|----------|
| **gsd** | 메인 프로젝트 워크플로우 (요구사항 → phase 계획 → 빌드 → 배포) | `/gsd-*` |
| **gstack** | gsd가 안 다루는 보조 작업 (plan 리뷰, QA, 디자인 점검, 브라우징, Codex 2차 의견) | `/plan-eng-review`, `/qa`, `/design-review`, `/browse`, `/codex`, `/investigate` |
| **MCP 서버** | 외부 시스템 직접 조작 (Supabase, Vercel, GitHub, Figma) | tool calls |

**원칙:** gsd로 못 하는 일만 gstack 사용. 같은 기능이 양쪽에 있으면 **gsd 우선.**

---

## 2. 워크플로우

### 2.1 gsd 메인 명령어

| 단계 | 명령 | 결과물 |
|------|------|--------|
| 새 마일스톤 시작 | `/gsd-new-milestone` | `PROJECT.md` 업데이트, `REQUIREMENTS.md` |
| 로드맵 작성 | (gsd-new-milestone 안에서) | `ROADMAP.md` |
| Phase 계획 | `/gsd-plan-phase` | `.planning/phases/<phase>/PLAN.md` |
| Phase 실행 | `/gsd-execute-phase` | 코드 + atomic commits |
| 동작 검증 | `/gsd-verify-work` | UAT 통과 여부 |
| 코드 리뷰 | `/gsd-code-review` | `REVIEW.md` |
| 리뷰 자동 수정 | `/gsd-code-review-fix` | `REVIEW-FIX.md` + commits |
| 출시 | `/gsd-ship` | PR 생성, CI 대기 |
| 위치 확인 | `/gsd-progress` | 다음 액션 |
| 도움말 | `/gsd-help` | 전체 명령 목록 |

### 2.2 gstack 보조 명령어

| 명령 | 언제 쓰는가 |
|------|------------|
| `/plan-eng-review` | Phase 계획 엔지니어링 검토 (gsd-plan-phase 보완) |
| `/plan-design-review` | UI/디자인 계획 검토 |
| `/codex review` / `/codex challenge` / `/codex consult` | Codex로 독립 2차 의견 |
| `/qa` / `/qa-only` | 라이브 사이트 QA 테스트 |
| `/design-review` | 라이브 사이트 디자인 점검 |
| `/browse` | 모든 웹 브라우징 (`mcp__claude-in-chrome__*` 절대 금지) |
| `/investigate` | 버그 진단 |

### 2.3 세션 분리 기준

새 세션으로 분리해야 하는 시점:
- Plan → Build 전환 시
- 컨텍스트 80% 초과 시
- 다른 feature branch로 이동 시

### 2.4 수동 실행 원칙

스킬은 **사용자가 명시적으로 요청할 때만** 실행한다. 자동 체이닝(예: build 후 자동 review → ship) 금지. AI 에이전트는 각 단계를 완료 보고 후 멈춘다.

### 2.5 역할별 gsd 사용 순서

#### 공통 (전원, 매 작업 세션 시작 시)

1. `git pull origin main` — 최신 받기
2. Claude Code에서 `/gsd-progress` — 현재 마일스톤/phase 위치 + 다음 액션 확인
3. 본인 담당 phase / branch로 체크아웃

#### PM (최윤서 — 기획 · 진행 관리 · QA)

| 시점 | 명령 | 결과 |
|------|------|------|
| 새 마일스톤 시작 | `/gsd-new-milestone` | `PROJECT.md` 업데이트, `REQUIREMENTS.md` 갱신 |
| 로드맵 정리 | (위에서 이어짐) | `ROADMAP.md` 생성/갱신 |
| 매일 진행 점검 | `/gsd-progress` · `/gsd-list-workspaces` | 누가 어디까지 했는지 |
| 백로그 정리 | `/gsd-review-backlog` · `/gsd-check-todos` | 다음 phase로 promote |
| UAT 검증 | `/gsd-verify-work` · `/gsd-audit-uat` | 요구사항 충족 여부 |
| 마일스톤 종료 | `/gsd-complete-milestone` · `/gsd-milestone-summary` | 아카이브 + 회고 자료 |
| 다음 마일스톤 준비 | `/gsd-review-backlog` | v2 항목 검토 |

> PM은 직접 코드 작업은 하지 않는다. `/gsd-execute-phase`는 개발자가 실행.

#### 개발자 (백은혜 · 김민주 · 이찬희 — Phase 빌드 담당)

각 phase는 **3개 세션으로 분리**해 진행한다. 같은 세션에 plan + build + ship을 몰면 컨텍스트 폭발.

**세션 1 — Plan** (할당받은 phase 시작 시)

1. `/gsd-plan-phase <phase 번호>` — RESEARCH → DISCUSS → PLAN.md 생성
2. (선택) `/plan-eng-review` — 엔지니어링 측면 2차 검토
3. (UI 포함 phase면) `/gsd-ui-phase` — `UI-SPEC.md` 생성
4. (불안하면) `/codex consult` — Codex로 plan 독립 검토
5. PLAN.md 확정되면 **세션 종료** (컨텍스트 비우기)

**세션 2 — Build** (새 Claude Code 세션)

6. `/gsd-execute-phase <phase 번호>` — PLAN.md 따라 빌드, atomic commit
7. 외부 API 쓰면 §4 절차 먼저 (코드 전에 실호출 확인)
8. `/gsd-verify-work` — UAT 기준 e2e 동작 검증 (§5)
9. `/gsd-code-review` — `REVIEW.md` 생성
10. `/gsd-code-review-fix` — 리뷰 지적사항 자동 수정
11. (auth/payment/RLS 만진 경우) `/gsd-secure-phase` — 보안 감사
12. Build 완료 시 **세션 종료**

**세션 3 — Ship** (새 세션)

13. `/gsd-ship` — PR 생성
14. CI 통과 확인 → PM에게 머지 요청 또는 본인 머지
15. main 머지 후 Vercel MCP `list_deployments`로 READY 확인 (§8)
16. 배포 실패면 `get_deployment_build_logs`로 확인

#### 역할별 phase 매핑 (현재 마일스톤 — 2026-06-07 데모)

| 담당자 | 주력 phase | 비고 |
|--------|-----------|------|
| 이찬희 (FE · 디자인) | **Phase 0** (Foundation) + **Phase 1A** (FE Screens) | Next.js 스캐폴딩 · Supabase 스키마 · 공유 타입 · 랜딩/대화/피드백 UI · DESIGN.md |
| 백은혜 (AI · 데이터) | **Phase 1B** (Pally Canvas2D) | 5축 파라미터 → Canvas2D Superformula 시각화 · thinking 애니메이션 |
| 김민주 (BE · Supabase) | **Phase 1C** (Voice + Feedback BE) | `/api/chat` (Whisper → 5축 → GPT-4o → TTS) · `/api/feedback` · Gemini 인라인 힌트 |
| 전원 | **Phase 2** (Integration & Demo Polish) | 모바일 폴리시 · Vercel 배포 · 데모 리허설 |

> Phase 0 완료 전엔 1A/1B/1C 병렬 작업 불가. 이찬희가 Phase 0을 가장 먼저 끝내야 백은혜/김민주가 시작 가능.

#### 막힐 때 (전 역할 공통)

| 상황 | 명령 |
|------|------|
| 버그 진단 | `/gsd-debug` 또는 `/investigate` |
| 다른 AI 의견 | `/codex consult` · `/codex challenge` |
| 이전 세션 컨텍스트 복원 | `/gsd-resume-work` · `/context-restore` |
| 작업 일시 중단 | `/gsd-pause-work` (다음에 `/gsd-resume-work`로) |
| gsd 상태 점검 | `/gsd-health` |
| 전체 명령 보기 | `/gsd-help` |

---

## 3. 핵심 원칙 (전 팀원 + AI 공통)

### 3.1 Top 5 — 절대 지킨다

1. **외부 API는 코드 전에 실제 호출한다.** 스키마만 맞추고 넘어가지 않는다. 데이터 양/품질/구조를 직접 확인. (§4 절차)
2. **"동작할 것이다"는 검증이 아니다.** 실제 출력을 보여준다. 타입체크/유닛테스트만으로 완료 처리 금지. (§5 절차)
3. **에러를 삼키지 않는다.** Empty `catch {}` 금지. `|| {}`, `?? []` 폴백 금지. 크래시가 침묵보다 낫다.
4. **`git add .` 금지.** 파일 개별 스테이징. `.env` / 자격증명 커밋 감지 시 즉시 중단.
5. **비즈니스 로직을 추측하지 않는다.** 모호하면 묻는다. auth / 결제 / 데이터 삭제는 확인 후 진행.

### 3.2 Boil the Lake

AI 코딩에서 완전한 구현 비용은 거의 0이다. 90% 구현과 100% 구현의 차이가 수십 줄이면 항상 100%를 선택한다. 테스트/엣지 케이스/에러 핸들링을 "follow-up PR"로 미루지 않는다.

### 3.3 Search Before Building

새 패턴/인프라를 만들기 전에 반드시 기존 해법을 검색한다. 검색 비용은 0에 가깝고, 안 한 비용은 더 나쁜 것을 재발명하는 것이다.

### 3.4 Communication

- 한국어 사용. (코드/커밋/기술 문서는 영어)
- 직접적이고 간결하게. "great question!" 같은 필러 금지.
- 모르면 "모른다"고 말한다. 추측보다 낫다.

---

## 4. 외부 API 사전 검증 절차

> 원칙은 §3.1 #1. 여기는 실행 절차.

코드 한 줄 작성 전 외부 API 실제 응답을 확인한다:

1. API를 직접 호출해 응답 데이터 구조/양/품질 확인 (Postman 역할)
2. 스키마만 맞추지 말 것. 실제 데이터가 충분한지, 기대한 필드가 다 있는지 확인
3. Apify actor 등 외부 서비스는 **테스트 호출 → 응답 확인 → 비교표 작성 → 사용자 승인** 순서
4. API key가 없으면 deferred로 넘기지 말고 즉시 요청
5. 이 단계 건너뛰고 빌드 시작 금지

---

## 5. E2E 검증 규칙

> Phase 빌드 중에는 이 규칙이 "3 actions마다 checkpoint"보다 우선한다.

**테스트 데이터 선택:** 충분한 데이터가 있는 실제 계정/엔티티 사용. "동작만 확인"이 아니라 모든 범위를 커버하는 대표 데이터. 예: Threads 분석이면 100+ 게시물 + 다양한 미디어 타입.

**빌드 완료 후 e2e:**
- 외부 API 연동 → 응답 → DB 저장 → UI 표시 전체 흐름 확인
- 충분한 데이터 있는 실제 계정으로
- 타입 체크 / 유닛 테스트 통과만으로 검증 완료 처리 금지
- Supabase 등 인프라 프로비저닝 필요 시 반드시 실행 (코드와 별개)
- `/browse`(headed) 또는 Playwright MCP로 사용자가 실시간으로 확인 가능하게

---

## 6. Phase 설계 & 빌드

### 6.1 Phase 분할 — 병렬 우선

- **기능(vertical slice) 단위.** 레이어 단위(DB→API→UI) 금지. 하나의 Phase가 DB+API+UI 포함 가능.
- **의존 관계 명시.** 각 Phase에 `depends_on: [Phase X]`.
- **Phase 0 (Foundation):** 공유 인프라(DB 스키마, 인증, 공통 타입). 다른 모든 Phase가 이것만 의존.
- **병렬 가능 Phase는 같은 번호 + 접미사.** 예: Phase 2A, 2B, 2C 동시 빌드.
- **공유 상태 최소화.** DB 테이블이 겹치면 의존성 발생. 테이블 소유권을 Phase별로 할당.

```
Phase 0: Foundation (DB schema, auth, shared types) — no deps
Phase 1A: Feed scraping pipeline — depends on 0
Phase 1B: Dashboard UI — depends on 0
Phase 1C: Analytics engine — depends on 0
Phase 2: Integration (cross-feature flows) — depends on 1A, 1B, 1C
```

병렬 Phase는 별도 branch + 별도 PR. Conductor 워크스페이스 병렬 가능.

### 6.2 빌드 절차

"Phase N build해줘" 요청 시 AI 에이전트가 따르는 순서:

1. 필수 문서 로드: `.planning/phases/<phase>/PLAN.md`, `docs/code-convention.md`, `docs/adr/*.md`, `DESIGN.md`
2. `/plan-eng-review` (선택) 또는 `/gsd-plan-phase` 결과 재확인
3. 빌드 + checkpoint commit (atomic)
4. 완료 보고 → review/qa/ship은 사용자 요청 시에만

### 6.3 ADR (Architecture Decision Records)

핵심 결정만 `docs/adr/`에 기록. 세션당 최대 3개. 템플릿: `docs/adr/TEMPLATE.md`. 나머지는 plan 문서에 "Minor Decision:"으로 인라인.

---

## 7. 코드 규칙

### 7.1 TypeScript / Next.js

- TypeScript strict mode. `any` 금지 (불가피한 경우 `// TODO` 사유 명시)
- 주석/변수명/함수명은 영어
- 기본 Server Components. `'use client'`는 인터랙션/브라우저 API/훅 필요 시만
- 변이는 Server Actions. Route Handlers는 webhook/3rd-party 연동만
- Tailwind CSS + `cn()` 유틸 (문자열 연결 금지)
- Named export 선호. Default export는 Next.js page/layout/route handler만
- 외부 입력(유저 입력, API 응답, URL params)은 Zod로 경계에서 검증

### 7.2 에러 핸들링

- Empty `catch {}` 금지. 절대로 에러를 삼키지 않는다.
- `|| {}`, `?? []` 폴백 금지. 의미 있는 기본값 또는 명시적 에러.
- Server Actions: `{ data, error }` 패턴 반환. 클라이언트로 throw 금지.
- 서버에서는 전체 에러 로그, 클라이언트로는 안전한 메시지만.

### 7.3 Supabase

- **모든 테이블 RLS 활성화. 예외 없음.**
- RLS 정책은 `auth.uid()` 검증. `true` 정책 금지.
- 마이그레이션은 forward-only. 적용된 마이그레이션 수정 금지, 새로 생성.
- `supabase-js` v2 타입 클라이언트 (`supabase gen types`).
- 클라이언트: `anon` key only. `service_role` key는 서버 전용 — 클라이언트 import 금지.

### 7.4 Git

- `git add .` 금지. 파일 개별 스테이징.
- 커밋 메시지: imperative mood, 72자 이내, **왜(why)** 설명.
- `.env` / credentials / API key 커밋 금지. 감지 시 즉시 중단.
- `--no-verify` / `--force` 금지 (명시 요청 시 제외).
- **Production branch는 `main` 고정.** Feature branch에서 직접 prod 배포 금지.

---

## 8. 배포 워크플로우

**Production branch:** `main` (Vercel Git 연동 자동 배포).

### 8.1 절차

1. **배포 = `main`에 push.** 그게 전부. `vercel deploy` 수동 금지.
2. feature 브랜치 작업 → PR 머지 또는 `main`에 push → 자동 배포
3. 배포 후 **반드시** Vercel MCP `list_deployments`로 상태 확인 (BUILDING → READY)
4. 빌드 실패 시 Vercel MCP `get_deployment_build_logs`로 로그 확인

### 8.2 Vercel 도구 사용 기준

- **Vercel MCP**: 배포 상태 / 빌드 로그 / 런타임 로그 (읽기 전용)
- **Vercel CLI**: 초기 프로젝트 셋업 / 환경변수 설정 / 프로젝트 설정 변경 (쓰기)
- **금지**: Vercel CLI로 `vercel deploy --prod` 수동 배포 (Git 연동과 충돌)

### 8.3 주의

- `.vercel/project.json`이 로컬에 있어도 배포는 항상 GitHub → Vercel Git 연동
- "배포해줘" 요청 시: `git push origin <branch>:main` 후 배포 상태 확인까지 한 번에 완료

---

## 9. 리뷰 & Design

### 9.1 리뷰 시 필수 참조

`/gsd-code-review` 또는 `/review` 시: `docs/code-convention.md`, `docs/adr/*.md`, `DESIGN.md`(있으면) 모두 읽고 위반 체크.

### 9.2 Design System

- UI 작업 전 **`DESIGN.md` 필수 참조**.
- 명시 규칙과 충돌하는 변경은 사용자 승인 필요.
- QA에서는 렌더링된 UI가 DESIGN.md와 다른지 시각적 결과 기준으로 확인.

---

## 10. 문서 저장 규칙

**Source of Truth:** `docs/`가 정본. `.planning/`은 gsd 작업 영역. 충돌 시 `docs/` 우선.

| 스킬 / 결과물 | 저장 경로 | 파일명 |
|---------------|----------|--------|
| `/office-hours` | `docs/plan/` | `{YYYY-MM-DD}-{feature}-design.md` |
| `/plan-ceo-review` | `docs/plan/` | `{YYYY-MM-DD}-{feature}-ceo-review.md` |
| `/plan-eng-review` | `docs/plan/` | `{YYYY-MM-DD}-{feature}-eng-plan.md` |
| `/plan-design-review` | `docs/design/` | `{YYYY-MM-DD}-{feature}-design-review.md` |
| `/design-consultation` | `docs/design/` + 루트 `DESIGN.md` | `{YYYY-MM-DD}-design-system.md` |
| `/gsd-*` | `.planning/` | gsd가 자동 관리 (PROJECT/REQUIREMENTS/ROADMAP/PLAN/REVIEW…) |

### 10.1 프로젝트 문서 구조

```
capstone-latest/
├── CLAUDE.md / AGENTS.md  ← 이 파일 (AGENTS.md는 symlink)
├── README.md              ← 프로젝트 소개 (외부 독자용)
├── .env.example           ← 환경 변수 템플릿
├── .planning/             ← gsd 작업 영역
│   ├── PROJECT.md
│   ├── REQUIREMENTS.md
│   ├── ROADMAP.md
│   └── phases/<phase>/PLAN.md, REVIEW.md ...
├── docs/
│   ├── plan/              ← office-hours / 리뷰 / eng-plan
│   ├── design/            ← 디자인 리뷰 / 디자인 시스템 문서
│   ├── adr/               ← 아키텍처 결정 (TEMPLATE.md 참조)
│   ├── PMF/               ← AI 투명성 / 경쟁 분석
│   ├── _archive/          ← 옛 풀스코프 문서 (참조용)
│   ├── code-convention.md ← 코드 컨벤션 (리뷰 시 필수)
│   ├── Team_Ground_Rule.md
│   └── elevator_speech.md
├── ai/                    ← Python 핵심 엔진 (analyzer, matrix_engine)
├── data/                  ← 데이터셋
├── tests/                 ← 테스트 / 데모
└── assets/                ← 시각화 프로토타입
```

---

## 11. AI 에이전트별 사용 가이드

### 11.1 Claude Code

- 기본 진입점. 모든 gsd / gstack 스킬 사용 가능.
- 새 세션마다 이 파일 + `docs/code-convention.md` + `DESIGN.md` 자동 로드.

### 11.2 Codex CLI

- `AGENTS.md`(= 이 파일 symlink)를 본다. 동일한 규칙 적용.
- 주 용도: Claude 결과의 독립 2차 검토 (`/codex review`, `/codex challenge`).
- Claude가 이미 작성한 패턴과 충돌 시 **Claude의 패턴 우선** (일관성 유지).
- MCP 셋업은 `~/.codex/config.toml`에 Claude Code와 동일 서버 등록.

### 11.3 Cursor / 기타

- 같은 `CLAUDE.md`(또는 `AGENTS.md`) 규칙 따름.
- 도구별 차이가 있으면 이 파일 규칙 우선.

---

## 12. 금지 / 권장 정리

### 금지

- `mcp__claude-in-chrome__*` 사용 (항상 `/browse` 또는 Playwright MCP)
- `git add .` (개별 스테이징만)
- `.env` / credentials 커밋
- `--no-verify`, `--force` (명시 허락 없이)
- `vercel deploy --prod` 수동 실행
- Empty `catch {}` / silent fallback (`|| {}`, `?? []`)
- "동작할 것이다" 식 미검증 완료 보고
- README.md / ARCHITECTURE.md / 문서 파일을 사용자가 요청하지 않았는데 자동 생성
- 코드 / 커밋 메시지에 이모지 추가 (사용자가 요청한 경우 제외)
- 현재 task와 무관한 코드 리팩토링
- 새 의존성 설치 전 사전 보고 누락
- 비즈니스 로직 추측 (모호하면 묻기)

### 권장

- 기존 코드 / 프로젝트 CLAUDE.md를 먼저 읽고 패턴 매칭
- 3회 실패 시 stop & reassess
- auth / 결제 / 데이터 삭제 작업 전 사용자 확인
- 병렬 가능한 작업은 한 메시지에 multiple tool calls
- gsd 작업 중 무엇을 하고 있는지 짧게 보고 (silent 금지)
