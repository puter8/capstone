# Pally — CharaShift MVP

> 대화 진행에 따라 성격이 변하는 AI 캐릭터와의 정서적 유대감 기반 영어 회화 학습 지속 서비스

이화여대 캡스톤 디자인 (산학 트랙) · 팀명 **퓨터(puter8)** · 지도교수 심재형 · 2026-06-07 데모

---

## 데모 (Live)

| Surface | URL | 상태 |
|---|---|---|
| 데모 영상 | https://youtu.be/Ptlq6SM4C6g?si=ShOETKqPAWakxxjb | YouTube |
| Frontend (Vercel) | https://capstone-eight-virid.vercel.app/home | 200 OK |
| Backend (Railway) | https://capstone-production-e8c2.up.railway.app | `/api/health` 200 OK |

> **모바일 폭 ~360px**에 최적화되어 있습니다. 데스크톱 브라우저는 반드시 개발자 도구의 모바일 뷰로 열어 주세요.

### 데모에서 확인할 수 있는 흐름

1. 홈 화면에서 마이크 버튼(rec)을 누르면 브라우저 권한 요청 후 녹음 시작
2. 영어로 한 문장 말하기 → STT(Google Cloud) → Gemini 2.5 Flash 응답
3. 발화 텍스트가 5축으로 분석되고 → CHARACTER MATRIX 통과 → Pally 외형과 말투가 즉시 변함
4. 응답은 TTS로 자연 음성 재생, 화면 하단에는 한국어 인라인 힌트가 표시됨
5. 우상단 X로 세션 종료 시 누적 점수가 반영된 최종 Pally 모습을 공개

---

## 팀

| 이름 | 역할 |
|------|------|
| 최윤서 | PM · 기획 · QA |
| 백은혜 | BE · AI 파이프라인 (FastAPI · GCP STT/TTS · Gemini · Supabase) |
| 김민주 | AI 엔진 · Pally 렌더러 (5축 분석 · CHARACTER MATRIX · Canvas2D) |
| 이찬희 | FE · 디자인 (Next.js 14 · 메인/오디오 셸 · 디자인 시스템) |

---

## 문제와 솔루션 한 줄

- 해결하려는 문제: 기존 영어 회화 서비스는 사용자 말투와 대화 성향을 충분히 반영하지 못해 대화가 획일적으로 느껴질 수 있습니다.
- 기술 솔루션: 사용자 발화를 5개 축으로 수치화한 뒤, CHARACTER MATRIX 연산으로 AI 캐릭터 파라미터로 변환합니다. EMA 설정을 통해 Pally의 성격 변화율을 안정적으로 유지합니다.
- 기대 효과: 사용자 스타일이 반영되는 더 몰입감 있는 회화 경험을 제공하여 사용자가 향후 실제 AI 대화 시스템과 연결 가능한 핵심 엔진을 확보합니다.
- MVP 핵심기술: `사용자 발화 스타일 -> 5축 점수 -> CHARACTER MATRIX -> 캐릭터 반응 성격`

- **입력 5축**: `Formality` · `Energy` · `Intimacy` · `Humor` · `Curiosity`
- **출력 캐릭터 파라미터**: `tone_casual` · `energy_level` · `humor_level`
- **변환 로직**: 규칙 기반 5축 분석 → 가중합 행렬(CHARACTER MATRIX) → EMA 보정 → 파라미터 → Canvas2D Superformula 렌더링

영어 회화 학습 서비스는 보통 질문에 답하는 기능 자체는 제공하지만, 사용자의 말투와 친밀도, 에너지 수준, 질문 성향까지 세밀하게 반영하는 경우는 많지 않습니다. 그 결과 사용자는 "나에게 맞춘 대화"보다 "정해진 챗봇 응답"을 받는 느낌을 받기 쉽습니다.

자세한 설계 근거는 [`docs/mvp/PRD.md`](docs/mvp/PRD.md) 와 [`docs/mvp/2026-05-midterm-qa.md`](docs/mvp/2026-05-midterm-qa.md) 참고.

---

## 주요 기능

- **음성 입력/출력** — 브라우저 마이크 → Google Cloud Speech-to-Text(EN) → Gemini 2.5 Flash → Google Cloud Text-to-Speech(EN) → 즉시 재생
- **CHARACTER MATRIX 엔진** — 발화 1턴마다 5축 점수를 다시 계산하고, EMA(alpha=0.7)로 부드럽게 누적해 캐릭터 파라미터에 반영
- **Pally 실시간 변형** — Canvas2D Superformula 도형이 형태·색·표정으로 5축 변화를 시각화
- **인라인 한국어 힌트** — Gemini가 사용자 발화에서 어색한 영어를 감지하면 화면에 한국어 설명/교정/대안 표현을 표시
- **세션 종료 컷신** — X 버튼으로 세션 종료 시 누적된 변화가 적용된 최종 Pally를 공개
- **익명 세션** — Supabase `sessions` / `messages` 테이블에 세션 ID 기반으로 모든 턴·5축·캐릭터 파라미터를 JSONB로 저장. RLS는 `session_id` 기준

## 기술 솔루션

현재 MVP의 핵심은 `CHARACTER MATRIX 엔진`입니다.

---

1. 사용자 발화를 입력받습니다.
2. 발화에서 언어적 특징을 추출해 5개 축 점수를 계산합니다.
3. CHARACTER MATRIX가 이 점수를 캐릭터 파라미터로 변환합니다.
4. 변환된 파라미터에 따라 AI 캐릭터의 말투와 반응 스타일이 달라집니다.
5. 변화된 스타일에 맞추어 사용자와 대화, 피드백이 진행됩니다.

### 최종 MVP 소프트웨어는 무엇인가

이 프로젝트의 최종 MVP는 사용자가 영어 문장을 입력하면, 시스템이 그 발화 스타일을 분석하고 이에 맞춰 AI 캐릭터의 반응 성격이 달라지는 `웹 기반 영어 회화 프로토타입`입니다.

예를 들어,

- 캐주얼하고 친한 말투를 사용하면 더 편하고 친근한 캐릭터 반응이 나옵니다.
- 격식 있는 문장을 쓰면 더 정중하고 차분한 반응이 나옵니다.
- 질문이 많은 발화는 탐구형 대화로 이어질 가능성이 높아집니다.
- 유머 성향이 높은 발화는 더 가볍고 장난기 있는 반응으로 연결될 수 있습니다.
- 자연스럽게 사용자의 실수를 교정하도록 AI 대화방식을 설정하여 학습에 필요한 피드백을 받을 수 있습니다.

### 입력 5축

- `Formality`: 격식도
- `Energy`: 에너지
- `Intimacy`: 친밀도
- `Humor`: 유머 성향
- `Curiosity`: 탐구 성향

### 출력 캐릭터 파라미터

- `tone_casual`: 캐주얼한 말투 정도
- `energy_level`: 응답의 활발함
- `humor_level`: 유머러스한 반응 정도

## 왜 이 기술이 핵심기술인가

이 프로젝트의 고유핵심기술은 특정 외부 AI 모델 호출이 아니라, `사용자 발화 스타일을 구조화된 수치로 바꾸고 다시 캐릭터 성격으로 변환하는 로직`입니다.

- 단순한 프롬프트 엔지니어링이 아니라, 입력과 출력 사이에 자체 설계한 변환 구조가 있습니다.
- 사용자의 발화 특징이 어떤 방식으로 결과에 반영되는지 설명하기 쉽습니다.
- 테스트 코드로 실제 실행 과정을 직접 보여줄 수 있습니다.
- 향후 LLM, UI, 시각 캐릭터 시스템과 연결해도 중심 엔진으로 유지될 수 있습니다.

## 기대 성과와 사용자 효능

- 사용자 말투가 반영된 응답을 받아 더 개인화된 회화 경험을 느낄 수 있습니다.
- 고정형 챗봇보다 덜 딱딱하고 더 몰입감 있는 상호작용이 가능합니다.
- 향후 학습 피드백, 캐릭터 시각화, 장기 사용자 상태 저장과 연결하면 더 확장성 있는 회화 학습 시스템으로 발전할 수 있습니다.

## 현재 저장소에서 구현된 범위

### 현재 구현됨

**AI 엔진 (`ai/`)**
- 규칙 기반 5축 발화 분석기 (`analyzer.py`)
- CHARACTER MATRIX 가중합 + EMA 보정 (`matrix_engine.py`)
- 25개 수작업 라벨 데이터셋 (`data/dataset.py`)
- 전체 파이프라인 데모 스크립트 (`tests/test_matrix.py`)
- CHARACTER MATRIX 시각화 HTML 프로토타입 (`assets/visualizer.html`)

**Backend (`backend/`, FastAPI · Railway 배포 중)**
- `POST /api/stt` — Google Cloud Speech-to-Text 실호출 (영어)
- `POST /api/chat` — 5축 분석 + Gemini 2.5 Flash 응답 + 인라인 한국어 힌트(structured payload) + 캐릭터 파라미터
- `POST /api/tts` — Google Cloud Text-to-Speech 실호출 (base64 오디오)
- `POST /api/feedback` — 발화 표현 교정 / 대안 표현
- `GET /api/health` — 헬스 체크
- Supabase service-role 클라이언트로 `sessions` / `messages` 테이블에 모든 턴 영속화

**Frontend (`frontend/`, Next.js 14 App Router · Vercel 배포 중)**
- 메인 홈 화면 (rec 버튼 · 채팅 영역 · 인라인 한국어 힌트) — 모바일 폭 ~360px 최적화
- 브라우저 마이크 녹음 → `/api/stt` → `/api/chat` → `/api/tts` 자동 재생 E2E 연결
- Canvas2D Superformula Pally 렌더러 (5축 → 형태·색·표정 변형)
- Listening / Thinking UI 상태, ChatBubble + LongBubble (X 닫기 포함)
- 세션 종료 컷신 — 우상단 X로 누적 변화 반영된 최종 Pally 공개
- GNB 라우팅 (home · history · my · ranking) + `/dev/pally` 렌더러 테스트 화면
- Supabase anon 클라이언트, Zod boundary 검증

**Database (`supabase/migrations/`)**
- `sessions` / `messages` 테이블 forward-only 마이그레이션
- `session_id` 기반 RLS 정책 (익명 세션)

**Infra**
- Vercel (FE) + Railway (BE) — `main` push 시 자동 배포
- 데모 URL 두 곳 모두 200 OK (헬스 체크 통과)

### 향후 확장 예정

- LLM 기반 축 분석기 보완 또는 대체 (현재는 규칙 기반)
- 사용자별 장기 상태 저장 (Supabase pgvector)
- 슬랭 RAG 파이프라인 (Reddit PRAW)
- 학습 효과 추적 / 사용자 인증


## 폴더 구조

```text
capstone/
├─ frontend/                  Next.js 14 App Router 앱 (Vercel)
│  ├─ app/
│  │  ├─ home/                메인 화면 (rec 버튼 · Pally · 인라인 힌트)
│  │  ├─ history/             대화 기록
│  │  ├─ my/                  마이페이지
│  │  ├─ ranking/             랭킹
│  │  ├─ dev/                 개발용 화면 (Pally 렌더러 테스트 등)
│  │  └─ api/health/          FE 헬스 라우트
│  ├─ components/
│  │  ├─ audio/               TalkButton, 녹음 상태 UI
│  │  ├─ chat/                ChatBubble, MessageRow
│  │  └─ pally/               Canvas2D Superformula 렌더러
│  ├─ lib/                    타입(`Message`, `Session`), Supabase 클라이언트, mock transport
│  └─ .env.example
│
├─ backend/                   FastAPI 백엔드 (Railway)
│  ├─ main.py                 /api/stt · /api/chat · /api/tts · /api/feedback · /api/health
│  ├─ lib/supabase.py         service-role Supabase 클라이언트 (서버 전용)
│  ├─ Procfile · runtime.txt  Railway 배포 설정
│  └─ .env.example
│
├─ ai/                        AI 핵심 엔진 (FE/BE 모두에서 import)
│  ├─ analyzer.py             규칙 기반 5축 발화 분석기
│  └─ matrix_engine.py        CHARACTER MATRIX 가중합 + EMA 보정
│
├─ data/dataset.py            25개 수작업 라벨 예문 (엔진 검증용)
├─ tests/test_matrix.py       엔진 전체 파이프라인 데모 스크립트
├─ assets/visualizer.html     CHARACTER MATRIX 시각화 프로토타입
│
├─ supabase/migrations/       sessions / messages 테이블 + RLS (forward-only)
│
├─ docs/
│  ├─ mvp/                    MVP 스펙 (PRD, 중간발표 Q&A)
│  ├─ final/                  전체 제품 기획 (Ideation, Implementation_Plan, Project Briefs 등)
│  ├─ shared/                 팀 그라운드 룰, 셋업 가이드, PMF 분석
│  ├─ plan/                   날짜별 plan 리뷰
│  ├─ adr/                    아키텍처 결정 기록
│  ├─ design/                 디자인 문서
│  └─ qa/                     데모 직전 QA 체크리스트
│
├─ .planning/                 gsd 워크플로 산출물 (PROJECT/REQUIREMENTS/ROADMAP/STATE + phases/)
├─ CLAUDE.md                  팀 + AI 에이전트 공용 가이드 (AGENTS.md symlink)
└─ DESIGN.md                  디자인 시스템 명세
```

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Next.js 14 (App Router) · React 18 · TypeScript · Tailwind CSS · Canvas2D + Superformula |
| Backend | FastAPI · Python 3.11 · Pydantic v2 · httpx |
| AI | Google Cloud STT/TTS · Gemini 2.5 Flash (Google AI Studio) · 자체 5축 분석기(Python) |
| Database | Supabase (PostgreSQL · Auth · RLS) |
| Infra | Vercel (FE) · Railway (BE) — 둘 다 `main` push로 자동 배포 |

---

## 로컬 실행

### 사전 준비

- Node.js 20+ / npm
- Python 3.11
- Supabase 프로젝트 (또는 팀 공유 ID 사용)
- Google Cloud API key (Speech-to-Text, Text-to-Speech) + Gemini API key (AI Studio)

자세한 키 발급/MCP 설정은 [`docs/shared/SETUP.md`](docs/shared/SETUP.md) 참고.

### 1) Frontend

```bash
cd frontend
cp .env.example .env.local
# .env.local 작성:
#   NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
#   NEXT_PUBLIC_SUPABASE_URL=...
#   NEXT_PUBLIC_SUPABASE_ANON_KEY=...
npm install
npm run dev          # http://localhost:3000 → 자동 redirect /home
```

### 2) Backend

```bash
cd backend
cp .env.example .env
# .env 작성: GOOGLE_AI_API_KEY · GOOGLE_CLOUD_API_KEY · SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# 헬스 체크: curl http://localhost:8000/api/health → {"status":"ok"}
```

### 3) 엔진만 단독 실행 (백엔드/프론트 없이 빠르게 확인)

```bash
# 저장소 루트에서
python tests/test_matrix.py
```

입력 문장별 5축 결과와 캐릭터 파라미터가 콘솔에 출력됩니다. 시각화는 `assets/visualizer.html`을 브라우저로 열어 확인하세요.

---

## API 개요

Backend (`backend/main.py`) 가 노출하는 엔드포인트:

| Method · Path | 역할 |
|---|---|
| `GET /api/health` | 헬스 체크 |
| `POST /api/stt` | 녹음 오디오(`multipart/form-data`) → Google Cloud STT → 영어 텍스트 |
| `POST /api/chat` | 사용자 발화 텍스트 → 5축 분석 + Gemini 응답 + 인라인 한국어 힌트 + 캐릭터 파라미터 |
| `POST /api/tts` | 영어 응답 텍스트 → Google Cloud TTS → base64 오디오 |
| `POST /api/feedback` | 발화 1턴에 대한 표현 교정 / 대안 표현 |

상세 스키마는 [`backend/README_API.md`](backend/README_API.md) 참고.

---

## 엔진 실험 결과

`python tests/test_matrix.py` 실행 시 입력 스타일이 캐릭터 파라미터로 어떻게 이어지는지 직접 재현할 수 있습니다.

캐주얼 발화 (`yo what's up lol, u wanna hang or nah?`)
```text
Formality: 0   Energy: 58   Intimacy: 48   Humor: 38   Curiosity: 27
tone_casual: 69   energy_level: 57   humor_level: 38
```

격식 발화 (`I would like to formally inquire about the implications of this matter.`)
```text
Formality: 83  Energy: 30   Intimacy: 0    Humor: 0    Curiosity: 30
tone_casual: 16   energy_level: 39   humor_level: 13
```

질문 중심 발화 (`Why do you think people struggle with English conversation?`)
```text
Formality: 38  Energy: 30   Intimacy: 20   Humor: 10   Curiosity: 51
tone_casual: 40   energy_level: 43   humor_level: 21
```

분류 정확도 자체보다 **입력 스타일 변화 → 5축 변화 → 캐릭터 변화**의 연결성을 재현 가능하게 보이는 것이 이 실험의 목적입니다.

---

## 한계와 향후 확장

- 5축 분석기는 규칙 기반이라 문맥 이해에 한계가 있음 → LLM 기반 분석기로 보완 예정
- 데이터셋이 25개로 작음 → Reddit PRAW 기반 슬랭 RAG 파이프라인 도입 예정
- 사용자 학습 효과는 본 MVP 범위에 포함되지 않음 → 장기 사용자 상태 저장(Supabase pgvector) 후 검증 예정

---

## 라이선스 / 문의

학내 캡스톤 산학 프로젝트 산출물. 외부 사용 문의는 팀 PM(최윤서, imyure@ewhain.net)으로.
