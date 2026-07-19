# Pally MVP 화면 플로우 기반 3인 기능 분담안

> 기준: [Figma Design_v4](https://www.figma.com/design/4kLxDLD2LdbB5BiY2QT5qU/%EB%94%94%EC%9E%90%EC%9D%B8?node-id=842-2486&t=lN0iVM9fi5yvz4uj-1) (`842:2486`)
>
> 대상 역할: 프론트엔드 1명, 백엔드 1명, AI 1명
>
> 전제: 프론트엔드의 디자인 다듬기와 기본 퍼블리싱은 완료된 상태다.

## 1. 결론

기존의 `백엔드 API 완성 → 프론트엔드 연결` 순차 방식 대신 다음 두 축을 함께 사용한다.

1. **화면은 사용자 플로우별로 세로 분담한다.** 각 담당자는 자기 플로우의 화면, API 연결, E2E 완료 여부를 끝까지 책임진다.
2. **공유 인프라는 전문 담당자가 관리한다.** Supabase와 최종 API는 백엔드, 공통 UI는 프론트엔드, AI contract는 AI 담당자가 gatekeeper가 된다.

전체 작업을 순차 진행하지 않는다. 세 명이 공통 타입과 최소 DB 구조를 먼저 합의한 뒤 프론트엔드는 mock, 백엔드는 fake AI adapter, AI는 fixture를 사용해 동시에 작업한다.

- 프론트엔드 담당: 로그인 → 온보딩 → My Pally/설정 플로우
- AI 담당: Pally Talk → Feedback 생성 플로우 + Reddit meme vocabulary 품질
- 백엔드 담당: History → Achievements → 사용량/결제 플로우
- Reddit 데이터 수집은 백엔드, meme 단어 추출·검수 규칙은 AI가 책임진다.
- 프론트엔드는 AI 엔진이나 service role을 직접 호출하지 않는다.
- 화면 플로우의 최종 책임과 공유 인프라의 변경 권한은 분리한다.

```text
Frontend → Backend API → AI Engine
                     ├→ Database
                     └→ Storage
```

## 2. Figma에서 확인한 기능 범위

### 2.1 로그인

- Google 로그인
- Kakao 로그인
- 대표 프레임: `00. 로그인` (`842:3906`)

### 2.2 온보딩

- 영어 레벨 선택: A2, B1, B2, C1
- 사용자 이름 입력
- 설정 완료 안내
- 대표 프레임:
  - `01-1 온보딩 1` (`842:3925`)
  - `01-1 온보딩 2` (`842:4600`)
  - `01-1 온보딩 3` (`842:4663`)

### 2.3 Pally 음성 대화

- 새 대화 시작
- 사용자 음성 듣기
- STT 결과 표시
- Pally 답변 생성 중 표시
- Pally 답변과 TTS 재생
- 대화 패널 펼치기/접기
- 이전 대화 이어가기
- 무료 사용자 대화량 제한
- 대표 프레임:
  - `Pally talk - 새 채팅` (`842:3970`)
  - `Pally talk - 듣는 중_user 첫 발화 시` (`842:3718`)
  - `Pally talk - 생각중` (`842:3626`)
  - `Pally talk - 대화중(TTS 재생 중)` (`842:3640`)
  - `Pally talk - 듣는중_user 발화 기록 있을 때` (`842:3656`)
  - `Pally talk - 무료 사용자 limit` (`842:3673`)
  - 펼쳐진 대화 기록 (`842:3693`, `842:3700`)
  - `Continue the conversation` (`842:3601`)

### 2.4 History와 Feedback

- 대화 주제별 History 카드
- 과거 대화 다시 시작
- 대화별 피드백 조회
- 피드백이 없는 상태
- 피드백 구조: 원문, 교정문, 한국어 설명
- 대표 프레임:
  - `Feedback note` (`842:3997`)
  - `Feedback` (`842:4009`)
  - `Feedback Empty` (`842:4016`)

### 2.5 Achievements

- 연속 학습일 Streak
- Daily Tasks
- Task 완료 상태
- 대표 프레임: `Challenge` (`842:3896`)

### 2.6 My Pally와 설정

- 프로필 이름과 특성 태그
- 이름 변경
- 영어 레벨 변경
- 요금제 및 결제
- 데이터 삭제
- 로그아웃
- 회원탈퇴
- 대표 프레임:
  - `My Pally` (`842:3734`)
  - `영어 레벨 변경` (`842:3868`)
  - `요금제 및 결제` (`842:3879`)
  - `데이터 삭제` (`842:3764`)
  - `이름 수정` (`842:3834`)
  - `로그아웃` (`842:3799`)
  - `회원탈퇴` (`919:2698`)

### 2.7 Reddit meme vocabulary

이 기능은 Figma에 별도 화면으로 표현되지 않은 데이터 파이프라인이다.

- 합의된 subreddit에서 허용된 방식으로 게시물·댓글 데이터를 수집한다.
- 수집 텍스트에서 최신 meme/slang 단어 후보를 추출한다.
- 철자 변형과 중복 표현을 하나의 canonical term으로 정규화한다.
- 의미, 한국어 설명, 사용 맥락, 안전성, 신뢰도를 생성한다.
- 검수 또는 승인된 단어만 Pally 대화 엔진에서 사용한다.
- 원문 전체와 작성자 정보는 필요 이상 저장하지 않는다.

```text
Reddit 공식 API 또는 승인된 접근
→ Backend Collector
→ AI Meme Term Extractor
→ 중복·안전성·품질 검수
→ Supabase Meme Vocabulary
→ Pally Conversation Engine
```

Reddit 데이터 접근은 구현 전에 [Reddit Data API Terms](https://redditinc.com/policies/data-api-terms), [Developer Terms](https://redditinc.com/policies/developer-terms), 공식 개발자 문서의 현재 요구사항을 확인하고 승인을 받아야 한다. HTML 무단 크롤링이나 우회 접근을 기본 구현으로 사용하지 않는다.

## 3. 화면 플로우별 분담

화면을 한 장씩 나누지 않고 상태와 데이터가 이어지는 사용자 플로우 단위로 나눈다.

| 최종 담당 | 화면 플로우 | E2E 책임 |
|---|---|---|
| 프론트엔드 | 로그인 → 온보딩 → My Pally/설정 | 로그인부터 프로필 변경까지 |
| AI | Pally Talk → Feedback 생성 | 녹음부터 답변·TTS·학습 피드백까지 |
| 백엔드 | History → Achievements → 사용량/결제 | 기록 조회부터 정책·결제까지 |
| AI + 백엔드 | Reddit meme vocabulary | 허용된 수집부터 승인된 단어 활용까지 |

최종 담당자는 모든 코드를 혼자 작성하는 사람이 아니다. 해당 플로우의 contract, 통합 상태, 사용자 결과를 끝까지 확인하는 사람이다.

### 3.1 프론트엔드 담당: 사용자 진입과 설정

- Google/Kakao 로그인
- 영어 레벨 선택
- 이름 입력과 온보딩 완료
- My Pally
- 이름 수정과 영어 레벨 변경
- 로그아웃·회원탈퇴 UI
- 공통 하단 네비게이션

백엔드 담당자는 인증, RLS, 프로필 저장, 회원탈퇴 로직을 지원하고 리뷰한다.

### 3.2 AI 담당: 핵심 대화와 피드백

- 새 채팅
- Listening과 Thinking
- Pally 답변과 TTS 재생
- 대화 펼치기·접기
- 이전 대화 이어가기
- Feedback structured output 생성과 화면 연결
- Reddit 텍스트에서 meme/slang 단어 후보 추출
- 단어 정규화, 의미·맥락·신뢰도·안전성 생성
- 승인된 meme vocabulary를 Pally prompt에 반영

프론트엔드 담당자는 마이크, 오디오 재생, 모바일 브라우저 동작을 지원한다. 백엔드 담당자는 대화 저장과 사용량 처리를 지원한다.

### 3.3 백엔드 담당: 기록, 성과, 정책

- History
- Feedback 목록과 상세 조회
- Feedback Empty
- Streak와 Daily Tasks
- 무료 사용량 제한
- 요금제와 결제
- 데이터 삭제
- Reddit 공식 API 수집과 갱신 스케줄
- 원본 source metadata와 meme vocabulary 저장
- 중복 수집 방지, 보존 기간, 삭제 처리

AI 담당자는 Feedback 결과 형식을 지원하고, 프론트엔드 담당자는 목록·빈 상태·dialog UI를 지원한다.

## 4. 전문 영역별 지원 책임

화면 플로우를 세로로 나누더라도 공유 기반은 각 전문 담당자가 관리한다.

| 공유 영역 | Gatekeeper | 변경 책임 |
|---|---|---|
| 디자인 시스템·공통 UI·브라우저 오디오 | 프론트엔드 | 공통 컴포넌트와 client 상태 |
| Supabase·migration·RLS·Storage·최종 API | 백엔드 | 스키마와 데이터 안전성 |
| AI contract·prompt·structured output·평가 | AI | 모델 입출력과 품질 |
| Reddit 접근·수집 정책 | 백엔드 | 인증, 수집, 스케줄, 저장 |
| Meme vocabulary 품질 | AI | 추출, 정규화, 안전성, 승인 기준 |

### 4.1 프론트엔드 전문 지원

프론트엔드는 퍼블리싱된 화면을 실제 사용자 동작과 서버 데이터에 연결한다.

#### 담당 범위

- Google/Kakao 로그인 시작과 callback 처리
- 온보딩 단계 이동, 입력, validation
- 마이크 권한 요청
- 녹음 시작·중지와 오디오 Blob 생성
- 오디오 업로드
- TTS 오디오 재생·중지
- 대화 패널 펼치기·접기
- 대화 상태에 맞는 Pally 화면 전환
- History, Feedback, Achievements, My Pally 데이터 연결
- loading, empty, error, quota 상태 표시
- 모바일 환경에서 실제 녹음·재생 검증

#### 대화 화면 상태

여러 boolean을 조합하지 않고 단일 상태 머신으로 관리한다.

```ts
export type ConversationState =
  | "idle"
  | "listening"
  | "processing"
  | "speaking"
  | "quota_exceeded"
  | "error";
```

각 상태는 Figma 화면과 다음처럼 대응한다.

| 상태 | Figma 표현 |
|---|---|
| `idle` | 새 채팅, 마이크 버튼 |
| `listening` | `Listening...`, 녹음 중 버튼 |
| `processing` | 사용자 transcript, `Thinking...` |
| `speaking` | Pally 답변 표시, TTS 재생 |
| `quota_exceeded` | 오늘의 대화량 소진 dialog |
| `error` | 안전한 오류 메시지와 재시도 동작 |

#### 프론트엔드 완료 기준

- mock fixture만으로 모든 Figma 상태를 재현할 수 있다.
- 실제 백엔드 연결 시 컴포넌트 구조를 다시 만들지 않아도 된다.
- 모바일 브라우저에서 녹음과 TTS 재생이 동작한다.
- 서버 오류와 권한 거부가 빈 화면이나 무응답으로 끝나지 않는다.

### 4.2 백엔드 전문 지원

백엔드는 프론트엔드가 사용하는 최종 API와 서비스 정책을 책임진다.

#### 담당 범위

- 로그인 사용자 및 세션 처리
- 온보딩 정보 저장
- 프로필 이름과 영어 레벨 변경
- conversation과 turn 생성·저장
- History와 Feedback 조회
- AI 엔진 호출과 결과 저장
- Streak와 Daily Task 계산
- 무료 사용량 확인과 차감
- 구독 상태 및 결제 결과 반영
- 데이터 삭제
- 로그아웃 및 회원탈퇴
- 인증, 권한, RLS
- 서버 로그와 안전한 오류 응답

#### 백엔드 원칙

- 프론트엔드에 AI provider 세부 형식을 노출하지 않는다.
- 사용량 차감, 대화 저장, AI 호출 결과를 하나의 서비스 흐름으로 관리한다.
- AI가 실패하면 성공한 것처럼 빈 결과를 저장하지 않는다.
- 데이터 삭제와 회원탈퇴는 서로 다른 작업으로 취급한다.
- Daily Task와 Streak는 규칙 기반 도메인 로직으로 구현하며 AI에 맡기지 않는다.

#### 백엔드 완료 기준

- 동일한 API contract로 fake AI adapter와 real AI engine을 교체할 수 있다.
- conversation, turn, feedback 간 연결이 DB에 보존된다.
- 무료 사용량의 중복 차감이나 우회가 불가능하다.
- 사용자 간 대화와 프로필 데이터가 분리된다.
- 삭제·탈퇴 결과를 실제 DB에서 확인할 수 있다.

### 4.3 AI 전문 지원

AI 담당자는 개별 모델 호출이 아니라 **대화 엔진의 전체 입력과 출력 품질**을 책임진다.

#### 담당 범위

- 사용자 오디오 STT
- 이전 대화와 사용자 설정을 포함한 문맥 구성
- 영어 레벨에 맞는 답변 생성
- Pally 응답 생성
- 학습 피드백 structured output 생성
- Pally 답변 TTS 생성
- latency 측정
- 모델 오류, 빈 응답, 잘못된 structured output 처리
- 실제 한국어·영어·혼합 발화 테스트

#### AI 엔진 입력 예시

```ts
export type ConversationTurnInput = {
  conversationId: string;
  audioUrl: string;
  userLevel: "A2" | "B1" | "B2" | "C1";
  userName: string;
  previousTurns: Array<{
    speaker: "user" | "pally";
    text: string;
  }>;
};
```

#### AI 엔진 출력 예시

```ts
export type ConversationTurnResult = {
  transcript: string;
  assistantText: string;
  audioUrl: string;
  feedback: FeedbackItem[];
};

export type FeedbackItem = {
  original: string;
  corrected: string;
  explanationKo: string;
};
```

`FeedbackItem`은 Figma Feedback 카드의 `원문 → 교정문 → 한국어 설명` 구조와 직접 대응한다.

#### AI 완료 기준

- 같은 입력 fixture에 대해 항상 contract를 만족하는 결과를 반환한다.
- transcript, 답변, 피드백, TTS 중 하나가 실패했을 때 실패 위치가 드러난다.
- A2와 C1의 답변 난이도 차이를 실제 출력으로 검증한다.
- 여러 턴 대화에서 이전 문맥을 유지한다.
- 생성된 피드백이 History의 해당 turn과 연결될 수 있다.

### 4.4 기능별 협업 매트릭스

| 기능 | 최종 책임자 | 협업 |
|---|---|---|
| 로그인→온보딩 플로우 | 프론트엔드 | 백엔드가 인증·저장 지원 |
| My Pally→설정 플로우 | 프론트엔드 | 백엔드가 프로필 API 지원 |
| 녹음·재생·화면 상태 | 프론트엔드 | AI, 백엔드 |
| 음성 대화 E2E | AI | 프론트엔드, 백엔드 |
| 대화 저장·이어하기 | AI | 백엔드가 저장 지원 |
| Feedback 생성과 내용 품질 | AI | 백엔드가 저장 지원 |
| History·Feedback 조회 플로우 | 백엔드 | 프론트엔드, AI |
| Streak·Daily Tasks | 백엔드 | 프론트엔드 |
| 무료 사용량 제한 | 백엔드 | 프론트엔드 |
| 결제·구독 상태 | 백엔드 | 프론트엔드 |
| 데이터 삭제·회원탈퇴 | 백엔드 | 프론트엔드 |
| 모바일 사용성 | 프론트엔드 | 전원 |

최종 책임자는 모든 코드를 혼자 작성한다는 의미가 아니다. 해당 기능의 contract, 통합 상태, 완료 여부를 끝까지 확인하는 사람이다.

### 4.5 Supabase 운영 방식

Supabase는 백엔드 담당자가 단독 gatekeeper가 된다. 화면 플로우의 담당자가 누구인지와 Supabase 변경 권한은 별개다.

| 역할 | Supabase 접근 범위 |
|---|---|
| 프론트엔드 | anon client, 로그인·세션, RLS가 허용한 조회 |
| 백엔드 | migration, RLS, Storage, service role, 중요 데이터 저장 |
| AI | 원칙적으로 Supabase에 직접 접근하지 않음 |

#### 원칙

- AI 엔진은 결과만 반환하고 백엔드가 검증 후 저장한다.
- 프론트엔드는 service role을 사용하지 않는다.
- 다른 담당자는 Supabase Dashboard에서 테이블을 직접 만들거나 수정하지 않는다.
- 필요한 필드가 생기면 공통 contract 변경을 요청하고 백엔드가 migration으로 반영한다.
- 실제 적용 전 로컬 Supabase에서 migration과 RLS를 검증한다.
- 적용된 migration은 수정하지 않고 새 migration을 추가한다.
- migration과 생성된 DB 타입을 함께 공유한다.
- 공유 개발 DB 적용 후 팀에 변경 내용을 알린다.

#### Figma 화면에서 예상되는 데이터 영역

```text
profiles
conversations
conversation_turns
feedback_items
daily_task_completions
daily_usage
subscriptions
reddit_source_items
meme_term_candidates
meme_terms
```

위 목록은 테이블 이름 확정안이 아니라 화면에서 요구되는 데이터 경계다. 실제 컬럼과 관계는 공통 contract를 합의한 후 결정한다.

#### 무엇만 순차 진행하는가

전체 개발이 아니라 공유 기반의 변경만 순서가 필요하다.

1. 세 명이 공통 요청·응답 타입과 최소 DB 관계를 합의한다.
2. 백엔드 담당자가 migration, RLS, 생성 타입을 반영한다.
3. 다른 담당자는 반영된 contract를 기준으로 실제 API 연결을 완료한다.

Supabase 준비 중에도 나머지 작업은 병렬로 진행한다.

```text
Frontend → mock repository로 로그인·온보딩·설정 구현
Backend  → Supabase migration·RLS·API·fake AI adapter 구현
AI       → fixture로 STT·답변·TTS·Feedback 엔진 구현
```

#### 통합 순서

```text
1. Frontend → Mock fixture
2. Frontend → Backend → Fake AI adapter → Supabase
3. Frontend → Backend → Real AI engine → Supabase
```

따라서 프론트엔드와 AI가 Supabase 구축을 기다린 뒤 시작하는 구조가 아니다.

### 4.6 Reddit meme vocabulary 파이프라인

#### 역할 분담

| 단계 | 최종 담당 | 결과 |
|---|---|---|
| API 접근 승인·credential·수집 | 백엔드 | 허용된 source item |
| subreddit·기간·정렬 조건 적용 | 백엔드 | 중복 제거된 수집 batch |
| meme/slang 후보 추출 | AI | `MemeTermCandidate[]` |
| 정규화·의미·맥락·안전성 | AI | 품질 정보가 포함된 후보 |
| 저장·승인 상태·갱신 | 백엔드 | 활성 `MemeTerm[]` |
| Pally 대화 활용 | AI | 승인된 단어만 포함한 prompt context |

#### 수집 원칙

- Reddit 공식 API 또는 Reddit이 승인한 접근 방식을 우선한다.
- 구현 전에 인증 방식, 허용 용도, 수집 범위, 보관 조건을 실제 호출로 확인한다.
- Reddit 응답 구조와 필요한 필드가 실제로 제공되는지 확인한 후 collector를 작성한다.
- 허용되지 않은 HTML scraping, 인증 우회, 무제한 수집을 구현하지 않는다.
- subreddit allowlist와 수집 기간을 명시한다.
- post/comment id를 기준으로 중복 수집을 방지한다.
- 작성자 이름, 사용자 id 등 meme 단어 추출에 불필요한 개인정보는 저장하지 않는다.
- 원문 전체는 기본 영구 저장 대상이 아니다. 필요한 경우 보관 기간과 삭제 절차를 먼저 확정한다.
- 승인되지 않은 후보는 Pally prompt에 넣지 않는다.
- Reddit 데이터를 모델 학습에 사용하지 않는다. 별도 사용이 필요하면 Reddit의 명시적 허용 여부를 먼저 확인한다.

#### Meme term contract 예시

```ts
export type MemeTermCandidate = {
  term: string;
  normalizedTerm: string;
  meaningKo: string;
  usageContext: string;
  subreddit: string;
  sourceId: string;
  sourceUrl: string;
  observedAt: string;
  confidence: number;
  safety: "safe" | "review" | "blocked";
};

export type MemeTerm = MemeTermCandidate & {
  id: string;
  status: "approved" | "rejected" | "expired";
  approvedAt: string | null;
};
```

`sourceId`와 `sourceUrl`은 추출 근거 추적과 중복 방지를 위한 값이다. Reddit 원문을 사용자에게 그대로 제공하기 위한 필드가 아니다.

#### 완료 기준

- 허용된 실제 Reddit 응답으로 한 번 이상 E2E 수집한다.
- 같은 source를 다시 수집해도 중복 row가 생기지 않는다.
- 추출된 후보가 canonical term으로 정규화된다.
- 욕설, 혐오, 성적 표현 등 안전하지 않은 후보가 자동 사용되지 않는다.
- 승인된 term만 대화 엔진에서 조회된다.
- source 삭제 또는 보존 기간 만료 시 처리 절차가 있다.

## 5. 병렬 개발을 위한 공통 계약

세 명이 구현을 시작하기 전에 다음 타입과 요청·응답 예시를 함께 확정한다.

### 공통 타입

```text
UserProfile
Conversation
ConversationTurn
FeedbackItem
UsageQuota
Subscription
DailyTask
RedditSourceItem
MemeTermCandidate
MemeTerm
```

### 최소 API 경계

구체적인 URL은 기존 코드 패턴에 맞추되, 기능 경계는 다음을 포함한다.

| 기능 | 입력 | 출력 |
|---|---|---|
| 로그인 후 세션 | OAuth callback | 사용자와 온보딩 상태 |
| 온보딩 저장 | 이름, 영어 레벨 | 저장된 프로필 |
| 새 대화 | 사용자 id | conversation id |
| 대화 turn | conversation id, audio | transcript, Pally 답변, TTS, quota |
| 대화 목록 | 사용자 id, cursor | History 목록 |
| 대화 상세 | conversation id | turn과 feedback 목록 |
| Achievements | 사용자 id | streak와 daily tasks |
| 프로필 수정 | 이름 또는 레벨 | 변경된 프로필 |
| 사용량 조회 | 사용자 id | 남은 대화량과 구독 상태 |
| 사용자 데이터 삭제 | 확인값 | 삭제 결과 |
| 회원탈퇴 | 확인값 | 계정 삭제 결과 |
| Reddit source 수집 | subreddit allowlist, cursor | 수집 batch와 source metadata |
| Meme 후보 추출 | source item batch | 정규화된 MemeTermCandidate 목록 |
| 승인 단어 조회 | 활성 상태, 갱신 시점 | Pally가 사용할 MemeTerm 목록 |

### 대화 turn 응답 예시

```json
{
  "conversationId": "conv_123",
  "turnId": "turn_456",
  "user": {
    "transcript": "I had no lunch. I'm on a diet."
  },
  "pally": {
    "text": "Oh no, you skipped lunch because you're on a diet?",
    "audioUrl": "https://storage.example/pally-turn-456.mp3"
  },
  "feedback": [
    {
      "original": "I'm diet",
      "corrected": "I'm on a diet",
      "explanationKo": "diet 앞에는 on a를 사용해요."
    }
  ],
  "quota": {
    "remainingTurns": 4,
    "exhausted": false
  }
}
```

## 6. Mock부터 실제 통합까지

세 역할은 API 완료를 기다리지 않고 같은 contract를 이용해 동시에 작업한다.

```text
1단계: Frontend → Mock fixture
2단계: Frontend → Backend → Fake AI adapter
3단계: Frontend → Backend → Real AI engine
```

### 프론트엔드 fixture

최소한 다음 시나리오를 준비한다.

- 신규 사용자
- 온보딩 미완료 사용자
- 대화가 없는 사용자
- 대화가 3턴 있는 사용자
- 피드백이 3개 있는 사용자
- 피드백이 없는 사용자
- 무료 사용량을 소진한 사용자
- AI 처리 실패 사용자
- 마이크 권한을 거부한 사용자

### 백엔드 fake AI adapter

- real AI engine과 동일한 결과 타입을 반환한다.
- 고정된 transcript, 답변, audio URL, feedback을 반환한다.
- timeout과 오류 fixture도 제공한다.

### AI fixture

- 짧고 명확한 영어 발화
- 문법 오류가 있는 영어 발화
- 한국어와 영어가 섞인 발화
- 무음 또는 인식 불가 오디오
- A2와 C1 사용자
- 이전 문맥이 필요한 다중 turn 대화

## 7. 권장 구현 순서

### 7.1 공통 준비

1. Figma 상태와 공통 타입을 대응시킨다.
2. 요청·응답 JSON fixture를 확정한다.
3. 프론트엔드 API client interface를 만든다.
4. 백엔드 AI adapter interface를 만든다.
5. 성공, quota, 오류 시나리오를 합의한다.

### 7.2 첫 번째 통합 목표: 핵심 대화

다음 한 줄을 가장 먼저 완성한다.

```text
녹음
→ STT transcript 표시
→ Pally 답변 생성
→ TTS 재생
→ 대화 DB 저장
→ History 조회
→ Feedback 표시
```

이 흐름이 완료되기 전에는 결제나 부가 설정 화면을 먼저 확장하지 않는다.

### 7.3 두 번째 통합 목표: 사용자 생명주기

```text
로그인
→ 온보딩
→ My Pally 조회
→ 이름·레벨 변경
→ 로그아웃
```

### 7.4 세 번째 통합 목표: 정책과 부가 기능

```text
무료 사용량 제한
→ 요금제 화면
→ 구독 상태 반영
→ Achievements
→ 데이터 삭제·회원탈퇴
```

## 8. 협업 규칙

### 8.1 API가 준비될 때까지 기다리지 않는다

- 프론트엔드는 fixture로 먼저 연결한다.
- 백엔드는 fake AI adapter로 먼저 E2E를 만든다.
- AI는 독립 fixture로 품질과 contract를 검증한다.

### 8.2 공유 타입을 임의로 바꾸지 않는다

- 요청·응답 변경은 세 명이 확인한다.
- 필드 추가와 필드 의미 변경을 구분한다.
- nullable 필드를 임의로 늘리지 않는다.
- 실패를 빈 문자열이나 빈 배열로 표현하지 않는다.

### 8.3 매일 한 번 통합한다

각자 브랜치에서 오래 작업한 뒤 한 번에 합치지 않는다. 하루에 최소 한 번 아래 흐름을 실제로 실행한다.

```text
Frontend → Backend → AI → DB → Frontend
```

### 8.4 완료는 화면 렌더링이 아니다

다음이 실제로 확인되어야 완료다.

- 오디오가 실제 STT로 변환된다.
- AI 답변과 TTS가 실제로 생성된다.
- 실제 DB row가 저장된다.
- 새로고침 후 History와 Feedback에서 다시 조회된다.
- 모바일 화면과 모바일 마이크에서 동작한다.

## 9. Figma만으로 결정할 수 없는 항목

다음은 화면에 결과만 표현되어 있어 별도 제품 결정이 필요하다.

- My Pally의 `bestie`, `ridiculous`, `lively`, `curious`, `blunt` 태그가 고정값인지 AI 분석 결과인지
- Daily Task의 완료 조건과 갱신 주기
- Streak의 날짜 및 타임존 기준
- 무료 사용자의 일일 대화량 단위
- 월간·연간 요금제의 실제 가격과 무료 체험 정책
- 결제 provider와 App/Web 결제 범위
- 데이터 삭제와 회원탈퇴 시 보존해야 하는 데이터
- 대화 turn 응답을 한 번에 받을지, transcript와 답변을 단계적으로 받을지
- 수집할 subreddit allowlist와 수집 기간
- Reddit meme 단어를 Pally 대화에 어느 빈도와 상황으로 사용할지
- meme 단어 승인 방식을 자동으로 할지 사람이 검수할지
- Reddit source 원문의 보존 여부와 보관 기간
- Reddit 이용 목적이 현재 Data API·Developer Terms에서 허용되는지

이 항목은 구현자가 추측하지 않고 PM이 먼저 결정해야 한다.

## 10. 최종 Definition of Done

MVP의 핵심 완료 기준은 다음과 같다.

- 사용자가 로그인하고 온보딩을 완료할 수 있다.
- 모바일에서 실제 음성을 녹음할 수 있다.
- 실제 STT 결과가 화면에 표시된다.
- 사용자 레벨과 이전 문맥을 반영한 Pally 답변이 생성된다.
- 실제 TTS가 재생된다.
- 대화와 피드백이 실제 DB에 저장된다.
- History와 Feedback 화면에서 저장된 내용을 다시 볼 수 있다.
- 무료 사용량이 소진되면 Figma의 limit dialog가 표시된다.
- 프로필 이름과 영어 레벨을 변경할 수 있다.
- 허용된 Reddit source에서 meme 단어를 추출하고 중복 없이 저장할 수 있다.
- 승인된 안전한 meme 단어만 Pally 대화에 사용된다.
- 오류가 무응답이나 빈 데이터로 숨겨지지 않는다.

핵심 원칙은 **역할별 전문 영역은 유지하되, 계약과 E2E 완료 기준은 세 명이 공유하는 것**이다.

## 11. 7주 개발 계획

### 전체 흐름

```text
1주차  [공동 주도] 계약·기술 기반
       FE: mock·상태 모델 / BE: Supabase·RLS / AI: 외부 API 실검증
  ↓
2주차  [FE 주도] 로그인·온보딩·프로필
       BE: 인증·프로필 저장 / AI: 레벨별 prompt
  ↓
3주차  [AI 주도] 음성 대화 Happy Path
       FE: 녹음·화면 상태·TTS 재생 / BE: turn API·Storage·DB 저장
  ↓
4주차  [BE 주도] 다중 대화·History·Feedback
       FE: History·Feedback UI / AI: 다중 문맥·Feedback 생성
  ↓
5주차  [BE 주도] Achievements·사용량·설정·결제
       FE: 화면·dialog 연결 / AI: 설정 반영·edge case
  ↓
6주차  [공동 주도] 전체 통합·보안·모바일 QA
       FE: 모바일 UX / BE: RLS·보안·배포 환경 / AI: 품질·latency
  ↓
7주차  [공동 주도] 안정화·배포·시연 준비
       FE: 최종 UX / BE: 배포·로그 / AI: 실제 환경 응답 안정화
```

각 주차는 프론트엔드, 백엔드, AI가 병렬 작업하되 마지막에는 하나의 실제 사용자 흐름으로 통합한다. 주차 완료 기준을 통과하지 못한 기능은 완료로 처리하지 않는다.

### Reddit 병렬 트랙

Reddit meme vocabulary는 화면 플로우와 병렬로 진행한다. 프론트엔드는 별도 노출 화면이 확정된 경우에만 참여한다.

| 주차 | 백엔드 | AI | 주차 완료 결과 |
|---|---|---|---|
| 1주차 | 공식 접근 방식·인증·약관·실응답 확인 | sample에서 meme 후보 추출 실험 | 접근 허용 여부와 실제 응답 shape 확인 |
| 2주차 | collector fixture와 source contract | 후보 추출·정규화 contract | 고정 fixture → MemeTermCandidate 생성 |
| 3주차 | 실제 수집, 중복 방지, 임시 저장 | 의미·맥락·안전성·confidence 생성 | 실제 source → candidate 저장 |
| 4주차 | 승인 상태와 활성 term 조회 | 품질 평가와 오탐 제거 | 승인된 MemeTerm 목록 생성 |
| 5주차 | 갱신 schedule·보존·삭제 처리 | 승인 term을 대화 context에 반영 | Pally 답변에서 제한적으로 활용 |
| 6주차 | 재수집·중복·장애·RLS 검증 | 안전성·품질·최신성 평가 | Reddit → DB → Pally E2E 통과 |
| 7주차 | 안정된 vocabulary snapshot·모니터링 | 시연 term과 fallback 검증 | 배포 환경에서 재현 가능한 결과 |

### 1주차: 공통 계약과 기술 기반

#### 공동 작업

- Figma 화면을 세 플로우로 최종 분류한다.
- 공통 타입과 API 요청·응답 fixture를 확정한다.
- Figma만으로 결정할 수 없는 정책을 PM이 확정한다.
  - 무료 사용량
  - Daily Task 완료 조건
  - Streak 기준
  - 결제 provider와 MVP 결제 범위
  - 프로필 특성 태그 생성 방식
- 브랜치와 공유 파일 ownership을 정한다.

#### 프론트엔드

- 퍼블리싱된 화면과 Figma 상태의 누락 여부를 점검한다.
- API client/repository interface를 만든다.
- 로그인, 온보딩, 대화, History용 mock fixture를 만든다.
- 대화 상태 모델을 코드에 반영한다.

#### 백엔드

- Supabase 로컬 개발 환경과 migration 흐름을 확인한다.
- 최소 스키마 초안을 만든다.
  - profile
  - conversation과 turn
  - feedback
  - usage와 subscription
- 모든 테이블의 RLS 원칙을 정한다.
- fake AI adapter interface를 만든다.

#### AI

- STT, 대화 생성, TTS를 각각 실제 API로 호출한다.
- 한국어·영어·혼합 발화의 실제 응답을 확인한다.
- latency, 응답 구조, 오류 형태를 기록한다.
- ConversationTurnInput과 ConversationTurnResult contract를 확정한다.
- A2와 C1용 최소 평가 fixture를 만든다.

#### 1주차 완료 기준

- 세 명이 동일한 요청·응답 fixture를 사용한다.
- Supabase 초기 migration과 RLS 초안이 로컬에서 적용된다.
- 외부 AI API의 실제 호출 결과가 확인된다.
- 프론트엔드에서 mock으로 핵심 Figma 상태를 전환할 수 있다.
- 미정 정책이 담당자와 결정 기한 없이 남아 있지 않다.

### 2주차: 로그인, 온보딩, My Pally 기반

#### 프론트엔드

- Google/Kakao 로그인 UI와 callback 흐름을 연결한다.
- 영어 레벨 선택, 이름 입력, 설정 완료 화면을 연결한다.
- validation과 중복 제출 방지를 구현한다.
- My Pally 기본 프로필 조회 화면을 연결한다.

#### 백엔드

- Supabase Auth와 사용자 profile 연결을 구현한다.
- 온보딩 상태, 이름, 영어 레벨 저장 API를 구현한다.
- profile 조회·수정 정책과 RLS를 검증한다.
- 프론트엔드가 사용할 생성 DB 타입을 공유한다.

#### AI

- 사용자 이름과 영어 레벨을 prompt 입력에 반영한다.
- 레벨별 답변 길이와 어휘 난이도 규칙을 구현한다.
- 실제 대화 엔진 대신 사용할 안정적인 fixture 결과를 제공한다.

#### 2주차 통합 결과

```text
로그인
→ 최초 사용자 확인
→ 영어 레벨 선택
→ 이름 입력
→ 설정 완료
→ My Pally 조회
→ 새로고침 후 설정 유지
```

#### 2주차 완료 기준

- 신규 사용자와 기존 사용자의 이동 경로가 다르게 동작한다.
- 이름과 영어 레벨이 실제 Supabase row에 저장된다.
- 다른 사용자의 profile을 조회하거나 수정할 수 없다.
- My Pally에 실제 저장값이 표시된다.

### 3주차: 음성 대화 Happy Path

#### 프론트엔드

- 마이크 권한 요청과 거부 상태를 구현한다.
- 녹음 시작·중지와 오디오 Blob 생성을 구현한다.
- `idle → listening → processing → speaking` 전환을 구현한다.
- TTS 오디오 재생과 중지를 구현한다.
- 중복 녹음, 중복 요청, 페이지 이탈을 처리한다.

#### 백엔드

- conversation 생성 API를 구현한다.
- 오디오 업로드와 turn 처리 API를 구현한다.
- fake AI adapter 결과를 turn과 feedback으로 저장한다.
- 실패한 turn과 완료된 turn을 구분한다.
- 요청 재시도로 같은 turn이 중복 저장되지 않게 한다.

#### AI

- STT → 대화 생성 → TTS 파이프라인을 연결한다.
- Pydantic 또는 동등한 boundary validation으로 입출력을 검증한다.
- 무음, 짧은 발화, 인식 실패를 구분한다.
- 한 문장 Happy Path의 실제 결과와 latency를 확인한다.

#### 3주차 통합 결과

```text
마이크 녹음
→ 오디오 업로드
→ 실제 STT
→ Pally 답변
→ 실제 TTS 재생
→ Supabase에 turn 저장
```

#### 3주차 완료 기준

- 모바일 브라우저에서 실제 음성을 녹음할 수 있다.
- 실제 transcript, Pally 답변, TTS가 순서대로 나타난다.
- 새로고침 후에도 저장된 turn을 확인할 수 있다.
- 실패가 빈 transcript나 무응답으로 숨겨지지 않는다.

### 4주차: 다중 대화, History, Feedback

#### 프론트엔드

- 펼쳐진 대화 기록과 Thinking 상태를 연결한다.
- 이전 대화 이어가기를 구현한다.
- History 목록과 대화 상세를 연결한다.
- Feedback 카드와 Feedback Empty 상태를 연결한다.
- 목록 loading, pagination, error 상태를 구현한다.

#### 백엔드

- conversation 목록과 상세 조회 API를 구현한다.
- turn 순서와 conversation 소유권을 검증한다.
- feedback을 해당 turn에 연결해 저장한다.
- History pagination과 정렬 기준을 구현한다.
- 이전 대화를 이어갈 때 필요한 context 조회를 구현한다.

#### AI

- 이전 turn을 반영한 다중 대화를 구현한다.
- `원문 → 교정문 → 한국어 설명` structured output을 안정화한다.
- 교정이 필요 없는 발화의 처리 규칙을 구현한다.
- Feedback 품질 평가 fixture를 확장한다.

#### 4주차 통합 결과

```text
3턴 대화
→ 대화 종료
→ History 목록
→ 대화 상세
→ Feedback 확인
→ 이전 대화 이어가기
```

#### 4주차 완료 기준

- 최소 3턴의 문맥이 유지된다.
- turn 순서와 Feedback 연결이 실제 DB에서 정확하다.
- 새로고침 후 History와 Feedback을 다시 조회할 수 있다.
- 피드백이 없는 대화는 Figma의 Empty 상태로 표시된다.

### 5주차: Achievements, 사용량, 설정, 결제

#### 프론트엔드

- Streak와 Daily Tasks 화면을 연결한다.
- Task 완료 상태를 표시한다.
- 이름과 영어 레벨 변경을 구현한다.
- 데이터 삭제, 로그아웃, 회원탈퇴 dialog를 연결한다.
- 무료 사용량 소진 dialog와 요금제 화면을 연결한다.
- 확정된 범위에 따라 결제 UI를 연결한다.

#### 백엔드

- Daily Task와 Streak 계산 규칙을 구현한다.
- 일일 사용량 확인과 원자적 차감을 구현한다.
- subscription 상태를 저장하고 조회한다.
- 결제가 MVP 범위라면 webhook과 중복 처리 방지를 구현한다.
- 이름·레벨 변경, 데이터 삭제, 회원탈퇴를 구현한다.
- 삭제 범위와 복구 불가 동작을 실제 DB에서 검증한다.

#### AI

- 레벨 변경이 다음 turn부터 반영되는지 확인한다.
- quota 초과 시 AI 호출이 발생하지 않도록 백엔드 contract를 검증한다.
- 긴 발화, 혼합 언어, 반복 요청 등 edge case를 보강한다.
- 프로필 특성 태그가 AI 생성으로 확정된 경우에만 해당 로직을 구현한다.

#### 5주차 통합 결과

```text
대화 사용량 차감
→ 무료 한도 도달
→ limit dialog
→ 요금제 화면
→ 구독 상태 반영
```

```text
My Pally
→ 이름·레벨 변경
→ 다음 대화에 설정 반영
```

#### 5주차 완료 기준

- 사용량이 중복 차감되거나 음수가 되지 않는다.
- quota 초과 사용자는 AI 호출 전에 차단된다.
- Streak와 Task 완료 조건이 합의된 규칙대로 동작한다.
- 삭제와 회원탈퇴 후 대상 데이터가 실제로 제거된다.
- 결제가 범위에 포함된 경우 테스트 결제와 webhook까지 확인된다.

### 6주차: 전체 통합, 보안, 모바일 QA

#### 프론트엔드

- 약 360px 모바일 폭에서 전체 화면을 점검한다.
- 실제 모바일 브라우저의 마이크 권한과 TTS 재생을 확인한다.
- loading, error, empty, disabled 상태를 전수 점검한다.
- 긴 transcript와 긴 Feedback의 레이아웃을 검증한다.
- 키보드, focus, 접근성 기본 항목을 점검한다.

#### 백엔드

- 모든 테이블의 RLS와 사용자 간 데이터 격리를 검증한다.
- service role이 클라이언트에 노출되지 않는지 확인한다.
- quota 차감, turn 저장, 결제 webhook의 idempotency를 검증한다.
- 서버 로그와 오류 응답을 점검한다.
- 배포 환경의 migration, Storage, 환경변수를 확인한다.

#### AI

- 실제 평가 fixture 전체를 실행한다.
- STT 인식률, 답변 적절성, TTS 자연도, structured output 성공률을 기록한다.
- latency가 긴 단계와 실패율이 높은 단계를 개선한다.
- timeout, provider 오류, 잘못된 응답의 사용자 경험을 검증한다.

#### 공동 E2E

- 신규 사용자 플로우
- 기존 사용자의 다중 대화 플로우
- 무료 사용량 소진 플로우
- History와 Feedback 재조회 플로우
- 설정 변경과 다음 대화 반영 플로우
- 데이터 삭제와 회원탈퇴 플로우

#### 6주차 완료 기준

- 실제 외부 API, 실제 Supabase row, 실제 모바일 브라우저로 E2E가 통과한다.
- 치명적 보안·데이터 격리 문제가 없다.
- 핵심 플로우에 blocker급 버그가 없다.
- 남은 버그가 우선순위와 담당자별로 정리된다.

### 7주차: 안정화, 배포, 시연 준비

7주차에는 새로운 기능을 추가하지 않는다.

#### 전원

- 기능 동결 후 blocker와 critical 버그만 수정한다.
- 배포 환경의 migration과 환경변수를 최종 확인한다.
- Vercel과 Railway 배포 상태 및 로그를 확인한다.
- 배포 URL에서 모바일 E2E를 다시 실행한다.
- 실패 상황과 복구 절차를 준비한다.
- 실제 시연 계정과 충분한 대화·피드백 데이터를 준비한다.
- 시연 순서와 역할을 정하고 반복 리허설한다.

#### 프론트엔드

- 모바일 레이아웃과 브라우저 권한 문제를 최종 수정한다.
- 느린 네트워크에서 loading과 중복 클릭을 확인한다.
- 시연 중 사용할 안정적인 화면 이동 경로를 확인한다.

#### 백엔드

- production migration 적용 상태를 확인한다.
- RLS, Storage, quota, webhook, 로그를 최종 점검한다.
- 배포 장애 시 확인할 로그 위치와 복구 순서를 정리한다.

#### AI

- 시연용 음성 입력 세트를 실제 환경에서 검증한다.
- 응답 latency와 provider 오류율을 확인한다.
- 실패 시 재시도 또는 안전한 안내가 동작하는지 확인한다.

#### 7주차 완료 기준

- production URL에서 핵심 E2E가 연속 3회 통과한다.
- 실제 모바일 기기에서 녹음부터 Feedback 조회까지 성공한다.
- 시연 계정과 데이터가 준비되어 있다.
- blocker와 critical 버그가 0개다.
- 팀원 모두가 장애 발생 시 확인할 위치와 대응 순서를 알고 있다.

### 매주 공통 운영 리듬

- 주 초: 이번 주 contract와 완료 기준을 세 명이 확인한다.
- 주 중: 각자 fixture 또는 adapter를 사용해 병렬 개발한다.
- 주 후반: 실제 Backend·AI·Supabase로 교체해 통합한다.
- 주 마지막: 모바일 E2E를 실행하고 다음 주 blocker를 정리한다.

### 일정이 밀릴 때 기능 축소 순서

핵심 대화 경험을 보호하기 위해 다음 순서로 범위를 줄인다.

1. AI 기반 프로필 특성 태그
2. 실제 결제 연동을 제외하고 요금제·구독 상태 UI만 유지
3. Daily Task 종류 축소
4. Streak 세부 통계 축소

다음 기능은 축소 대상에서 제외한다.

- 로그인과 온보딩
- 실제 음성 녹음, STT, Pally 답변, TTS
- 대화 저장과 History
- Feedback
- 사용자 데이터 격리와 RLS
- 모바일 핵심 E2E

## 12. 1주차 상세 협업 실행 순서

### 12.1 1주차 목표

1주차의 목적은 기능을 많이 만드는 것이 아니다. 세 명이 2주차부터 서로 기다리지 않고 개발할 수 있도록 **공통 계약, Supabase 기반, 외부 API 실응답, 교체 가능한 mock·adapter**를 준비하는 것이다.

금요일까지 다음 두 흐름의 얇은 통합이 성공해야 한다.

```text
Frontend Fixture
→ Backend API
→ Fake AI Adapter
→ Local Supabase
```

```text
Reddit 실제 허용 source
→ Backend Collector
→ AI Meme Extractor
→ Local Supabase Candidate
```

실제 STT·대화 생성·TTS는 각각 실호출을 검증해야 한다. 전체 실시간 음성 대화 E2E 완성은 3주차 목표다.

### 12.2 시작 전에 준비할 접근 권한

월요일 시작 전에 각 담당자는 credential의 존재 여부만 확인한다. secret 값은 문서, 채팅, fixture, Git에 남기지 않는다.

| 항목 | 확인 담당 | 없을 때 처리 |
|---|---|---|
| Supabase 개발 project 접근 | 백엔드 | 작업 시작 전에 PM에게 요청 |
| Supabase anon·service role 환경변수 | 백엔드 | service role은 서버 환경에만 설정 |
| Google Cloud STT/TTS/Gemini 권한 | AI | 실제 호출 전 즉시 요청 |
| Reddit 공식 API 또는 승인된 접근 | 백엔드 | 허용 여부 확인 전 collector 구현 금지 |
| 모바일 마이크 테스트 기기 | 프론트엔드 | 최소 한 대 확보 |

credential이 없으면 가짜 성공 처리하거나 나중으로 미루지 않는다. 해당 외부 연동의 blocker로 즉시 공유하고, 다른 fixture 작업은 계속 진행한다.

### 12.3 파일 소유 경계

1주차에는 동일 파일을 여러 명이 동시에 수정하지 않는다.

| 담당 | 기본 소유 영역 |
|---|---|
| 프론트엔드 | `frontend/app/`, `frontend/components/`의 공통 UI·audio·conversation, `frontend/lib/audio/`, `frontend/lib/state/` |
| AI | `ai/`, `frontend/components/pally/`, `frontend/app/dev/pally/`, `frontend/lib/types/character.ts` |
| 백엔드 | `backend/`, `supabase/migrations/`, Supabase 공유 개발 환경 |

공유 contract 변경은 다음 규칙을 따른다.

- Frontend ↔ Backend API contract 최종 편집자는 백엔드 담당자다.
- Backend ↔ AI engine contract 최종 편집자는 AI 담당자다.
- 프론트엔드 담당자는 화면에 필요한 필드를 요청하고 mock으로 먼저 검증한다.
- breaking change는 매일 통합 시간에 세 명이 확인한 뒤 반영한다.
- Supabase Dashboard 수동 스키마 변경은 백엔드 담당자도 하지 않고 migration으로 남긴다.

### 12.4 매일 고정 일정

시간은 팀 일정에 맞게 이동할 수 있지만 순서는 유지한다.

| 시간 | 참여자 | 내용 |
|---|---|---|
| 업무 시작 후 15분 | 전원 | 오늘 입력물, 출력물, blocker 확인 |
| 오전 | 각 담당 | 독립 작업과 실험 |
| 점심 전 10분 | 필요한 담당자 | contract 질문만 해결, 긴 회의 금지 |
| 오후 | 각 담당 | 구현과 검증 |
| 업무 종료 60분 전 | 전원 | 통합, 실제 결과 확인, breaking change 결정 |
| 업무 종료 전 | 각 담당 | 다음 담당자에게 필요한 fixture·endpoint·migration 상태 전달 |

공유 메시지는 다음 형식으로 짧게 작성한다.

```text
[완료] 실제로 확인한 결과
[변경] contract 또는 migration 변경
[필요] 다른 담당자가 제공해야 할 입력
[차단] credential·정책·기술 blocker
```

### 12.5 월요일: 범위와 Contract v0 고정

#### 오전 1: 전원 Figma 플로우 확인

세 명이 함께 다음 화면 상태만 확인한다.

1. 로그인과 온보딩
2. 새 채팅, Listening, Thinking, TTS 재생
3. History와 Feedback
4. 무료 사용량 제한
5. My Pally와 설정
6. Reddit meme vocabulary가 Pally에서 사용되는 위치

이 시간에는 구현 방법보다 사용자 입력과 화면 출력만 결정한다.

#### 오전 2: PM 결정이 필요한 항목 확정

- Reddit subreddit allowlist
- Reddit meme 단어 사용 빈도와 사용 상황
- 자동 승인인지 사람 검수인지
- 무료 대화량 단위
- Streak와 Daily Task 기준
- 결제 기능의 7주 MVP 포함 범위
- 프로필 특성 태그 생성 방식

결정되지 않은 항목은 담당자와 결정 기한을 적는다. 구현자가 임의로 정하지 않는다.

#### 오후: 세 역할이 동시에 contract 초안 작성

##### 프론트엔드

- 각 Figma 화면에 필요한 필드를 목록으로 만든다.
- 성공, loading, empty, quota, error fixture를 만든다.
- `ConversationState` 전환표를 검증한다.

##### 백엔드

- Profile, Conversation, Turn, Feedback, Usage의 API shape를 만든다.
- RedditSourceItem과 수집 batch shape를 만든다.
- 최소 Supabase 관계를 초안으로 만든다.

##### AI

- ConversationTurnInput과 ConversationTurnResult를 만든다.
- MemeTermCandidate 입출력 shape를 만든다.
- 외부 API별 실제 호출에서 확인해야 할 필드를 정한다.

#### 월요일 종료 통합 순서

1. 프론트엔드가 화면별 필수 필드를 설명한다.
2. 백엔드가 공개 API 요청·응답을 맞춘다.
3. AI가 backend 내부 engine contract를 맞춘다.
4. 세 명이 성공·오류 JSON fixture를 직접 읽는다.
5. 백엔드가 API Contract v0, AI가 Engine Contract v0를 동결한다.

#### 월요일 산출물

- Profile fixture
- Conversation turn 성공·quota·error fixture
- History와 Feedback fixture
- Reddit source fixture
- MemeTermCandidate fixture
- 최소 DB 관계 초안
- 미정 정책 목록과 결정 기한

월요일에는 실제 Supabase 테이블이나 production engine을 먼저 구현하지 않는다. contract가 고정되기 전에 코드를 생성하면 세 역할의 결과가 갈라진다.

### 12.6 화요일: 외부 API 실호출과 Supabase 기반

화요일부터는 세 명이 서로 기다리지 않고 병렬 작업한다.

#### 프론트엔드

1. 월요일 fixture를 mock repository에 연결한다.
2. `idle`, `listening`, `processing`, `speaking`, `quota_exceeded`, `error` 화면을 전환한다.
3. 로그인·온보딩·History가 fixture로 렌더링되는지 확인한다.
4. 모바일 약 360px에서 상태별 화면을 확인한다.

#### 백엔드

1. 최소 Supabase migration을 작성한다.
2. 모든 테이블에 RLS를 적용한다.
3. 로컬 Supabase에 migration을 적용한다.
4. fixture 데이터를 실제 row로 넣고 소유권 조회를 검증한다.
5. Reddit 공식 API 또는 승인된 접근을 실제로 한 번 호출한다.
6. 인증, 응답 구조, 필요한 필드, 오류 형태를 확인한다.

#### AI

다음 순서로 각각 실호출한다. 실제 호출 결과를 확인하기 전 production 코드를 작성하지 않는다.

1. STT: 한국어·영어·혼합 음성 transcript
2. Gemini: 레벨별 답변과 structured Feedback
3. TTS: 한국어 또는 영어 Pally 음성
4. Reddit sample: 실제 허용 source에서 meme 후보를 수동 또는 일회성 실험으로 추출

각 호출에서 latency, 입력, 응답 shape, 오류를 확인한다. secret이나 Reddit 원문 전체를 fixture에 그대로 남기지 않는다.

#### 화요일 종료 통합 순서

1. 백엔드가 migration 적용 결과와 생성된 타입을 공유한다.
2. AI가 실제 API 응답이 contract를 만족하는지 보고한다.
3. Reddit 접근이 허용되는지, 추가 승인이 필요한지 결정한다.
4. 프론트엔드가 mock으로 재현되는 Figma 상태를 보여준다.
5. 실제 응답과 contract가 다르면 Contract v0.1로 한 번만 수정한다.

#### 화요일 완료 기준

- 로컬 Supabase migration과 RLS가 적용된다.
- 다른 사용자 데이터 접근이 차단된다.
- STT, Gemini, TTS 실제 출력이 확인된다.
- Reddit 실제 접근 가능 여부와 응답 shape가 확인된다.
- 프론트엔드 mock으로 핵심 상태가 보인다.

### 12.7 수요일: 교체 가능한 Skeleton 구현

#### 프론트엔드

1. mock repository와 real API client가 같은 interface를 사용하게 한다.
2. 대화 상태 머신을 화면에 연결한다.
3. 실제 endpoint URL 없이도 전체 상태를 시연할 수 있게 한다.
4. API 오류를 안전한 사용자 메시지로 변환한다.

#### 백엔드

1. FastAPI 공개 endpoint skeleton을 만든다.
2. FakeAIAdapter를 연결한다.
3. conversation과 turn 저장·조회 repository를 만든다.
4. Reddit collector interface와 fake collector를 만든다.
5. 같은 source id의 중복 저장을 막는다.

#### AI

1. 화요일 실호출 결과에 맞춰 AI engine adapter를 만든다.
2. STT, conversation, Feedback, TTS 결과를 contract로 검증한다.
3. Reddit source fixture에서 MemeTermCandidate를 생성한다.
4. 중복 정규화와 `safe/review/blocked` 안전성 상태를 구현한다.

#### 수요일 종료 통합 순서

1. 프론트엔드가 mock interface 호출 예시를 전달한다.
2. 백엔드가 같은 응답을 주는 endpoint를 실행한다.
3. AI가 FakeAIAdapter와 동일한 engine result를 반환한다.
4. Reddit fake collector 결과가 meme extractor 입력과 맞는지 확인한다.
5. mismatch는 interface에서 해결하고 화면이나 DB에 임시 변환 코드를 흩뿌리지 않는다.

#### 수요일 완료 기준

- 프론트엔드는 mock과 real client를 교체할 수 있다.
- 백엔드는 fake AI만으로 turn을 저장할 수 있다.
- AI는 fixture만으로 contract 테스트를 통과한다.
- Reddit fixture가 MemeTermCandidate로 변환된다.

### 12.8 목요일: 첫 번째 얇은 통합

목요일에는 다음 순서를 지킨다. 앞 단계가 실패해도 다른 담당자의 독립 작업을 중단하지 않고 fake 구현으로 진행한다.

#### 통합 A: Frontend → Backend → Fake AI → Supabase

1. 백엔드가 migration version과 로컬 endpoint를 공지한다.
2. 프론트엔드가 API client를 mock에서 real backend로 교체한다.
3. 프론트엔드가 고정 오디오 또는 고정 turn 요청을 보낸다.
4. 백엔드가 FakeAIAdapter 결과를 반환하고 Supabase에 저장한다.
5. 프론트엔드가 Thinking과 Pally 답변 상태를 표시한다.
6. 새로고침 후 저장된 turn을 다시 조회한다.

#### 통합 B: Backend → Real AI Engine

1. AI 담당자가 engine 실행 명령과 입력 fixture를 전달한다.
2. 백엔드가 FakeAIAdapter 대신 real adapter를 연결한다.
3. 고정된 짧은 오디오 한 개로 STT·답변·TTS 결과를 확인한다.
4. 실패하면 원인을 단계별로 기록하고 fake adapter로 복귀할 수 있게 유지한다.

#### 통합 C: Reddit → Meme Candidate

1. 백엔드가 허용된 실제 Reddit source batch를 만든다.
2. AI가 MemeTermCandidate 목록을 반환한다.
3. 백엔드가 source id와 normalized term 기준으로 중복을 확인한다.
4. candidate를 `review` 상태로 local Supabase에 저장한다.
5. 승인 전에는 Pally prompt에서 조회되지 않는지 확인한다.

#### 목요일 완료 기준

- 프론트엔드 요청이 backend와 local Supabase까지 도달한다.
- FakeAIAdapter 결과가 화면과 DB에 동일하게 보인다.
- real AI engine 한 건의 결과가 contract를 만족한다.
- 실제 Reddit source 한 batch가 candidate row로 저장된다.

### 12.9 금요일: 안정화와 Contract v1 동결

금요일에는 새 기능을 추가하지 않고 1주차 기반만 검증한다.

#### 오전 검증 순서

1. 프론트엔드가 모든 mock 화면 상태를 시연한다.
2. 백엔드가 migration을 빈 로컬 DB에 처음부터 다시 적용한다.
3. 백엔드가 RLS로 사용자 간 데이터가 격리되는지 확인한다.
4. AI가 STT, Gemini, TTS 실제 호출 결과를 다시 보여준다.
5. 전원이 FakeAI 기반 얇은 E2E를 실행한다.
6. 전원이 Reddit 실제 source → candidate 저장을 실행한다.

#### 오후 정리 순서

1. blocker와 contract mismatch만 수정한다.
2. API Contract v1을 동결한다.
3. AI Engine Contract v1을 동결한다.
4. Supabase migration version과 생성 타입을 공유한다.
5. 2주차 담당 입력물을 확인한다.
6. 남은 실험 코드는 production 코드와 분리한다.

#### 금요일 최종 체크리스트

- [ ] FE가 backend 완료를 기다리지 않고 mock으로 개발 가능
- [ ] BE가 AI 완료를 기다리지 않고 FakeAIAdapter로 개발 가능
- [ ] AI가 DB 완료를 기다리지 않고 fixture로 개발 가능
- [ ] local Supabase migration을 처음부터 재현 가능
- [ ] 모든 테이블의 RLS 적용 확인
- [ ] STT, Gemini, TTS 실제 호출 확인
- [ ] Reddit 접근 허용 여부와 실제 응답 shape 확인
- [ ] 실제 Reddit source에서 candidate 추출·저장 확인
- [ ] secret과 credential이 Git에 포함되지 않음
- [ ] 2주차에 breaking change 없이 사용할 Contract v1 존재

### 12.10 정확히 무엇이 순차이고 무엇이 병렬인가

#### 반드시 순차로 진행할 항목

```text
화면 입력·출력 합의
→ API Contract v0
→ Supabase migration
→ 실제 Backend 연결
```

```text
외부 API 실제 호출
→ 응답 shape 확인
→ AI adapter 구현
→ Backend에 real adapter 연결
```

```text
Reddit 접근 허용 확인
→ 실제 source 수집
→ meme 후보 추출
→ candidate 저장
→ 승인 후 Pally 사용
```

#### 동시에 진행할 항목

```text
FE: mock UI와 상태 머신
BE: migration·RLS·API·fake adapter
AI: fixture·외부 API 실검증·engine
```

#### 기다리지 않는 규칙

- FE는 Backend endpoint가 없으면 mock repository를 사용한다.
- BE는 AI engine이 없으면 FakeAIAdapter를 사용한다.
- AI는 Supabase가 없으면 JSON fixture를 사용한다.
- Reddit 접근 승인이 지연되면 fake source fixture로 extractor를 개발하되 실제 수집 완료로 처리하지 않는다.
- 공유 contract를 바꿀 필요가 생기면 임시 필드를 각자 추가하지 않고 당일 통합 시간에 결정한다.
