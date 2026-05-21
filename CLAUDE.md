## gstack

Use /browse from gstack for all web browsing. Never use mcp__claude-in-chrome__* tools.

Available skills: /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review,
/design-consultation, /review, /ship, /land-and-deploy, /canary, /benchmark, /browse,
/qa, /qa-only, /design-review, /setup-browser-cookies, /setup-deploy, /retro,
/investigate, /document-release, /codex, /cso, /autoplan, /careful, /freeze, /guard,
/unfreeze, /gstack-upgrade, /connect-chrome.

---

## 핵심 원칙

**Boil the Lake:** AI 코딩에서 완전한 구현의 비용은 거의 0이다. 90% 구현과 100% 구현의 차이가 수십 줄이면, 항상 100%를 선택한다. 테스트, 에지 케이스, 에러 핸들링을
"follow-up PR"로 미루지 않는다.

**Search Before Building:** 새로운 패턴이나 인프라를 만들기 전에 반드시 기존 해법을
먼저 검색한다. 검색 비용은 0에 가깝고, 검색하지 않는 비용은 더 나쁜 것을 재발명하는 것이다.

## 세션 운용

**수동 스킬 실행:** 각 스킬(review, qa, ship, document-release 등)은 사용자가 직접 요청할 때만 실행한다. 자동 체이닝하지 않는다.
**세션 분리:** Plan→Build 전환 시, 컨텍스트 초과 시, 다른 feature branch 시.

---

## 외부 API 사전 검증 (구체 절차)

> Global CLAUDE.md에 원칙이 있다. 여기서는 구체적 실행 절차를 정의한다.

코드를 한 줄이라도 작성하기 전에, 외부 API의 실제 응답을 반드시 먼저 확인한다:
1. API를 직접 호출해서 실제 응답 데이터의 구조, 양, 품질을 확인한다 (Postman 역할)
2. 스키마만 맞추고 넘어가지 않는다. 실제 데이터가 충분히 오는지, 기대한 필드가 다 있는지 확인한다
3. Apify actor 등 외부 서비스는 테스트 호출 → 응답 확인 → 비교표 작성 → 사용자 승인 순서로 진행한다
4. 이 단계를 건너뛰고 빌드하는 것은 금지한다

## E2E 검증 규칙

> Phase 빌드 중에는 이 규칙이 Global의 "3 actions마다 checkpoint"보다 우선한다.

**테스트 데이터 선택:** e2e 테스트는 반드시 충분한 데이터가 있는 실제 계정/엔티티로 검증한다.
"동작하는지만 확인"이 아니라, 모든 범위를 커버할 수 있는 대표 데이터를 선택한다.
예: Threads 분석이면 게시물이 100개 이상인 활발한 계정, 다양한 미디어 타입 포함.

빌드 완료 후 e2e 테스트는 반드시 **실제 동작하는 데이터**로 검증한다:
- 외부 API 연동이 있으면 실제 API 호출 → 응답 → DB 저장 → UI 표시까지 전체 흐름 확인
- 테스트 계정은 충분한 데이터가 있는 실제 계정 사용 (예: Threads 분석이면 게시물이 많은 계정)
- "타입 체크 통과" 또는 "유닛 테스트 통과"만으로 검증 완료 처리 금지
- Supabase 등 인프라 프로비저닝이 필요하면 코드 작성과 별개로 반드시 실행
- /connect-chrome으로 headed 브라우저를 띄워서 사용자가 실시간으로 확인 가능하게

---

## Phase 설계 & 빌드

### /plan-eng-review 2단계

**1차 (설계 게이트, Plan 세션):** 전체 아키텍처, Phase 분할, 테스트 전략 확정.
`docs/code-convention.md` 없으면 생성. ADR은 핵심 결정만 `docs/adr/`에 기록 (세션당 최대 3개, 템플릿: `docs/adr/TEMPLATE.md`). 나머지는 eng-plan에 "Minor Decision:"으로 인라인.

**Phase 설계 원칙 — 병렬 우선:**
- **기능(vertical slice) 단위로 쪼갠다.** 레이어 단위(DB→API→UI) 금지. 하나의 Phase가 DB+API+UI를 포함해도 된다.
- **의존 관계를 명시한다.** 각 Phase에 `depends_on: [Phase X]`를 표기.
- **Phase 0 (Foundation):** 공유 인프라(DB 스키마, 인증, 공통 타입)는 Phase 0으로 분리. 다른 모든 Phase가 이것만 의존하게 설계.
- **병렬 가능한 Phase는 같은 번호를 쓴다.** 예: Phase 2A, 2B, 2C는 동시 빌드 가능.
- **공유 상태를 최소화한다.** Phase 간 DB 테이블이 겹치면 의존성 발생. 테이블 소유권을 Phase별로 할당.

```
예시:
Phase 0: Foundation (DB schema, auth, shared types) — no deps
Phase 1A: Feed scraping pipeline — depends on 0
Phase 1B: Dashboard UI — depends on 0
Phase 1C: Analytics engine — depends on 0
Phase 2: Integration (cross-feature flows) — depends on 1A, 1B, 1C
```

병렬 Phase는 각각 별도 branch에서 빌드하고 별도 PR로 머지한다. Conductor 워크스페이스를 병렬로 띄워서 동시 진행 가능.

**2차 (구현 게이트, Build 세션):** 해당 Phase만 검증.
PASS → Build, PASS WITH CHANGES → eng-plan 수정 후 Build, FAIL → 사용자에게 보고.

### Phase 빌드 절차

"Phase N build해줘" 요청 시:
1. 필수 문서 읽기 (eng-plan, code-convention, ADR, DESIGN.md)
2. /plan-eng-review 2차 → Phase 검증
3. Build + checkpoint commit
4. 빌드 완료 보고 → 이후 스킬(review, qa, ship 등)은 사용자가 직접 요청

---

## 배포 워크플로우

- **Production branch:** `main` — 이 브랜치에 push하면 Vercel Git 연동으로 자동 배포됨

### 절차
1. **배포 = `main`에 push.** 그게 전부. Vercel CLI(`vercel deploy`)로 수동 배포하지 않는다.
2. feature 브랜치에서 작업 → PR 머지 또는 `main`에 push → 자동 배포.
3. 배포 후 반드시 `Vercel MCP > list_deployments`로 상태 확인 (BUILDING → READY).
4. 빌드 실패 시 `Vercel MCP > get_deployment_build_logs`로 로그 확인.

### Vercel tool 사용 기준
- **Vercel MCP**: 배포 상태 확인, 빌드 로그, 런타임 로그 조회 (읽기 전용)
- **Vercel CLI**: 초기 프로젝트 셋업, 환경변수 설정, 프로젝트 설정 변경 등 (쓰기 작업)
- **절대 하지 않을 것**: Vercel CLI로 `vercel deploy --prod` 수동 배포 (Git 연동과 충돌)

### 주의사항
- production 브랜치는 `main`으로 고정. 절대 feature 브랜치에서 직접 production 배포하지 않는다.
- `.vercel/project.json`이 로컬에 있을 수 있지만, 배포는 항상 GitHub → Vercel Git 연동으로 한다.
- "배포해줘" 요청 시: `git push origin <branch>:main` 후 배포 상태 확인까지 완료한다.

---

## 리뷰 & Design

### 리뷰 참조
/review 시 반드시 읽고 위반 체크: `docs/code-convention.md`, `docs/adr/*.md`, `DESIGN.md` (존재 시).

### Design System
UI 작업 전 DESIGN.md 필수 참조. 명시 규칙과 충돌하는 변경은 사용자 승인 필요.
QA에서는 렌더링된 UI가 DESIGN.md와 다른지 확인 (시각적 결과 기준).

---

## 문서 저장 규칙

gstack 스킬 문서 생성 시 `~/.gstack/projects/`에 추가로 아래 경로에 저장. 디렉토리 없으면 `mkdir -p`.

**Source of Truth:** `docs/`가 정본. `~/.gstack/projects/`는 캐시. 충돌 시 `docs/` 우선.

| 스킬 | 저장 경로 | 파일명 형식 |
|------|----------|------------|
| /office-hours | `docs/plan/` | `{YYYY-MM-DD}-{feature}-design.md` |
| /plan-ceo-review | `docs/plan/` | `{YYYY-MM-DD}-{feature}-ceo-review.md` |
| /plan-eng-review | `docs/plan/` | `{YYYY-MM-DD}-{feature}-eng-plan.md` |
| /plan-design-review | `docs/design/` | `{YYYY-MM-DD}-{feature}-design-review.md` |
| /design-consultation | `docs/design/` + 루트 `DESIGN.md` | `{YYYY-MM-DD}-design-system.md` |
| /autoplan | 위 스킬들의 규칙을 각각 적용 | |

### 프로젝트 문서 구조

```
프로젝트/
├── CLAUDE.md              ← 이 파일
├── docs/
│   ├── plan/              ← office-hours, CEO 리뷰, eng plan
│   ├── design/            ← 디자인 리뷰, 디자인 시스템 문서
│   ├── adr/               ← 아키텍처 결정 기록 (TEMPLATE.md 참조)
│   └── code-convention.md ← 코드 컨벤션 (필수 참조)
└── ...
```
