# CHARACTER MATRIX 전체 개발 계획 (2026.05 ~ 10)

## 팀 역할 정의

| 역할 | 담당 도메인 |
|------|------------|
| **PM1** | 일정·스프린트 관리, PRD·문서, 발표/데모 준비, QA 조율 |
| **FE1** | Next.js 14, Canvas2D Superformula 캐릭터, Zustand, UI 구현 |
| **BE1** | FastAPI, Supabase 스키마·Auth·RLS, Railway 배포 |
| **AI1** | 발화 분석기(Rule-Based→ML), MATRIX 엔진, Slang 파이프라인 |

---

## 전체 로드맵

```
5월           6월           7월           8월           9월           10월
기획 마무리    설계·환경     핵심 개발 1    핵심 개발 2    통합·ML       QA·발표
─────────────────────────────────────────────────────────────────────────────
PRD           Phase 0       Phase 1       Phase 2       Phase 4       최종 QA
User Flow     Foundation    AI Core       FastAPI API   ML Model      발표 자료
Wireframe     DB 스키마     FE 기반       FE 완성       E2E 안정화    졸업 발표
              아키텍처 확정  Canvas2D      Slang Pipeline Polish
```

---

## 5월 — 기획 마무리

> **목표:** PRD, 유저 플로우, 와이어프레임 완성. 6월 개발 착수 전 팀 전원 공유·확정.

### PM1 (주도)

**PRD 작성** (`docs/plan/PRD.md`)
- 문제 정의 & 타겟 유저 (20~30대, B1 이상, "사람이랑 대화하는 느낌" 원하는 유저)
- 핵심 기능 명세
  ```
  F1. 회원가입/로그인 (Supabase Auth)
  F2. 실시간 영어 대화 (SSE 스트리밍)
  F3. 5축 발화 분석 → CHARACTER MATRIX 연산
  F4. Canvas2D Superformula 캐릭터 실시간 변화
  F5. Intimacy 누적 진화 (EMA)
  F6. Slang RAG 주입 (Humor 축 기반)
  F7. 대화 이력 조회
  ```
- Non-goal 명시 (음성 입력, 모바일 앱, 다국어)
- 성공 지표: 5분 대화에서 캐릭터 형태 변화 3회 이상 감지

**유저 플로우** (`docs/design/user-flow.md`)
```
[신규 유저]
랜딩 → 회원가입 → 온보딩(캐릭터 소개) → 첫 대화 → 축 점수 변화 확인

[기존 유저]
로그인 → 이전 대화 이어서 or 새 대화 → 캐릭터 누적 진화 확인 → 대화 이력 조회

[대화 한 턴]
메시지 입력 → 전송 → 스트리밍 응답 수신 → 캐릭터 애니메이션 → 축 점수 패널 업데이트
```

**와이어프레임** (`docs/design/wireframes/`)
- 툴: Figma (또는 팀 합의 툴)
- 필요 화면 목록:
  ```
  01_landing.png      랜딩 페이지
  02_login.png        로그인/회원가입
  03_onboarding.png   캐릭터 첫 소개
  04_chat_main.png    채팅 메인 (캐릭터 + 메시지 + 입력창)
  05_axis_panel.png   5축 점수 시각화 패널
  06_history.png      대화 이력
  ```

### FE1
- 와이어프레임 리뷰 참여 (UI 실현 가능성 검토)
- Superformula 캐릭터 5축 → 시각 매핑 최종 확정

### BE1
- PRD 기반 DB 스키마 초안 검토
- 인프라 비용 검토 (Supabase free tier, Railway 플랜)

### AI1
- PRD F3(발화 분석) 요구사항 검토
- 200개 샘플 데이터셋 완성 목표일 확정

**5월 완료 기준:**
- PRD, 유저 플로우, 와이어프레임 팀 전원 승인
- `docs/design/` 폴더에 전부 커밋
- 6월 1일 개발 착수 가능한 상태

---

## 6월 — 설계 확정 & Foundation

> **목표:** 공유 인프라 완성. 모든 Phase의 의존성 해소.

### PM1
- 스프린트 보드 세팅 (GitHub Projects, 이슈 템플릿)
- `docs/code-convention.md` 작성 (팀 합의 후 확정)
- `docs/adr/` 폴더 생성, ADR 템플릿 작성

### BE1 (Phase 0)
- Supabase 프로젝트 생성 (Auth: Email + Google OAuth)
- DB 스키마 마이그레이션
  ```sql
  users            -- Supabase Auth 연동
  conversations    -- id, user_id, created_at
  messages         -- id, conv_id, role, content, created_at
  axis_scores      -- user_id, F, E, I, H, C (EMA), updated_at
  slang_entries    -- id, text, embedding(vector), metadata
  ```
- RLS 정책 (users는 자신의 데이터만 접근)
- FastAPI 프로젝트 초기화 (Railway 배포 파이프라인 설정)

### FE1 (Phase 0)
- Next.js 14 프로젝트 초기화 (App Router, Tailwind, Zustand)
- 폴더 구조 확정
  ```
  app/              페이지 (App Router)
  components/       공통 컴포넌트
  components/canvas/ Superformula 캐릭터
  lib/              Supabase 클라이언트, API 호출
  store/            Zustand 스토어
  types/            공통 타입
  ```
- Supabase Auth 로그인/회원가입 구현
- 공통 타입 정의 (`AxisScore`, `CharacterParams`, `Message`)

### AI1 (Phase 0)
- 200개 샘플 데이터셋 완성 (`dataset.py`, CSV)
  - 발화 유형별 40개씩: 캐주얼/격식/유머/탐구형/일반
  - 5축 라벨 포함
- Python 공통 타입 정의 (`AxisScore`, `CharacterParams`)
- 기존 `analyzer.py`, `matrix_engine.py` 코드 리팩토링 (FastAPI 통합 준비)

**6월 완료 기준:**
- Supabase 접속 + RLS 동작 확인
- Next.js 앱 로컬 실행 + 로그인 동작
- 200개 데이터셋 커밋
- FastAPI 로컬 실행 + `/health` 응답

---

## 7월 — 핵심 개발 1

> **목표:** AI 핵심 엔진 완성 + FE 기반 + Canvas2D 캐릭터

### Sprint 1 (7월 1~14일)

**PM1**
- 주간 스탠드업 운영 (월/목)
- 발화 분석기 테스트 결과 문서화 기준 정의

**BE1**
- FastAPI 프로젝트 구조 확정
  - `routers/`, `services/`, `models/`, `utils/`
- Supabase 연결 모듈 구현 (service_role 키)
- `POST /api/chat` 엔드포인트 스켈레톤 (에러 처리 구조만)

**FE1**
- 채팅 페이지 레이아웃 (`/chat`)
  - 캐릭터 영역 (좌) + 메시지 영역 (우) + 입력창 (하단)
- Zustand 스토어 설계
  ```ts
  useAxisStore  // { F, E, I, H, C, updateAxes() }
  useChatStore  // { messages, addMessage(), isStreaming }
  ```
- Canvas2D 기본 렌더링 루프 (60fps, `requestAnimationFrame`)
- Superformula 원형 기본 렌더링

**AI1 (Phase 1)**
- Rule-Based 발화 분석기 완성
  - 키워드 사전 200개 (슬랭, 격식어, 감탄사, 밈)
  - 패턴 매칭: 축약어, 이모지, 질문빈도, 문장 복잡도
  - 가중치 테이블
- 200개 샘플 대비 정확도 평가 (`pytest`)

### Sprint 2 (7월 15~31일)

**PM1**
- 중간 데모 시나리오 초안 (3가지 발화 스타일 비교)
- Sprint 1 회고 진행

**BE1**
- MATRIX 엔진 FastAPI 통합 (AI1과 협업)
- 발화 분석기 → MATRIX 연산 → EMA 업데이트 서비스 레이어 연결

**FE1**
- Superformula 5축 완전 연동
  ```
  Humor     → m (꼭짓점 수: 원↔별↔클로버)
  Formality → n1 (각진 정도)
  Energy    → 눈 크기/형태 (점↔별 눈)
  Intimacy  → HSL hue (파랑↔핑크)
  Curiosity → scale sin() 호흡 효과
  ```
- lerp 전환 (0.3초), 눈 깜빡임 (3~6초 랜덤)
- Idle 부유 효과 (`y += sin(time)`)

**AI1 (Phase 1)**
- MATRIX 엔진 완성
  - `W × [F,E,I,H,C]ᵀ + bias` 가중합
  - 0~100 클리핑
- EMA 모듈 (Intimacy `α=0.1`, 나머지 `α=0.5`)
- 전체 단위 테스트 (`pytest`) — 정확도 리포트 작성

**7월 완료 기준:**
- `pytest tests/` 전체 통과
- Canvas2D에서 캐주얼 vs 격식 발화 시 캐릭터 형태 눈에 띄게 다름 (로컬)
- FastAPI ↔ MATRIX 엔진 연결 완료

---

## 8월 — 핵심 개발 2

> **목표:** 전체 대화 흐름 완성 + Slang 파이프라인 + 배포

### Sprint 3 (8월 1~14일)

**PM1**
- E2E 테스트 시나리오 작성 (5개 케이스)
- 중간 발표 자료 준비 (교수님 피드백용)

**BE1 (Phase 2)**
- `POST /api/chat` 완전 구현
  ```
  입력: { user_id, conversation_id, message }
  처리:
    1. 이전 축 점수 조회 (Supabase)
    2. 발화 분석기 호출 → raw 5축 점수
    3. EMA 업데이트
    4. W × v + bias → 캐릭터 파라미터
    5. system prompt 구성
    6. GPT-4o 호출 (SSE 스트리밍)
    7. Supabase 저장 (대화 + 축 점수)
  출력: SSE 스트리밍 텍스트 + 완료 시 축 점수 JSON
  ```
- System prompt builder 구현 (캐릭터 파라미터 → GPT-4o 지시문)
- 에러 핸들링 7케이스 전부 구현

  | Case | Fallback |
  |------|---------|
  | 발화 분석기 실패 | 이전 점수 유지 |
  | GPT-4o timeout | 3회 재시도 → 에러 메시지 |
  | 응답 파싱 실패 | 텍스트만 반환, 점수 유지 |
  | 축 점수 범위 초과 | clamp(0, 100) |
  | Supabase 저장 실패 | 응답은 정상 반환, 로그만 |
  | Reddit rate limit | 기존 슬랭 데이터 사용 |
  | Canvas NaN/undefined | 기본값 50 적용 |

**FE1 (Phase 3)**
- SSE 클라이언트 구현 (텍스트 스트리밍 실시간 렌더링)
- Zustand → Canvas2D 실시간 연결
- 5축 점수 시각화 패널 (레이더 차트 또는 바 차트)
- 로딩/에러 UI 상태 처리

**AI1**
- GPT-4o API 실제 호출 테스트 (응답 품질 확인)
- system prompt 품질 검토 (캐주얼/격식/유머 발화별 응답 차이)

### Sprint 4 (8월 15~31일)

**PM1**
- Vercel + Railway 배포 완료 확인
- 버그 트래킹 우선순위 결정
- `docs/adr/` 3개 작성 (FastAPI 선택, Supabase pgvector, Superformula vs Rive)

**BE1**
- Vercel(FE) + Railway(BE) 배포 설정
- 환경변수 관리 분리 (로컬 `.env`, 배포 환경변수)
- 대화 이력 조회 API (`GET /api/conversations/:id`)
- 배포 환경 E2E 확인

**FE1**
- 대화 이력 페이지 (`/history`)
- 온보딩 화면 (캐릭터 첫 소개)
- 반응형 디자인 (모바일 대응)
- 최종 와이어프레임 대비 UI 검토 (PM1과 함께)

**AI1 (Phase 5 — Slang Pipeline)**
- PRAW Reddit 수집 스크립트 작성
  - `r/slang`, `r/GenZ`, `r/OutOfTheLoop`
  - 업보트 기준 필터링
- `text-embedding-3-small` 벡터화 → Supabase `slang_entries` 저장
- 코사인 유사도 벡터 검색 쿼리 작성
- System prompt에 Humor 축 기반 슬랭 빈도 조절 주입
- GitHub Actions cron 설정 (주 1회 자동 수집)

**8월 완료 기준:**
- 배포된 URL에서 메시지 → 스트리밍 응답 → 캐릭터 변화 전체 동작
- Slang 검색 → system prompt 반영 확인
- 에러 핸들링 7케이스 테스트 통과

---

## 9월 — 통합 & ML 모델

> **목표:** ML 발화 분석기 + A/B 비교 + E2E 안정화

### Sprint 5 (9월 1~14일)

**PM1**
- 사용자 테스트 모집 (5~10명) 및 진행
- 졸업 발표 PPT 구조 설계
- 버그 리스트 취합 + 우선순위 결정

**BE1**
- ML 모델 서빙 엔드포인트 (`/api/analyze/ml`)
- Rule-Based vs ML 라우팅 (feature flag)
- 앱 사용 데이터 수집 로그 확인 (발화 → 점수 쌍 축적 현황)
- Rate limiting (GPT-4o 비용 보호)

**FE1**
- 사용자 테스트 피드백 기반 UX 개선
- 캐릭터 애니메이션 튜닝 (더 자연스러운 lerp 전환)
- `tone_casual`, `energy_level`, `humor_level` 수치 표시 토글 (디버그 모드)

**AI1 (Phase 4 — ML 모델)**
- 앱 사용 데이터 파이프라인 (발화 + Rule-Based 점수 쌍 자동 축적)
- ML 모델 학습
  - `sentence-transformers` 임베딩
  - 5축 regression head (각 축별 MAE 측정)
- A/B 비교 실험 설계
  - 평가 메트릭: MAE per axis
  - 200개 샘플 + 앱 수집 데이터 분리

### Sprint 6 (9월 15~30일)

**PM1**
- 졸업 발표 PPT draft 완성
- 데모 시나리오 최종 확정 (3가지 발화 스타일)
- 최종 README 업데이트

**BE1**
- ML 모델 최종 통합 (Rule-Based는 fallback 유지)
- 성능 모니터링 (Railway 로그, Supabase 쿼리 최적화)
- 보안 점검 (RLS 확인, API key 노출 없는지)

**FE1**
- 시연용 데모 계정 세팅
- 최종 UI 버그 수정
- 5분 연속 대화 안정 동작 확인

**AI1**
- A/B 비교 실험 결과 정리 (Rule-Based vs ML MAE 비교표)
- EMA alpha 튜닝 (실제 대화 데이터 기반)
- 핵심기술 설명 자료 작성 (발표용 — 발화 → 5축 → MATRIX → 캐릭터 흐름 시각화)

**9월 완료 기준:**
- 배포 환경에서 5분 연속 대화 안정 동작
- ML vs Rule-Based A/B 결과 수치 확보
- 발표 PPT draft 완성

---

## 10월 — QA & 최종 발표

> **목표:** 완성도 높은 데모 + 발표 준비

### 10월 1~15일

**PM1**
- 발표 리허설 (2회 이상)
- 역할 분담 확정 (발표자 누가 어느 파트)
- 최종 제출 문서 패키징

**전 팀원**
- 핵심 시연 3가지 최종 점검
  ```
  시나리오 1: "yo what's up lol"
    → Humor 높음, 둥근 별 모양, 핑크, 큰 눈 캐릭터
    → GPT: 가볍고 장난스러운 응답 + 슬랭 포함

  시나리오 2: "I would like to formally inquire about..."
    → Formality 높음, 각진 사각형, 차가운 파랑, 작은 눈
    → GPT: 정중하고 격식 있는 응답

  시나리오 3: "Why do you think people struggle with..."
    → Curiosity 높음, 호흡 효과 강함
    → GPT: 깊은 탐구형 응답
  ```
- Rule-Based vs ML A/B 결과 슬라이드 완성
- `docs/` 최종 정리 (PRD, 플로우, 와이어프레임, ADR 전부 최신화)

### 10월 16~31일
- 최종 발표
- 제출 마감 대응

---

## 산출물 체크리스트

### 기획 산출물 (5월)

| 문서 | 담당 | 경로 |
|------|------|------|
| PRD | PM1 | `docs/plan/PRD.md` |
| 유저 플로우 | PM1 | `docs/design/user-flow.md` |
| 와이어프레임 (6개 화면) | PM1+FE1 | `docs/design/wireframes/` |
| DB 스키마 초안 | BE1 | `docs/plan/db-schema.md` |

### 개발 산출물 (6~9월)

| 산출물 | 담당 |
|--------|------|
| Supabase DB + RLS | BE1 |
| FastAPI `/api/chat` (SSE, 에러 7케이스) | BE1 |
| Rule-Based 발화 분석기 + pytest 200개 | AI1 |
| MATRIX 엔진 + EMA 모듈 | AI1 |
| ML 발화 분석기 + A/B 비교 | AI1 |
| Slang Pipeline (PRAW + pgvector + Actions) | AI1 |
| Next.js 앱 (Auth, 채팅, 이력) | FE1 |
| Canvas2D Superformula 캐릭터 (5축 완전 연동) | FE1 |
| Vercel + Railway 배포 | BE1 |
| ADR 3개 | PM1+팀 |
| Rule-Based vs ML A/B 실험 결과 | AI1 |

---

## 리스크 & 대응

| 리스크 | 대응 |
|--------|------|
| GPT-4o 비용 초과 | Rate limiting + 팀 공용 키 사용량 모니터링 |
| ML 모델이 Rule-Based보다 낮은 정확도 | Rule-Based fallback 유지, 결과 그대로 발표 (이것도 발견임) |
| Canvas2D 60fps 유지 실패 | 파라미터 변화 없으면 렌더링 스킵 (dirty flag) |
| 8월 통합 지연 | Phase 5(Slang)는 발표에서 "확장 기능"으로 포지셔닝 가능 |
| 사용자 테스트 모집 실패 | 팀원 지인 5명 + 교수님 활용 |
