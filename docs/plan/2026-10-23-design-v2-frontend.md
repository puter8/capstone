# Pally v2 디자인 프론트 반영 · `/v2` 병행 구현

기준: 2026-10-23 KST, 브랜치 `feat/design-v2`(`1015-frontend` → 10/15 미커밋 작업 2커밋 → `origin/main` 머지).

## Claire 결정

- v2 디자인(Figma `1023_디자인 업그레이드 v2`, 페이지 `1360:750`)을 코드로 옮기되, **v1은 당장 지우지 않고 `/v2` 경로로 병행**한다. 최종 목표는 v2가 v1을 대체하는 것이다.
- 1차 범위는 10개 경로 전부. 백엔드는 기존 `lib/api`(Railway)를 그대로 써서 실연결한다.
- v2 화면의 문구는 디자인 문서 "코드 문구를 바꿔야 하는 제안" 표를 따른다(v1 문구는 v1에 그대로 남는다).

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
- **미검증/한계:**
  - 360px은 Aside가 viewport 설정을 지원하지 않아 같은 출처 iframe(360×800)으로 확인했다. 물리 모바일·iOS Safari·200% 확대는 미확인.
  - 한도 시트, 녹음 권한 오류, 요금제 Pro/해지/결제 확인 중 상태, 결제 실행, 온보딩 실저장(계정이 이미 온보딩·목소리 등록 완료)은 화면 코드만 작성했고 실데이터로 띄우지 않았다.
  - `npm run test:e2e`의 v2 테스트는 버튼 가시성 단언까지 통과했으나 AI 단언 단계가 모델 제공자 오류(Bad Request)로 실패했다. v1 테스트도 같은 단계를 쓴다.
  - `/v2/auth/callback`은 Supabase redirect 허용 목록을 확인하지 못했다(MCP로 조회 불가). 실제 OAuth 로그인은 Claire가 Dashboard › Authentication › URL Configuration에서 `{origin}/v2/**`를 확인한 뒤 시도해야 한다. 현재 검증은 v1 로그인 세션을 그대로 썼다.

## 열어둔 판단

- 결제 `success_url`: `backend/lib/billing.py`가 `/settings/plans?checkout=…`만 허용해 v2도 v1 URL을 보낸다(`// v2-routes-allow`). 결제 후 v1 요금제 화면에 착지한다. 교체 시 자동 해소.
- 다시 듣기는 현재 세션의 마지막 답장만. `/api/tts` 재합성은 비용 판단 후.
- 기록 카드 밀도는 정보 4줄 유지.
- 10/15 백엔드 보완(`ai/reply_segments.py`, `backend/main.py`)은 별도 커밋 `1885ff3`에 있다. `main` 머지 시 Railway가 재배포되므로 백은혜와 공유 후 별도 PR로 나눌 것.

## 교체(v1 삭제) 체크리스트

플랜 파일(`~/.claude/plans/crispy-bubbling-ocean.md`) §6과 같다: `app/v2/*` → `app/*` 이동, `V2_BASE = ""`, 토큰 선택자 `:root`, 루트 `layout.tsx` 폰트·viewport 교체, Tailwind v1 토큰 제거, v1 컴포넌트·스크립트·e2e 정리, 김민주에게 `PallyCanvas` 정적 렌더 export 요청.
