# Pally — One-Time Setup Guide

> 처음 1회만 따라하면 됨. 매 세션 워크플로우는 `CLAUDE.md` 참조.
---

## 1. Local Tools

| Tool | Version | 누가 쓰나 |
|------|---------|----------|
| Node.js | 20+ | frontend (이찬희·김민주) |
| pnpm | latest | frontend deps |
| Python | 3.11 | backend·ai (백은혜·김민주) |
| gcloud CLI | latest | GCP STT/TTS/Vertex (백은혜) |
| Railway CLI | latest | backend 배포 로그 (백은혜) |
| Vercel CLI | latest | env vars only (이찬희) |
| Claude Code | latest | 메인 에이전트 (전원) |

설치 — macOS 기준:

```bash
brew install node python@3.11 pnpm
brew install --cask google-cloud-sdk
npm i -g @railway/cli vercel
```

Claude Code 본체는 공식 가이드대로 설치: <https://docs.claude.com/claude-code>.

---

## 2. 스킬 - gsd + gstack 설치

이 프로젝트는 **별개의 두 번들**을 모두 깐다. 둘은 다른 repo, 다른 install 명령. 하나만 깔면 다른 쪽 슬래시 명령은 안 뜸.

- **gsd** (`gsd-build/get-shit-done`) — phase 워크플로우. `/gsd-discuss-phase`, `/gsd-plan-phase`, `/gsd-execute-phase`, `/gsd-verify-work`, `/gsd-ship` 등. **메인**.
- **gstack** (`garrytan/gstack`) — 보조 도구. `/browse`, `/codex`, `/qa`, `/design-review`, `/investigate` 등.

### gsd 설치

https://github.com/gsd-build/get-shit-done
링크를 복사하고 클로드나 코덱스에게 깔아달라고 하기

### gstack 설치

https://github.com/garrytan/gstack
링크를 복사하고 클로드나 코덱스에게 깔아달라고 하기

### 확인

Claude Code를 새로 띄우고 `/`를 치면 자동완성에 **양쪽 다** 떠야 함:

- gsd: `/gsd-help`, `/gsd-progress`, `/gsd-plan-phase` ...
- gstack: `/browse`, `/codex`, `/ship`, `/gstack-upgrade` ...

한쪽만 보이면 그쪽만 깔린 상태. 빠진 쪽 다시 설치.

**버전 동기화:** PM이 "이번 주는 gstack v1.X 쓰자"라고 공지하면 `/gstack-upgrade`로 올림. 팀원 간 버전이 어긋나면 같은 명령이 다르게 동작할 수 있음. gsd도 동일 — 같은 시점에 다 같이 `npx get-shit-done-cc@latest`.

**Codex CLI 사용자만:** `AGENTS.md`(=`CLAUDE.md` symlink)를 자동으로 읽음. 별도 작업 없음. gsd는 `npx` 실행 시 runtime으로 Codex를 같이 선택. MCP는 `~/.codex/config.toml`에 §3과 같은 4개 서버 등록.

---

## 3. MCP 연결

repo 루트의 `.mcp.json`에 4개 서버(`supabase`, `vercel`, `github`, `figma`)가 정의되어 있음. `git pull`로 받으면 Claude Code가 자동 인식. **`claude mcp add` 직접 칠 필요 없음.**

```bash
claude mcp list                  # 4개 떠야 함
```

각 MCP를 **처음 호출하면 OAuth 브라우저 플로우 → 본인 계정 로그인**. 이건 한 번만.

**Figma만 추가 조건:** Figma Desktop 앱이 실행 중이어야 작동 (port 3845).

**Railway는 공식 MCP 없음** → `railway` CLI 사용 (CLAUDE.md §7 참조).

**공유 리소스 — PM에게 초대 요청해야 보임:**
- Supabase org `puter8` → 프로젝트 `capstone` (`orhodalbxhbzlvjsqalu`, ap-northeast-1)
- GitHub repo `puter8/capstone`
- Vercel team: TBD (셋업 후 갱신)
- Railway project: TBD

---

## 4. GCP 인증

PM이 GCP project `capstone-puter8`을 만들고 전원을 Owner로 초대해뒀음. Phase 2 통합 디버깅(GCP 로그 조회, 응답 shape 확인 등)에 전원이 필요하니까 **각자 본인 컴퓨터에서 인증 3줄**:

```bash
gcloud auth login                              # 본인 Google 계정 로그인
gcloud auth application-default login          # 로컬 dev용 ADC
gcloud config set project capstone-puter8
```

> 모르겠으면 Claude / Codex에게 "gcloud 셋업 도와줘"라고 하면 됨.

**API 활성화 / Service account 생성 / JSON 키 발급 / Railway 환경변수 등록**은 Phase 1C의 첫 task로 진행한다 (`.planning/ROADMAP.md` Phase 1C Task order 참조).

---

## 5. 환경 변수

```bash
cp frontend/.env.example frontend/.env.local
cp backend/.env.example  backend/.env
```

**필수 키:**

`frontend/.env.local` (Vercel root):
- `NEXT_PUBLIC_BACKEND_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

`backend/.env` (Railway root):
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` (base64)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

**키 추가 시 4단계 (전원 따름):**
1. 해당 `.env.example` 업데이트 (값 비우고 키만)
2. Notion 비공개 페이지에 실제 값
3. Vercel/Railway dashboard 동기화
4. 팀 채널 한 줄 공지 ("backend에 X 추가했어요")

**금지:** `.env*`, GCP service account JSON, Supabase `service_role` 커밋. `git add .` 절대 금지 (개별 스테이징만).

---

## 6. 첫 동작 확인

```bash
python tests/test_matrix.py                  # 5축 엔진 OK 확인 (전원)
cd frontend && pnpm install && pnpm dev      # /api/health 200 (Phase 0 완료 후)
```

Claude Code 안에서 `/gsd-progress` 실행 → 현재 phase + 다음 액션이 출력되면 셋업 완료.

---

*Last updated: 2026-05-21*
