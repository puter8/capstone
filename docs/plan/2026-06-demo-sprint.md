# June 8 데모 스프린트 계획

> 데모일: **2026-06-08**  
> 작성일: 2026-05-21  
> 각 트랙 난이도: ★★★★ (균등 분배)

---

## 트랙 요약

| 트랙 | 담당자 | 작업 | 난이도 |
|------|--------|------|--------|
| **A** | 이찬희 | Figma → 화면 구현 (랜딩/온보딩/채팅) + 피드백 FE | ★★★ + ★ |
| **B** | 김민주 | Canvas2D Superformula 캐릭터 변화 고도화 | ★★★★ |
| **C** | 백은혜 | STT 안정화 + TTS 추가 + `/api/feedback` BE | ★★★ + ★ |

### 시작 순서

```
A ──────────────────────────────────────────▶  피드백 FE 완료
B ──────────────────────────────────────────▶  캐릭터 완료
C ── STT/TTS ─────────────────────────────▶  피드백 BE 완료
                                   ↑
              C의 피드백 BE는 A의 피드백 FE 완료 후 연결
```

- A, B, C **동시 착수 가능**
- **블로킹 의존:** C의 피드백 BE 연결 → A의 피드백 FE UI 완료 후 진행

---

## A — 이찬희 ★★★★

### A-1. Figma → 실제 화면 적용 ★★★

**랜딩 페이지 (`/`)**
- 서비스 한 줄 소개 + "대화 시작하기" 버튼
- CTA 클릭 → `/login`

**로그인 (`/login`)**
- 캐릭터 이미지 + 환영 문구
- Google 로그인 버튼 (흰 배경, Google 아이콘)
- 카카오로 시작하기 버튼 (노란 배경, 카카오 아이콘)
- Supabase Auth OAuth 연결: Google + Kakao

**온보딩 4단계 (`/onboarding/1~4`)**

| 화면 | 내용 | 핵심 컴포넌트 |
|------|------|--------------|
| 온보딩 1 | "대화할수록 나를 닮아가는 영어 친구" + 캐릭터 애니메이션 + 페이지 인디케이터 | SlideIntro |
| 온보딩 2 | 영어 레벨 선택 (A2/B1/B2/C1), 선택 시 주황 테두리 강조 | LevelSelector |
| 온보딩 3 | Pally 이름 입력창 + 추천 버튼 (Bobo/Mama/Coco/Nana) | NameInput |
| 온보딩 4 | 유저 이름 입력창 + 추천 버튼 | NameInput |

- 완료 후 Supabase `user_profiles` 저장 → `/chat` 이동

**채팅 메인 (`/chat`)**
- 3열 레이아웃:
  ```
  ┌────────────┬──────────────────┬────────────┐
  │ 캐릭터 패널 │   채팅 영역       │  5축 패널  │
  │ (Canvas2D) │ 메시지 목록       │  수치 바   │
  │            │ 입력창 + 마이크   │            │
  └────────────┴──────────────────┴────────────┘
  ```
- 메시지 목록: 사용자(우) / AI(좌), 스트리밍 타이핑 효과
- 입력창: 텍스트 입력 + Enter 전송 + 마이크 버튼(STT)
- 상단: 잔여 토큰 표시 (`💬 남은 대화: N턴`)
- UI 상단 상시 표시: "AI 캐릭터와 대화 중"

**토큰 소진 바텀시트**
- 캐릭터 이미지 + `"{pally_name}(이)가 더 대화하고 싶어해요!"`
- 패키지 선택 UI (스타터/베이직/플러스)
- "충전하기" + "나중에" 버튼

---

### A-2. `/feedback` 페이지 UI 구현 ★

채팅 화면 하단 슬라이드업 피드백 패널:

```
┌─────────────────────────────────┐
│ ✏️  Correction                  │
│  "You could say 'What's up?'"  │
│  [▶ 듣기]                       │
├─────────────────────────────────┤
│ 💬  Tone Feedback               │
│  "Your casual tone is great!"  │
├─────────────────────────────────┤
│ 🎯  Practice This               │
│  "Try saying it more formally." │
└─────────────────────────────────┘
```

- `FeedbackCard` 컴포넌트: correction / tone_feedback / practice_prompt 3종
- [▶ 듣기] 버튼: `/api/tts` 호출 → MP3 재생
- **정적 Mock 데이터로 먼저 구현** → C 트랙 BE 완료 후 실 API 연결

---

### A 완료 기준

- [ ] 로그인 → 온보딩 4단계 → 채팅 전체 라우팅 동작
- [ ] Supabase Auth (Google/Kakao) 로그인 동작
- [ ] 채팅 3열 레이아웃 + 토큰 표시 렌더링
- [ ] 피드백 카드 3종 Mock UI 표시
- [ ] TTS 듣기 버튼 동작

---

## B — 김민주 ★★★★

### B-1. Canvas2D Superformula 형태 변화 고도화

**렌더링 기반**
- `requestAnimationFrame` 60fps 루프
- Superformula 수식: `r(θ) = (|cos(mθ/4)/a|ⁿ² + |sin(mθ/4)/b|ⁿ³)^(-1/n1)`
- 성능 최적화: 파라미터 변화 없으면 렌더링 스킵 (dirty flag)

**5축 → Canvas 파라미터 매핑**

| 입력 | Canvas 효과 | 상세 |
|------|-------------|------|
| `tone_casual` (0~100) | 꼭짓점 수 `m` | 0→각진 별(m=4~6), 100→둥근 유기체(m=2~3) |
| `Formality` (0~100) | 각진 정도 `n1` | 높을수록 기하학적, 낮을수록 부드러운 곡선 |
| `energy_level` (0~100) | 전체 크기 + 눈 크기 | 70↑ → 크고 반짝임, 30↓ → 작고 차분 |
| `Intimacy` (0~100) | 색상 HSL hue | 0=차가운 파랑(220°), 100=따뜻한 핑크(350°) |
| `humor_level` (0~100) | 색상 채도 | 높을수록 선명하고 불규칙한 형태 |
| `Curiosity` (0~100) | 호흡 sin 강도 | 높을수록 빠르고 강한 부유 효과 |

**표정 변화**
- 눈: 에너지 높음 → 별 눈(★), 에너지 낮음 → 반원 눈(◡)
- 눈 깜빡임: 3~6초 랜덤 인터벌
- Idle 부유: `y += sin(time * speed) * amplitude`

**트랜지션**
- lerp(선형 보간) 0.3초 부드러운 형태 전환
- 응답 생성 중 로딩 애니메이션 (회전 또는 진동)

**테스트 도구**
- 개발 중 슬라이더 UI로 5축 값 수동 조절 → 캐릭터 변화 실시간 확인
- 데모 시나리오 3가지 형태 차이 눈에 띄게 검증:

  | 시나리오 | 예상 형태 | 색상 |
  |----------|-----------|------|
  | 캐주얼 ("yo lol") | 둥근 별, 큰 눈 | 핑크/따뜻함 |
  | 격식 ("I would like to...") | 각진 사각형, 작은 눈 | 차가운 파랑 |
  | 탐구형 ("Why do you think...") | 호흡 강함, 균형 형태 | 중간 채도 |

**Zustand 연결**
```ts
useCharacterStore: { tone_casual, energy_level, humor_level }
// /api/chat 응답 수신 시 스토어 업데이트 → Canvas 자동 반영
```

### B 완료 기준

- [ ] 캐주얼 vs 격식 발화 시 캐릭터 형태 차이 육안으로 명확히 구분
- [ ] lerp 전환 0.3초 동작 (형태/색상 모두)
- [ ] 눈 깜빡임 + Idle 부유 효과 동작
- [ ] 60fps 유지 (Chrome DevTools 확인)
- [ ] Zustand 스토어에서 파라미터 받아 실시간 반영

---

## C — 백은혜 ★★★★

### C-1. STT 안정화 + TTS 추가 ★★★

**STT 안정화 (`POST /api/stt`)**
- Google Cloud Speech-to-Text v1 (기존 구현 기반)
- 개선 사항:
  - webm/opus, MP3, WAV, FLAC 포맷 자동 감지 (`_detect_encoding`)
  - 무음 입력 시 `{ transcript: "", confidence: 0.0 }` 정상 반환
  - 60초 초과 오디오 → 409 에러 + 안내 메시지 반환
  - Google STT 실패 시 상세 에러 메시지 반환 (현재는 502 raw)
- 테스트: 실제 영어 발화 5가지 유형으로 transcript 품질 확인
  - 캐주얼 슬랭, 격식체, 짧은 문장, 긴 문장, 배경 소음 포함

**TTS 추가 (`POST /api/tts`)**
- Google Cloud Text-to-Speech v1 (기존 구현 기반)
- 응답: `{ audio_b64, voice, encoding: "MP3" }`
- 기본 음성: `en-US-Journey-F`
- TTS 실패 시 FE가 조용히 무시하도록 null 반환 (대화 흐름 유지)

---

### C-2. `/api/feedback` 엔드포인트 고도화 ★

**기존 구현 (`backend/main.py`) 기반 개선**

현재 구조:
```
utterance → analyze_utterance() → apply_ema() → compute_character()
         → Gemini 2.5 Flash → { correction, tone_feedback, practice_prompt }
         → Google TTS → tts_audio (base64 MP3)
```

개선 사항:
1. **영어 레벨 파라미터 추가:**
   ```json
   요청: { "utterance": "...", "current_axes": {...}, "english_level": "B1" }
   ```
   - Gemini 프롬프트에 레벨 정보 주입 → correction 난이도 조절
   - A2: 아주 간단한 교정, C1: 고급 표현 대안 제시

2. **Gemini 프롬프트 품질 개선:**
   ```
   레벨별 지시문 예시:
   [A2] correction은 기초 문법 오류만 수정. 쉬운 어휘만 사용.
   [B1] correction은 자연스러운 표현 대안 제시. 일상 어휘 범위.
   [B2] correction은 뉘앙스/어조 개선까지 포함.
   [C1] correction은 고급 어휘·관용구 대안 제시.
   ```

3. **응답 스키마 확정:**
   ```json
   {
     "status": "ok",
     "axes": { "Formality": 18, "Energy": 65, "Intimacy": 55, "Humor": 47, "Curiosity": 62 },
     "character": { "tone_casual": 72, "energy_level": 61, "humor_level": 44 },
     "character_labels": { "tone": "casual", "energy": "lively", "humor": "playful" },
     "feedback": {
       "correction": "You could say 'What's the vibe today?' instead.",
       "tone_feedback": "Your casual energy is really coming through!",
       "practice_prompt": "Can you say the same thing more formally?"
     },
     "tts_audio": "(base64 MP3 또는 null)"
   }
   ```

4. **A 트랙 피드백 FE 완료 후 연결:**
   - A의 `FeedbackCard` 컴포넌트가 완성되면 실 API 연결
   - 연결 전: A는 Mock 데이터로 UI 개발 진행

### C 완료 기준

- [ ] STT: 영어 발화 5가지 유형 transcript 정상 반환
- [ ] TTS: correction 문장 MP3 정상 반환 + FE 재생 확인
- [ ] `/api/feedback`: 영어 레벨별 교정 품질 차이 확인 (A2 vs C1 비교)
- [ ] Gemini fallback 동작 확인
- [ ] A 트랙 피드백 FE와 연결 완료

---

## 통합 의존 관계

```
[A] 피드백 FE UI 완료
        ↓
[C] /api/feedback 실 API 연결 (C의 피드백 BE 마지막 단계)
        ↓
[전체] /chat 화면에서 메시지 → AI 응답 + 피드백 카드 + 캐릭터 변화 통합 확인
```

**A ↔ B 연결:**
- A가 Zustand `useCharacterStore` 스토어 정의
- B가 Canvas2D에서 스토어 구독해 파라미터 반영
- `/api/chat` 응답의 `character` 필드 → Zustand 업데이트 → Canvas 자동 반영

---

## 데모 완료 기준 체크리스트

### 인프라 (이찬희 선행)
- [ ] Vercel 배포 URL 접근 가능
- [ ] Railway 백엔드 `/api/health` 200 응답
- [ ] Supabase 연결 + RLS 동작

### 기능 통합
- [ ] Google 또는 카카오 로그인 동작
- [ ] 온보딩 4단계 완료 → 채팅 진입
- [ ] 영어 메시지 전송 → AI 응답 수신
- [ ] 5축 패널 수치 변화 (메시지마다 업데이트)
- [ ] 캐릭터 형태 변화 (캐주얼 vs 격식 발화 차이 육안으로 구분)
- [ ] AI 피드백 카드 3종 표시 (correction / tone / practice)
- [ ] correction TTS 재생 ([▶ 듣기] 버튼)
- [ ] STT 마이크 버튼 → 음성 → 입력창 자동 삽입
- [ ] 잔여 토큰 표시 + 소진 시 바텀시트 표시
