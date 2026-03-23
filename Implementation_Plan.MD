# **Plan: Emotion MATRIX - Personalized English Conversation Service**

## **Context**

졸업 프로젝트로 감정 MATRIX 기반 개인화 영어 회화 학습 서비스를 구축한다. 기존 영어 회화 앱의 뻣뻣하고 반복적인 대화를 해결하기 위해, 사용자 발화를 5축으로 분석하고 AI 캐릭터 성격을 동적으로 조절하는 시스템이다.

디자인 문서(**`/.context/plans/design-emotion-matrix-personalized-english-convers.md`**)에서 엔지니어링 리뷰를 거쳐 다음 결정이 확정되었다:

## **Agreed Architecture (eng review decisions)**

```
┌──────────────┐      ┌─────────────┐
│  Next.js 14  │─────→│  Supabase   │  Auth, CRUD, RLS, Realtime
│  (Vercel)    │      │  (Postgres) │
│  + Rive      │      └─────────────┘
│  + Zustand   │
└──────┬───────┘      ┌─────────────┐      ┌──────────┐
       └─────────────→│  FastAPI     │─────→│  GPT-4o  │
        (AI 요청만)    │  (Railway)   │      └──────────┘
                      │  + PRAW      │
                      └──────┬───────┘
                             │ service_role
                       ┌─────────────┐
                       │  Supabase   │
                       │  (저장)      │
                       └─────────────┘
```

| **#** | **Decision** | **Result** |
| --- | --- | --- |
| 0 | 백엔드 아키텍처 | **FastAPI 단일 백엔드** — Spring Boot 제거 |
| 1 | DB/Auth | **Supabase Auth + RLS** — FastAPI는 AI/매트릭스 전담 |
| 2 | LLM 호출 | **단일 GPT-4o 호출** — structured output으로 축 점수 + 대화 응답 통합 |
| 3 | RAG 파이프라인 | **Supabase pgvector** — 외부 벡터 DB 없이 기존 DB 내 벡터 검색 |
| 4 | 데이터 저장 | **FastAPI가 service_role로 Supabase 직접 저장** |
| 5 | 가중치 행렬 W | **MVP: identity** — 축 점수 초기값 0, 사용자별 독립 |
| 6 | 축 감쇠 | **모든 축에 EMA** — Intimacy alpha=0.1(느림), 나머지 alpha=0.5(빠름) |
| 7 | 에러 핸들링 | **6개 케이스 전부 커버** + 테스트 |
| 8 | 응답 UX | **스트리밍** — 텍스트 스트리밍, 축 점수는 완료 후 파싱 |

## **Data Flow (per conversation turn)**

```
사용자 입력
    │
    ▼
Next.js ──POST──→ FastAPI /api/chat
                      │
                      ├─ 1. 사용자 축 점수 이력 조회 (Supabase)
                      ├─ 2. system prompt 구성 (축 점수 기반 캐릭터 성격)
                      ├─ 3. GPT-4o 호출 (streaming + structured output)
                      │     └─ response: { text: "...", scores: {F,E,I,H,C} }
                      ├─ 4. EMA로 축 점수 업데이트
                      │     └─ new_score = alpha * raw + (1 - alpha) * prev
                      ├─ 5. Supabase에 저장 (대화 + 점수)
                      └─ 6. 스트리밍 응답 반환
                              │
                              ▼
                         Next.js
                      ├─ 텍스트: 실시간 렌더링
                      ├─ 축 점수: Zustand 상태 업데이트
                      └─ Rive: 파라미터 반영 (색조, 속도, 형태, 밝기, 크기)
```

## **5-Axis → Rive Visual Mapping**

```
Axis        → Visual Property   → Range
─────────────────────────────────────────
Intimacy    → Hue (색조)        → 0:파랑 ~ 100:핑크
Energy      → Anim Speed (속도) → 0:느림 ~ 100:빠름
Humor Style → Vertex Count      → 0:원 ~ 100:별
Formality   → Brightness (밝기) → 0:비비드 ~ 100:차분
Curiosity   → Size Pulse (크기) → 0:일정 ~ 100:호흡
```

## **Implementation Steps**

### **Phase 1: Project Setup**

1. **Next.js 14 프로젝트 초기화** — Tailwind, TypeScript strict
2. **FastAPI 프로젝트 초기화** — Python 3.11+, uvicorn
3. **Supabase 프로젝트 생성** — Auth 설정, DB 스키마

### **Phase 2: Database Schema (Supabase)**

```sql
-- users: Supabase Auth 기본 제공

-- user_emotion_scores: 사용자별 현재 축 점수
CREATE TABLE user_emotion_scores (
  user_id UUID REFERENCES auth.users PRIMARY KEY,
  formality FLOAT DEFAULT 0,
  energy FLOAT DEFAULT 0,
  intimacy FLOAT DEFAULT 0,
  humor FLOAT DEFAULT 0,
  curiosity FLOAT DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- conversations: 대화 세션
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- messages: 개별 메시지
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  raw_scores JSONB,  -- 이번 턴의 raw 축 점수
  ema_scores JSONB,  -- EMA 적용 후 축 점수
  created_at TIMESTAMPTZ DEFAULT now()
);

-- slang_entries: Reddit 슬랭 + pgvector 벡터 검색
CREATE TABLE slang_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  term TEXT NOT NULL,
  definition TEXT,
  context TEXT,
  source_url TEXT,
  popularity INT DEFAULT 0,
  embedding VECTOR(1536),  -- text-embedding-3-small
  created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS: 모든 테이블 auth.uid() 기반
```

### **Phase 3: FastAPI AI Service**

1. **POST /api/chat** — 메인 대화 엔드포인트
    - 입력: `{ user_id, conversation_id, message }`
    - 처리: 축 점수 조회 → system prompt 구성 → GPT-4o → EMA 업데이트 → 저장
    - 출력: SSE 스트리밍 (텍스트) + 완료 시 축 점수 JSON
2. **EMA 모듈** — 축별 alpha 값, clamp(0~100)
3. **System prompt builder** — 축 점수를 캐릭터 성격 지시문으로 변환
4. **에러 핸들링**: 6개 케이스 전부 (GPT 실패, 파싱 실패, 범위 초과, DB 실패, Reddit rate limit, Rive NaN)

### **Phase 4: Next.js Frontend**

1. **Auth 페이지** — Supabase Auth UI
2. **채팅 페이지** — SSE 스트리밍 수신, 메시지 렌더링
3. **Rive 캐릭터 컴포넌트** — 5축 파라미터 실시간 반영
4. **Zustand 스토어** — 축 점수 상태, 대화 이력

### **Phase 5: Slang Pipeline (Supabase pgvector)**

1. **PRAW Reddit 수집 스크립트** — GitHub Actions cron
2. **임베딩 생성** — text-embedding-3-small로 슬랭 벡터화
3. **DB 저장** — slang_entries 테이블 (embedding 컬럼, pgvector)
4. **벡터 검색** — 대화 맥락 기반 유사 슬랭 검색 (cosine similarity)
5. **System prompt 주입** — Humor Style 축 점수에 따라 슬랭 빈도 조절

## **Error Handling Matrix**

| **Case** | **Fallback** | **User sees** |
| --- | --- | --- |
| GPT-4o timeout/rate limit | 3회 재시도 후 "잠시 후 다시 시도" 메시지 | 에러 메시지 |
| Structured output 파싱 실패 | 텍스트만 반환, 축 점수 유지 | 정상 대화 (점수 변화 없음) |
| 축 점수 0~100 초과 | clamp(0, 100) | 무음 (정상 동작) |
| Supabase 저장 실패 | 로그 + 응답은 정상 반환 | 정상 대화 (이력 미저장) |
| Reddit API rate limit | 기존 슬랭 데이터 사용 | 무음 |
| Rive NaN/undefined | 기본값 50 적용 | 기본 형태 캐릭터 |

## **Verification**

1. **FastAPI**: `pytest` — 축 점수 EMA 계산, structured output 파싱, 에러 핸들링 6케이스
2. **Next.js**: `npm run build` — 타입 에러 체크
3. **E2E**: 메시지 전송 → AI 응답 수신 → 축 점수 변화 → Rive 캐릭터 변화 확인
4. **Supabase**: RLS 정책이 다른 사용자 데이터 접근을 차단하는지 확인

## **Unresolved Decisions**

없음 — 모든 주요 기술 결정 완료.

## **TODOs (deferred)**

1. **EMA alpha 값 튜닝** — 실제 대화 데이터 50회화 이상 축적 후 최적화. 초기값: Intimacy 0.1, 나머지 0.5.
