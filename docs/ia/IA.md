# Pally MVP — Information Architecture

> Pally(CharaShift) MVP의 화면 구조 · 네비게이션 · 데이터 모델 · 상태를 한 곳에 정리한 PM 산출 문서.
> 코드 진실(`frontend/app/`, `backend/main.py`)과 충돌 시 코드 우선. 본 문서는 코드 변경 시 함께 갱신한다.

- Owner: 최윤서 (PM)
- 최신화: 2026-05-31
- 대상 데모: 2026-06-07
- 디바이스 기준: **모바일 폭 402px 고정** (Figma 기준, 데스크톱은 모바일 뷰)

---

## 0. 이 문서의 위치

| 문서 | 다루는 것 |
|---|---|
| `README.md` | 제품 한 줄 소개 + 데모 URL + 로컬 실행 |
| `.planning/ROADMAP.md` | Phase 단위 일정·owner |
| `DESIGN.md` / `docs/design/` | 색·타이포·토큰·컴포넌트 비주얼 |
| `docs/mvp/PRD.md` | 왜 만드는가 (problem·solution) |
| **`docs/ia/IA.md` (이 문서)** | **무엇을 어디에 두는가** — 화면·내비·콘텐츠·상태 |
| `docs/qa/PRE_DEMO_QA.md` | 데모 직전 통과 기준 |

---

## 1. 대상 사용자 · 사용 컨텍스트

| 항목 | 값 |
|---|---|
| 1차 사용자 | 영어 회화에 자신 없는 20대 한국인 학습자 |
| 사용 디바이스 | 모바일 브라우저(Safari iOS / Chrome Android) |
| 사용 자세 | 한 손 세로, 마이크 가까이 |
| 1회 세션 길이 | 1~3분 (발화 3~5턴) |
| 네트워크 가정 | 안정적인 Wi-Fi/LTE (대용량 오디오 왕복 전제) |

설계 제약:
- 한 화면에 **5축 점수를 노출하지 않는다.** Pally의 변화 자체가 피드백.
- 사용자가 직접 누르는 버튼은 화면당 **최대 2개** (TalkButton + 세션 종료 X).
- 텍스트 길이 < 2줄. 한국어 인라인 힌트만 예외.

---

## 2. 사이트맵

```text
/ (root)
└─ redirect → /home

/home                ★ 메인 — 녹음, 응답, Pally 변형, 인라인 힌트
/history             대화 기록 (MVP 스텁)
/ranking             랭킹 (MVP 스텁)
/my                  마이페이지 (MVP 스텁)

/dev/pally           [internal] Pally 렌더러 테스트 (GNB에서 접근 불가)
/api/health          [internal] FE 헬스 라우트
```

**MVP에서 동작하는 화면은 `/home` 하나.** 나머지 3개는 GNB 라벨/라우팅만 살아 있고 내용은 placeholder. 데모 시나리오는 `/home`에서 시작해 `/home`에서 끝난다.

라우트 코드: `frontend/app/<route>/page.tsx`

---

## 3. 글로벌 내비게이션 (GNB)

`frontend/components/nav/BottomNav.tsx` 기준.

### 구조

| 위치 | 컴포넌트 | 라벨 | 라우트 | MVP 동작 |
|---|---|---|---|---|
| 좌1 | tab | 홈 | `/home` | ✅ 동작 |
| 좌2 | tab | 학습 | `/history` | placeholder |
| 중앙 | FAB | "새 대화" (`+`) | — | **disabled** (MVP 무동작) |
| 우1 | tab | 랭킹 | `/ranking` | placeholder |
| 우2 | tab | 내 정보 | `/my` | placeholder |

### 규칙

- GNB는 **모든 메인 라우트에 노출**되고 위치 고정 (bottom: 10px).
- 현재 라우트 탭은 `#FFB84A`, 비활성은 `#FFFFFF`. (`mask-image` 틴팅)
- FAB는 데모 시 **회색 빠진 비활성 상태로 노출**. 누르면 아무 일도 일어나지 않는다. (정책상 의도된 비활성)
- `/dev/*`, `/api/*`는 GNB에서 진입 불가. 직접 URL로만.

### 의도된 비대칭

- `/home`만 동작하는 이유는 데모 범위 한정. **빈 화면이라도 4탭을 띄우는 이유는 "제품이 어떻게 자랄지"를 한 화면에 보이기 위함**이다. 데모 발표 스크립트에서도 동일하게 설명.

---

## 4. 화면 인벤토리

### 4.1 `/home` — 메인

**역할:** 사용자가 영어 한 문장을 말하면 Pally가 변형·응답한다. 제품 가치 전체가 이 화면에 압축됨.

**Layout (top → bottom):**

| 영역 | 컴포넌트 | 비고 |
|---|---|---|
| 상단 우 | 세션 종료 `X` 버튼 | 세션 중에만 노출. 누르면 최종 Pally 컷신 |
| 중앙 상 | `PallyCanvas` | Canvas2D Superformula. 5축 변화 즉시 반영 |
| 중앙 하 | `ChatBubble` 스택 | 사용자 발화 + Pally 응답 1쌍씩 |
| (조건부) | 인라인 한국어 힌트 | Gemini가 어색한 영어 감지 시 |
| (빈 상태) | `EmptyGreeting` | 첫 진입 시 "안녕, 나는 Pally야" |
| 하단 | `TalkButton` (FAB과 분리) | 5-state 시각 |
| 최하단 | `BottomNav` | 위 §3 |

**핵심 인터랙션:**
1. TalkButton 탭 → 권한 요청 → 녹음 시작 (max 30s)
2. 탭/30s 만료 → 녹음 종료 → 백엔드 왕복
3. STT 결과 `ChatBubble`에 사용자 메시지로 추가
4. Gemini 응답 `ChatBubble`에 Pally 메시지로 추가
5. `PallyCanvas` 즉시 새 5축으로 변형
6. TTS 자동 재생
7. (옵션) 인라인 한국어 힌트 노출

**Out:**
- `X` 버튼 → "최종 Pally 공개" 컷신 → 세션 종료 → 다시 빈 상태

**구현 파일:** `frontend/app/home/page.tsx`

### 4.2 `/history` — 대화 기록 (스텁)

| 항목 | 값 |
|---|---|
| MVP 동작 | placeholder만 |
| 의도 | 과거 세션 리스트 → 탭하면 발화·5축 그래프 |
| 데이터 소스 | `messages` 테이블 (이미 저장됨) |
| 데모 시 | 탭 진입 가능, 안에는 "준비 중" |

### 4.3 `/ranking` — 랭킹 (스텁)

| 항목 | 값 |
|---|---|
| MVP 동작 | placeholder만 |
| 의도 | 5축별 사용자 순위, "오늘의 캐릭터" |
| 데모 시 | 탭 진입 가능, 안에는 "준비 중" |

### 4.4 `/my` — 내 정보 (스텁)

| 항목 | 값 |
|---|---|
| MVP 동작 | placeholder만 |
| 의도 | 누적 Pally 상태, 학습 통계, 로그아웃 |
| 데모 시 | 탭 진입 가능, 안에는 "준비 중" |

### 4.5 `/dev/pally` — 내부 (비공개)

| 항목 | 값 |
|---|---|
| 용도 | 5축 슬라이더로 Pally 렌더러 직접 조작 |
| 접근 | URL 직접 입력만. GNB 미노출 |
| 데모 시 | 사용 안 함. 발표 환경에서는 열지 않는다 |

---

## 5. 메인 사용자 흐름

### 5.1 골든 패스 (데모 시나리오)

```
[1] /home 진입
     ↓ (자동) 빈 상태 + EmptyGreeting
[2] TalkButton 탭
     ↓ 마이크 권한 요청 (최초 1회)
     ↓ 녹음 시작 (상태: recording)
[3] 영어 한 문장 발화 → TalkButton 다시 탭 (or 30s 자동)
     ↓ 녹음 종료
     ↓ POST /api/stt (multipart audio)
     ↓ 상태: thinking
[4] STT 결과 도착
     ↓ ChatBubble에 사용자 메시지 추가
     ↓ POST /api/chat { text }
[5] Gemini 응답 도착
     ↓ ChatBubble에 Pally 메시지 추가
     ↓ PallyCanvas: 5축 → 캐릭터 파라미터 즉시 반영
     ↓ (조건부) 인라인 한국어 힌트 노출
     ↓ POST /api/tts { text }
[6] TTS 오디오 자동 재생
     ↓ 상태: playing → idle
[7] (반복 2~5턴) → 누적 EMA로 Pally 점진 변형
[8] 우상단 X 탭
     ↓ 최종 Pally 컷신 (누적 파라미터 적용된 모습 공개)
     ↓ 세션 종료
[9] 다시 /home 빈 상태
```

### 5.2 분기/예외 흐름

| 분기 | 트리거 | 처리 |
|---|---|---|
| 마이크 권한 거부 | OS 다이얼로그 거부 | Toast "마이크 권한이 필요해요" + TalkButton 비활성 |
| STT 실패 (네트워크 등) | 5xx | Toast "다시 말해줘" + 사용자 메시지 미추가 |
| Gemini 실패 | 5xx | Toast + ChatBubble에 "..." 후 사라짐 |
| TTS 실패 | 5xx | 응답 텍스트만 표시 (오디오 생략) |
| 빈 발화 (STT 빈 문자열) | STT 200 + text="" | "안 들렸어" Toast |
| 30s 초과 | recorder timer | 자동 종료 후 정상 흐름 |
| 세션 중 라우트 이탈 | GNB 탭 | 녹음 중지, 진행 중 요청은 cancel |

---

## 6. 콘텐츠 모델 / 데이터 엔티티

### 6.1 핵심 엔티티 (Supabase 테이블)

```
sessions
├─ id (uuid, PK)
├─ session_id (text, 익명 식별자, RLS 키)
├─ created_at
├─ ended_at (nullable)
├─ final_axes (jsonb, 5축 최종)
└─ final_params (jsonb, 캐릭터 파라미터 최종)

messages
├─ id (uuid, PK)
├─ session_id (FK)
├─ role ('user' | 'pally')
├─ text
├─ axes (jsonb, 이 턴의 5축)
├─ params (jsonb, 이 턴 적용 후 캐릭터 파라미터)
├─ hint_ko (nullable, 인라인 한국어 힌트)
└─ created_at
```

RLS: 모든 row는 `session_id` 기준 격리. anonymous 세션만.

### 6.2 도메인 값

**5축 (Axes) — 입력:** `analyzer.py`에서 계산
- `Formality` 0–100
- `Energy` 0–100
- `Intimacy` 0–100
- `Humor` 0–100
- `Curiosity` 0–100

**캐릭터 파라미터 — 출력:** `matrix_engine.py`에서 가중합 → EMA(α=0.7)
- `tone_casual` 0–100
- `energy_level` 0–100
- `humor_level` 0–100

**Pally 시각화 — `PallyCanvas`가 위 파라미터로:**
- 형태(Superformula m·n1·n2·n3)
- 색상(채도/명도)
- 표정/입꼬리

### 6.3 데이터 흐름

```
사용자 오디오
   │
   ▼
[STT] Google Cloud STT (en-US)
   │
   ▼ 영어 텍스트
[5축 분석] ai/analyzer.py
   │
   ▼ Axes
[행렬 엔진] ai/matrix_engine.py (가중합 + EMA α=0.7)
   │
   ▼ 캐릭터 파라미터
   ├──→ [Pally 렌더] PallyCanvas (즉시 반영)
   ├──→ [Gemini] system prompt에 파라미터 주입 → 영어 응답 + 한국어 힌트
   │       │
   │       ▼ 응답 텍스트
   │   [TTS] Google Cloud TTS → 자동 재생
   │
   └──→ [Supabase] messages insert
```

---

## 7. 화면 상태 모델

`/home`은 하나의 reducer로 관리. 외부에서 보이는 상태는 다음 5가지.

| 상태 | TalkButton | PallyCanvas | ChatBubble | 트리거 |
|---|---|---|---|---|
| `idle` | 대기 (탭 가능) | 마지막 파라미터 유지 | 마지막 대화 유지 | 진입 / 세션 종료 후 |
| `recording` | "듣고 있어" | 살짝 떨림 (옵션) | 변화 없음 | TalkButton 첫 탭 |
| `thinking` | 비활성 + spinner | 변화 없음 | 사용자 메시지만 추가 | 녹음 종료 ~ Gemini 응답 도착 |
| `playing` | 비활성 | **즉시 새 파라미터로 변형** | Pally 메시지 추가 | Gemini 응답 도착 |
| `ended` | 숨김 | 최종 컷신 모습 | 비활성 | X 버튼 |

전이도:

```
idle ──tap──→ recording ──stop──→ thinking ──response──→ playing ──audio end──→ idle
   ↑                                                                              │
   └──────────────────────── X tap → ended ──tap anywhere──────────────────────────┘
```

구현 위치: `frontend/lib/state/conversation.ts` (reducer)

---

## 8. MVP scope vs Out-of-scope

### In-scope (6/7 데모 통과 기준)

- `/home` 풀 사이클 (rec → STT → 5축 → Gemini → TTS → Pally 변형)
- EMA 누적 (세션 내 1턴 → 2턴 → … 점진 변화)
- 인라인 한국어 힌트
- 세션 종료 컷신
- GNB 4탭 노출 (3탭은 빈 화면이라도 라우팅 동작)
- Supabase `sessions` / `messages` insert + RLS

### Out-of-scope (의도적으로 안 함)

- 로그인/회원가입
- 푸시 알림
- 결제
- `/history` `/ranking` `/my` 실데이터
- 오프라인 모드
- Pally 음성 커스터마이즈
- 다국어 (UI 한국어 고정, 발화는 영어 고정)
- 사용자별 Pally 영구 저장 (세션 종료 시 누적값은 final_*에 박지만 복원 안 함)

---

## 9. 한국어 카피 · 라벨 규칙

| 영역 | 규칙 |
|---|---|
| UI 라벨 | 한국어 (홈/학습/랭킹/내 정보) |
| 발화 언어 | 영어 (Pally 응답·TTS 모두 영어) |
| 힌트 | 한국어 (Gemini가 영어 발화에 대한 코멘트만 한국어로) |
| Toast | 한국어, 반말 톤 ("다시 말해줘", "안 들렸어") |
| aria-label | 한국어 |

말투 톤: **Pally는 친구 같은 반말, 시스템 메시지(Toast)도 반말.** 격식체 금지.

---

## 10. 미해결 결정 로그 (Open Questions)

> 데모 전 확정 필요. 결정 나면 본 문서에서 지우고 PRD/ROADMAP에 옮긴다.

- [ ] 세션 종료 컷신 길이 — 1초 vs 2초 (발표 흐름상)
- [ ] 인라인 한국어 힌트 최대 줄 수 — 2줄 강제? 잘릴 시 처리?
- [ ] FAB 비활성을 데모 시 어떻게 설명할지 (PM 발표 멘트 결정 필요)
- [ ] `/history` 진입 시 "준비 중" 외 다른 카피 사용 여부
- [ ] 세션 중 라우트 이탈했다가 돌아왔을 때 — 복원 vs 새 세션
- [ ] 마이크 권한 거부 후 재요청 동선

---

## 변경 이력

| 일자 | 변경 | author |
|---|---|---|
| 2026-05-31 | 초안 작성 (Phase 1A 완료 시점 기준) | 최윤서 |
