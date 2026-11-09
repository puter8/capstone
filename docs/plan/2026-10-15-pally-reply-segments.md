# Pally 응답 색상 연결

기준: 2026-10-15 KST, `1015-frontend`, 시작 커밋 `3fbda2a`.

## 확정한 동작

- Claire의 후속 수정 기준: `correction`은 주황·굵게, `new_expr`는 민트·굵게이며 밑줄은 없다. `own_remark`·`question`·`plain`은 기본색·보통 굵기다. Pally/YOU 화자 라벨의 기존 굵기는 유지한다.
- YOU와 Pally의 기본 본문은 모두 검은색 토큰 `text`(`#1C1A17`)로 통일한다. 화자 라벨의 주황·민트 색과 교정·새 표현의 강조는 유지한다.
- 짧은 보기와 펼친 보기에서 파란 인라인 피드백 박스를 제거한다. 사용자 발화와 Pally 응답 본문은 그대로 표시한다.
- 서버가 지정한 조각 전체를 순서대로 표시한다. 본문을 재분석하거나 조각의 공백을 제거·추가하지 않는다.
- POST `pally.segments`와 GET `pally_segments`를 UI 메시지에 보존하고, 짧은 보기·펼친 보기·녹음 중 직전 응답·새로고침·History 재개에 같은 렌더러를 사용한다.
- 조각은 턴 본체와 분리해 검증한다. `null`·생략은 정상 평문 경로다. 잘못된 구조·빈 배열·본문과의 불일치는 오류 로그를 남기고 해당 응답만 평문으로 표시한다. 턴 성공·음성·다른 응답 필드는 유지한다.
- 조각 오류 로그에는 응답 종류·원인·필드 위치만 남긴다. 실제 본문·조각 내용·인증정보는 기록하지 않는다. 본체 오류는 기존 오류 처리대로 실패시킨다.
- 최초 FE 연결 범위에서는 백엔드·DB 마이그레이션·새 의존성·History 피드백 카드 변경을 제외했다. 이후 Claire가 정상 문장의 잘못된 교정 표시 수정을 요청해 백엔드의 교정 판정 보완까지 범위를 확장했다. DB 변경·배포는 포함하지 않는다.

## 운영 및 사전 확인

- 2026-10-15 16:22:52 KST, Railway `powerful-laughter / production / web`의 활성 배포 `82da4392-6355-4d02-90ef-8e49eb033949` 확인. `SUCCESS`, `stopped: false`, Git SHA `3fbda2ad244022870ea524d1b40b4d1f11c78a4a`.
- #117 머지 `d7aea4a`와 기능 `e39cf3a`가 배포 커밋의 조상임을 확인했다. 재배포·연결 설정 변경은 하지 않았다.
- Aside CLI를 공식 업데이트로 `1.26.1015.732`로 갱신하고 가이드·인증을 확인했다. Claire가 지정한 이찬희 Google 계정으로 localhost에서 공식 OAuth 로그인했다.
- `/api/usage` HTTP 200: 무료 계정, 하루 20회, 시작 시 사용 0회·잔여 20회, 초기화 2026-10-16 00:00 KST.
- Aside에서 AudioContext·MediaRecorder·WebAudio MediaStream 생성이 가능함을 확인했다. 기존 검증 방식대로 실제 Google TTS 음성을 MediaStream으로 입력해 앱의 녹음·WAV 변환·실제 GCP STT/Gemini/TTS를 통과시켰다. 물리 마이크 발화와는 구분한다.
- 코드 수정 전 첫 실제 턴 HTTP 201, 약 5.7초. 7개 조각의 연결 결과와 본문이 일치했고, 상세 GET HTTP 200의 저장된 조각과 동일했다.
- 같은 Idempotency-Key로 재요청한 결과 HTTP 201, `replayed: true`, 동일 turn ID·본문·조각 확인. 추가 발화로 계산하지 않는다.
- 운영 DB 마이그레이션은 BE의 적용 완료 안내를 전제로 재적용하지 않았다. 저장 확인은 운영 백엔드의 상세 재조회와 영속 turn ID를 근거로 한다. Supabase 관리 API 직접 조회와 구분한다.

## 최초 구현의 실제 검증 기록

아래는 후속 표시 수정 전 검증이다. 현재 표시 규칙과 화면 검증은 문서 하단의 후속 수정 기록을 따른다.

- 새 테스트 대화: `9563d3a2-53ee-4d6e-b242-3d3cff762270`.
- Google TTS 합성 음성 3개를 앱의 녹음 UI로 전송했다. 실제 POST 응답은 모두 HTTP 201, audio 포함, 각 7개 조각과 본문 일치였다. 저장 후 상세 GET에서도 3개 턴 모두 같은 조각을 반환했다.

| STT 결과 | 턴 응답 시간 | Formality | Energy | Intimacy | Humor | Curiosity |
|---|---|---|---|---|---|---|
| `yesterday, I go to the park with my` | 5.700초 | 40 | 34 | 22 | 7 | 5 |
| `She do not like coffee but I think it is funny.` | 7.341초 | 47 | 31 | 21 | 2 | 2 |
| `Could you please explain why I feel very tired today.` | 5.621초 | 46 | 30 | 12 | 1 | 25 |

- 첫 샘플의 입력 문장은 `Yesterday I go to the park with my friend.`였으나 STT 결과의 마지막 `friend`는 누락됐다. 음성 인식 품질 개선은 이번 변경 범위 밖이며 조각/본문 일치 검증과 구분한다.
- 짧은 말풍선의 교정 주황·새 표현 민트 밑줄·질문 기본색 굵기를 확인했다. 녹음 중 직전 응답에도 7개 조각이 유지됐다.
- 펼친 보기의 조각 총 21개, Pally 본문 3개가 원문과 모두 일치했다. 첫 인사는 평문으로 유지됐다.
- 실제 페이지 새로고침 후 마지막 응답의 7개 조각과 굵기가 복원됐다. 대화를 종료하고 History의 `Feeling Tired After Park Visit` 카드에서 다시 열어 동일 결과를 확인했다.
- 이전 실제 대화: `c7a3252e-bf40-4334-a5a1-0b115f99b8a3`, 시작 2026-10-08 17:45:06 KST. 상세 조회의 5개 메시지 쌍(첫 인사 포함) 모두 `pally_segments: null`이었다. History의 `Studying and Funny Stories` 카드에서 실제로 재개한 뒤, 색칠 span 0개·원래 Pally 본문 표시를 확인했다. 새 발화는 추가하지 않고 다시 종료했다.
- 검증 종료 시 두 대화 모두 `completed`. 새 대화는 사용자 3턴, 이전 대화는 기존 사용자 4턴을 유지한다. 삭제는 수행하지 않았다.
- 최종 `/api/usage`: 사용 3회, 잔여 17/20회. 재반환·재조회·History 재개는 추가 발화를 소비하지 않았다.

## 화면·자동 검증

- Aside의 `setViewportSize`는 지원되지 않았다. 기존 방식대로 문서 콘텐츠 폭을 360px로 맞춰 검증했다. 실제 브라우저 viewport는 1440px이며 모바일 viewport 에뮬레이션·물리 모바일 기기 테스트로 간주하지 않는다.
- 360px 콘텐츠에서 가로 넘침 없음. 펼친 History의 스크롤 높이 740px, 표시 높이 563px, 끝까지 스크롤 후 마지막 질문 전체가 표시 영역 안에 들어옴을 확인했다.
- 오류 경로는 자동 검사 fixture로 확인했다. 잘못된 구조·본문 불일치 등 8가지 입력, `replayed: true`의 오류 조각, History의 한 턴만 손상된 경우 모두 로그 1회와 해당 응답의 평문 처리를 확인했다. 서버 저장 데이터를 고의로 손상시키지 않았다.
- `check:pally-segments`: POST/GET의 null·생략 무로그, 독립 검증과 본체 실패 유지, 음성·축·상태 보존, 로그의 실제 내용 비노출, 재반환, 혼합 History, 공백·escaping·중복 없음, 짧은/펼친/녹음 중 UI 검사 통과. 기존 CI에 연결했다.
- 기존 `check:conversation-order`, `check:opener`, `check:inline-feedback`, `check:mock-api`, `check:query-cache`, `check:home-snapshot` 모두 통과했다. opener의 503/409 로그는 기존 오류 fixture의 기대 결과다.
- `npm run lint`, `tsc --noEmit`, `npm run build` 통과. 기존 `<img>` 사용 권고만 남아 있다. 최초 빌드에서 테스트의 iterator spread가 저장소 TypeScript target과 맞지 않아 `Array.from()`으로 수정했고, 타입검사·새 검사·빌드를 다시 통과했다. 프로젝트 설정은 변경하지 않았다.
- 화면 근거: `output/pally-segments-20261015/reply-short.png`, `reply-expanded.png`, `history-null.png`, `history-expanded-bottom.png`.

## 색상과 대비

브라우저의 실제 계산 스타일에서 `rgb(254, 144, 18)`, `rgb(0, 195, 208)`, `rgb(28, 26, 23)`과 흰 말풍선 배경 `rgb(255, 255, 255)`를 확인했다. 본문 크기는 16px이다. 최초 구현의 질문 굵기·새 표현 밑줄은 후속 요청에 따라 제거하고, 주황·민트의 강조 굵기 700은 유지한다.

| 용도 | 토큰 | 색상 | 흰색 `#FFFFFF` 대비 |
|---|---|---|---|
| 교정 | `primary` | `#FE9012` | 2.280:1 |
| 새 표현 | `accent` | `#00C3D0` | 2.161:1 |
| 일반 본문·질문 | `text` | `#1C1A17` | 17.362:1 |

상대 휘도 `(밝은색 휘도 + 0.05) / (어두운색 휘도 + 0.05)`로 계산했다. 현재 16px 본문의 주황·민트는 WCAG AA 4.5:1에 미달한다. 굵게 표시해도 이 대비 기준을 충족하는 것은 아니다. Claire가 확정한 이미지 기준 색상을 이번 범위에서 유지하고 제한을 기록한다. [W3C 대비 기준](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)

## 협업 및 마무리

- **`frontend/components/chat`과 `.github/workflows/ci.yml` 변경은 PR 시 팀 공지가 필요하다.** 변경 범위·표시 규칙·검증 결과를 공지하고 공유 파일 충돌을 확인한다.
- 이 작업은 실제 팀 공지·커밋·푸시·PR·머지·배포를 포함하지 않는다.
- 검증용 음성 주입·네트워크 관찰은 원복했고, 새로고침으로 임시 전역 객체가 사라진 것도 확인했다. 검증 전용 탭을 닫아 너비 조정도 정리했다.
- 기존 미추적 산출물과 `.env.local`은 보존했다. 사용자 요청의 3000 개발 서버는 빌드 충돌 방지를 위해 잠시 종료한 뒤 다시 실행했고, `/home` HTTP 200을 확인했다.
- `git diff --check` 통과, `AGENTS.md -> CLAUDE.md` 유지. 코드·테스트·문서 외 요청 밖 파일 변경은 없다.

## 로컬 실제 마이크 권한 — 후속 확인

- Claire의 로컬 발화 테스트 요청에 따라 Aside의 `http://localhost:3000` 사이트 권한을 확인했다. 안전한 컨텍스트였고 앱의 마이크 차단 헤더는 없었으나 사이트 설정의 Microphone이 `Block`, Permissions API가 `denied`였다.
- Aside의 기본 사이트 설정 화면에서 해당 origin의 Microphone만 `Allow`로 변경했다. 새로고침 후 `granted`를 확인했다. 다른 사이트·카메라·전역 권한은 변경하지 않았다.
- 원래 `getUserMedia`로 `MacBook Air Microphone (Built-in)`의 `live` 트랙을 열 수 있음을 확인하고 즉시 종료했다. 녹음 저장·턴 전송은 하지 않았다.
- 기존 360px 콘텐츠·합성 음성 검증과 구분한다. 실제 장치 연결은 확인했지만 Claire의 실제 발화를 통한 STT 결과와 물리 모바일 테스트는 이 확인에 포함하지 않는다. 기존 로컬 탭을 새로고침한 뒤 직접 녹음할 수 있다.

## 대화 표시 — 후속 수정

- Claire의 최종 정정에 따라 주황 교정과 민트 새 표현만 굵게 표시한다. 기본색 본문과 질문은 보통 굵기이며, 새 표현의 밑줄은 제거한다.
- 짧은 보기·펼친 보기의 파란 인라인 피드백 박스와 `피드백 보기` 버튼을 제거했다. History의 별도 피드백 화면은 유지한다.
- 저장된 실제 대화를 검증 전용 탭에서 다시 열었다. 짧은 보기 7개·펼친 보기 14개 조각에서 교정/새 표현의 계산 굵기 700, 나머지 400, 모든 조각의 `text-decoration-line: none`을 확인했다. 두 화면 모두 피드백 버튼이 없고 원문은 표시됐다.
- 360px 콘텐츠 폭에서 줄바꿈과 전체 본문 표시를 확인했다. 펼친 보기의 콘텐츠 너비·스크롤 너비 모두 360px으로 가로 넘침이 없었다. 브라우저 viewport 자체는 기존 1440px이며 물리 모바일 검증과 구분한다.
- 최신 검사: `check:pally-segments`, `check:inline-feedback`, `tsc --noEmit`, 변경한 컴포넌트·검사 파일의 lint 통과. 전체 빌드는 최초 구현 때 통과했으며 이번 표시 수정 후에는 다시 실행하지 않았다.
- 최신 화면 근거: `output/pally-segments-20261015/reply-style-short.png`, `reply-style-expanded.png`. 앞선 `reply-short.png`·`reply-expanded.png`는 수정 전 화면이다.
- 이번 확인에서 새 발화나 대화 종료는 하지 않았다. 사용자 테스트 탭과 3000 개발 서버는 유지하고 검증 전용 탭만 닫았다.

## 기본 본문색 통일 — 추가 수정

- YOU 본문의 회색을 제거하고 Pally와 동일한 `text` 토큰(`#1C1A17`)을 적용했다. 화자 라벨의 색과 주황·민트의 굵은 강조, 밑줄·파란 박스 제거 상태는 유지한다.
- 실제 저장된 대화의 짧은 보기·펼친 보기에서 YOU/Pally 본문의 계산 색상이 모두 `rgb(28, 26, 23)`임을 확인했다. 펼친 보기를 360px 콘텐츠 폭에서도 확인했다.
- 기존 `check:pally-segments`·`check:inline-feedback`와 `MessageRow.tsx` lint 통과. 새 발화·커밋·배포는 하지 않았다.
- 화면 근거: `output/pally-segments-20261015/reply-black-text-expanded.png`.

## 최신 main 동기화 — 2026-10-15

- Claire의 요청으로 `1015-frontend`를 `3fbda2a`에서 `origin/main`의 `4f7bd7a`까지 fast-forward했다. PR #119(음성 Energy), #120(개인 데이터 제외), #121(교정 구간 분리)의 10개 커밋을 포함한다.
- 기존 미커밋 변경은 자동 임시 보관 후 복원했다. API 타입·스키마·CI는 양쪽 변경이 함께 반영됐고 충돌은 없었다. 나머지 기존 수정 파일은 임시 보관본과 동일함을 확인했다. 새 커밋·푸시·배포·DB 마이그레이션 실행은 하지 않았다.
- #121의 `corrected_expr`는 모델 내부 필드다. 외부 API의 5종 `kind`와 조각 구조는 유지돼 현재 FE 렌더러와 호환된다. `plain`은 이제 공백 외에 교정 구간 주변 문구나 교정 없는 반응 전체도 포함하며, FE는 그대로 출력한다.
- 정상 문장을 잘못 교정하는 문제의 완전한 해결은 미확인이다. `99f222e`의 작성자 실험 기록에는 정상 문장 18개 중 2개의 오탐이 남아 있다. 이번 동기화에서는 실제 모델 호출을 다시 하지 않았다. 과거 저장된 잘못된 조각은 이번 코드 변경만으로 재분류되지 않는다.
- 병합 후 `check:pally-segments`, `check-energy-contracts`, `check:inline-feedback`, `check:mock-api`, `tsc --noEmit`, lint 통과. lint에는 기존 `<img>` 권고만 있다. `git diff --check` 통과 및 기존 개발 서버의 `/home` HTTP 200을 확인했다.
- 기본 Python 환경에 pytest가 없어 백엔드 테스트는 이번 동기화에서 실행하지 못했다. 전체 빌드·실제 음성 E2E·운영 배포 상태는 이번 동기화에서 재검증하지 않았다.

## #121 반영 후 실제 연결 재검증

- 작업 브랜치는 계속 `1015-frontend`다. Railway `powerful-laughter / production / web`에서 #121 커밋 `4f7bd7a`, 배포 `80f1cc7e-8cca-4230-847d-f336d30bca24`의 `SUCCESS`를 확인한 뒤 실험했다. 당시 후속 #122 배포는 `BUILDING`이었다.
- 실제 계정 한도는 20회, 시작 시 사용 5회·잔여 15회였다. 별도 대화 `f023b534-fbbd-4e65-aaa5-8a91d7fdea89`를 생성하고 기존 합성 음성 입력 방식으로 3턴만 보냈다.

| 실제 STT 결과 | POST 시간 | 교정 조각 | 의미 판정 |
|---|---|---|---|
| `I was just chilling.` | 7.085초 | 없음 | 정상 문장이 기본색으로 표시됨 |
| `She don't like coffee.` | 7.308초 | `doesn't like` | 교정 부분만 주황, 나머지 문장은 기본색 |
| `I like coffee very much.` | 6.007초 | `a lot` | 동의어 교체를 교정으로 잘못 판단하는 오탐 재현 |

- 세 턴 모두 HTTP 201, 음성 포함, 조각 합산과 본문 일치. GET 상세의 영속 turn ID·본문·조각이 POST와 동일했다. 마지막 요청 재전송에서도 `replayed: true`, 동일 turn ID·조각을 확인했고 추가 한도는 소비하지 않았다.
- UI 계산 스타일에서 `chilling` 반응은 기본색·400, `doesn't like`는 주황·700, 새 표현은 민트·700이었다. 실제 새로고침으로 저장된 조각 복원을 확인했다. 360px 콘텐츠의 펼친 보기에서 영역 너비와 스크롤 너비 모두 360px이었다. 브라우저 viewport는 1440px이며 실제 모바일 viewport 검증과 구분한다.
- 화면 근거: `output/pally-segments-20261015/post121-expanded.jpeg`. 마지막 `a lot`의 주황은 검증에서 발견한 백엔드 오탐이다.
- 테스트 대화는 `completed`, 사용자 3턴으로 정리했다. Claire의 기존 대화 `21dc70a3-b81e-496e-a22e-185942aaf190`는 `active`, 사용자 2턴을 유지한다. 마지막 한도 조회는 사용 8회·잔여 12회, 초기화는 2026-10-16 00:00 KST다.
- 검증 전용 탭과 음성 입력·네트워크 관찰을 원복했다. 과거 잘못 저장된 조각은 수정하거나 삭제하지 않았다.
- FE 검사에 부분 교정 주변의 일반 `plain` 문구·문장부호와 `correction`이 0개인 유효 조각을 추가했다. POST·재반환·History 매핑·짧은/펼친/녹음 중 보기에서 본문·스타일·무로그를 검사한다.

## 정상 문장 오탐 보완 — 로컬 코드

- #121 실검증에서 재현된 `very much` → `a lot` 오탐을 줄이도록 Gemini 내부 계약을 보완했다. 답변을 생성하기 전에 현재 사용자 발화의 `original_error`와 구체적인 `error_reason`을 먼저 작성한다. 오류가 없거나 불확실하면 두 필드와 `corrected_expr`를 모두 빈 문자열로 반환한다.
- `build_reply(payload, utterance)`는 문자열 타입·필수 필드·세 필드의 일관성과 원문 구간이 현재 발화에 실제로 포함되는지 검증한다. 잘못된 근거는 기존 2회 시도 후 평문 경로를 사용한다. 실제 문법 오류 여부는 모델의 의미 판단이며 문자열 포함 검사만으로 증명하지 않는다.
- 정상 `chilling`, `very much`, 인칭 변경과 실제 문법·시제 오류의 예시를 완전한 필드 형태로 정리했다. 답변 내부의 최소 교정 부분만 표시한다. 외부 API·DB 구조·5종 `kind`·90자 제한은 유지한다. 근거 필드는 음성·저장·UI로 전달하지 않고 로그에도 넣지 않는다.
- 모델·temperature·재시도 상한·턴당 모델 호출 구조는 유지했다. 프롬프트와 내부 출력 필드가 늘었으므로 속도 변화가 없다고 단정하지 않는다.

### 실제 Gemini 반복 검사

- `gemini-2.5-flash-lite`, temperature 0.85, thinkingBudget 0, maxOutputTokens 512로 실행했다. 수정한 `RESPONSE_SCHEMA`·프롬프트·`build_reply`를 그대로 사용했다. `very much`는 앞서 오탐이 발생한 chilling/coffee 대화 문맥도 넣었다.
- 정상 4종(`I was just chilling.`, 전체 chilling 발화, `I like coffee very much.`, `I was tired yesterday.`)을 각 3회 호출: **12/12회 교정 없음**.
- 오류 2종(`She don't like coffee.`, `Yesterday I go to park with my friend.`)을 각 3회 호출: **6/6회 각각 `doesn't`, `went to the park`만 교정**.
- 총 18/18회 첫 시도에 유효한 조각을 만들었다. 중앙값 1.143초는 로컬에서 측정한 Gemini 요청·조립 시간이며 음성·DB를 포함한 턴 지연과 다르다. 제한된 표본에서의 통과이며 모든 발화의 오탐 제거를 보장하지 않는다.
- 결과 근거: `output/pally-segments-20261015/grounded-correction-eval.json`. 인증정보는 저장하지 않았다.

### 승인된 로컬 전체 연결 검사

- 운영 자격증명을 로컬 백엔드에 주입하는 최초 실행은 자동 승인 검토에서 거부됐다. Claire가 **이찬희 테스트 계정 1턴 검증**을 명시적으로 승인한 뒤 실행했다.
- 임시 백엔드는 `127.0.0.1:8000`에만 바인딩했다. 결제·세션 피드백·음성 Energy 백그라운드 작업과 디버그 엔드포인트를 껐다. 축 분석은 로컬 `rule` 설정을 사용했으므로 운영 F/H/C 모델·음성 Energy 검증으로 간주하지 않는다.
- 프론트는 프로세스 환경변수로만 로컬 백엔드에 연결했다. `.env.local`은 수정하지 않았다. 지정 계정으로 실제 Google TTS → 앱 녹음/WAV → Google STT → 수정된 Gemini 응답 → 실제 Supabase 저장 → UI를 확인했다.
- 대화 `606c28f5-abe7-428d-9bca-6dcaa5c2f428`, 턴 `a3a0a78c-78d6-45ca-91b5-0835dd299f76`. STT는 `I like coffee very much.`, 응답은 `You like coffee a lot? I start my day with tea. How do you like it?`. HTTP 201, 3.866초, 음성 포함, `correction` 0개였다.
- 운영 백엔드의 별도 GET에서도 같은 본문·조각이 조회돼 실제 DB 저장을 확인했다. `a lot`은 기본색·400, `start my day`는 민트·700이었다. 새로고침과 History의 `Coffee Preferences Discussion` 재개 후에도 교정 0개·본문·새 표현이 유지됐다.
- 360px 콘텐츠의 펼친 보기에서 가로 넘침 없음. 화면 근거: `output/pally-segments-20261015/grounded-correction-history.png`. 물리 모바일 검증은 아니다.
- 승인 범위대로 사용자 발화 1턴만 추가했다. 테스트 대화는 최종 `completed`, 사용자 1턴이다. 최종 한도 사용 9회·잔여 11회, 초기화는 2026-10-16 00:00 KST다.
- 임시 백엔드와 로컬 백엔드 연결 프론트 프로세스는 종료했다. 검증용 음성 입력·네트워크 관찰·탭을 정리하고 3000 개발 서버를 원래 `.env.local` 설정으로 재시작했다. 운영 배포·DB 마이그레이션·과거 조각 수정은 하지 않았다.

### 최종 검사와 협업

- 수정 후 조각/백엔드 smoke 검사 114개, 응답 길이·opener 회귀 검사 37개 통과. ruff의 E9/F63/F7/F82 검사와 `git diff --check` 통과. Python은 임시 가상환경의 3.14를 사용했으며 CI의 3.11 검증은 PR 단계에 남아 있다.
- 추가 FE 조각 검사를 통과했고 최신 `main`과 후속 화면 변경을 포함해 `npm run build`를 다시 통과했다. 타입검사·lint도 빌드에서 통과했으며 기존 `<img>` 권고만 남아 있다.
- 새 저장소 의존성은 추가하지 않았다. 기존 CI에 쓰는 pytest·ruff와 백엔드 실행 의존성은 `/private/tmp/pally-correction-20261015-venv`에만 설치했다. 이 임시 검증 환경에는 인증정보를 파일로 저장하지 않았다.
- PR 시 `frontend/components/chat`·`.github/workflows/ci.yml`뿐 아니라 이번 `ai/reply_segments.py`·`backend/main.py` 변경도 해당 담당자에게 공유해야 한다. 실제 팀 공지·커밋·PR·배포는 수행하지 않았다.
- 이 보완은 현재 브랜치의 미커밋 코드다. 기존 3000 개발 서버는 다시 운영 API를 사용하므로 새 판정이 운영에 반영된 상태로 오해하면 안 된다. 과거 History의 잘못된 조각도 자동 재분류되지 않는다.
