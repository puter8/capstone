# 감정 MATRIX 기반 사용자 맞춤형 AI 영어 회화 학습 서비스

> 2026 한이음 드림업 프로젝트

---

## 프로젝트 소개

사용자의 대화 패턴을 실시간 분석하여 AI 캐릭터의 성격이 동적으로 변화하는 개인화 영어 회화 학습 서비스입니다.
5가지 성격 축(Formality, Energy, Intimacy, Humor Style, Curiosity)으로 구성된 감정 MATRIX 시스템, 최신 슬랭 자동 수집 파이프라인, Superformula + Canvas2D 기반 캐릭터 시각화를 핵심 기술로 적용합니다.

---

## 기술 스택

### 프론트엔드

| 역할              | 스택         |
| ----------------- | ------------ |
| 프레임워크        | Next.js 14   |
| 스타일링          | Tailwind CSS |
| 캐릭터 애니메이션 | Canvas2D + Superformula |
| 상태관리          | Zustand      |

### 백엔드

| 역할       | 스택                    |
| ---------- | ----------------------- |
| API 서버   | FastAPI (Python)        |
| DB / Auth  | Supabase (PostgreSQL + Auth + RLS) |
| LLM        | GPT-4o                  |
| 슬랭 수집  | Reddit PRAW             |
| 파이프라인 | GitHub Actions          |

### 배포

| 대상   | 스택              |
| ------ | ----------------- |
| 프론트 | Vercel            |
| 백엔드 | Railway or Render |
| DB     | Supabase          |

---

## 핵심 모듈 구조

```
capstone/
├── analyzer.py        # 규칙 기반 5축 분석기 (추후 LLM으로 교체 예정)
│                      # 발화의 언어적 특징(슬랭, 격식 표현, 이모지 등)을 분석하여
│                      # Formality / Energy / Intimacy / Humor / Curiosity 수치 산출
│
├── matrix_engine.py   # CHARACTER MATRIX 핵심 연산 모듈
│                      # 5축 수치 벡터에 가중치 행렬 W를 곱해 AI 캐릭터 파라미터 산출
│                      # W × [F, E, I, H, C]ᵀ + bias → tone_casual / energy_level / humor_level
│
├── dataset.py         # Ground Truth 학습 데이터셋 (25개 발화 라벨링)
│                      # 팀이 직접 채점한 5축 정답 수치 포함
│                      # 현재: 규칙 기반 분석기 검증용 / 추후: LLM 파인튜닝 학습 데이터
│
└── tests/
    ├── test_matrix.py  # 전체 파이프라인 데모 실행 스크립트
    │                   # analyzer → matrix_engine → AI 응답 생성까지 시연
    │                   # 실행: python tests/test_matrix.py
    │
    └── visualizer.html # CHARACTER MATRIX 캐릭터 시각화 (Canvas2D)
                        # 5축 수치 변화에 따라 캐릭터 색상 / 스파이크 수 / 애니메이션 속도 변화
                        # test_matrix.py 실행 시 브라우저 자동 실행
```
