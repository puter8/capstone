# CharaShift 기능 명세서 (MVP v1.0)

> 데모 목표일: 2026.06.07  
> 범위: June 7 데모에 필요한 최소 기능만 포함. 그 외는 Post-MVP로 분리.

---

## 1. 서비스 개요

사용자가 영어로 대화하면 발화 스타일을 5개 축으로 분석하고, 그 결과에 따라 AI 캐릭터의 성격이 실시간으로 변하는 영어 회화 학습 서비스.

**핵심 가치:** "내 말투에 반응하는 AI"

---

## 2. 사용자 플로우

```
[랜딩 페이지]
    → 시작하기 클릭
    → [온보딩] 스타일 선택 (격식체 / 캐주얼 / 탐구형)
    → [채팅 화면]
        - 사용자 메시지 입력
        - 5축 분석 → 캐릭터 파라미터 계산
        - GPT-4o 캐릭터 응답 표시
        - 5축 점수 패널 업데이트
        - 캐릭터 형태 변화 (Canvas2D)
```

---

## 3. 화면 구성

### 3-1. 랜딩 페이지 (`/`)
- 서비스 한 줄 소개
- "대화 시작하기" 버튼 → `/chat`으로 이동
- MVP에서는 로그인 없이 익명 세션으로 진입

### 3-2. 온보딩 (`/onboarding`)
- 초기 발화 스타일 선택 (3가지 옵션)

| 옵션 | 설명 | 5축 초기값 |
|------|------|------------|
| 캐주얼 | 친근하고 편한 대화 | Formality:20, Energy:70, Intimacy:60, Humor:50, Curiosity:40 |
| 격식체 | 정중하고 차분한 대화 | Formality:80, Energy:30, Intimacy:20, Humor:10, Curiosity:40 |
| 탐구형 | 질문 많고 호기심 있는 대화 | Formality:50, Energy:50, Intimacy:40, Humor:30, Curiosity:80 |

- 선택 후 세션에 초기 5축 값 저장 → `/chat`으로 이동

### 3-3. 채팅 화면 (`/chat`)

**레이아웃 (3열 구성):**
```
┌──────────────┬────────────────────┬──────────────┐
│  캐릭터 패널  │     채팅 영역       │  5축 패널    │
│  (Canvas2D)  │  메시지 목록        │  Formality   │
│              │  입력창             │  Energy      │
│  형태 변화   │                     │  Intimacy    │
│  실시간 반영  │                     │  Humor       │
│              │                     │  Curiosity   │
└──────────────┴────────────────────┴──────────────┘
```

**채팅 영역 상세:**
- 메시지 목록: 사용자(오른쪽), AI 캐릭터(왼쪽)
- 입력창: 영어 텍스트 입력 + 전송 버튼 (Enter 키도 동작)
- AI 응답은 스트리밍으로 표시 (타이핑 효과)

**5축 패널 상세:**
- 5개 축 각각 수치(0~100)와 바 형태로 표시
- 메시지 전송 시 애니메이션으로 수치 변화
- 현재 캐릭터 파라미터 표시 (tone_casual, energy_level, humor_level)

**캐릭터 패널 상세:**
- Canvas2D Superformula 기반 도형
- tone_casual, energy_level, humor_level 값에 따라 형태 변화
- 응답 생성 중 로딩 애니메이션

---

## 4. 기능 상세 명세

### F1. 세션 초기화

**트리거:** 온보딩에서 스타일 선택 완료  
**동작:**
1. 선택한 스타일 기반 초기 5축 값을 세션 스토리지에 저장
2. `session_id` 생성 (UUID)
3. `/chat`으로 이동

**저장 형태:**
```json
{
  "session_id": "uuid",
  "axes": {
    "Formality": 50,
    "Energy": 50,
    "Intimacy": 40,
    "Humor": 30,
    "Curiosity": 80
  }
}
```

---

### F2. 메시지 전송 및 응답

**트리거:** 사용자가 영어 문장 입력 후 전송  
**동작 순서:**

```
1. 입력창 비우기 + 로딩 상태 표시
2. POST /api/chat 호출
3. 서버에서:
   a. analyze_utterance(message) → 새 5축 점수
   b. apply_ema(prev_axes, new_axes) → 누적 5축 점수
   c. compute_character(smoothed_axes) → 캐릭터 파라미터
   d. GPT-4o 호출 (시스템 프롬프트 + 캐릭터 파라미터 주입)
   e. 응답 반환
4. 채팅창에 AI 응답 표시
5. 5축 패널 수치 업데이트 (애니메이션)
6. 캐릭터 형태 업데이트
7. 세션 스토리지의 axes 값 갱신
```

**요청 형식:**
```json
POST /api/chat
{
  "message": "yo what's up lol",
  "session_id": "uuid",
  "current_axes": {
    "Formality": 50,
    "Energy": 50,
    "Intimacy": 40,
    "Humor": 30,
    "Curiosity": 80
  }
}
```

**응답 형식:**
```json
{
  "reply": "omg heyyy!! what's the vibe today??",
  "new_axes": {
    "Formality": 18,
    "Energy": 65,
    "Intimacy": 55,
    "Humor": 47,
    "Curiosity": 62
  },
  "character": {
    "tone_casual": 72,
    "energy_level": 61,
    "humor_level": 44
  }
}
```

---

### F3. GPT-4o 시스템 프롬프트 (AI 파트 담당)

캐릭터 파라미터를 받아 응답 방식을 지시하는 프롬프트 구조:

```
You are an English conversation partner named Pally.
Your personality adapts based on the following parameters (0-100 scale):

- tone_casual: {value} → 0=very formal, 100=very casual/slangy
- energy_level: {value} → 0=calm and quiet, 100=enthusiastic and lively  
- humor_level: {value} → 0=serious and direct, 100=playful and meme-friendly

Respond in English only. Keep responses to 1-3 sentences.
Match your tone, energy, and humor to the parameters above.
Do not mention these parameters or that you are adjusting your style.

[tone_casual > 60] Use contractions, casual words, maybe light slang.
[tone_casual < 30] Use formal vocabulary, complete sentences, polite phrasing.
[energy_level > 60] Use exclamations, show excitement, be expressive.
[energy_level < 30] Be measured, calm, minimal punctuation.
[humor_level > 60] Light jokes, wordplay, memes references are okay.
[humor_level < 30] Stay focused and sincere, skip jokes.

Conversation history:
{history}

User: {message}
Pally:
```

---

### F4. 캐릭터 시각화 (Canvas2D)

**Superformula 파라미터 매핑:**

| 캐릭터 파라미터 | Canvas2D 영향 |
|----------------|---------------|
| tone_casual | 꼭짓점 수 (낮을수록 뾰족, 높을수록 둥글고 유기적) |
| energy_level | 크기 / 진동 주파수 |
| humor_level | 색상 채도 / 불규칙성 |

**업데이트 시점:** 메시지 응답 도착 직후 부드러운 트랜지션으로 변경

---

## 5. API 명세

| 메서드 | 경로 | 담당 | 설명 |
|--------|------|------|------|
| POST | `/api/chat` | BE | 메시지 전송 및 응답 |
| GET | `/api/health` | BE | 서버 상태 확인 |

### POST /api/chat

**Request:**
```typescript
{
  message: string          // 사용자 발화
  session_id: string       // 세션 ID
  current_axes: {          // 현재 누적 5축 점수
    Formality: number      // 0-100
    Energy: number
    Intimacy: number
    Humor: number
    Curiosity: number
  }
}
```

**Response:**
```typescript
{
  reply: string            // GPT-4o 응답
  new_axes: {              // EMA 적용 후 새 5축 점수
    Formality: number
    Energy: number
    Intimacy: number
    Humor: number
    Curiosity: number
  }
  character: {             // 캐릭터 파라미터
    tone_casual: number
    energy_level: number
    humor_level: number
  }
}
```

---

## 6. DB 스키마 (Supabase)

MVP에서는 로그인 없이 세션 기반으로 단순화. 단, 스키마는 추후 확장 가능하게.

```sql
-- 세션 (익명 사용자 단위)
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMP DEFAULT NOW(),
  initial_style TEXT  -- 'casual' | 'formal' | 'curious'
);

-- 메시지 이력
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id),
  role TEXT NOT NULL,  -- 'user' | 'assistant'
  content TEXT NOT NULL,
  axes JSONB,          -- 해당 턴의 5축 점수
  character JSONB,     -- 해당 턴의 캐릭터 파라미터
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 7. 환경변수 (.env)

```
# OpenAI
OPENAI_API_KEY=

# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# FastAPI
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 8. MVP 범위 정의

### 포함 (June 7 데모)
- [x] 익명 세션 기반 채팅 (로그인 없음)
- [x] 5축 실시간 분석 및 패널 표시
- [x] GPT-4o 캐릭터 성격 반영 응답
- [x] EMA 기반 세션 내 성격 누적
- [x] Canvas2D 캐릭터 형태 변화
- [x] 온보딩 초기 스타일 선택

### 제외 (Post-MVP)
- [ ] 회원가입 / 로그인
- [ ] 대화 이력 영구 저장
- [ ] Reddit PRAW 슬랭 파이프라인
- [ ] 세션 종료 후 문법 피드백
- [ ] STT / TTS
- [ ] ML 기반 발화 분석기 전환

---

## 9. 데모 시나리오 (June 7)

발표에서 보여줄 3가지 대조 케이스:

**케이스 1 — 캐주얼 발화**
```
입력: "yo what's up lol, u wanna hang or nah?"
기대: Formality↓, Energy↑, Humor↑ → 캐릭터가 친근하고 장난스러운 응답
```

**케이스 2 — 격식 발화**
```
입력: "I would like to formally inquire about this matter."
기대: Formality↑, Energy↓ → 캐릭터가 정중하고 차분한 응답
```

**케이스 3 — 연속 대화로 성격 변화**
```
격식체로 시작 → 점점 캐주얼하게 바꾸기
→ 캐릭터가 서서히 변하는 과정을 5축 패널로 보여줌
```
