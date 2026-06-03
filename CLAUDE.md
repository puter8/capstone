# Pally — CharaShift MVP · Team CLAUDE.md

> 사람 팀원 + AI 에이전트(Claude Code / Codex / Cursor) 공용 가이드.
> **Source of truth: `.planning/ROADMAP.md`** — 충돌 시 ROADMAP 우선.
> **AGENTS.md는 이 파일의 symlink.** Codex도 동일 규칙.
> **초기 셋업(도구·MCP·gcloud·env)은 `docs/shared/SETUP.md` 참조.** 처음 1회만.

## Codex bootstrap

- Codex는 repo root의 `AGENTS.md`를 먼저 읽는다.
- 이 repo에서는 `AGENTS.md -> CLAUDE.md` symlink를 유지한다. 즉 Codex가 `AGENTS.md`를 읽으면 항상 이 `CLAUDE.md` 전체 규칙을 읽는다.
- `AGENTS.md`를 별도 문서로 복사해 관리하지 않는다. 규칙 변경은 `CLAUDE.md`에만 한다.
- symlink가 깨졌거나 일반 파일로 바뀌었으면 작업 전에 `ln -sf CLAUDE.md AGENTS.md`로 복구한다.

---

## 0. 매 세션 시작 — 무조건 이 4가지

```bash
git pull origin main                         # 1. 최신 받기 (diverge 방지)
```
```
/gsd-progress                                # 2. 현재 phase + next action 확인
```
```bash
git checkout gsd/phase-<N>-<slug>            # 3. 본인 phase branch로
```

4. 환경변수가 바뀌었는지 팀 채널/Notion 확인.

**세션 분리:** Plan / Build / Ship 각각 새 세션. 컨텍스트 80% 넘으면 강제 분리. 한 세션에 다 몰면 컨텍스트 폭발.

---

## 1. 팀 & Phase Ownership

| 사람 | 역할 | Phase | 주력 디렉토리 |
|------|------|-------|--------------|
| 최윤서 | PM · 기획 · QA | 전체 검수 | `.planning/`, `docs/` |
| 이찬희 | FE · 디자인 | **Phase 0** + **Phase 1A** | `frontend/` (Pally 영역 제외) |
| 김민주 | AI · 데이터 | **Phase 1B** | `ai/`, `frontend/components/pally/`, `frontend/app/dev/pally/`, `frontend/lib/types/character.ts` |
| 백은혜 | BE · AI | **Phase 1C** | `backend/`, Supabase 마이그레이션 |
| 전원 | Integration | **Phase 2** | 전체 |

**의존 관계:**
- Phase 0 완료 전 1A/1B/1C **불가**
- 1C는 1B 전체 머지가 아니라 **D+1 Python engine ADR**만 기다림
- Phase 2는 1A+1B+1C 머지 후 시작

**충돌 회피 (중요):** 1A와 1B 둘 다 `frontend/`를 만진다.
- 이찬희 = 메인 화면, audio shell, 네비게이션
- 김민주 = Pally renderer, character types, dev 페이지
- 다른 영역 만져야 하면 → 팀 채널 공지 + 짧은 PR

---

## 2. 공유 리소스 ID

MCP가 본인 계정의 모든 리소스를 보여주므로, AI가 매 명령마다 **어떤 project**를 다룰지 알아야 한다. 아래 식별자를 그대로 사용한다.

| 리소스 | 식별자 |
|--------|-------|
| Supabase project | `orhodalbxhbzlvjsqalu` (org: `puter8`, region: `ap-northeast-1`) |
| GitHub repo | `puter8/capstone` |
| GCP project | `capstone-puter8` |
| Vercel team / project | `puter8` / `capstone-eight-virid` → `https://capstone-eight-virid.vercel.app` |
| Railway project | `capstone-production-e8c2` → `https://capstone-production-e8c2.up.railway.app` |

다른 본인 개인 계정 리소스와 혼동하지 않도록 위 ID로 명시. 새 리소스 추가 시 이 표를 먼저 업데이트하고 팀 채널 공지.

---

## 3. Workflow

### Session 1 · Plan

```
/gsd-discuss-phase <N>         # 필수. 컨텍스트 질문 → CONTEXT.md
/gsd-plan-phase <N>            # 필수. PLAN.md (research 내장)
```

PLAN.md 확정 → **세션 종료** (컨텍스트 비움).

### Session 2 · Build (새 세션)

```
/gsd-execute-phase <N>         # 필수. PLAN.md 따라 atomic commit
                               # 외부 API 쓰면 §4 절차 먼저
/gsd-verify-work               # 필수. UAT (§5)
/gsd-code-review               # REVIEW.md
/gsd-code-review-fix           # auto-fix + commit
/gsd-secure-phase              # auth/RLS 만진 경우만
```

Build 완료 → **세션 종료**.

### Session 3 · Ship (새 세션)

```
/gsd-ship                      # 필수. PR 생성
```

CI 통과 → main 머지 → Vercel/Railway 자동 배포 → Vercel MCP `list_deployments`로 READY 확인 (§8).

### 막힐 때

| 상황 | 명령 |
|------|------|
| 버그 진단 | `/investigate` 또는 `/gsd-debug` |
| 다른 AI 의견 | `/codex consult` / `/codex challenge` |
| 이전 세션 복원 | `/gsd-resume-work` / `/context-restore` |
| 일시 중단 | `/gsd-pause-work` |
| 전체 명령 | `/gsd-help` |

**원칙:** 스킬은 **명시적으로 요청할 때만**. 자동 체이닝(build → review → ship) 금지. AI는 단계별로 멈추고 보고.

---

## 4. 외부 API — 코드 전에 실호출

코드 한 줄 쓰기 전:

1. 실제 API 호출로 응답 구조/양/품질 확인 (Postman 역할)
2. 스키마만 맞추지 말 것. 기대 필드/데이터가 실제로 오는지
3. 후보 2-3개면 비교표(비용/품질/제한) → 사용자 승인
4. API key 없으면 deferred 금지 → 즉시 요청
5. 이 단계 건너뛰고 빌드 시작 **금지**

**Phase 1C 특히:** Google Cloud STT/TTS/Gemini 2.5 Flash 각각 실제 호출 → latency, 응답 shape, 한국어 STT 인식률, TTS 자연도, structured output 안정성 확인 **후** 코드.

---

## 5. E2E 검증

Phase 빌드 중에는 "3 actions마다 checkpoint"보다 이 규칙이 우선.

- 외부 API → 응답 → DB 저장 → UI 표시 **전체 흐름** 확인
- 실제 GCP 호출 + 실제 Supabase row (mock 아님)
- 타입체크 / 유닛테스트 통과만으로 검증 완료 처리 **금지**
- `/browse`(headed) 또는 Playwright MCP로 사용자가 실시간 확인 가능하게
- **모바일 폭 ~360px**에서 확인 (Pally MVP는 모바일 우선)
- 충분한 데이터로 (한 문장 말고 다양한 5축 분포)

---

## 6. Top 5 — 절대 지킨다

1. **외부 API는 코드 전에 실호출.** 스키마만 맞추고 넘어가지 않는다. (§4)
2. **"동작할 것이다"는 검증이 아니다.** 실제 출력 보여준다. (§5)
3. **에러 삼키지 않는다.** Empty `catch {}` 금지. `|| {}`, `?? []` 폴백 금지. 크래시가 침묵보다 낫다.
4. **`git add .` 금지.** 파일 개별 스테이징. `.env` / GCP JSON / Supabase service role 감지 시 즉시 중단.
5. **비즈니스 로직 추측 금지.** 모호하면 묻는다. auth / 결제 / 데이터 삭제는 확인 후 진행.

---

## 7. Code Rules

### TypeScript / Next.js (`frontend/`)

- TS strict. `any` 금지 (불가피하면 `// TODO: 사유`)
- 주석·변수명·함수명은 영어. 사용자 대화는 한국어
- 기본 Server Components. `'use client'`는 인터랙션/브라우저 API/훅 필요 시만
- 변이는 Server Actions. Route Handlers는 webhook/3rd-party만
- Tailwind + `cn()` 유틸 (문자열 연결 금지)
- Named export 선호. Default는 page/layout/route만
- 외부 입력(유저·API·URL params)은 **Zod로 boundary 검증**

### Python / FastAPI (`backend/`, `ai/`)

- Python 3.11. wire format은 **Pydantic v2**로 검증
- 루트 `ai/` import는 `sys.path` 조정 또는 `PYTHONPATH=.` (배포에도 반영)
- 동기 GCP client 기본. 비동기 필요하면 별도 ADR
- `backend/lib/supabase.py`는 service role — server only

### Error handling (공통)

- 에러 삼키지 않는다 (§6 #3 재강조)
- Server: 전체 에러 로그, Client: 안전한 메시지만
- Server Actions: `{ data, error }` 반환. 클라이언트로 throw 금지

### Supabase

- **모든 테이블 RLS 활성화. 예외 없음.**
- 정책은 `session_id` 기반 (익명 세션). `true` 정책 금지
- 마이그레이션 forward-only. 적용된 건 수정 금지, 새로 생성
- 클라이언트 = anon key, 서버 = service role
- 스키마 변경 후: `supabase gen types` → 타입 갱신 → 팀 채널 공지

### Git

- `git add .` **금지** (재강조)
- 커밋: imperative mood, 72자 이내, **왜(why)** 설명
- Branch: `gsd/phase-<N>-<slug>` (예: `gsd/phase-1a-fe-audio-shell`)
- `--no-verify` / `--force` 금지 (명시 허락 시만)
- Production = `main`. feature → main PR 머지로만

---

## 8. Deployment — `main`에 push하면 끝

| Surface | Platform | Root | Owner |
|---------|----------|------|-------|
| Frontend | **Vercel** (Git 자동 배포) | `frontend/` | 이찬희 |
| Backend | **Railway** (Git 자동 배포) | `backend/` | 백은혜 |

### Vercel

- `vercel deploy --prod` 수동 **금지** (Git 연동과 충돌)
- 환경변수 변경만 Vercel CLI 또는 dashboard
- 배포 상태/로그: **Vercel MCP** `list_deployments`, `get_deployment_build_logs`, `get_runtime_logs`

### Railway

- 공식 MCP 없음 → **`railway` CLI**:
  ```bash
  railway logs --tail              # 런타임 로그
  railway variables                # env 확인
  railway status                   # 배포 상태
  ```
- 필요 파일: `backend/Procfile` (`web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT`), `backend/runtime.txt` (`python-3.11.0`)
- 배포 후 Railway URL → `frontend/.env.local`의 `NEXT_PUBLIC_BACKEND_URL` 업데이트 + Vercel dashboard도 동기화

### 배포 후 체크

1. Vercel READY 확인 (MCP)
2. Railway healthy 확인 (`railway status`)
3. 모바일 브라우저에서 배포 URL 열어 rec → Pally 응답 흐름 1회
4. 실패 시 **로그 먼저 확인**. 추측 금지

---

## 9. 문서 저장 경로

| 종류 | 경로 |
|------|------|
| 프로젝트 진행 (gsd 자동 관리) | `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md` |
| Phase 작업 | `.planning/phases/<N>/PLAN.md`, `REVIEW.md`, `UI-SPEC.md` |
| ADR (아키텍처 결정) | `docs/adr/0001-*.md` (`TEMPLATE.md` 참조) |
| Plan 리뷰 / office-hours | `docs/plan/{YYYY-MM-DD}-{feature}-*.md` |
| Design system | `DESIGN.md` (루트) + `docs/design/` |
| Code 컨벤션 | `docs/code-convention.md` |
| 팀 그라운드룰 · 셋업 가이드 | `docs/shared/` |

**Source of truth: `.planning/ROADMAP.md`** — 충돌 시 ROADMAP 우선. `docs/_archive/`는 참조용.

ADR은 **세션당 최대 3개**. 나머지는 PLAN.md에 "Minor Decision:" 인라인.

---

## 10. NEVER / ALWAYS

### NEVER

- `mcp__claude-in-chrome__*` — `/browse` 또는 Playwright MCP 사용
- `git add .` — 개별 스테이징만
- `.env*`, GCP service account JSON, Supabase `service_role` 커밋
- `--no-verify`, `--force push` (명시 허락 시만)
- `vercel deploy --prod` 수동 (Git 연동 사용)
- Empty `catch {}`, silent fallback (`|| {}`, `?? []`)
- "동작할 것이다" 식 미검증 완료 보고
- README.md / ARCHITECTURE.md / 문서 자동 생성 (요청 없으면)
- 코드 · 커밋 메시지에 이모지
- 현재 task와 무관한 리팩토링
- 새 의존성 사전 보고 누락
- 비즈니스 로직 추측 (모호하면 묻기)
- `feedback` 별도 page 만들기 (MVP는 inline payload만)
- OpenAI / Whisper / GPT-4o 호출 (MVP는 GCP 단일)

### ALWAYS

- 세션 시작 시 `git pull` + `/gsd-progress`
- 기존 코드 패턴 매칭 (재발명 금지)
- 외부 API 코드 전 실호출 (§4)
- E2E는 실제 모바일 + 실제 데이터 (§5)
- auth / 결제 / 데이터 삭제는 사용자 확인 후
- 3회 실패 시 stop & reassess
- gsd 작업 중 짧게 보고 (silent 금지)
- 디렉토리 경계 지키기 (§1)

---

## 11. AI 에이전트별 차이

- **Claude Code**: 기본. 이 파일 + `docs/code-convention.md` + `DESIGN.md`(있으면) 매 세션 로드
- **Codex CLI**: `AGENTS.md`(이 파일 symlink)를 읽음. 주로 `/codex review`, `/codex challenge`로 2차 검토. Claude가 이미 만든 패턴과 충돌하면 **Claude 패턴 우선** (일관성)
- **Cursor / 기타**: 같은 규칙. 도구별 차이 있으면 이 파일 우선

---

*Last updated: 2026-05-21 · synchronized to `.planning/ROADMAP.md` (June 7 demo)*
