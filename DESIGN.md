# Pally — Design System

Source: Figma `디자인` file ([4kLxDLD2LdbB5BiY2QT5qU](https://www.figma.com/design/4kLxDLD2LdbB5BiY2QT5qU)).
Last synced: 2026-05-25.

When tokens diverge between this file and Figma, **Figma wins** — re-sync and update this file.

---

## Product Context

- **What this is:** Pally — 한국인 영어학습자용 모바일 음성 회화 앱. 사용자 발화를 5축(Formality, Energy, Intimacy, Humor, Curiosity)으로 분석해 AI 캐릭터 Pally의 외형·색·표정·말투를 실시간 변화.
- **Who it's for:** 한국인 영어학습자 (모바일 우선, ~360px).
- **Target moment:** June 7 데모.
- **Project type:** Mobile-first web app (PWA-style usage, voice + chat hybrid).

## Memorable Thing

> *"가시 돋은 핑크 친구가 따뜻한 크림 배경 위에서 내 영어에 반응해준다."*

학습 부담감 없는 친구 같은 분위기. 공식 학습앱이 아닌 캐릭터 동반자. 모든 design decision은 이 한 줄을 받쳐야 한다.

## Aesthetic Direction

- **Direction:** Playful Warmth — 친근함 + 약간의 장난기 + 살아있는 캐릭터 중심.
- **Decoration level:** Intentional — UI는 미니멀, 모든 decoration은 Pally 캐릭터에 응집. 캐릭터가 곧 decoration.
- **Mood:** 따뜻하고 친근. 학습 앱이 아니라 친구와 대화하는 느낌. 부담감 없음.
- **Category posture:** 영어학습 카테고리의 흔한 패턴(짙은 청색 + 흰색 + 정렬된 카드)을 명백히 거부.

### Deliberate Risks (where Pally gets its own face)

1. **가시 돋은 핑크 캐릭터가 hero** — 영어학습 앱은 보통 깔끔한 일러스트/아이콘 위주. Pally는 "살아있는 생물"처럼 보임. 보상: 즉각적 캐릭터 인식 + 5축 변화가 시각적으로 직관적.
2. **크림 배경 (`#fcf9f6`)** — 흰 배경 거부. 거의 모든 학습앱이 흰 배경인데 우리는 따뜻한 톤. 보상: 부담감 ↓, 분위기 ↑.
3. **Teal/Orange 듀얼 액센트** — YOU(teal) = 차분·객관 / Pally(orange) = 따뜻·감정. 화자 구분이 색만으로 즉시 됨.

---

## Color

**Approach:** Restrained warm palette — 따뜻한 neutral 베이스 + 2개 액센트(orange primary, teal secondary).

### Tokens

| Token | Hex | Source | Usage |
|---|---|---|---|
| `surface` | `#fcf9f6` | Figma `Background` | 페이지 배경 (메인 surface) |
| `surface-raised` | `#ffffff` | Figma `Backgrounds/Primary` | 말풍선, 카드, modal |
| `primary` | `#fe9012` | Figma `Orange 5` | Primary CTA, mic button active, key accent |
| `primary-soft` | `#ffb84a` | Figma `Orange 4` | Mic button idle, hover state, secondary surfaces |
| `accent` | `#00c3d0` | Figma `Accents/Teal` | "Pally" 이름 라벨, link, secondary highlight |
| `text` | `#1a1a1a` | Figma `B1` | Primary body/heading text |
| `text-strong` | `#000000` | Figma `Labels/Primary` | Maximum contrast (rare use) |
| `text-secondary` | `#212529` | Figma `Neutral/900` | Secondary text |
| `text-muted` | `#6b7280` | **Proposed** (gap fill) | Timestamps, captions, hint labels |
| `icon` | `#33363F` | Figma `Line_icon` | Bottom nav icons, action icons |
| `border` | `#e5e0d8` | **Proposed** (gap fill) | Input borders, dividers (warm gray to match surface) |
| `success` | `#10b981` | **Proposed** (gap fill) | Confirmation states |
| `warning` | `#f59e0b` | **Proposed** (gap fill) | Caution states |
| `error` | `#ef4444` | **Proposed** (gap fill) | Error states, destructive actions |

### Notes

- **Dark mode:** Out of scope for MVP. Light mode only until June 7 demo.
- **Proposed tokens** (`text-muted`, `border`, semantic) are not in Figma yet. Add them to the Figma file when convenient, or revise hex values if the designer has different preferences.

---

## Typography

**Font family:** Pretendard Variable (Korean + Latin). Already installed in the project.

All sizes use `letterSpacing: 0`. Sizes and line-heights are in `px`.

### Tokens

| Token (Tailwind) | Figma name | Size | Line | Weight | Usage |
|---|---|---|---|---|---|
| `text-title-1` | Title 1 / Title/24/SB | 24 | 36 | 600 | Page title (H1) |
| `text-title-2` | Title 2 / Title/20/SB | 20 | 28 | 600 | Section title (H2) |
| `text-subtitle-sb` | Subtitle/18/SB | 18 | 24 | 600 | Emphasized subtitle |
| `text-subtitle` | Subtitle/18/R | 18 | 24 | 400 | Subtitle / lead text |
| `text-body-sb` | Body/16/SB | 16 | 24 | 600 | Emphasized body |
| `text-body` | Body/16/R | 16 | 24 | 400 | Default body |
| `text-body-2-sb` | Body/14/SB | 14 | 24 | 600 | Emphasized small body |
| `text-body-2` | Body/14/R | 14 | 24 | 400 | Small body |
| `text-button-1` | Button/18/SB | 18 | 24 | 600 | Primary CTA |
| `text-button-2-sb` | Button/16/SB | 16 | 20 | 600 | Secondary CTA (emphasized) |
| `text-button-2` | Button/16/R | 16 | 20 | 400 | Secondary CTA |
| `text-button-3` | Button/14/R | 14 | 20 | 400 | Tertiary button |
| `text-button-4` | Button/12/R | 12 | 16 | 400 | Compact button |
| `text-caption-1` | Caption/12/R | 12 | 16 | 400 | Caption |
| `text-caption-2` | Caption/11/R | 11 | 12 | 400 | Smallest caption |

### Usage

```tsx
<h1 className="text-title-1">Page title</h1>
<p className="text-body">Body copy.</p>
<button className="text-button-2-sb">Confirm</button>
```

The Tailwind token bakes in `font-size`, `line-height`, and `font-weight` — do **not** layer `font-bold` / `leading-*` on top unless intentionally overriding the system.

---

## Spacing

- **Base unit:** 4px
- **Density:** Comfortable (mobile — touch target 우선)
- **Min touch target:** 44px (mic 버튼은 ~64px 권장)

### Scale

| Token | Value |
|---|---|
| `xs` | 4px |
| `sm` | 8px |
| `md` | 12px |
| `lg` | 16px |
| `xl` | 24px |
| `2xl` | 32px |
| `3xl` | 48px |
| `4xl` | 64px |

---

## Radius

| Token | Value | Usage |
|---|---|---|
| `sm` | 8px | Small buttons, inputs |
| `md` | 16px | Cards, chat bubbles |
| `lg` | 24px | Large cards, modal sheets |
| `full` | 9999px | Mic button, avatar, pill labels |

---

## Layout

- **Approach:** Stage-centered (mobile-first). 모바일 한 화면을 명확한 3 zone으로 분할.
- **Target width:** ~360px (mobile), max 480px (handheld limit).
- **Container padding:** `lg` (16px) on mobile.

### Stage zones (main conversation screen)

1. **상단 (~1/3)** — 대화 컨텍스트 (말풍선 / 빈 상태 안내 메시지).
2. **중앙 (~1/3)** — Pally 캐릭터 (항상 같은 위치, 상태별로만 변화).
3. **하단 (~1/3)** — Mic button (큰 원형, 중앙 정렬) + Bottom nav (5 tabs).

### Bottom navigation

5 tabs (home, book/dictionary, chat, +, person). 동등한 간격. `icon` color.

---

## Motion

- **Approach:** Minimal-functional UI + character-expressive Pally.
- **Principle:** UI 모션은 최소. 모든 표현은 Pally 캐릭터에 집중.

### Pally state transitions

| State | Motion |
|---|---|
| idle | 미세한 breathing pulse (느린 sine, 2s loop) |
| listening (rec on) | mic button morphs to stop, Pally subtle scale-up |
| thinking | Pally shape gentle rotation/morph (느린 ease-in-out) |
| speaking | Superformula 파라미터 morphing, EMA 보정 alpha=0.7 |

### UI motion

| Element | Motion |
|---|---|
| Chat bubble enter | fade + slide-up 8px, 200ms ease-out |
| Mic press | scale 0.95, 150ms |
| Bottom nav tab change | content fade 150ms |
| Hint reveal | fade-in 250ms ease-out |

### Easing & duration

- **Easing:** enter `ease-out`, exit `ease-in`, transform `ease-in-out`.
- **Duration:** micro 100ms, short 200ms, medium 300ms, long 500ms.

---

## Implementation Status

- ✅ Pretendard Variable installed (`npm i pretendard` 완료)
- ✅ Typography tokens in [frontend/tailwind.config.ts](frontend/tailwind.config.ts)
- ⏳ Color tokens — TODO: add to `tailwind.config.ts` `theme.extend.colors`
- ⏳ Spacing/radius tokens — TODO: add to `tailwind.config.ts`
- ⏳ Pretendard `layout.tsx`에서 실제 폰트 로드 (현재 Geist 변수 정리 + Pretendard className 적용)

---

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-25 | Initial typography tokens extracted from Figma | Phase 1A frontend audio shell이 type 시스템 필요 |
| 2026-05-25 | Full design system added via `/design-consultation` | Color·spacing·layout·motion을 Figma 메인 스크린(node 341-1132)에서 추출, Figma에 없는 갭(text-muted·border·semantic colors)은 제안값으로 채움 |
| 2026-05-25 | Dark mode out of scope for MVP | June 7 데모 범위. Light only |
| 2026-05-25 | Speaker color coding **YOU = teal / Pally = orange** confirmed | Pally가 핵심 캐릭터 → 따뜻한 primary orange. YOU는 차분·객관 teal. Figma mvp design (node 341-1132)도 동일 방향으로 instance override 정리. master 컴포넌트는 미터치 (PM 합의 전) |
| 2026-05-25 | Bottom nav: light surface + #33363F icons + orange `+` (primary CTA) | 어두운 nav는 따뜻한 톤 컨셉과 충돌. + 새 채팅 = primary action이므로 `primary` 색 부여 |
| 2026-05-25 | Pally character size target ~200px (Star 4 actual width) on 402px stage | 5축 morph 시 가시 길이/형태 변화 폭 확보. 원본 ~225px에서 축소 |
| 2026-05-25 | Listening state = mic morph to stop + character 1.1× scale-up (~220px) | DESIGN.md motion §과 일치하는 명시적 화면 추가. Figma mvp design에 `Pally talk - listening` 프레임 신설 |
| 2026-05-25 | History view에 4×40px panel handle 추가 | Drag/dismiss affordance. 라벨은 별도로 두지 않음 (사용자 결정) |
| 2026-05-25 | Thinking state 색상: `text-muted` (#6b7280) 통일 | "처리 중 / 임시" 뉘앙스를 색으로 표현. teal/orange 사용은 화자 색과 혼동 위험 |
| 2026-05-25 | Timestamp 양옆 dash 장식 제거 | 시각 노이즈 감소, 캡션은 텍스트만 |
| 2026-05-25 | **Mic idle**: primary orange disc(#FE9012) + 화이트 mic 아이콘 + outer glow ring(orange 18% opacity, 132×132) + drop shadow | 더 강한 CTA 시그널, surface와 분리감. primary-soft 단색 disc는 평면적이라 senior 폴리쉬 부족 |
| 2026-05-25 | **Recording (stop) button**: red disc(#EF4444) + 화이트 rounded square(radius 6) + pulse ring(red 22% opacity, 144×144) + drop shadow | red = "recording active" 보편적 시그널. orange disc와 동일 색이면 idle↔recording 구분 약함 |
| 2026-05-25 | Navbar separator: 1px top border `#E5E0D8` + upward soft drop shadow (`y:-2, blur:10, alpha:0.06`) | cream surface + white navbar는 contrast 부족. 하단 영역의 elevation 시그널 |
| 2026-05-25 | **Bottom nav 5 tabs 라벨**: 홈 / 히스토리 / 새 대화 / 랭킹 / 내 정보 (Korean, 11px Regular, 4px gap below icon) | 첫 사용자 자기설명 도움. 영어 라벨은 학습자 인지 부담 ↑ |
| 2026-05-25 | **Nav active state**: 활성 탭은 icon stroke + 라벨 모두 `primary` orange, inactive는 `#33363F` icon + muted gray 라벨 | 어디 화면에 있는지 시각 즉시 인식 |
| 2026-05-25 | **+ 새 대화 FAB**: 검정 disc(`#1A1A1A`) + 흰 cross. 라벨 색은 inactive와 동일 (muted gray) | active tab orange와 색 분리 — 둘 다 orange면 "+가 active처럼" 헷갈림. action affordance ≠ navigation indicator |
| 2026-05-25 | **History view 주황색 stripe 일관성**: 메인 chat bubble의 orange bottom stripe(#FFB84A, 13px)를 history panel 하단에도 동일 적용. 흰 panel 높이 686→605로 축소해 stripe가 panel 바로 밑에 자연스럽게 peek out | 메인뷰와 history뷰가 모두 같은 "bubble" 시스템임을 시각적으로 통일. 사용자가 panel을 내려도 brand decoration 일관 |
| 2026-05-25 | **Mic idle ring vs Recording pulse ring 동일 사이즈** (132px) | 이전엔 idle 132px / pulse 144px로 stop이 더 커 보였음. 동일 사이즈 + 색만 다르게 (idle=orange / recording=red) |
| 2026-05-25 | **Mic permission request 프레임** 신설 — 큰 타이틀 ("마이크 사용 권한이 필요해요") + body + primary CTA "마이크 권한 허용하기" + secondary "나중에 설정하기" | 권한 거부 직전 친근한 안내. 이성적 학습 동반자 톤 |
| 2026-05-25 | **Error states 4종** 신설 — 마이크 권한 거부 / 음성 인식 실패 / 오프라인 / 응답 지연 (이성적 톤 한국어) | 데모 시연 중 가장 자주 마주칠 시나리오 4개 cover |
| 2026-05-25 | **Empty state 한국어로 전환**: "오늘은 어떤 이야기를 해볼까요?\n마이크를 눌러 영어로 말해보세요" | 학습자가 첫 화면에서 영어 카피로 인지 부담 받지 않도록. Pally는 이성적 학습 동반자 톤 |

---

## Known limitations (Figma file ↔ DESIGN.md gaps)

> Figma desktop에 Pretendard Variable이 로컬 설치되어 있지 않은 환경에서 작업 시 다음이 막힘. **Pretendard 설치 후** 후속 작업 가능.

1. **Sender label hierarchy (YOU/Pally)** — 현재 Title1/Title2 크기(20–24px)로 본문보다 크게 표시됨. 의도는 `text-caption-1` (12px SemiBold)로 축소해 본문 위계 아래에 두는 것. Pretendard 미로딩으로 `fontSize` 변경 차단됨.
2. **Demo sample copy typo** — `"I had no lunch I'm diet"` → `"I had no lunch — I'm on a diet"`. 3/11 instance만 수정 성공, 나머지 8개는 Pretendard 미로딩으로 차단됨.

---

## Senior Elevation Plan (App-Store Readiness)

Full plan: [docs/plan/2026-05-25-senior-design-elevation.md](docs/plan/2026-05-25-senior-design-elevation.md)

현재 디자인 완성도 **7.0 / 10**. June 7 데모 전까지 **8.7 / 10** (앱스토어 등록 가능 수준) 목표.

가장 큰 갭: ① **Interaction state coverage** (speaking · error 4종 · permission · partial · offline 미정의), ② **Responsive & A11y** (360px 미검증, contrast 미감사, screen reader spec 없음). Phase A (Pre-demo critical, 4일)에 집중.

Pretendard 설치 후 `/figma-use` 또는 plugin script로 재실행하면 일괄 적용 가능.
