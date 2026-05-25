# Phase 1A: FE Screens & Audio Shell - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning
**Owner:** 이찬희 (FE · 디자인, 5d parallel with 1B/1C)

<domain>
## Phase Boundary

모바일 메인 대화 화면 1개 + rec/audio UX shell이 **Figma 디자인 폭(402px) 기준**으로 **mock transport**로 동작한다. 실제 `/api/chat` 호출, 음성 인식, TTS 재생은 전부 Phase 2 wiring. 1A는 **FE only**.

**핵심 (must work):**
- rec 버튼: start → stop만 잘 동작
- 대화 내용 표시 (CHAT-01: SMS 스타일, user=teal "YOU"/Pally=orange "Pally")
- Pally placeholder 영역 (1B가 Canvas2D로 덮어쓸 자리)

**범위 안 (in scope):**
- Figma `mvp design` (node 427:2173)의 6 frames 구현: 새 채팅(empty) / 생각중 / 대화중 / history view 3 variants
- TalkButton 2-state (idle orange mic / thinking red square) + 1A 추가 state (speaking, error 통합 1개, permission-denied)
- 5-tab bottom nav — **시각만**, 5개 모두 disabled, + 버튼 포함 안 눌림
- Top chat bubble + chevron 토글 → full-sheet history view
- Empty state 한국어 카피 ("오늘은 어떤 이야기를 해볼까요?" / "마이크를 눌러 영어로 말해보세요")
- Mock chat transport (`lib/mocks/chat-mock.ts` 같은 단일 함수)
- MediaRecorder로 브라우저 녹음 → Blob 생성 (전송은 mock으로 흘려보냄)
- sessionId 클라이언트 생성 + localStorage 영속화 (mock 흐름에 동반)
- **Figma 디자인 폭(402px) 기준 구현** + 디자인 토큰 DESIGN.md / Figma 동기화 (다른 viewport 폭 대응은 1A scope 밖)

**범위 밖 (out of scope, 다른 phase로):**
- 실제 `/api/chat` 네트워크 호출, STT, TTS 재생 → Phase 2 wiring
- Pally Canvas2D 렌더러 (Superformula, 5축 morph) → Phase 1B (김민주)
- `Axes` / `CharacterParams` TS 타입 정의 → Phase 1B
- Supabase 직접 호출 → 1A는 backend가 책임 (FE는 sessionId만 보유)
- 새 대화 시작(+ 버튼) UX → Post-MVP / Phase 2
- 다른 nav 탭(home/book/trophy/profile) routing → Post-MVP
- 온보딩 / character_name / level 입력 화면 → v2 (MVP는 default 'Pally' / 'B1')
- Splash screen, sound, haptic, A11y full audit → Senior plan Phase B/C/D (post-demo)
- 다른 viewport 폭 대응(반응형) → Senior plan Phase A1 또는 post-demo

</domain>

<decisions>
## Implementation Decisions

### A. Mock Transport

- **D-01:** Mock 함수는 단일 export — `frontend/lib/mocks/chat-mock.ts`에 `mockChat(req: ChatRequest): Promise<ChatResponse>` 형태. Phase 2 swap point = 이 한 함수의 호출처를 real `fetch(NEXT_PUBLIC_BACKEND_URL + '/api/chat')`로 교체.
- **D-02:** Wire 타입은 Phase 1C 확정 shape 그대로 사용. Request `{ utterance: string, session_id: string, level: 'B1' }`, Response `{ status, transcript, reply, tts_audio (base64 mp3), axes, character, character_labels, hint_ko: { hint, expression } }`. 1A는 `tts_audio`를 받아도 **재생하지 않음** (Phase 2가 처리).
- **D-03:** Canned fixture **1개 고정** — `transcript: req.utterance`(echo), `reply: "What a bummer! But don't be too sad."`(Figma 샘플과 동일), `axes`/`character`는 0 default, `hint_ko`는 Figma 톤에 맞는 짧은 샘플 1개.
- **D-04:** Latency **고정 800ms** (`await new Promise(r => setTimeout(r, 800))`). random / jitter / 에러 시뮬레이션 1A에서 **안 함**.

### B. Audio Capture & Playback

- **D-05:** **start / stop만 동작** 시키면 됨 (user 요청). MediaRecorder API 사용, MIME type은 브라우저 detection (`MediaRecorder.isTypeSupported('audio/webm;codecs=opus')` 우선, fallback `audio/mp4`).
- **D-06:** 마이크 권한 요청은 **implicit** — 첫 rec 버튼 tap 시 `getUserMedia()` 호출. pre-permission CTA / 안내 screen 없음 (간단하게).
- **D-07:** 권한 거부 시 = idle 복귀 + 작은 toast/inline 메시지 "마이크 권한이 필요해요" (한국어). 설정으로 보내는 deep link 없음.
- **D-08:** 녹음 max 30s — `MediaRecorder.stop()` 자동 호출. min duration 검사 **없음** — 너무 짧으면 mock이 그대로 echo. user 요청대로 단순화.
- **D-09:** 녹음 Blob은 mock 흐름에서는 **사용 안 함** — `mockChat()` 호출만 트리거. Phase 2가 Blob을 FormData로 전송.
- **D-10:** TTS 재생은 1A에서 **안 함** — `tts_audio`(base64 mp3) 응답 받아도 재생 코드 없음. UI는 "speaking" 상태로 일정 시간(예: 1.5s) 머무른 뒤 idle 복귀.

### C. Pally Placeholder + State Coverage

- **D-11:** Pally 영역(262×262, Figma Group 7)에 **정적 SVG placeholder** 배치 — Figma의 Star4 spike 도형을 export한 SVG 1개 (Pally의 default appearance). Phase 1B가 같은 영역을 Canvas2D 컴포넌트로 덮어쓰면 됨. **`frontend/components/pally/`는 1B 소유 영역이므로 1A는 그 안에 만들지 않는다**. 1A는 메인 화면 컴포넌트 안에서 `<PallyPlaceholder />` 같은 로컬 컴포넌트 또는 직접 SVG inline.
- **D-12:** TalkButton states (1A 구현):
  - `idle` — orange mic (Figma `state=idle`)
  - `recording` — red disc + white square (Figma `state=thinking`)
  - `processing` — `recording`와 동일 시각 (TS 상태값만 분리)
  - `speaking` — `recording`와 동일 시각 (1.5s 머무름)
  - `error` — `idle`와 동일 시각 + 위에 작은 inline 에러 메시지
- **D-13:** rec state machine (1A 전체):
  ```
  idle → (tap, 권한 OK) → recording → (tap stop / 30s auto) → processing →
  → (mockChat 800ms) → speaking → (1.5s) → idle
                                ↘ (mock 항상 성공) error 분기 사실상 없음
  idle → (tap, 권한 거부) → idle + toast
  ```
- **D-14:** 에러 처리는 **권한 거부 1개** + **통합 에러 1개**만. 통합 에러는 mock에서는 발생하지 않으나 catch-all path 보유 (Phase 2에서 network/timeout/STT-fail가 흘러들어옴). 통합 에러 UI = "다시 한 번 말해주세요" inline 메시지.
- **D-15:** Senior plan의 나머지 state들 (offline, mic too short/long, low-confidence, background noise, splash, streak) — **전부 deferred**. 1A는 user가 요청한 "start/stop + 대화 표시"에 집중.

### D. Session Lifecycle + Nav Tabs

- **D-16:** `session_id` = UUID v4 — **app load 시 첫 client mount 시점**에 `crypto.randomUUID()`로 생성, `localStorage.setItem('pally:sessionId', id)`로 영속화. 이미 저장돼 있으면 재사용. SSR-safe하게 `useEffect` 안에서 처리 (server에서는 sessionId undefined).
- **D-17:** 새 대화 시작 UX **1A에서 구현 안 함** (user 요청). + 버튼 포함 5개 nav 탭 **전부 시각만, disabled**. tap 했을 때 아무 일도 일어나지 않음 (toast조차 없음 — user 요청 "간단하게").
- **D-18:** 페이지 새로고침 시 메시지 리스트는 **빈 상태**에서 시작. localStorage에서 메시지 복원 안 함 (1A는 mock이라 의미 없음 + Supabase 호출은 Phase 2). sessionId만 유지.

### Claude's Discretion

다음은 plan / researcher가 표준 관행으로 결정:
- 컴포넌트 디렉토리 구조 (`frontend/app/page.tsx` vs `frontend/app/(chat)/page.tsx`, `frontend/components/chat/`, `frontend/components/audio/` 등)
- State 관리 도구 — 단순 `useState` + `useReducer`로 충분할지 zustand 도입할지 (1A 한 화면이라 useReducer 추천)
- Tailwind class 그룹화 / extract 컴포넌트 기준
- Figma Star4 spike SVG export 방식 (직접 SVG 코드 inline vs `public/pally-placeholder.svg`)
- MediaRecorder MIME fallback 순서 (browser detection 우선순위)
- localStorage key prefix (`pally:*` 추천)
- 5개 nav 탭 disabled 시각화 (opacity 100% 유지 + cursor: default vs opacity 50%) — Figma 그대로 유지 추천
- chat bubble vs full-history view 전환 애니메이션 (slide-down vs fade) — Figma motion spec 따름
- mockChat의 에러 path catch-all 구현 (try/catch만 두고 1A에선 안 흘림)

### Folded Todos

해당 없음 (todo match-phase 결과 0건).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1A Scope (planning source of truth)
- `.planning/ROADMAP.md` § Phase 1A — Success Criteria 1~4, "Note — 온보딩 없음", "Note — 피드백 화면 없음"
- `.planning/REQUIREMENTS.md` § MAIN-01, CHAT-01 (Traceability 표 Phase 1A 매핑)
- `.planning/PROJECT.md` § Constraints (Mobile-first; 1A 구현 폭은 Figma 402px 기준), Key Decisions (`/feedback` 없음, 온보딩 없음, GCP only)
- `.planning/STATE.md` § Hand-off Notes (Phase 1C → Phase 1A/2) — Railway URL, env 키, `/api/chat` request 최소 필드, Supabase 테이블

### Design (Figma + 시스템 문서)
- `DESIGN.md` (전체) — color/typography/spacing tokens
- Figma `mvp design` canvas — node 427:2173 — 6 frames: `새 채팅(427:2216)` / `생각중(427:2174)` / `대화중(427:2194)` / `유저 발화 history(427:2235)` / `유저 발화 + thinking(427:2246)` / `유저 발화 + Pally current(427:2265)`. TalkButton component (441:30, states idle/thinking). 5-tab GNB (`GNB` 인스턴스). Pally Chat bubble (427:2197). 5-tab bottom nav.
- `docs/plan/2026-05-25-senior-design-elevation.md` — 디자인 elevation plan (Phase A~D), 13 state coverage 표, 11 unresolved decisions. 1A 범위 안에 들어갈 부분은 위 D-12/D-13에 반영됨. 나머지 (splash, 반응형 variant, error 4종 등)는 Senior Plan Phase A/B/C로 deferred.

### Wire Format (Phase 1C 산출, mock도 따라야 함)
- `backend/main.py` `/api/chat` 엔드포인트 — request `{utterance, session_id, level}`, response `{status, transcript, reply, tts_audio, axes, character, character_labels, hint_ko: {hint, expression}}`. 1A mock은 이 shape을 그대로 반환.
- 1A는 wire 타입을 `frontend/lib/types/chat.ts`(신규) 같은 곳에 정의. **Source of truth는 1C 응답** — 변환 레이어 없이 직결.

### Team Conventions
- `CLAUDE.md` § 1 (Phase Ownership — 1A vs 1B 영역 분리), § 7 (Code Rules — TS/Next.js, Tailwind, Error handling), § 5 (E2E 검증 — 모바일 폭은 1A의 경우 Figma 402px), § 10 (NEVER/ALWAYS)
- `frontend/lib/types/message.ts`, `frontend/lib/types/session.ts` — Phase 0 산출, 1A가 mock 데이터/UI 상태로 사용

### Existing Assets
- `frontend/app/page.tsx` — Phase 0 placeholder ("Pally" 텍스트만). 1A가 메인 화면 컴포넌트로 덮어쓰기.
- `frontend/app/layout.tsx` — Pretendard variable import 완료. 1A에서 metadata title/description 갱신 가능.
- `frontend/tailwind.config.ts` — Pretendard sans + 14 typography tokens 정의 완료.
- `frontend/lib/utils.ts` — `cn()` 유틸 사용 가능.
- `frontend/lib/supabase/client.ts` — anon client 존재하나 1A는 사용 안 함 (FE 직접 DB 호출 없음).

### Out-of-Scope (참조만, 1A에서 만들지 않음)
- `frontend/components/pally/*` — Phase 1B 소유 영역
- `frontend/app/dev/pally/*` — Phase 1B (데모용 슬라이더 페이지)
- `frontend/lib/types/character.ts` — Phase 1B (`Axes`, `CharacterParams`)
- `docs/adr/0001-python-engine-integration.md` — Phase 1B 산출, 1A와 무관
- `backend/`, `ai/`, `supabase/migrations/*` — Phase 1C 영역, 1A에서 수정 금지

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`frontend/lib/types/message.ts`, `session.ts`** — Phase 0이 정의한 UI 타입. 1A가 mock 메시지 리스트 / sessionId 보관에 그대로 사용. `Message.role = 'user' | 'pally'`, `Message.transcript`, `Message.createdAt`.
- **`frontend/tailwind.config.ts`** — typography token (`text-title-1` 등) 사용 가능. DESIGN.md와 sync.
- **`frontend/lib/utils.ts` `cn()`** — Tailwind 조건부 클래스 결합 표준.
- **Figma `TalkButton` ComponentSet (441:30)** — variants `state=idle` / `state=thinking`. 1A는 두 시각 자산을 직접 React/SVG로 구현 (or `mcp__figma__get_design_context`로 reference code 받아서 어댑트).
- **Figma `GNB` 인스턴스 (5-tab nav)** — Figma frame 그대로 React 컴포넌트로 옮김.

### Established Patterns
- **Server Component 기본** + 인터랙티브 부분만 `'use client'` (CLAUDE.md §7). 메인 페이지 자체는 client component가 될 가능성 큼 (rec 버튼 + state).
- **TS strict, `any` 금지**, named export 선호, Tailwind + `cn()`만 (string concatenation 금지).
- **모노레포 분리** — 1A는 `frontend/` 안에서만 작업. `backend/`, `ai/` 절대 손대지 않음.
- **에러 처리 원칙** (CLAUDE.md §7): empty `catch {}` 금지, silent fallback `|| {}` / `?? []` 금지. mock에서 에러 안 던지더라도 catch-all path는 명시적으로 처리.

### Integration Points
- **Phase 1B 머지 후**: `frontend/components/pally/` 안의 Canvas2D 컴포넌트가 1A의 placeholder를 대체. 1A는 placeholder를 prop으로 교체 가능한 구조 유지 (예: `<MainScreen pallyVisual={<PallyPlaceholder />} />` 또는 children).
- **Phase 1C 산출물과 wire format 일치** — mock 응답이 real 응답과 100% 같은 shape이어야 Phase 2 swap이 한 줄.
- **Phase 2 swap 지점**: `frontend/lib/mocks/chat-mock.ts`의 `mockChat()` 호출처 — `fetch(NEXT_PUBLIC_BACKEND_URL + '/api/chat')`로 교체. 그 외 UI 코드는 변경 없음.

### Constraints
- **iOS Safari MediaRecorder**: `audio/webm`을 지원하지 않을 수 있음. 1A는 brower MIME detection으로 fallback하되, 실제 STT 호환성 검증은 Phase 2 (user 요청 "간단하게").
- **localStorage SSR**: Next.js App Router server render 단계에서는 `window`/`localStorage` 미존재. `useEffect` 안에서만 접근.
- **Viewport target = Figma 402px**: 1A 구현은 Figma 프레임 폭(402px)을 그대로 따른다. 다른 viewport 폭 대응(반응형)은 1A scope 밖.

</code_context>

<specifics>
## Specific Ideas

- **User 요청 한 문장 요약**: "근데 1A는 프론트만 하는 거 아냐?? ... 1A는 프론트만이니까 간단하게 가자 ... + 버튼은 안 눌려도 돼, 그냥 start, stop 이랑 대화 내용만 잘 뜨면 됨"
- **간단 우선 원칙**: 1A는 mock-only frontend. "동작하면 됨" 수준. polish / 에러 covariance / 다양한 fixture는 Senior plan Phase B/C로 미룸.
- **Figma가 source of truth**: DESIGN.md와 Figma 충돌 시 Figma 우선 (DESIGN.md `When tokens diverge ... Figma wins`).
- **chat-mock = Phase 2의 single swap point**: 이 약속을 어기면 Phase 2가 광범위 수정 필요해짐. 모든 화면 데이터 흐름은 `chat()` 한 함수를 통과해야 함.

</specifics>

<deferred>
## Deferred Ideas

- **Splash screen 1.5s** (Senior plan A7) — post-demo Phase D
- **반응형(다양한 viewport 폭) 대응** (Senior plan A1) — 1A는 Figma 402px 폭만 구현. 다른 폭 대응은 post-demo 또는 별도 phase.
- **Error states 4종 디자인** (mic-denied / STT-fail / network-offline / API-timeout, Senior plan A2) — Phase A/B 디자인, Phase 2 wiring에서 활용
- **Mic permission 친근화 카피 + 일러스트** (Senior plan A3) — Phase B
- **Speaking state morph + waveform** (Senior plan A5, C1) — 1B의 Canvas2D 연동 이후
- **WCAG AA contrast 감사 + dark orange sender label** (Senior plan A6) — Phase B
- **Shadow tokens, motion easing cubic-bezier, A11y 토큰** (Senior plan B1/B2, C5) — DESIGN.md 보강 단계
- **Pally typewriter text reveal + haptic + sound effects** (Senior plan C2/C3/C4) — Phase C
- **App icon, character expression library, onboarding, dashboard, settings, dark mode, tablet, native wrapper** (Senior plan D1~D9) — post-demo
- **5탭 nav routing + 새 대화(+) 동작** — Post-MVP / Phase 2 / v2
- **메시지 영속화 (localStorage / Supabase 직접)** — Phase 2 wiring에서 Supabase 통해
- **STT 인식 실패, 너무 짧음/김, background noise, low-confidence, offline** — Phase 2 또는 post-demo
- **`Axes` / `CharacterParams` 타입, Canvas2D 렌더러, dev/pally 슬라이더 페이지** — Phase 1B
- **실제 `/api/chat` 호출, STT 업로드, TTS 재생** — Phase 2

### Reviewed Todos (not folded)
해당 없음.

</deferred>

---

*Phase: 01A-fe-screens-audio-shell*
*Context gathered: 2026-05-25*
</content>
</invoke>