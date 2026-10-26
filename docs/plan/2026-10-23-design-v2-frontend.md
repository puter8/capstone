# Pally v2 디자인 프론트 반영 · 루트 경로 전환

기준: 2026-10-23 KST, 브랜치 `feat/design-v2`(`1015-frontend` → 10/15 미커밋 작업 2커밋 → `origin/main` 머지).

현재 결정은 아래 **교체(v1 삭제) 체크리스트**의 2026-10-26 KST 기록을 따른다. 그 앞의 구조·화면·검증·열어둔 판단은 2026-10-23 병행 구현 당시 기록이다.

## Claire 결정

- v2 디자인(Figma `1023_디자인 업그레이드 v2`, 페이지 `1360:750`)을 코드로 옮기되, **v1은 당장 지우지 않고 `/v2` 경로로 병행**한다. 최종 목표는 v2가 v1을 대체하는 것이다.
- 1차 범위는 10개 경로 전부. 백엔드는 기존 `lib/api`(Railway)를 그대로 써서 실연결한다.
- v2 화면의 문구는 디자인 문서 "코드 문구를 바꿔야 하는 제안" 표를 따른다(v1 문구는 v1에 그대로 남는다).
- **2026-10-26 변경:** v2를 루트로 옮긴다. 겹치는 v1 페이지·오류 화면만 삭제하고, v1 컴포넌트·Tailwind 토큰은 보존한다. `feat/design-v2`에서 로컬 커밋만 만들며 푸시·PR·main 합류·배포는 하지 않는다. 백엔드·PallyCanvas·app/dev는 수정하지 않는다.

## 구조

- **v1 파일 0줄 수정.** 공유하는 것은 디자인과 무관한 계층뿐이다: `lib/api/*`, `lib/state/conversation.ts`, `lib/audio/useRecorder.ts`(상수 `MAX_DURATION_MS` export만 추가), `lib/hooks/usePally.ts`, `components/pally/PallyCanvas.tsx`(김민주 영역, 읽기 전용).
- 토큰: `frontend/styles/v2-tokens.css`는 `docs/design/pally.tokens.css`의 복사본이며 선택자만 `[data-design="v2"]`(+ `html:has(...)`)로 바꿨다. 유일한 값 차이는 `--p-font-brand`(next/font 변수). `check:v2-tokens`가 동기화를 검사한다.
- Tailwind: `tailwind.config.ts`에 `p-*` 네임스페이스(색·서체·타입 스케일·간격·모서리)를 CSS 변수로 추가했다. v1 토큰은 그대로다.
- 폰트: Pretendard는 설치돼 있던 `pretendard` 패키지의 동적 서브셋 CSS를 `app/v2/layout.tsx`에서만 import한다. Fraunces는 `next/font/google`(`weight: "variable"`, `axes: SOFT/WONK/opsz`)로 빌드 시 자체 호스팅한다. 새 npm 의존성은 없다.
- 경로: `lib/v2/routes.ts`의 `V2_BASE` 하나로 모든 v2 링크를 만든다. `check:v2-routes`가 리터럴 경로를 막는다. 유일한 예외는 결제 `success_url`(아래).
- 홈 대화 로직은 `lib/hooks/useHomeConversation.ts`로 포팅했다(v1 `app/home/page.tsx`는 그대로). 추가한 것: 건너뛰기(`skipPlayback`), 마지막 답장 다시 듣기(메모리 보관, 새로고침 후 비활성), 녹음 경과·30초 고리, 단일 버튼 한도 시트, `pressStart`에서도 AudioContext 언락.
- 목소리 등록 로직은 `lib/hooks/useEnergyBaselineRecorder.ts`로, 대화 재개는 `lib/api/resume-conversation.ts`로 포팅했다.
- 32px 팔리 아바타는 `components/v2/PallyThumb.tsx`가 숨긴 `PallyCanvas`(128px)를 한 번 그려 `toDataURL`로 스냅샷한다. 캐릭터 매핑을 다시 그리지 않았다.
- 아이콘 32개는 Figma SVG를 내보내 `components/v2/icons/index.tsx`에 `currentColor` 컴포넌트로 넣었다(`lucide-react` 미설치).

## 화면

`app/v2/`: 로그인 `/v2`, `auth/callback`, `onboarding`(레벨·이름·목소리 소개·질문 3개·완료, `?step=voice` 재진입), `home`(시작 전·선발화·내 차례·녹음·처리·응답·전체 대화·오류·복원·한도·종료 저장), `history`, `history/feedback`, `ranking`, `my`(이름·기록 삭제·로그아웃·탈퇴 시트), `settings/level`, `settings/plans`(구독 시작·해지·해지 완료·결제 상세 시트), `error.tsx`, `not-found.tsx`, `[...rest]` catch-all.

## 검증 (2026-10-23)

- `tsc --noEmit`, `next lint`(v2 코드 경고 0, v1 기존 `<img>` 권고 4건만), `next build` 통과(`/v2/*` 11개 경로 정적 생성).
- `check:*` 14개 통과. 새로 추가: `check:v2-tokens`, `check:v2-routes`, `check:pally-segments`의 v2 `Bubble` 단언(라일락 실선·버터 점선·숨긴 라벨·`lang="en"`). CI `frontend-billing` job에 연결.
- **실백엔드(Railway) E2E, Claire 계정(이찬희), Aside Browser:**
  - `/v2/home`: 실제 사용량(20회 → 19회), 프로필 이름, 라이브 `PallyCanvas` 렌더 확인. 대화 시작 → 실제 opener 수신·재생("Hey! So, any fun plans lined up for the weekend?").
  - 백엔드 `/api/tts`로 만든 음성을 MediaStream으로 주입해 녹음 → 실제 STT → Gemini 조각 응답 → TTS 재생. STT: "Yesterday, I go to the park with my friend and we eat ice cream." 응답 조각: `correction` "went to the park", `new_expr` "a good walk" + 범례 표시. 무대 상태 `speaking` → 건너뛰기 → `idle`. 다시 듣기 활성 → 재생 → 건너뛰기. 전체 대화(날짜 구분선 2026.10.23, 3개 말풍선) → 대화 종료 → 시작 화면 복귀(2초). `/v2/history` 첫 카드에 새 대화(1번 주고받음, 제목 생성 대기 표시).
  - 새로고침 후 다시 듣기 비활성 확인(백엔드가 `pally_audio_url`을 반환하지 않음).
  - 기록·피드백 상세(빈 상태)·업적·마이·레벨 변경·요금제·온보딩(레벨/완료)·로그인·없는 페이지를 360px iframe으로 캡처해 Figma와 대조했다.
- **새 계정 실검증(Claire 계정 탈퇴 → Google 재가입, Aside Browser, Railway, 2026-10-23 오전):**
  - 마이 페이지 시트 4개 실동작: 이름 변경(철수 → 클레어), 로그아웃 시트, 대화 기록 삭제(실삭제 + 토스트) → 기록 빈 상태 → 피드백 상세 "아직 나눈 대화가 없어요"(이 상태를 이번에 추가), 회원탈퇴 실행 → `/v2` 복귀.
  - 재가입: `/v2`의 Google 버튼이 `redirect_to=…/v2/auth/callback`으로 계정 선택까지 이동하는 것을 확인했고, 로그인 자체는 자동화하지 않고 Claire가 Aside에서 직접 했다. **로그인 직후 착지 주소(허용 목록 통과 여부)는 미확인.**
  - 온보딩 실저장: 레벨 B2 → 이름 "철수" → 프로필 생성 → 목소리 소개 → 질문 3개 녹음(`/api/tts` 합성 음성, 각 9초) → `POST /api/energy/baseline` 200 `status: ready`(`range_st 7.54`, `valid_clips 3`) → "다 됐어요!" → 홈(20회 남음).
  - 오류 경로 1건 실확인: 세 질문에 같은 음원을 쓰자 백엔드가 "같은 파일 3개"로 422(`clip_index` 없음)를 돌려줬고 화면은 "녹음을 확인하지 못했어요. 질문을 눌러 각각 다시 녹음해 주세요."를 띄웠다. 질문마다 다른 음원으로 바꾸니 등록됐다.
  - 새 계정 첫 턴: opener "Hey! Do you have any pets…" → 합성 음성 → STT "Not much honestly, I think I will stay home and watch some movie…" → 조각 `new_expr` "cozy movie night"(버터 점선, `own_remark`·`question` 조각은 강조 없음) → 사용량 20 → 19, 팝오버(1회 사용 · 19회 남음 · 10월 24일 0시) → Escape로 닫힘 → 종료 → 시작 화면 + "에너지는 갱신하지 않았어요" 경고 토스트(짧은 합성 음성 때문, 백엔드 판단).
  - 녹음 권한 거부: `getUserMedia`가 `NotAllowedError`를 던지게 하고 마이크를 누르자 토스트 "마이크 권한이 필요해요…", 도크 "다시 말하기"(retry), 상태 문구 "권한을 허용한 뒤 눌러 주세요".
  - 기록 "이어서 대화": `/v2/home?conversation_id=…`로 이동해 지난 opener를 복원하고 "눌러서 말하기"까지 확인, 종료.
  - 한도 시트: **브라우저 안에서 `/api/usage` 응답만 `remaining_turns: 0`으로 바꿔**(Response.prototype 패치, 백엔드 호출·상태 변경 없음) 홈에 들어가자 시트 "오늘 무료 대화를 모두 썼어요"(초기 포커스 "확인") → 닫으면 칩 "오늘 남은 대화 없음", CTA "내일 0시에 다시 대화할 수 있어요" 비활성. 실제 429 `quota_exceeded`는 실행하지 않았다.
  - 요금제: 실제 무료 상태(월 9,900원 · 연 99,000원 7일 체험) → 연간 선택 → 계속하기 → 시트 "구독 시작하기"(오늘 결제 0원, 초기 포커스 결제 버튼) → Escape로 닫힘. 결제는 실행하지 않았다.
- **미검증/한계:**
  - 360px은 Aside가 viewport 설정을 지원하지 않아 같은 출처 iframe(360×800)으로 확인했다. 새 계정 흐름 캡처는 데스크톱 폭이다. 물리 모바일·iOS Safari·200% 확대는 미확인.
  - 요금제 Pro/해지/해지 완료/결제 확인 중 상태와 결제 실행은 실데이터가 없어 화면 코드만 있다. 카카오페이 샌드박스로 실제 체험 구독을 만들어야 확인할 수 있다.
  - `npm run test:e2e`의 v2 테스트는 버튼 가시성 단언까지 통과했으나 AI 단언 단계가 모델 제공자 오류(Bad Request)로 실패했다. v1 테스트도 같은 단계를 쓴다.
  - `/v2/auth/callback`: Supabase redirect 허용 목록은 MCP로 조회하지 못했다. Claire가 `/v2`에서 로그인해 새 계정 세션은 만들어졌지만, 콜백 페이지에 착지했는지 Site URL로 폴백됐는지는 기록이 없다. Dashboard › Authentication › URL Configuration의 `{origin}/v2/**`와 함께 다음 로그인 때 확인한다.
  - Aside 메모: `window.fetch`를 감싸면 App Router 링크 이동이 전체 새로고침으로 떨어진다(v1·v2 모두 동일, 앱 버그 아님). 응답을 바꿔야 하면 `Response.prototype.json/text`를 패치한다.

## 열어둔 판단

- 결제 `success_url`: `backend/lib/billing.py`가 `/settings/plans?checkout=…`만 허용해 v2도 v1 URL을 보낸다(`// v2-routes-allow`). 결제 후 v1 요금제 화면에 착지한다. 교체 시 자동 해소.
- 다시 듣기는 현재 세션의 마지막 답장만. `/api/tts` 재합성은 비용 판단 후.
- 기록 카드 밀도는 정보 4줄 유지.
- 10/15 백엔드 보완(`ai/reply_segments.py`, `backend/main.py`)은 별도 커밋 `1885ff3`에 있다. `main` 머지 시 Railway가 재배포되므로 백은혜와 공유 후 별도 PR로 나눌 것.

## 교체(v1 삭제) 체크리스트

2026-10-26 KST · Claire의 이번 작업 지시를 기준으로 범위를 좁혔다.

- [x] 시작 상태: `feat/design-v2`, `git fetch origin` 후 `origin/main...HEAD = 0 5`. main 머지 불필요.
- [x] 태그 없이 롤백 기준 해시 기록: `a3d43e1303d24d63d76b6f96fb6f3cdb9bdd6bf9`. `git reset --hard` 실행은 Claire에게 별도 확인한다.
- [x] 겹치는 v1 페이지·error/not-found/global-error만 삭제하고 `app/v2/*`를 `git mv`로 루트에 이동. `app/api`, `app/dev`, favicon, globals, 루트 layout은 보존.
- [x] `V2_BASE = ""`, `v2Path("/") = "/"`. 로그인 콜백은 `/auth/callback`, 결제 반환은 공통 `routes.plans`(`/settings/plans`). 결제 예외 주석 제거.
- [x] 토큰 선택자 `:root`, 래퍼 스타일 `body`로 이동. 토큰 값 유지. Fraunces 변수를 `html`에 두어 `:root`의 브랜드 폰트 토큰에서도 해석되게 함.
- [x] 루트 layout에서 Pretendard·Fraunces·확대 허용 viewport 사용, Noto Sans KR 제거. v1 html 배경은 v2 배경 토큰으로 교체.
- [x] 코드의 `/v2` 페이지 경로 제거. 소스 import 경로와 정상 표시되는 `public/v2/*.svg` URL은 유지.
- [x] 경로 검사는 `app`·`components/v2`를 읽고 `app/api`·`app/dev`는 제외. 토큰 검사는 `:root` 및 문서 값 동기화를 유지. v1/v2 말풍선 검사 블록은 기존 컴포넌트 경로 그대로 유지.
- [x] v2 공개 페이지 e2e의 시작 주소를 `/`로 변경하고 `test:e2e`는 해당 테스트만 실행. v1 e2e 파일은 후속 정리까지 보존. CI의 기존 v2 검사 호출을 유지하고 이름 변경 다이얼로그 검사를 추가.
- [x] 백엔드 보완 커밋 `1885ff3` 유지. 백엔드·ai·app/dev·PallyCanvas·캐릭터 타입 변경 없음.
- [x] 최종 검증 결과 기록: 아래 표·Aside 검증 참조. 페이지 이동 커밋은 `aafcef3`.

### 루트 전환 검증 (2026-10-26 KST)

| 검사 | 실제 결과 |
|---|---|
| 타입체크 | `npm --prefix frontend exec tsc -- --noEmit -p frontend/tsconfig.json` 종료 0. 지시문의 `-p` 없는 명령은 저장소 루트에서 tsconfig를 찾지 못해 도움말만 출력했으므로 프로젝트를 명시함. |
| 린트 | `npm --prefix frontend run lint` 종료 0. 보존한 v1 컴포넌트의 기존 `<img>` 권고 17건. |
| 빌드 | `npm --prefix frontend run build` 종료 0. `/`, `/home`, `/history`, `/history/feedback`, `/ranking`, `/my`, `/settings/level`, `/settings/plans`, `/onboarding`, `/auth/callback` 생성. `/v2/*` 페이지 없음. |
| 필수 스크립트 | `check:v2-tokens`, `check:v2-routes`, `check:pally-segments` 모두 통과. 123개 토큰 동기화, 59개 Tailwind 참조 해석, 38개 소스 파일 경로 검사. |
| v1 유지 검사 | `check:name-edit-dialog`, `check:inline-feedback` 통과. 기존 컴포넌트를 보존했으므로 검사 이관 불필요. |
| CI 프론트 회귀 검사 | 위 검사와 함께 billing-contract, billing-view, billing-account-binding, mock-api, query-cache, conversation-order, opener, home-snapshot 모두 로컬 통과. |
| 경로 유틸 | `v2Path("/")`, 끝 슬래시 정리, `/auth/callback`, `/settings/plans`, 4탭의 `href === dataKey` 직접 확인. |
| catch-all 충돌 | HTTP `/api/health` 200 및 `{"ok":true}`, `/dev/pally` 200. `/v2/home`·없는 경로는 404. |

첫 빌드는 `.next-dev/types/app/v2`에 남은 생성 타입이 삭제된 페이지를 참조해 실패했다. 실행 중인 기존 dev 서버가 없음을 확인하고 해당 생성 타입만 정리한 뒤 빌드·타입체크를 통과했다. 소스·tsconfig 변경으로 우회하지 않았다.

**Aside Browser 실검증:**

- 기존 로그인 세션으로 `http://localhost:3000`의 실제 Railway 연결을 사용했다. `.env.local`은 바꾸지 않았다.
- Aside의 같은 출처 iframe(360×800)에서 `/`, `/home`, `/history`, `/my`, `/settings/plans`를 캡처·확인했다. 각 화면의 `innerWidth`·`scrollWidth`가 모두 360. 배경 `rgb(23,23,27)`, 라일락 `#B7B5F2`, Pretendard UI·next/font Fraunces 브랜드 글꼴 및 확대 허용 viewport 확인. 로그인 SVG 2개도 실제 로딩됨.
- 홈→피드백→업적→마이→홈 이동 중 같은 window 표식과 `performance.timeOrigin`이 유지됐다. 하단 4탭은 전체 새로고침 없이 이동했다.
- `/home`에서 실제 선발화(201)→GCP TTS로 만든 8.616초 음성을 MediaStream 입력으로 녹음→실제 STT/Gemini/TTS 한 턴(201)→종료(200)를 수행했다. 사용량은 **20→19회**, 추가 턴 없음. 응답은 “You went to a cafe? Sounds like a lovely time! What did you talk about?”이며 `lovely time` 새 표현 표시를 확인했다.
- 대화 `cf794860-d2a1-480d-a50f-eec4eef132d2`를 목록·상세 API(각 200)로 재조회했다. `completed`, `turn_count: 1`, 제목 `Cafe Visit and Weekend Plans`, 사용자 STT와 Pally 응답이 저장돼 있었다. `/history` 카드와 `/history/feedback?conversation_id=…`에서도 표시됐다.
- 종료 시 백엔드의 `energy_unavailable` 경고가 화면에 표시됐다. 합성 음성으로 이 대화의 에너지는 갱신되지 않았지만 대화 저장은 성공했다.

**확인하지 않은 항목:**

- `npm run test:e2e` 러너는 별도 브라우저를 띄우므로 Aside 전용 규칙에 따라 실행하지 않았다. 변경한 공개 페이지의 가시성·디자인·가로 넘침은 Aside에서 직접 확인했다. 원격 CI 실행도 푸시하지 않아 미실행이다.
- 물리 모바일/iOS, 실제 마이크 입력, 새 OAuth 로그인 전체 왕복, 실제 결제 왕복은 이번 검증에 포함하지 않았다. 로그인 `redirectTo`와 결제 반환 URL은 경로표·호출 코드로 확인했다.

- [x] 정리: 검증용 dev 서버 종료(3000 포트 리스너 없음), 테스트 MP3·임시 JSON·명령 로그 제거, Aside 관찰 설정 복원 및 전용 탭 2개 종료. `.env.local` 변경 없음. 기존 미추적 `.playwright-mcp/`, `output/`, `yourpally-domain-mobile.png`는 보존하고 커밋에서 제외.

후속 작업(이번 범위 밖):

- [ ] v1 컴포넌트와 사용하지 않는 v1 검사·e2e 정리.
- [ ] Tailwind v1 토큰 제거.
- [ ] 하단 내비 `dataKey` 중복 제거(이번에는 `href`와 같은지 확인).
- [ ] 김민주에게 `PallyCanvas` 정적 렌더 export 요청(이번에는 연락·구현하지 않음).
