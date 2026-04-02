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
