# Pally 최종 보고서 초안

## 1. 프로젝트 개요

Pally는 대화 진행에 따라 성격이 변하는 AI 캐릭터와 함께 영어 회화를 연습하는 모바일 웹 서비스이다. 사용자가 영어로 말하면 시스템은 발화 스타일을 5개 축(Formality, Energy, Intimacy, Humor, Curiosity)으로 분석하고, CHARACTER MATRIX 연산을 통해 AI 캐릭터 Pally의 말투와 시각적 상태를 변화시킨다.

기존 영어 회화 서비스는 문법 교정이나 대화 기능은 제공하지만, 사용자의 말투, 친밀도, 에너지, 질문 성향을 충분히 반영하지 못해 대화가 획일적으로 느껴지는 문제가 있다. Pally는 사용자의 발화 스타일이 캐릭터 반응에 직접 반영되는 경험을 제공함으로써 더 몰입감 있고 지속 가능한 영어 회화 학습을 목표로 한다.

## 2. 문제 정의

영어 회화 학습자는 꾸준한 연습이 필요하지만, 기존 앱의 정형화된 응답과 반복적인 피드백 방식 때문에 학습 흥미를 잃기 쉽다. 특히 중급 이상 학습자는 단순한 문장 교정보다 실제 사람과 대화하는 듯한 반응성과 개인화를 원한다.

이 프로젝트는 다음 문제를 해결하고자 했다.

- 사용자의 말투와 대화 스타일을 반영하지 못하는 획일적인 AI 응답
- 학습 피드백이 대화 흐름과 분리되어 몰입을 방해하는 문제
- 사용자가 대화 과정에서 캐릭터와 관계가 형성된다고 느끼기 어려운 문제
- 음성 입력, AI 응답, 피드백, 캐릭터 변화를 하나의 모바일 흐름으로 연결하는 구현 난도

## 3. 핵심 아이디어

Pally의 핵심 아이디어는 "사용자 발화 스타일을 수치화하고, 그 수치가 캐릭터의 성격과 외형을 바꾼다"는 것이다.

전체 흐름은 다음과 같다.

1. 사용자가 모바일 웹에서 영어 문장을 말한다.
2. Google Cloud Speech-to-Text가 음성을 텍스트로 변환한다.
3. 자체 rule-based 분석기가 텍스트를 5축 점수로 분석한다.
4. CHARACTER MATRIX와 EMA 보정을 통해 캐릭터 파라미터를 계산한다.
5. Gemini 2.5 Flash가 Pally의 성격 상태를 반영한 영어 응답과 한국어 인라인 힌트를 생성한다.
6. Google Cloud Text-to-Speech가 응답을 음성으로 변환해 재생한다.
7. Canvas2D Superformula 캐릭터가 축 점수에 따라 형태, 색, 표정, 움직임을 바꾼다.

## 4. 핵심 기술

### 4.1 5축 발화 분석

사용자 발화는 다음 5개 축으로 분석된다.

| 축 | 의미 | 예시 반영 요소 |
|---|---|---|
| Formality | 격식도 | 정중한 표현, 문장 구조, 축약어 사용 |
| Energy | 에너지 | 감탄사, 문장 길이, 적극성 |
| Intimacy | 친밀도 | 자기 노출, 친근한 표현, 누적 대화 |
| Humor | 유머 성향 | 농담, 밈, 슬랭, 가벼운 표현 |
| Curiosity | 탐구 성향 | 질문 빈도, 주제 확장, 이유 탐색 |

MVP에서는 안정성과 설명 가능성을 위해 LLM 기반 분석기가 아니라 rule-based 분석기를 사용했다. 이를 통해 각 축 점수가 어떤 근거로 계산되는지 추적할 수 있고, 발표에서 핵심 기술을 명확히 설명할 수 있다.

### 4.2 CHARACTER MATRIX

CHARACTER MATRIX는 5축 점수를 캐릭터 파라미터로 변환하는 가중합 행렬이다. 입력 벡터 `[Formality, Energy, Intimacy, Humor, Curiosity]`가 행렬 연산을 거쳐 `tone_casual`, `energy_level`, `humor_level` 같은 캐릭터 반응 파라미터로 변환된다.

또한 EMA(Exponential Moving Average)를 적용해 한 번의 발화만으로 캐릭터가 급격히 튀지 않고, 대화 흐름에 따라 부드럽게 변화하도록 설계했다. 데모에서는 변화가 눈에 잘 보이도록 alpha 값을 0.7로 설정했다.

### 4.3 Pally Canvas2D 렌더러

Pally는 Canvas2D와 Superformula를 사용해 절차적으로 렌더링된다. 별도의 정적 이미지나 외부 애니메이션 도구에 의존하지 않고, 5축 점수에 따라 도형의 형태, 각진 정도, 색상, 눈 모양, 호흡 애니메이션이 바뀐다.

예를 들어 유머와 에너지가 높으면 더 뾰족하고 활발한 형태로, 격식도가 높으면 더 차분하고 각진 형태로 변화한다. 사용자는 대화가 진행될수록 자신의 발화 스타일이 Pally의 모습과 말투에 반영되는 것을 확인할 수 있다.

## 5. 시스템 구조

최종 MVP는 monorepo 구조로 구현했다.

| 영역 | 기술 | 역할 |
|---|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind | 모바일 대화 화면, 녹음 UI, Pally 렌더링, TTS 재생 |
| Backend | FastAPI, Python 3.11 | STT/TTS/Gemini 연동, 5축 엔진 호출, Supabase 저장 |
| AI Engine | Python | rule-based 분석기, CHARACTER MATRIX, EMA |
| Database | Supabase Postgres | 세션과 메시지, axes, character JSONB 저장 |
| Deployment | Vercel, Railway | 프론트엔드와 백엔드 배포 |

FastAPI 백엔드는 `ai/analyzer.py`와 `ai/matrix_engine.py`를 직접 import해 사용한다. 이 방식은 별도 마이크로서비스나 subprocess 호출보다 지연 시간이 낮고, 데모 기간 내 단일 백엔드로 안정적으로 운영하기 쉽다는 장점이 있다.

## 6. 구현 결과

최종 MVP에서 구현된 기능은 다음과 같다.

- 모바일 웹 메인 화면
- 브라우저 마이크 녹음 및 음성 업로드
- Google Cloud Speech-to-Text 기반 영어 발화 텍스트화
- 5축 발화 분석과 CHARACTER MATRIX 계산
- Gemini 2.5 Flash 기반 영어 응답 생성
- 한국어 인라인 힌트 및 자연스러운 문법 교정
- Google Cloud Text-to-Speech 기반 음성 응답 재생
- Canvas2D Superformula 기반 Pally 실시간 변화
- 세션 종료 시 누적 변화가 반영된 최종 Pally 공개
- Supabase `sessions` / `messages` 테이블 저장 및 RLS 정책
- Vercel 프론트엔드 배포와 Railway 백엔드 배포

데모 URL: https://capstone-eight-virid.vercel.app/home

## 7. 팀 역할

| 이름 | 역할 |
|---|---|
| 최윤서 | PM, 기획, QA |
| 이찬희 | Frontend, 디자인, 메인 화면과 오디오 셸 |
| 김민주 | AI 엔진, 5축 분석, CHARACTER MATRIX, Pally 렌더러 |
| 백은혜 | Backend, FastAPI, GCP STT/TTS, Gemini, Supabase |

## 8. 개발 과정

프로젝트는 병렬 개발이 가능하도록 Phase 단위로 나누어 진행했다.

- Phase 0: Next.js, Tailwind, Supabase client, 기본 타입 등 foundation 구성
- Phase 1A: 메인 대화 화면과 녹음/오디오 UX 셸 구현
- Phase 1B: Pally Canvas2D 렌더러와 Python 엔진 통합 ADR 작성
- Phase 1C: FastAPI 백엔드, GCP STT/TTS, Gemini 응답, Supabase schema/RLS 구현
- Phase 2: 프론트-백엔드 통합, 배포, 모바일 데모 검증

특히 Phase 1B와 1C 사이에서는 Python 엔진을 FastAPI에서 직접 import하는 방식으로 계약을 정했고, 이를 통해 AI 엔진과 백엔드 통합 비용을 줄였다.

## 9. 성과

Pally는 단순한 챗봇 응답 생성이 아니라, 사용자의 발화 스타일을 구조화된 수치로 변환하고 이를 캐릭터 반응에 연결하는 자체 기술 구조를 구현했다. 최종 데모에서는 사용자가 영어로 말하면 음성 인식, AI 응답, 음성 재생, 한국어 힌트, Pally 시각 변화가 하나의 모바일 흐름으로 작동한다.

프로젝트의 주요 성과는 다음과 같다.

- 사용자 발화 스타일을 5축으로 수치화하는 설명 가능한 분석 구조 구현
- CHARACTER MATRIX 기반 캐릭터 성격 변환 로직 구현
- Pally의 외형 변화와 말투 변화를 하나의 사용자 경험으로 연결
- 실제 클라우드 STT/TTS/LLM/Supabase/Vercel/Railway를 연결한 E2E MVP 완성
- 발표와 데모가 가능한 모바일 중심 프로토타입 확보

## 10. 한계와 향후 발전 방향

MVP에서는 안정적인 데모를 위해 rule-based 분석기를 사용했기 때문에, 맥락 의존적인 발화나 미묘한 뉘앙스를 완벽하게 해석하는 데 한계가 있다. 또한 사용자의 장기 학습 이력, 개인별 목표, 발음 평가 등은 MVP 범위에서 제외했다.

향후에는 다음 방향으로 확장할 수 있다.

- LLM 또는 ML 기반 축 분석기 도입
- 사용자별 장기 대화 상태와 학습 이력 저장
- 발음/억양 피드백 추가
- 사용자 인증과 개인화 프로필
- pgvector 기반 장기 기억/RAG
- 실제 사용자 테스트를 통한 CHARACTER MATRIX 가중치 튜닝

## 11. 참고 자료

- 프로젝트 README: `README.md`
- 최종 기획 문서: `docs/final/Project Briefs.MD`
- 디자인 문서: `docs/final/Design_Document.MD`
- 구현 계획: `docs/final/Implementation_Plan.MD`
- 개발 로드맵: `.planning/ROADMAP.md`
- Python 엔진 통합 ADR: `docs/adr/0001-python-engine-integration.md`
