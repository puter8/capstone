# CHARACTER MATRIX

> GitHub description: `Utterance-style analysis engine for personalized English conversation`

CHARACTER MATRIX는 사용자 영어 발화의 스타일을 5개 축으로 분석하고, 그 결과를 AI 캐릭터의 반응 성격 파라미터로 변환하는 개인화 영어 회화 시스템의 핵심 엔진 MVP입니다.

현재 저장소는 완성형 서비스 전체보다 `핵심 엔진의 구현과 검증`에 초점을 둡니다. 즉, 규칙 기반 발화 분석기, CHARACTER MATRIX 연산, 테스트 코드, 시각화 프로토타입을 통해 "사용자 발화 스타일이 실제 캐릭터 반응 변화로 이어지는가"를 재현 가능하게 보여주는 레포입니다.

---

## 팀 구성

**팀명:** 퓨터 · **트랙:** 산학 · **지도교수:** 심재형 교수님

| 이름 | 역할 |
|------|------|
| 최윤서 | PM · 기획 · QA |
| 백은혜 | AI 엔진 · 데이터 파이프라인 |
| 김민주 | 백엔드 (FastAPI · Supabase) |
| 이찬희 | 프론트엔드 · 디자인 (Next.js · Canvas2D) |

---

## 프로젝트 한눈에 보기

- 해결하려는 문제: 기존 영어 회화 서비스는 사용자 말투와 대화 성향을 충분히 반영하지 못해 대화가 획일적으로 느껴질 수 있습니다.
- 기술 솔루션: 사용자 발화를 5개 축으로 수치화한 뒤, CHARACTER MATRIX 연산으로 AI 캐릭터 파라미터로 변환합니다. EMA 설정을 통해 Pally의 성격 변화율을 안정적으로 유지합니다.
- 기대 효과: 사용자 스타일이 반영되는 더 몰입감 있는 회화 경험을 제공하여 사용자가  향후 실제 AI 대화 시스템과 연결 가능한 핵심 엔진을 확보합니다.
- MVP 핵심기술: `사용자 발화 스타일 -> 5축 점수 -> CHARACTER MATRIX -> 캐릭터 반응 성격`

## 문제 정의

영어 회화 학습 서비스는 보통 질문에 답하는 기능 자체는 제공하지만, 사용자의 말투와 친밀도, 에너지 수준, 질문 성향까지 세밀하게 반영하는 경우는 많지 않습니다. 그 결과 사용자는 "나에게 맞춘 대화"보다 "정해진 챗봇 응답"을 받는 느낌을 받기 쉽습니다. 때문에 사용자는 실제 회화 경험에서 얻을 수 있는 자연스러운 표현과 금세 서비스에서 이탈하게됩니다.

이 프로젝트는 이러한 한계를 해결하기 위해, 사용자의 발화 스타일을 정량적으로 분석하고 그 결과를 AI 캐릭터의 반응 방식에 반영하는 구조를 제안합니다.


## 주요 기능

- **음성 입력/출력** — 브라우저 마이크 → Google Cloud Speech-to-Text(EN) → Gemini 2.5 Flash → Google Cloud Text-to-Speech(EN) → 즉시 재생
- **CHARACTER MATRIX 엔진** — 발화 1턴마다 5축 점수를 다시 계산하고, EMA(alpha=0.7)로 부드럽게 누적해 캐릭터 파라미터에 반영
- **Pally 실시간 변형** — Canvas2D Superformula 도형이 형태·색·표정으로 5축 변화를 시각화
- **인라인 한국어 힌트** — Gemini가 사용자 발화에서 어색한 영어를 감지하면 화면에 한국어 설명/교정/대안 표현을 표시


## 기술 솔루션


현재 MVP의 핵심은 `CHARACTER MATRIX 엔진`입니다.

시스템은 다음 순서로 동작합니다.

1. 사용자 발화를 입력받습니다.
2. 발화에서 언어적 특징을 추출해 5개 축 점수를 계산합니다.
3. CHARACTER MATRIX가 이 점수를 캐릭터 파라미터로 변환합니다.
4. 변환된 파라미터에 따라 AI 캐릭터의 말투와 반응 스타일이 달라집니다.
5. 변화된 스타일에 맞추어 사용자와 대화, 피드백이 진행됩니다.

### 최종 MVP 소프트웨어는 무엇인가

이 프로젝트의 최종 MVP는 사용자가 영어 문장을 입력하면, 시스템이 그 발화 스타일을 분석하고 이에 맞춰 AI 캐릭터의 반응 성격이 달라지는 `웹 기반 영어 회화 프로토타입`입니다.

즉, 사용자는 단순히 질문에 대한 정답형 답변을 받는 것이 아니라, 자신의 말투와 대화 성향이 반영된 응답을 받게 됩니다.

예를 들어,

- 캐주얼하고 친한 말투를 사용하면 더 편하고 친근한 캐릭터 반응이 나옵니다.
- 격식 있는 문장을 쓰면 더 정중하고 차분한 반응이 나옵니다.
- 질문이 많은 발화는 탐구형 대화로 이어질 가능성이 높아집니다.
- 유머 성향이 높은 발화는 더 가볍고 장난기 있는 반응으로 연결될 수 있습니다.
- 단순 대화에 더해 자연스럽게 사용자의 실수를 교정하도록 AI 대화방식을 설정하여 학습에 필요한 피드백을 받을 수 있습니다.

즉, 이 소프트웨어는 "영어 문장을 이해하는 AI"를 넘어서, "사용자의 대화 스타일에 반응하는 AI 캐릭터"를 구현하는 것을 목표로 합니다.

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

이 프로젝트의 고유핵심기술은 특정 외부 AI 모델 호출이 아니라, `사용자 발화 스타일을 구조화된 수치로 바꾸고 다시 캐릭터 성격으로 변환하는 로직` 입니다.

이 기술이 핵심인 이유는 다음과 같습니다.

- 단순한 프롬프트 엔지니어링이 아니라, 입력과 출력 사이에 자체 설계한 변환 구조가 있습니다.
- 사용자의 발화 특징이 어떤 방식으로 결과에 반영되는지 설명하기 쉽습니다.
- 테스트 코드로 실제 실행 과정을 직접 보여줄 수 있습니다.
- 향후 LLM, UI, 시각 캐릭터 시스템과 연결해도 중심 엔진으로 유지될 수 있습니다.

## 기대 성과와 사용자 효능

이 프로젝트의 기대 성과는 단순히 기술 데모를 만드는 데 있지 않습니다. 실제로는 사용자가 영어 회화를 더 자연스럽고 오래 지속할 수 있도록 돕는 것이 목표입니다.

구체적인 사용자 효능은 다음과 같습니다.

- 사용자 말투가 반영된 응답을 받아 더 개인화된 회화 경험을 느낄 수 있습니다.
- 고정형 챗봇보다 덜 딱딱하고 더 몰입감 있는 상호작용이 가능합니다.
- 사용자는 같은 주제라도 자신의 표현 방식에 따라 달라지는 반응을 경험할 수 있습니다.
- 향후 학습 피드백, 캐릭터 시각화, 장기 사용자 상태 저장과 연결하면 더 확장성 있는 회화 학습 시스템으로 발전할 수 있습니다.

즉, 기대효과는 "정답을 알려주는 시스템" 하나를 더 만드는 것이 아니라, `사용자의 발화 스타일을 반영해 회화 경험 자체를 개인화하는 소프트웨어`를 만드는 데 있습니다.

## 현재 저장소에서 구현된 범위

### 현재 구현됨

- 규칙 기반 5축 발화 분석기
- CHARACTER MATRIX 가중합 연산
- EMA 기반 점수 완화 로직
- 수작업 라벨 데이터셋
- 테스트 및 데모 스크립트
- 시각화 HTML 프로토타입

### 향후 확장 예정

- LLM 기반 축 분석기 보완 또는 대체
- 실제 대화형 프론트엔드 (Next.js 14 + Canvas2D Superformula)
- 사용자별 상태 저장 (Supabase pgvector)
- 실시간 대화 UI 및 캐릭터 애니메이션 연동
- 슬랭 RAG 파이프라인 (Reddit PRAW)

## 핵심 실험과 결과

이 저장소는 핵심기술을 설명에만 그치지 않고, 직접 실행 가능한 형태로 검증합니다.

### 실험 목적

- 발화 스타일 차이가 실제로 다른 5축 점수로 계산되는지 확인
- 계산된 점수가 CHARACTER MATRIX를 통해 다른 캐릭터 파라미터로 변환되는지 확인
- 그 결과가 응답 스타일 변화로 이어지는지 확인

### 실행 방법

Python 3.10+ 환경에서 아래 명령어를 실행합니다.

```bash
python tests/test_matrix.py
```

### 실행 시 확인되는 내용

- 입력 문장별 5축 분석 결과
- 가중합 행렬 연산 결과
- 계산된 캐릭터 파라미터
- 캐릭터 파라미터에 따른 응답 스타일 변화
- 시각화 파일 경로

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

### 현재 결과 해석

현재 모델은 소규모 규칙 기반 프로토타입이기 때문에 정답 라벨과 완전히 일치하지는 않습니다. 그러나 문장 스타일의 차이를 구분하고, 그 차이를 캐릭터 파라미터 변화로 연결하는 기본 흐름은 재현 가능합니다.

추가로, 현재 결과는 "정답을 완벽히 맞춘다"보다 "스타일 차이를 안정적으로 구분하고, 그 차이를 캐릭터 반응 변화로 연결한다"는 점을 보여주는 데 의미가 있습니다. 즉, 이 MVP의 실험 목적은 분류 정확도 자체보다 `입력 스타일 변화 -> 수치 변화 -> 캐릭터 변화`의 연결성을 검증하는 것입니다.

즉, 이 저장소는 최종 성능을 주장하는 레포가 아니라, `핵심 아이디어가 실제 코드로 작동하는지 검증하는 MVP 실험 레포`입니다.

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


## 파일별 설명

### 핵심 엔진 (`ai/`)

- `ai/analyzer.py`
  영어 발화를 규칙 기반으로 분석하여 5축 점수를 산출합니다.

- `ai/matrix_engine.py`
  5축 점수를 CHARACTER MATRIX에 통과시켜 캐릭터 파라미터를 계산합니다. EMA 보정 로직도 포함합니다.

### 데이터 (`data/`)

- `data/dataset.py`
  25개의 수작업 라벨 예문 데이터셋입니다. 분석기 검증과 시연 예시로 사용됩니다.

### 테스트 및 시연

- `tests/test_matrix.py`
  전체 데모 실행 파일입니다. 분석 결과, 행렬 연산, 응답 예시를 한 번에 확인할 수 있습니다.

- `assets/visualizer.html`
  CHARACTER MATRIX 결과를 시각적으로 보여주는 시각화 프로토타입입니다.

### 문서

- `docs/mvp/PRD.md`
  June 7 데모 기준 MVP 기능 명세서입니다.

- `docs/mvp/2026-05-midterm-qa.md`
  중간발표 Q&A와 설계 결정(콜드 스타트, 페르소나 제어, 비용 구조 등)을 정리한 문서입니다.

- `docs/final/`
  전체 제품 비전·풀스코프 기획 문서(Ideation, Implementation_Plan, Project Briefs, 2026-05-development-plan, Design_Document)를 보관한 디렉토리입니다. MVP 이후 단계에서 참조합니다.

- `docs/shared/COMPETITIVE_ANALYSIS.md`
  경쟁 서비스 분석 및 차별화 전략 문서입니다.

- `docs/shared/AI transparency report.md`
  AI 투명성 보고서입니다.

- `docs/shared/Team_Ground_Rule.md`
  팀 그라운드 룰 문서입니다.

- `docs/shared/elevator_speech.md`
  Pally 제품 한 줄 소개 및 짧은 피치 문서입니다.

## 사용 기술

### 현재 구현 (MVP 핵심 엔진)

- Python 3.10+
- Rule-based NLP (키워드 딕셔너리 + 정규식 패턴 매칭)
- Weighted matrix transformation (5축 → 캐릭터 파라미터 가중합 변환)
- EMA smoothing (지수이동평균 기반 성격 누적)
- HTML/Canvas 기반 시각화 프로토타입

### 전체 서비스 목표 아키텍처 (2026.10 목표)

| 구분 | 기술 |
|------|------|
| Frontend | Next.js 14, Canvas2D + Superformula, Zustand |
| Backend | FastAPI |
| Database & Auth | Supabase (PostgreSQL · Auth · RLS · pgvector) |
| AI | GPT-4o (캐릭터 응답 생성) |
| Data Pipeline | Reddit PRAW (슬랭 데이터 수집) |
| Infra | Vercel (FE 배포), Railway (BE 배포) |
| CI/CD | GitHub Actions |


## 처음 보는 사람을 위한 읽는 순서

1. `analyzer.py`에서 5축 계산 방식을 확인합니다.
2. `matrix_engine.py`에서 축이 캐릭터 파라미터로 변환되는 방식을 확인합니다.
3. `dataset.py`에서 테스트 입력 예시를 확인합니다.
4. `tests/test_matrix.py`를 실행해 전체 흐름을 재현합니다.
5. `tests/visualizer.html`로 시각 결과를 확인합니다.

## 한계

- 규칙 기반 분석이라 문맥 이해가 제한적입니다.
- 데이터셋 규모가 작습니다.
- 실제 사용자 대상 학습 효과 검증은 아직 진행 전입니다.
- LLM과의 완전한 통합형 대화 시스템은 아직 아닙니다.

그럼에도 현재 저장소는 다음을 분명히 보여줍니다.

- 문제 정의가 분명합니다.
- 기술 솔루션이 코드 수준에서 구현되어 있습니다.
- MVP 핵심기술이 무엇인지 설명 가능합니다.
- 테스트 코드와 실험 흐름을 제3자가 재현할 수 있습니다.

## 한 줄 요약

이 저장소는 `사용자 발화 스타일을 5축으로 분석하고, CHARACTER MATRIX를 통해 AI 캐릭터의 반응 성격을 바꾸는 핵심 엔진 MVP`를 담고 있습니다.
