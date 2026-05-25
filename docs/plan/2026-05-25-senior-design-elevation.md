# Pally — Senior Design Elevation Plan

**Date:** 2026-05-25
**Reviewer:** 20년차 UI/UX 시니어 디자이너 perspective (Claude)
**Subject:** Figma `mvp design` canvas ([node 341-1132](https://www.figma.com/design/4kLxDLD2LdbB5BiY2QT5qU/디자인?node-id=341-1132)) + DESIGN.md
**Demo deadline:** 2026-06-07 (D-13)
**Outcome target:** 앱스토어 첫 화면에 올려도 손색없는 완성도

---

## TL;DR

지금 Figma 디자인은 **bones는 좋다 (7/10)**. 가시 돋은 Pally 캐릭터 + 따뜻한 크림 톤은 카테고리 안에서 명확히 차별화되는 자산. 하지만 앱스토어 레디까지 가려면 다음 4가지에서 senior 수준의 디테일이 빠져 있다:

1. **Interaction state coverage** — idle/listening/thinking은 있지만 **speaking, error 4종, permission, offline, partial speech**가 없음. 사용자가 실제로 마주칠 30% 시간이 무시됨.
2. **Mobile fidelity** — 402px(iPhone Pro Max-ish)에서만 디자인. **DESIGN.md target은 360px**. 한국 사용자의 절반 이상이 360–390px 단말. 검증 안 됨.
3. **Emotional arc & journey** — 단일 화면 상태는 있지만 **app launch → 첫 conv → 반복 사용자**의 시간 축 디자인이 없음. 첫 5초 / 5분 / 5일 사용자가 다른 경험을 해야 한다.
4. **Polish layer** — shadow tokens, motion specs, sound brief, haptic, 마이크로 카피, splash, 권한 요청 친근화 — 시니어 디자인의 90%는 이 폴리쉬 레이어에서 만들어진다.

D-13 안에 모두 끝낼 수는 없다. 데모용 / 데모 후 / 향후 로 명확히 분리한 phase 계획을 아래 제시.

---

## 1. Pre-review System Audit

### Current state
- **DESIGN.md**: 존재. Color·Typography·Spacing·Radius·Layout·Motion 정의 완비. 시각화 페이지(Color frame node 344:10)도 추가됨
- **Figma 디자인**: 7개 프레임 (`새 채팅` / `생각중` / `대화중` / `답변` / `유저 발화` / `생각중-history` / `listening`)
- **Senior polish 1차 적용 완료** (2026-05-25): YOU↔Pally 컬러 스왑, light navbar + hairline border + drop shadow, Pally 캐릭터 200px 축소, mic glow ring, recording red pulse, 캡션 muted, history panel handle, dash 정리
- **Pretendard 로컬 미설치** → fontSize 변경/일부 typo 수정 차단

### UI scope
- Phase 1A 메인 대화 화면 (1 screen, 7 states) + Phase 1B Pally 캐릭터 morph
- **Onboarding / feedback page 명시적으로 MVP scope 제외** (ROADMAP §1A note)
- 따라서 본 plan에서도 onboarding 풀 플로우는 post-demo로 분류

---

## 2. Step 0 — Initial Design Rating

**현재 디자인 완성도: 7.0 / 10**

세부 점수:

| 차원 | 현재 | 10/10이 되려면 |
|---|---|---|
| Information Architecture | 7.5 | 5-tab nav 의미·라벨 명확화, history view 진입/이탈 affordance 시각화 |
| Interaction state coverage | **5.0** | speaking state + error 4종 + permission + offline + partial speech + low-confidence |
| User journey & emotional arc | 6.0 | app launch → 첫 대화 → 반복 사용자 3 phase 감정 곡선 디자인 |
| AI slop risk | 8.5 | 거의 없음, 캐릭터가 모트 역할. 미세 정리: mic glow ring 자체는 보편적 |
| Design system alignment | 8.0 | shadow·motion duration token 추가, A11y 토큰 신설 |
| Responsive & accessibility | **4.0** | 360px 검증, VoiceOver/TalkBack labels, 고대비 모드, 큰 글씨 옵션 |
| Polish layer | 6.0 | splash, sound, haptic, copy, gradient micro-detail, 권한 요청 친근화 |

가장 큰 갭: **Interaction state coverage**와 **Responsive/Accessibility**.

---

## 3. 7-Pass Findings

### Pass 1 — Information Architecture (7.5/10)
**Strong:**
- 3-zone 레이아웃 (top context / center character / bottom action+nav) 일관성 ✓
- Pally 캐릭터가 hero anchor 명확 ✓
- History view 진입 시 panel handle 추가됨 ✓

**Gaps:**
- **Bottom nav 5 tabs 의미 불명**: home / book-check / + / trophy / profile — 5개 중 4개가 무엇을 하는지 불명확. 라벨 없음. 첫 사용자는 trial-and-error로 익혀야 함
- **+ 버튼이 새 채팅이라는 신호 약함**: 시니어 디자이너 관점에서 "+"는 universal "new" affordance이지만, conversation app 맥락에선 "compose" 아이콘이 더 명확
- **History 진입 chevron up/down의 의미 모호**: 라벨 없이도 panel handle이 있으면 OK하지만, 첫 대화 후 "이전 대화를 보려면 어떻게?"가 불명확

**Recommendations:**
- Bottom nav 5 tabs 각 의미 docs/adr/0XXX-nav-information-architecture.md 로 결정 후 라벨/툴팁 또는 long-press hint 추가
- + 아이콘을 새 채팅 의미를 잃지 않는 선에서 더 명확한 (chat bubble + 같은) 아이콘으로 교체 검토
- 첫 대화 완료 시 1회 한정 onboarding tooltip "위로 스와이프해서 이전 대화 보기" (post-demo)

### Pass 2 — Interaction State Coverage (5.0/10) ⚠️ 큰 갭

| 상태 | 현재 디자인 | 시니어 디자이너 표준 |
|---|---|---|
| Idle | ✓ orange mic + glow ring | OK |
| Listening (recording) | ✓ red disc + white square + pulse ring | OK |
| Thinking | ✓ "Thinking..." muted text | OK, +Pally 미세 회전 morph 모션 스펙 필요 |
| **Speaking (Pally 발화중)** | ❌ 미정의 | Pally 입 부분 미세 morph + audio waveform indicator + 텍스트 typewriter reveal |
| **Mic permission 요청** | ❌ 미정의 | 친근한 한국어 카피 + Pally 캐릭터가 마이크 가리키는 일러스트 |
| **Mic permission 거부됨** | ❌ 미정의 | 친근한 fallback ("Pally랑 이야기하려면 마이크가 필요해요") + 설정 가이드 |
| **STT 인식 실패** | ❌ 미정의 | "조금 더 천천히 말해주실래요?" 친근하게 + 재시도 |
| **Network 오프라인** | ❌ 미정의 | 오프라인 배너 + 마지막 대화 캐시 표시 |
| **API timeout / 5xx** | ❌ 미정의 | Pally가 "지금 멍해졌어요, 다시 한 번?" |
| **녹음 너무 짧음 (<1s)** | ❌ 미정의 | "더 길게 말해주세요" tooltip |
| **녹음 너무 김 (>30s)** | ❌ 미정의 | counter 표시 + 자동 끊김 |
| **Background noise 경고** | ❌ 미정의 | "주변이 조금 시끄러워요" |
| **Low confidence Pally response** | ❌ 미정의 | "이거 맞나? 다시 말해줘" 옵션 |

**Recommendations:** 데모 전 최소 4종 (permission denied, STT failure, network, timeout) 디자인 + 카피 확정.

### Pass 3 — User Journey & Emotional Arc (6.0/10)

**시간 축 분석 (Norman 3 levels):**

| 시간대 | 감정 목표 | 현재 디자인이 지원? |
|---|---|---|
| **First 5 seconds** (visceral) | 놀라움 + 호기심 — "어, 귀여워" | ⚠️ splash 없음, 바로 mic 화면. 첫인상이 너무 functional |
| **First 5 minutes** (behavioral) | 안심 + 성취 — "이거 진짜 내 말 알아듣네" | ✓ Pally 캐릭터가 즉각 시각 반응 (Phase 1B에서 검증) |
| **First 5 days** (reflective) | 동반자감 — "Pally랑 이야기하는 게 일과" | ❌ 반복 사용 hook 없음, 다시 와야 할 이유가 없음 |

**Gaps:**
- App launch → 첫 화면까지 splash screen 없음 (브랜드 각인 기회 손실)
- 첫 대화 완료 후 다음 단계 affordance 없음 ("오늘 N번째 대화" 같은 streak signal)
- Empty state 영어 ("Start the new conversation with Pally!") — 한국 학습자에게 첫 화면부터 영어는 인지 부담 ↑

**Recommendations:**
- Splash screen 디자인 (Pally 캐릭터 + "Pally" wordmark, 1.5s 후 페이드인 to 메인)
- Empty state 한국어로: "오늘은 어떤 이야기를 해볼까요?" + 작은 hint "마이크를 눌러 영어로 말해보세요"
- (post-demo) Streak signal: 화면 하단에 "Pally와 N일째" 작은 칩

### Pass 4 — AI Slop Risk (8.5/10)

**Strong (slop 아님):**
- 가시 돋은 Pally 캐릭터 — 어떤 AI generator도 이걸 만들지 않음
- 크림 배경 + Pretendard — 한국어 + 따뜻한 톤은 영어학습 카테고리 안에서 명확히 차별화
- Speech bubble + character 조합 — 영어학습 앱에서 흔치 않음 (대부분 강의/카드 위주)

**Watchouts (살짝 보편적):**
- Mic + glow ring 자체는 voice app universal pattern. Pally 색과의 조합으로 차별화 OK.
- Bottom nav 5-tab도 universal. 4 tabs로 줄이는 것 검토 가능 (book, trophy를 dashboard에 통합)

**Recommendation:** 현 수준 유지 + Pally 캐릭터의 표정 variation을 늘려서 차별화 강화 (post-demo phase B).

### Pass 5 — Design System Alignment (8.0/10)

**Strong:**
- DESIGN.md가 cohesive하고 Figma와 동기화됨
- Color tokens + Typography tokens + Spacing scale 정의 완비
- Decisions log + Limitations 명시

**Gaps:**
- **Shadow tokens 없음**: senior pass에서 추가한 mic drop shadow, navbar shadow가 DESIGN.md에 토큰화 안 됨 → 다른 컴포넌트에서 재사용 불가
- **Motion duration tokens는 있지만 easing curve를 cubic-bezier로 명시 안 함** (named "ease-out" 정도)
- **A11y 토큰 부재**: focus ring color, min touch target (44px) 명시는 있지만 토큰 형태 아님
- **Pretendard Variable이 Figma desktop 로컬에 미설치** → fontSize/style 변경 도구로 차단됨 (Known limitation 등재)

**Recommendations:**
- DESIGN.md에 `## Elevation / Shadow` 섹션 추가 (mic-elevation / nav-elevation / bubble-elevation)
- Cubic-bezier 값 spec ((0.4, 0, 0.2, 1) for ease-out, etc.)
- A11y 토큰 섹션: focus-ring color, min-touch, prefers-reduced-motion 대응

### Pass 6 — Responsive & Accessibility (4.0/10) ⚠️ 큰 갭

**Strong:**
- DESIGN.md에 모바일 우선 + ~360px target 명시 ✓
- Touch target 44px 명시 ✓
- Pretendard Variable 사용으로 한국어 가독성 보장

**Gaps:**
- **360px viewport에서 검증 안 됨**: Pally 캐릭터 200×200이 360px 폭에서 좌우 80px 여백. 5축 morph 시 200px 가시 직경이 변하면 overflow 가능
- **Keyboard navigation 미정의**: voice-first 앱이지만 web 환경에서는 키보드도 동작해야 함 (Tab으로 nav 이동, Space로 mic on/off)
- **Screen reader spec 없음**: VoiceOver/TalkBack이 Pally 캐릭터 morph를 어떻게 announce할지, "Listening..." 상태를 어떻게 읽을지 미정의
- **Color contrast 미감사**: orange `#FE9012` on white surface = 2.84:1 (AA fail, large text only AAA). Pally label 사용 시 contrast 부족
- **고대비 모드 없음**: 시각 장애 사용자 대응 미흡
- **Larger text 옵션 없음**: iOS Dynamic Type / Android font scale 대응 미정의
- **Reduced motion 대응 없음**: prefers-reduced-motion 시 Pally morph animation 어떻게 fallback할지

**Recommendations:**
- 360px 화면 별도 variant 디자인 (Figma frame variant)
- 색상 contrast 감사: WCAG AA 통과하도록 orange를 #E67E00 (어두운 orange)로 sender label 색만 따로 정의
- A11y spec 별도 ADR 작성: `docs/adr/0XXX-accessibility-spec.md`

### Pass 7 — Unresolved Decisions (11건)

| # | 결정 필요 | 미루면 발생할 일 |
|---|---|---|
| U1 | 360px viewport에서 character morph max 직경 | 5축 max값에서 viewport overflow |
| U2 | Bottom nav 5 tabs 각 의미·라벨 정책 | 사용자가 trial-and-error로 학습, 첫 사용성 ↓ |
| U3 | + 버튼 아이콘 (현재 plus) vs compose | 사용자가 "+"를 새 채팅으로 인식하지 못함 |
| U4 | App splash screen 유무 | 첫인상 무브랜딩, store 등록 시 마이너스 |
| U5 | Mic permission 거부 시 UX (engineer 추측 default 위험) | 엔지니어가 alert() 디폴트 사용 |
| U6 | STT 인식 실패 시 카피 (한/영) | 학습자가 자기 잘못이라 오해 |
| U7 | 네트워크 오프라인 시 fallback | 앱이 흰 화면 + 무한 로딩 |
| U8 | Pally "speaking" 상태 시각 표현 | 사용자가 응답이 끝났는지 모름 |
| U9 | Pally TTS audio 시각 동기화 (waveform / 입 morph) | 들리는데 안 보이는 dissociation |
| U10 | Conversation 종료 / 새 대화 시작 UX | + 버튼만으로는 약함 |
| U11 | App icon 디자인 (외부 작업 가능성) | App store 제출 차단 |

---

## 4. Senior Elevation Plan — Phase별 Roadmap

D-13 이내 가능한 것 / 데모 후 / 향후 로 분리.

### 🔴 Phase A — Pre-demo Critical (May 26 ~ May 29, 4 days)
**Owner**: 이찬희 (디자인 + 1A frontend)
**Goal**: 데모 시연 시 사용자가 마주칠 reasonable scenario에서 디자인이 깨지지 않게.

| Task | Effort | Output |
|---|---|---|
| A1. 360px viewport variant 디자인 (3 메인 프레임) | 0.5d | Figma frame variant + 캐릭터 max 직경 spec |
| A2. Error states 4종 디자인 (mic-denied / STT-failed / network-offline / API-timeout) | 1d | 4 Figma frames + 한국어 카피 |
| A3. Mic permission 요청 화면 디자인 (Pally 친근하게 안내) | 0.5d | Figma frame + 카피 |
| A4. Empty state 한국어 카피 변경 | 0.25d | Figma text 변경 |
| A5. Speaking state 디자인 (Pally 응답 중) — 텍스트 typewriter + 미세 morph hint | 0.5d | Figma frame + motion 의사 코드 |
| A6. Color contrast WCAG AA 감사 + sender 색상 조정 (필요시 #E67E00 dark orange) | 0.5d | Audit table + Figma update |
| A7. Splash screen 디자인 (Pally + wordmark, 1.5s) | 0.5d | Figma frame + Lottie/CSS spec |

**총 3.75d (4d 안)** — 데모 직전 buffer 0.25d

### 🟧 Phase B — Visual Polish (May 30 ~ Jun 2, 4 days)
**Owner**: 이찬희 (디자인 + 1A 구현)
**Goal**: 시니어 디테일 — 그림자/그라데이션/마이크로 카피/typography.

| Task | Effort | Output |
|---|---|---|
| B1. DESIGN.md에 Shadow/Elevation 토큰 추가 (mic-elevation, nav-elevation, bubble-elevation) | 0.25d | DESIGN.md §Elevation |
| B2. Motion duration·easing 토큰 cubic-bezier로 명시 (DESIGN.md §Motion 보강) | 0.25d | DESIGN.md update |
| B3. Pally Chat bubble 미세 gradient (top to bottom 5° warm cream) — bubble만 살짝 | 0.5d | Figma fill update |
| B4. Typography 위계 보강 (Pretendard local install 후 sender label 12px caption으로) | 0.5d | Figma 일괄 update |
| B5. Demo sample copy typo 8건 마저 수정 | 0.25d | Figma update |
| B6. Loading skeleton 디자인 (앱 로드 시 + Pally 응답 대기 시) | 0.5d | Figma frames |
| B7. 마이크로 카피 한 차례 정제 (모든 시스템 메시지 친근하게) | 0.5d | Copy document |
| B8. Pally 캐릭터 morph 안전영역 spec (5축 max에서 240×240 이내) | 0.5d | DESIGN.md update + Figma 가이드 |
| B9. Bottom nav 라벨/툴팁 정책 결정 ADR + 적용 | 0.75d | ADR + Figma update |

**총 4d** — Phase A와 일부 병행 가능

### 🟨 Phase C — Senior Details & Sound (Jun 3 ~ Jun 6, 4 days)
**Owner**: 이찬희 + 백은혜 (TTS 사운드 연결)
**Goal**: 인지 가능한 모든 미세 폴리쉬.

| Task | Effort | Output |
|---|---|---|
| C1. Audio waveform 컴포넌트 디자인 (recording 시 시각 피드백) | 0.5d | Figma + CSS/Canvas spec |
| C2. Pally text reveal animation spec (typewriter 30ms/char) | 0.25d | Motion doc |
| C3. Haptic patterns 명세 (mic-press 가벼움, recording-start 더블, achievement-soft) | 0.25d | Haptic doc |
| C4. Sound effects 브리프 (mic open chime, mic close chime, message receive) | 0.5d | Sound brief — 외부 sound designer 의뢰 or open-source 큐레이션 |
| C5. A11y spec ADR (VoiceOver/TalkBack labels, focus ring, reduced motion) | 0.75d | ADR + Figma 가이드 |
| C6. 데모 시연 user flow 리허설 + screen recording 검토 | 1d | 비디오 + 발견된 이슈 fix |
| C7. Demo day buffer (예측 못한 이슈 fix) | 0.75d | — |

**총 4d**

### 🟩 Phase D — Post-demo (Jun 8 이후, optional)
**Owner**: 전체 팀
**Goal**: 앱스토어 제출 / 추가 학습자 acquisition 준비.

| Task | Effort | Output |
|---|---|---|
| D1. App icon 디자인 (Pally 캐릭터 기반 3 variant) | 2d | Icon set 1024/512/256/etc. |
| D2. 풀 character expression library (8-12 emotion states for 5-축 매핑) | 5d | Sprite/SVG library + 5축 매핑 표 |
| D3. Onboarding flow (3-4 screens, optional skip) | 3d | Figma flow + 한국어 카피 |
| D4. 사용자 progress dashboard (5-축 radar, 일/주/월 통계, streak) | 5d | Figma + 데이터 모델 |
| D5. Library/topics tab content (대화 주제 카드 카탈로그) | 5d | Figma + content strategy |
| D6. Settings & profile detail (이름·레벨·Pally 성격 customization) | 3d | Figma + state model |
| D7. Dark mode | 4d | DESIGN.md dark tokens + Figma variant |
| D8. Tablet layout (768px, split history view) | 3d | Figma + responsive spec |
| D9. iOS / Android wrapper 검토 (PWA → native) | 외부 | platform-specific 디자인 가이드 |

**총 ~30d** — 데모 후 phase로 분할 진행

### ❌ Out of Scope (별도 workstream)
- 마케팅 랜딩 페이지
- 결제 / 구독 시스템 UI
- 소셜 / 친구 추가 / 리더보드
- 학습 진도 시험 / 평가 시험 UI
- 다국어 학습 (Pally가 일본어 / 중국어 등)

---

## 5. Approved Mockups (현재 Figma)

| Screen / state | Figma node | 평가 | Action |
|---|---|---|---|
| 새 채팅 (empty) | 341:1161 | OK, empty copy 한국어로 변경 필요 (A4) | minor edit |
| 생각중 (main) | 341:1133 | OK | as-is |
| 대화중 (response) | 341:1147 | OK, gradient 검토 (B3) | polish |
| 답변 (history view) | 341:1174 | OK | as-is |
| 유저 발화 (history+listening) | 341:1195 | OK | as-is |
| 생각중 (history) | 341:1214 | OK | as-is |
| Listening (main) | 365:10 | OK (신설) | as-is |
| Color frame | 344:10 | OK (DESIGN.md 시각화) | as-is |
| **에러 4종 (mic-denied / STT-fail / offline / timeout)** | ❌ 없음 | 신규 필요 | A2 |
| **Permission 요청** | ❌ 없음 | 신규 필요 | A3 |
| **Speaking state** | ❌ 없음 | 신규 필요 | A5 |
| **Splash screen** | ❌ 없음 | 신규 필요 | A7 |
| **360px variants** | ❌ 없음 | 신규 필요 | A1 |
| **Loading skeleton** | ❌ 없음 | 신규 필요 | B6 |

총 6 카테고리 / 15+ 신규 프레임 — Phase A에 집중.

---

## 6. TODOS for design debt

다음 항목은 별도 TODOS.md 또는 ADR로 관리:

1. **U2: Bottom nav 5-tab 의미 정책** → `docs/adr/0007-bottom-nav-ia.md`
2. **U11: App icon 디자인** → Phase D1, 외부 디자이너 검토 가능
3. **D2: Character expression library** → Phase 1B 김민주 ownership, post-demo
4. **D7: Dark mode** → DESIGN.md dark tokens 별도 ADR (이미 "Out of scope for MVP" 결정됨)
5. **U9: TTS audio ↔ Pally 입 morph 동기화** → Phase 1B + Phase 1C 협업 spec
6. **D9: PWA → native 진환** → Phase 2 이후 platform 결정 후

---

## 7. Completion Summary

```
+====================================================================+
|       PALLY DESIGN — SENIOR ELEVATION PLAN — SUMMARY               |
+====================================================================+
| System Audit         | DESIGN.md ✓ / 7 frames / Pretendard 미설치  |
| Step 0               | 7.0 / 10 (current) — Target 9+ by Jun 7    |
| Pass 1 (Info Arch)   | 7.5 → 8.5 (after A,B fix)                  |
| Pass 2 (States)      | 5.0 → 8.5 (after Phase A 큰 비중)          |
| Pass 3 (Journey)     | 6.0 → 7.5 (after A4·A7·B7)                 |
| Pass 4 (AI Slop)     | 8.5 → 8.5 (이미 strong)                    |
| Pass 5 (Design Sys)  | 8.0 → 9.0 (after B1·B2 토큰화)             |
| Pass 6 (Responsive)  | 4.0 → 7.5 (after A1·A6 + C5 ADR)           |
| Pass 7 (Polish)      | 6.0 → 9.0 (after Phase B + C)              |
+--------------------------------------------------------------------+
| Phase A (Pre-demo)   | 7 tasks, 4 days, critical                   |
| Phase B (Polish)     | 9 tasks, 4 days                             |
| Phase C (Senior)     | 7 tasks, 4 days                             |
| Phase D (Post-demo)  | 9 tasks, ~30 days                           |
| Out of scope         | 5 items (marketing, billing, etc.)          |
+--------------------------------------------------------------------+
| Overall projected    | 7.0 / 10 → 8.7 / 10 by Jun 7                |
| App-store readiness  | Phase A+B+C 완료 시 store 등록 가능 수준    |
+====================================================================+
```

**핵심 메시지:**
> 지금 디자인은 **bones가 좋다**. 캐릭터·컬러·레이아웃은 senior 수준의 차별화 자산. 부족한 건 **interaction state coverage**(missing 70%)와 **mobile fidelity**(360px 미검증) — 이 둘이 데모 시연 중 가장 빨리 들킨다. Phase A 4일에 집중 투자.
>
> 데모 후 phase D는 앱스토어 등록 + 사용자 retention을 위한 본격적인 expansion. 캐릭터 expression library는 김민주(1B)와 협업 영역.

---

## 8. Next Actions (이찬희 본인이 일어났을 때)

1. **이 plan 검토 → Phase A 7 task 우선순위 확정**
2. **A2 (error states 4종) 카피 한국어로 직접 작성 — 학습자 톤 결정** (PM 컨펌 권장)
3. **A1 (360px variant)부터 시작 — Figma frame width 360px duplicate**
4. **B9 (Bottom nav 라벨)은 5명 사용자 빠른 인터뷰 후 결정** (시간 없으면 long-press tooltip로 우회)
5. **Phase B 1차 의존성: Pretendard 로컬 설치 (Figma desktop)** — 우선 처리하면 B4·B5 unblock
6. **C4 (Sound brief)는 외부 sound designer 의뢰 검토** — 시간 부족하면 freesound.org 큐레이션으로 우회
