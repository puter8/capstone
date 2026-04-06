# **Plan: CHARACTER MATRIX - Personalized English Conversation Service**

## **Context**

졸업 프로젝트로 CHARACTER MATRIX 기반 개인화 영어 회화 학습 서비스를 구축한다. 기존 영어 회화 앱의 뻣뻣하고 반복적인 대화를 해결하기 위해, 사용자 발화를 5축으로 분석하고 AI 캐릭터 성격을 동적으로 조절하는 시스템이다.

디자인 문서(**`/.context/plans/design-emotion-matrix-personalized-english-convers.md`**)에서 엔지니어링 리뷰를 거쳐 다음 결정이 확정되었다:

## **Agreed Architecture (eng review decisions)**

```
┌──────────────┐      ┌─────────────┐
│  Next.js 14  │─────→│  Supabase   │  Auth, CRUD, RLS, Realtime
│  (Vercel)    │      │  (Postgres) │
│  + Canvas2D  │      └─────────────┘
│  + Zustand   │
└──────┬───────┘      ┌─────────────────────────────────────┐
       └─────────────→│  FastAPI (Railway)                   │
        (AI 요청만)    │                                     │
                      │  ┌───────────────────┐              │
                      │  │ 발화 분석기        │              │
                      │  │ (자체 개발)        │              │
                      │  │ Rule-Based → ML   │              │
                      │  └────────┬──────────┘              │
                      │           ▼                         │
                      │  ┌───────────────────┐  ┌────────┐ │
                      │  │ MATRIX 엔진       │→│ GPT-4o │ │
                      │  │ (EMA + 가중합)    │  └────────┘ │
                      │  └───────────────────┘  답변 생성만  │
                      │  + PRAW                             │
                      └──────────────┬──────────────────────┘
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
| 2 | 발화 분석 | **자체 개발 모델 (Hybrid)** — Rule-Based로 MVP 구현 → 앱 사용 데이터 축적 후 ML 모델로 진화. GPT-4o는 답변 생성만 담당 |
| 3 | RAG 파이프라인 | **Supabase pgvector** — 외부 벡터 DB 없이 기존 DB 내 벡터 검색 |
| 4 | 데이터 저장 | **FastAPI가 service_role로 Supabase 직접 저장** |
| 5 | 가중치 행렬 W | **MVP: 수동 설정 후 데이터 기반 튜닝** — 축 점수 초기값 0, 사용자별 독립 |
| 6 | 축 감쇠 | **모든 축에 EMA** — Intimacy alpha=0.1(느림), 나머지 alpha=0.5(빠름) |
| 7 | 에러 핸들링 | **7개 케이스 전부 커버** + 테스트 (발화 분석 실패 케이스 추가) |
| 8 | 응답 UX | **스트리밍** — 텍스트 스트리밍, 축 점수는 완료 후 전송 |
| 9 | 분석 모델 진화 | **Hybrid** — Phase 1~3 Rule-Based, Phase 4~5 ML 전환, 최종 A/B 비교 실험 |

## **Data Flow (per conversation turn)**

```
사용자 입력 ("yo what up my mate")
    │
    ▼
Next.js ──POST──→ FastAPI /api/chat
                      │
                      ├─ 1. 사용자 축 점수 이력 조회 (Supabase)
                      │
                      ├─ 2. 자체 발화 분석기로 5축 raw 점수 추출
                      │     ├─ [Rule-Based] 키워드 사전 + 패턴 매칭 + 가중치
                      │     │   "what up" → Formality↓, "mate/yo" → Intimacy↑
                      │     └─ [ML] (Phase 4+) sentence-transformers → regression
                      │     → raw_scores: {F:10, E:75, I:70, H:65, C:20}
                      │
                      ├─ 3. EMA로 축 점수 업데이트
                      │     └─ new_score = alpha * raw + (1 - alpha) * prev
                      │
                      ├─ 4. 행렬 연산 W × [F,E,I,H,C]ᵀ + bias
                      │     → 캐릭터 파라미터: {tone_casual, energy_level, humor_level, ...}
                      │
                      ├─ 5. system prompt 구성 (캐릭터 파라미터 수치 주입)
                      │     → GPT-4o 호출 (streaming) — 답변 생성만 담당
                      │
                      ├─ 6. Supabase에 저장 (대화 + raw/ema 점수)
                      │
                      └─ 7. 스트리밍 응답 + 축 점수 반환
                              │
                              ▼
                         Next.js
                      ├─ 텍스트: 실시간 렌더링
                      ├─ 축 점수: Zustand 상태 업데이트
                      └─ Canvas2D: Superformula 캐릭터 반영 (형태, 각도, 눈, 색조, 호흡)
```

## **5-Axis → Character Visual Mapping (Superformula + Canvas2D)**

Rive 대신 **Superformula 수학 공식 + Canvas2D**로 캐릭터를 절차적 생성한다.
Superformula는 하나의 파라미터 공식으로 원/별/클로버/사각형 등 모든 형태를 연속적으로 변환할 수 있다.

```
r(θ) = (|cos(mθ/4)/a|^n2 + |sin(mθ/4)/b|^n3)^(-1/n1)
```

### 축 → 시각 속성 매핑

```
Axis        → Visual Property          → Range                           → Superformula
────────────────────────────────────────────────────────────────────────────────────────
Humor       → Body Shape (형태)         → 0:●원 ~ 100:✱별/복잡 형태       → m (꼭짓점 수)
Formality   → Body Angularity (각진 정도) → 0:유기적/둥근 ~ 100:기하학적/각진 → n1 (각도)
Energy      → Eye Shape + Size (눈)     → 0:작은 점 눈 ~ 100:큰 별 모양 눈  → (별도 렌더링)
Intimacy    → Hue (색조)               → 0:차가운 파랑 ~ 100:따뜻한 핑크    → HSL hue
Curiosity   → Scale Pulse (호흡)        → 0:정적 ~ 100:호흡 효과           → scale sin()
```

### 레퍼런스 캐릭터 재현

```
분홍 뾰족이 (High Energy/Humor):     초록 클로버 (Calm/Friendly):       파란 사각형 (Formal/Cold):
  Humor=85  → m=8 (뾰족 별)           Humor=30  → m=4 (클로버)           Humor=10  → m=4 (단순)
  Formality=10 → 둥근 꼭짓점           Formality=10 → 둥근 잎              Formality=95 → 매우 각진
  Energy=90 → 큰 별 모양 눈            Energy=20 → 작은 점 눈              Energy=30 → 작고 각진 눈
  Intimacy=80 → 핑크/코랄              Intimacy=50 → 초록                  Intimacy=5 → 차가운 파랑
  Curiosity=50 → 약한 호흡             Curiosity=30 → 미세 호흡            Curiosity=10 → 거의 정적
```

### Idle 애니메이션 (항상 적용)

```
- 미세 부유 효과: y좌표를 sin(time) 곡선으로 미세 이동
- 랜덤 눈 깜빡임: 3~6초 간격, scaleY를 0으로 줄였다 복원
- 파라미터 전환: 현재값 → 목표값 lerp (0.3초 전환)
- 구현: React useRef + useEffect + requestAnimationFrame (60fps)
```

## **Utterance Analyzer: 자체 발화 분석 모델 (고유핵심기술)**

사용자 발화를 5축 점수로 변환하는 자체 개발 모델. Hybrid 전략으로 Rule-Based에서 시작하여 ML로 진화한다.

### **Phase A: Rule-Based 분석기 (MVP)**

```
사용자 발화 → [토큰화] → [키워드 매칭] → [패턴 분석] → [가중합] → 5축 raw 점수

분석 요소:
├─ 키워드 사전: 슬랭/격식 어휘/감탄사/밈 표현 (200개 샘플에서 추출)
├─ 패턴 매칭: 문장 구조 복잡도, 축약어 빈도, 이모지 사용, 질문 빈도
└─ 가중치 테이블: 각 신호 → 축별 가중치 (200개 샘플로 검증/튜닝)
```

200개 샘플 데이터의 역할: 규칙의 **검증 데이터셋**. 규칙이 샘플 대비 얼마나 정확한지 정량 평가.

### **Phase B: ML 모델 (진화)**

```
사용자 발화 → [sentence-transformers 임베딩] → [regression head] → 5축 점수

학습 데이터: 앱 사용 로그에서 축적된 (발화, 축 점수) 쌍
목표: Rule-Based 대비 정확도 향상, 특히 맥락 의존적 표현 처리
```

최종 발표에서 Rule-Based vs ML 정확도 A/B 비교 실험 결과 제시.

## **Implementation Steps**

### **Phase 0: Foundation (공유 인프라)** — depends on: 없음

1. **Supabase 프로젝트 생성** — Auth 설정, DB 스키마, RLS
2. **공통 타입 정의** — 5축 점수 타입, 캐릭터 파라미터 타입
3. **200개 샘플 데이터셋 구축** — 발화 ↔ 5축 점수 매핑 (규칙 검증용)

### **Phase 1: 발화 분석기 + MATRIX 엔진 (핵심기술)** — depends on: Phase 0

1. **Rule-Based 발화 분석기**
    - 키워드 사전 구축 (슬랭, 격식 어휘, 감탄사, 밈 표현)
    - 패턴 매칭 모듈 (문장 구조, 축약어, 이모지, 질문 빈도)
    - 가중치 테이블 + 200개 샘플 기반 튜닝
2. **MATRIX 엔진** — 가중합 행렬 연산 W × v + bias, 0~100 클리핑
3. **EMA 모듈** — 축별 alpha 값, clamp(0~100)
4. **테스트** — 200개 샘플 대비 분석기 정확도 평가, 행렬 연산 단위 테스트

### **Phase 2: FastAPI + GPT-4o 답변 생성** — depends on: Phase 1

1. **POST /api/chat** — 메인 대화 엔드포인트
    - 입력: `{ user_id, conversation_id, message }`
    - 처리: 발화 분석 → EMA 업데이트 → 행렬 연산 → system prompt 구성 → GPT-4o → 저장
    - 출력: SSE 스트리밍 (텍스트) + 완료 시 축 점수 JSON
2. **System prompt builder** — 캐릭터 파라미터 수치를 GPT-4o 성격 지시문으로 변환
3. **에러 핸들링**: 7개 케이스 전부 (발화 분석 실패, GPT 실패, 파싱 실패, 범위 초과, DB 실패, Reddit rate limit, Canvas NaN/undefined → 기본값 50)

### **Phase 3: Next.js Frontend** — depends on: Phase 0

1. **Auth 페이지** — Supabase Auth UI
2. **채팅 페이지** — SSE 스트리밍 수신, 메시지 렌더링
3. **Superformula 캐릭터 컴포넌트 (Canvas2D)** — 5축 파라미터 실시간 반영
    - Superformula로 body shape 절차적 생성 (Humor→m, Formality→n1)
    - Eye renderer: Energy→눈 형태+크기 (점 눈↔별 눈)
    - HSL color: Intimacy→hue (파랑↔핑크)
    - Scale pulse: Curiosity→호흡 효과
    - Idle 애니메이션: 부유, 깜빡임, lerp 전환
    - React useRef + requestAnimationFrame (60fps)
4. **Zustand 스토어** — 축 점수 상태, 대화 이력

### **Phase 4: ML 모델 전환** — depends on: Phase 2, Phase 3 (앱 사용 데이터 축적 후)

1. **데이터 수집 파이프라인** — 앱 사용 로그에서 (발화, Rule-Based 점수) 쌍 자동 축적
2. **ML 모델 학습** — sentence-transformers 임베딩 + regression head
3. **A/B 비교 실험** — Rule-Based vs ML 정확도 정량 비교
4. **ML 모델 교체** — ML 우선, Rule-Based는 fallback으로 유지

### **Phase 5: Slang Pipeline (Supabase pgvector)** — depends on: Phase 0

1. **PRAW Reddit 수집 스크립트** — GitHub Actions cron
2. **임베딩 생성** — text-embedding-3-small로 슬랭 벡터화
3. **DB 저장** — slang_entries 테이블 (embedding 컬럼, pgvector)
4. **벡터 검색** — 대화 맥락 기반 유사 슬랭 검색 (cosine similarity)
5. **System prompt 주입** — Humor Style 축 점수에 따라 슬랭 빈도 조절

## **Error Handling Matrix**

| **Case** | **Fallback** | **User sees** |
| --- | --- | --- |
| 발화 분석기 실패 (키워드 매칭 0건) | 이전 축 점수 유지, 로그 기록 | 정상 대화 (점수 변화 없음) |
| GPT-4o timeout/rate limit | 3회 재시도 후 "잠시 후 다시 시도" 메시지 | 에러 메시지 |
| GPT-4o 응답 파싱 실패 | 텍스트만 반환, 축 점수 유지 | 정상 대화 (점수 변화 없음) |
| 축 점수 0~100 초과 | clamp(0, 100) | 무음 (정상 동작) |
| Supabase 저장 실패 | 로그 + 응답은 정상 반환 | 정상 대화 (이력 미저장) |
| Reddit API rate limit | 기존 슬랭 데이터 사용 | 무음 |
| Canvas NaN/undefined | 기본값 50 적용 | 기본 형태 캐릭터 (원, 중간 색, 점 눈) |

## **Verification**

1. **발화 분석기**: `pytest` — 200개 샘플 데이터셋 대비 분석 정확도, 엣지 케이스 (빈 입력, 단일 단어, 이모지만 등)
2. **MATRIX 엔진**: `pytest` — 행렬 연산 정확성, EMA 계산, 0~100 클리핑, 다양한 입력에 대한 차별화 검증
3. **FastAPI**: `pytest` — 에러 핸들링 7케이스
4. **Next.js**: `npm run build` — 타입 에러 체크
5. **E2E**: 메시지 전송 → 발화 분석 → 축 점수 변화 → AI 응답 → Canvas2D 캐릭터 변화 확인
6. **Supabase**: RLS 정책이 다른 사용자 데이터 접근을 차단하는지 확인

## **Unresolved Decisions**

없음 — 모든 주요 기술 결정 완료.

## **TODOs (deferred)**

1. **EMA alpha 값 튜닝** — 실제 대화 데이터 50회화 이상 축적 후 최적화. 초기값: Intimacy 0.1, 나머지 0.5.
2. **ML 모델 전환 시점 판단** — Rule-Based 정확도 baseline 확보 후, 축적 데이터 500개 이상 시 ML 실험 시작.
3. **Rule-Based vs ML A/B 비교 실험 설계** — 평가 메트릭, 테스트 데이터셋 분리, 통계적 유의성 검증.
