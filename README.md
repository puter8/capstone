# 감정 MATRIX 기반 사용자 맞춤형 AI 영어 회화 학습 서비스

> 2026 한이음 드림업 프로젝트

---

## 프로젝트 소개

사용자의 대화 패턴을 실시간 분석하여 AI 캐릭터의 성격이 동적으로 변화하는 개인화 영어 회화 학습 서비스입니다.  
6가지 성격 축으로 구성된 감정 MATRIX 시스템, 최신 슬랭 자동 수집 파이프라인, Rive 기반 캐릭터 시각화를 핵심 기술로 적용합니다.

---

## 기술 스택

### 프론트엔드

| 역할              | 스택         |
| ----------------- | ------------ |
| 프레임워크        | Next.js 14   |
| 스타일링          | Tailwind CSS |
| 캐릭터 애니메이션 | Rive         |
| 상태관리          | Zustand      |

### 백엔드

| 역할     | 스택                 |
| -------- | -------------------- |
| API 서버 | Spring Boot 3 (Java) |
| DB       | PostgreSQL           |
| ORM      | JPA / Hibernate      |

### AI 서비스

| 역할       | 스택                      |
| ---------- | ------------------------- |
| LLM        | GPT-4o                    |
| RAG        | LangChain + Pinecone      |
| 슬랭 수집  | Reddit PRAW + YouTube API |
| 파이프라인 | GitHub Actions            |
| 임베딩     | text-embedding-3-small    |
| AI 서버    | FastAPI (Python)          |

### 배포

| 대상   | 스택              |
| ------ | ----------------- |
| 프론트 | Vercel            |
| 백엔드 | Railway or Render |
| DB     | Supabase          |
