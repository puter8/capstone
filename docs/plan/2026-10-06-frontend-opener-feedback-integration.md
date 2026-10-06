# 프론트 오프너·피드백·기록 삭제 통합 검증

기준: 2026-10-06 KST, main `cb11761`에서 분기한 `feat/frontend-opener-feedback-integration`.
Claire 요청: 이전에 승인한 기록 삭제·인라인 피드백과 새 실제 opener 연결을 마무리하고, Claude 검수용으로 커밋·푸시한다. PR·머지·배포는 범위에 포함하지 않는다.

## 구현

- 대화 시작 시 conversation row를 먼저 만들고 그 ID로 opener API를 호출한다. 고정 인사와 별도 프론트 TTS 호출을 제거했다.
- 시작 중 중복 클릭을 막고 opener 재시도에는 같은 conversation ID와 Idempotency-Key를 사용한다. `opener_failed`는 재시도를 안내하고, `conversation_started`는 저장된 대화를 복원하며, `conversation_closed`는 진행 ID를 지워 새 시작으로 복구한다.
- `audio: null`은 텍스트 표시 경로를 유지하고 서버 warnings를 안내한다. 종료는 진행 중 opener 저장을 기다린다. 늦게 도착한 응답이 종료 화면을 되돌리지 않는다. 사용자 발화 없이 종료하면 캐릭터 축을 덮어쓰지 않는다.
- 실제 백엔드의 `feedback_pending`은 종료 후 생성 대기다. 대화 중에는 종료 후 History에서 확인하라는 안내를 표시한다. 기존 피드백은 해당 Pally 답변에 연결해 짧은 말풍선·전체 기록에서 원문, 교정, 한국어 설명을 펼친다.
- 종료된 대화의 Feedback 화면은 대기 항목이 있으면 3초 간격으로 최대 10회 재조회한다. 읽은 모든 페이지를 새 응답으로 교체해 중복과 오래된 pending 상태를 방지한다. 실패·장기 대기는 수동 재시도를 제공한다. 활성 대화는 종료 안내만 보여준다.
- 기록 삭제는 기존 확인창에서 삭제 범위와 복구 불가를 안내한다. 계정 변경·중복 요청을 차단하고 성공 후 캐시·진행 ID·프로필을 갱신한다. 프로필 재조회 실패는 삭제 실패와 구분한다. 계정·구독·사용량·업적은 유지한다.
- Mock도 opener가 사용자 turn/사용량에 포함되지 않고, 피드백은 종료 후 채워지도록 맞췄다. 오프너·복원 회귀 검사를 기존 CI에 추가했다. 새 의존성은 없다.
- Minor Decision: opener만 있는 History는 서버의 영어 제목을 그대로 쓴다. 별도 배지는 추가하지 않는다. `preview: null`을 지원하는 기존 표시 경로를 유지한다.

## 실제 서비스 검증

대상: 기존 로그인 계정, Railway `web-production-8dee5.up.railway.app`, 별도 localhost:3001 프론트.

1. 코드 연결 전에 실제 create/opener API를 호출해 201, text, MP3 audio, warnings와 저장된 opener를 확인했다. 별도 테스트 대화는 종료 처리했다.
2. UI 시작에서 create 201 → opener 201(약 4.2초), 필수 헤더, 화면 영어 문구와 저장된 turn 일치, opener 호출 전후 사용량 20회 유지 확인.
3. Google TTS로 만든 영어 음성 세 개를 WebAudio MediaStream으로 주입했다. 프론트 MediaRecorder → WAV 변환 → 실제 GCP STT/AI/TTS → 백엔드 저장 → UI를 통과했다. 사용자 turn은 각각 201(약 7.6/3.8/4.4초), 사용량은 20 → 17회였다.
4. 일상 과거형 오류·정중한 질문·캐주얼한 감탄의 서로 다른 발화로 5축을 확인했다.

| 발화 | Formality | Energy | Intimacy | Humor | Curiosity |
|---|---:|---:|---:|---:|---:|
| yesterday I go to work… | 43 | 30 | 28 | 10 | 16 |
| could you please explain… | 69 | 30 | 8 | 3 | 40 |
| wow that movie was awesome… | 54 | 41 | 30 | 8 | 22 |

5. UI에서 종료한 뒤 인증된 상세 API를 다시 조회해 completed, opener+사용자 3개 turn, 모든 pending=false를 확인했다. 첫 발화의 교정 3개가 저장되어 실제 History Feedback 화면에 표시됐다. 나머지 발화는 교정 0개였다.
6. opener-only 대화는 turn_count=0, 영어 opener 제목, preview=null로 조회됐다.

검증 레코드 두 개는 completed 상태로 남겼다. 기존 기록을 삭제하지 않았다.

- opener-only: `541597ef-6bc9-4852-8d40-dc9e82740170`
- 3-turn: `e08f37ce-5074-4863-a755-e92214a8075c` (`Happy Friends and English Practice`)

## 브라우저·회귀 검증

Aside 전용 탭에서 콘텐츠 폭 360px로 확인했다. 도구의 viewport 에뮬레이션은 지원되지 않아 실제 모바일 기기 검증으로 간주하지 않는다.

- 실제 API 흐름 외 오류 검증은 브라우저 fetch fixture로 격리했다. 연속 시작 클릭 → create/opener 각각 1회, 503 후 같은 ID·키 재시도, null audio 및 warning, started 409 복원 및 인라인 교정 표시, closed 409의 ID 제거를 확인했다.
- opener 응답을 보류한 상태에서 종료: 응답 전 complete 요청 0회, 응답 후 complete 1회, 늦은 인사 표시 없음.
- Feedback 두 페이지: 최초 pending → 두 페이지 모두 자동 재조회 → 중복 없이 교정 2개 표시. 재조회 503 → 오류/다시 확인 → 수동 재시도 성공. 실제 종료 피드백은 화면 진입 전에 생성 완료됐으므로, 자동 polling 타이밍 자체는 fixture 검증이다.
- 삭제 UI는 앞선 검증에서 취소 시 요청 0회, 처리 중 버튼 잠금, 실패·재시도·성공, 캐시와 진행 ID 정리, 빈 History·기본 홈을 확인했다. 실제 전체 삭제는 실행하지 않았다.
- `npm run lint`, `npm run build`, `tsc --noEmit` 통과. lint의 기존 `<img>` 권고 외 오류 없음.
- `check:opener`, `check:mock-api`, `check:query-cache`, `check:conversation-order`, `tsx scripts/check-billing-account-binding.ts` 통과. 삭제 시 계정 전환은 네트워크 요청 전에 차단된다.
- `git diff --check` 통과. AGENTS.md → CLAUDE.md symlink 유지.

## 검수 시 구분할 점

- 실제 파괴적 전체 삭제, 물리 마이크 입력, 실제 모바일 기기의 오디오 정책은 미검증이다. 합성 영어 음성 입력은 한국어 STT 정확도나 TTS 청취 자연도를 검증하지 않는다.
- 저장된 교정에는 AI가 답변에서 추출한 `I go → You went`, `we was → feeling quite happy`가 포함됐다. 프론트는 서버 결과를 그대로 표시한다. 교정의 인칭·표현 품질은 AI 측 검수 대상이다.
- 확인한 저장 근거는 실제 백엔드의 인증된 상세 재조회와 영속 turn/feedback ID다. Supabase 관리 콘솔 직접 조회는 수행하지 않았다.
- 검증 후 작업용 fetch/media override·임시 로그인·탭과 3001 서버를 정리했다. 기존 3000 서버, `.env.local`, 작업 전부터 있던 미추적 산출물은 유지했다.
