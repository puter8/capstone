# Pally 학습 프로그램 확장 제안

기준: 2026-10-08, `origin/main`. 작성 계기: "Pally 답이 짧아서 배울 게 없다"는 팀 피드백.

## 1. 현재 상태 진단

### 1.1 답이 짧은 이유

| 원인 | 위치 | 내용 |
|---|---|---|
| 길이 제한 | `backend/main.py` `_build_chat_system_prompt` | "Keep the entire reply within 90 characters, using at most two short sentences." (2026-10-05 `55f52cd`) |
| 화면 제약 | `frontend/components/chat/ChatBubble.tsx` ShortBubble | 메시지 영역이 Figma 기준 높이 132px로 고정이라 긴 답이 잘림. 90자 제한은 이 문제 때문에 넣었음 |
| 응답 구조 | 같은 프롬프트 | "핵심 교정 표현으로 다시 말해주기(recast) + 짧은 질문 1개"가 기본 틀. Pally 자신의 이야기나 새 표현이 들어갈 자리가 없음 |

결과적으로 Pally는 "사용자 문장을 고쳐서 되돌려주고 질문하는" 역할만 한다. 사용자가 새로 들을 수 있는 영어(입력)가 거의 없다.

### 1.2 이미 있는 학습 자산

새 기능은 아래 자산을 재사용하는 것을 우선한다.

- **턴별 교정 추출**: `ai/generate_feedback.py`, `backend/lib/session_feedback.py`. 대화가 끝나면 `{original, corrected}` 교정 목록을 저장한다.
- **한국어 인라인 힌트**: `_call_gemini_hint_ko`. 무엇이 교정됐는지 한국어로 설명한다.
- **오프너**: `ai/opener.py`. 주제를 고르고 Pally가 먼저 말을 건다. 최근 대화와 겹치는 주제는 피한다.
- **Daily Task / Streak**: `_TASK_CATALOG`(A~D 카테고리, 하루 3개). 지금은 대부분 "앱 사용량" 과제다(대화 시작, 3턴, 로그 펼치기 등).
- **5축 캐릭터**: 사용자 말투에 따라 Pally 모습과 성격이 바뀐다.
- **STT 신뢰도**: `/api/stt`가 `confidence`를 반환한다.

## 2. 다른 앱 참고

| 앱 | 학습 구조 | Pally에 가져올 점 |
|---|---|---|
| Speak (스픽) | 표현 학습 → 반복 연습 → AI와 자유 대화의 3단계. 상위 요금제는 **사용자가 반복하는 실수로 맞춤 레슨**을 생성 | 내 실수 기반 복습 |
| Duolingo Max | Video Call(Lily가 **방금 배운 주제로 먼저 말 걸기**, 지난 대화 기억, 끝나면 대화록 제공), Roleplay(카페·공항·면접 상황), Explain My Answer(틀린 이유를 문법 규칙으로 설명) | 오프너에 학습 목표 연결, 상황극 |
| Praktika | 아바타마다 억양·성격·배경 이야기, 150개 이상의 대화 주제, 약한 영역으로 레슨 자동 조정 | 캐릭터가 자기 이야기를 함 |
| Loora | 실전 상황(면접, 회의, 스몰토크) 코칭, 막히면 **모국어 번역** 제공, 강점·약점 리포트 | 막힐 때 한국어 도움 |
| Ringle (링글) | AI 분석 리포트: **복잡성·정확성·유창성·발음** 4개 항목 점수 | 세션 리포트 지표 |

공통 패턴은 세 가지다. ① 배울 표현을 먼저 주고 대화에서 써보게 한다. ② 실수를 모아 다시 연습시킨다. ③ 진행 상황을 숫자로 보여준다. 리뷰들은 Speak의 약점으로 "구조화된 코스, 자유 대화, 개인화 복습이 서로 따로 논다"는 점을 꼽는다.

## 3. 방향

Pally는 튜터가 아니라 **"말투에 따라 변하는 친구"**다. 코스형 앱(Speak, Duolingo)을 따라 하기보다, **자유 대화 하나를 중심으로 학습 요소를 그 안에 엮는다.** 위에서 짚은 Speak의 약점(요소들이 따로 논다)을 피하는 방향이다.

```
오늘의 표현/복습할 실수 ──▶ 오프너가 그 표현·실수로 대화를 연다
                                │
                     대화 중: Pally가 표현을 들려주고, 사용자가 써본다
                                │
          대화 종료 ──▶ 교정 추출(기존) ──▶ 다음 대화의 복습 재료
                                │
                     세션 리포트 + Daily Task 달성
```

## 4. 제안 (우선순위순)

### P0-1. 응답 프롬프트 개선 — 담당: 백은혜(BE·AI)

**변경**
- 90자 고정 제한을 레벨별 길이로 바꾼다. 예: A2는 1~2문장, B1은 2문장, B2·C1은 2~3문장. 정확한 수치는 실호출로 정한다.
- 응답 틀을 바꾼다: **반응(교정 포함) + Pally 자신의 한마디(의견·경험·새 표현 1개) + 질문 1개.**
  - 질문만 되돌려주는 답을 금지한다.
  - 사용자 레벨보다 **한 단계 위의 자연스러운 표현(chunk) 1개**를 대화 속에 넣는다(i+1 입력).

**검증 (CLAUDE.md §4)**
- 레벨 4개 × 대표 발화 10개를 실제 Gemini로 호출해 전후를 비교한다.
- 응답 길이가 늘면 TTS 지연도 늘어나므로 턴 지연(`tts_ms`, `total_ms`)을 함께 잰다.

**주의**
- 오프너 프롬프트(`ai/opener.py`, 김민주 영역)도 같은 기준으로 맞출지 함께 정한다.

### P0-2. 말풍선이 긴 답을 보여주게 — 담당: 이찬희(FE)

- ShortBubble의 메시지 영역(132px)에 **세로 스크롤**을 넣는다(`overflow-y-auto`, 새 메시지가 오면 맨 아래로).
  - 또는 마지막 Pally 메시지만 크게 보여주고 이전 사용자 발화는 숨긴다.
- 펼친 화면(LongBubble)은 이미 있으므로 새 화면은 필요 없다.
- P0-1과 **같이 배포**해야 한다. 프롬프트만 먼저 바뀌면 화면이 다시 잘린다.
- 모바일 360px 폭에서 확인한다.

### P1-1. 내 실수로 복습 — 담당: BE·AI, FE

Speak의 "실수 기반 맞춤 레슨", Duolingo의 "배운 것으로 먼저 말 걸기"를 참고했다.

**흐름**
1. 지난 대화들에서 저장된 교정(`original → corrected`) 중 1~2개를 고른다(최근순 + 반복 횟수 기준).
2. 다음 대화의 오프너가 그 표현을 쓸 수밖에 없는 질문으로 대화를 연다. 예: 지난번 "she want cookies"를 교정받았다면 → "What does your sister want for her birthday?"
3. 사용자가 이번에 맞게 말하면 "복습 성공"으로 기록하고 Daily Task로 인정한다.

**재사용**
- 교정 저장(기존), 오프너(주제 선택 대신 복습 표현을 입력), Daily Task.

**정해야 할 것**
- 오프너가 "과거 대화를 언급하지 않는다"는 현재 규칙과 충돌한다. 직접 언급 없이 자연스럽게 유도할지, 대놓고 "지난번에 배운 표현 써볼까?"라고 할지 정해야 한다.

### P1-2. 오늘의 표현 — 담당: PM(콘텐츠), BE

- 레벨별로 하루 1개의 표현(chunk)을 정한다. 예: B1 "I'm into ~", "It's not my thing".
- 홈 화면에 표현과 한국어 뜻을 보여준다. Pally는 대화 중 한 번 그 표현을 써서 들려준다.
- 사용자가 transcript에서 그 표현을 쓰면 새 Daily Task 카테고리(E)로 달성 처리한다. 판정은 정규화한 문자열 매칭으로 시작한다.

**정해야 할 것**
- 표현 목록을 누가 만들지(PM 수작업 vs Gemini 생성 후 검수).
- `ai/reddit_vocabulary.py`의 기존 어휘 자료를 쓸 수 있는지 확인이 필요하다.

### P1-3. 막힐 때 한국어 도움 — 담당: BE·AI, FE

Loora를 참고했다.

- 마이크 옆에 "도움" 버튼을 둔다. 사용자가 한국어로 말하면 영어 표현 2~3개를 돌려준다(캐주얼/중립).
- 기존 STT는 `en-US` 고정이므로 이 버튼에서만 `ko-KR`로 인식한다.
- 응답은 대화 기록이 아니라 힌트 패널에 띄우고, 고른 표현으로 바로 다시 말해보게 한다.
- 한국어 STT 인식률과 지연은 실호출로 먼저 확인한다(§4).

### P2-1. 상황극 — 담당: AI(김민주), BE, FE

- 카페 주문, 길 묻기, 면접 첫인사 등 상황 5~10개로 시작한다.
- 오프너에 `scenario` 인자를 추가한다. Pally는 그 역할(점원, 면접관)을 맡고, 상황의 목표(주문 완료 등)를 체크리스트로 보여준다.
- 역할을 맡는 동안 5축 캐릭터 반영을 어떻게 할지(유지할지, 역할 성격으로 덮어쓸지) 정해야 한다.

### P2-2. 말투 바꾸기 챌린지 — Pally만의 차별점

- "같은 말을 더 격식 있게/더 캐주얼하게 해보기" 미션을 준다. Pally의 모습이 바뀌는 것 자체가 시각적 피드백이 된다.
- 기존 Daily Task D1(톤 변화 느껴보기), B6(뚜렷한 톤)이 같은 방향이지만, 지금은 "무엇을 배우는지"가 드러나지 않는다.
- 이 기능은 **격식(register)을 가르치는 학습**으로 바꾼다. 전후 문장을 나란히 보여주고, Gemini가 "무엇이 격식을 바꿨는지"를 한국어로 설명한다.
- **주의**: 현재 규칙 분석기는 사람 점수와의 상관이 낮다(dev-200 기준 5축 평균 Spearman 0.37). Formality는 사람끼리도 점수가 가장 많이 갈렸다(평가자 간 ICC 0.474). 그래서 축 점수로 성공/실패를 채점하지 말고, Gemini 판정이나 "놀이"로 다룬다.

### P2-3. 세션 리포트 — 담당: BE, FE

Ringle의 4개 지표를 참고하되, 지금 데이터로 정직하게 낼 수 있는 것만 보여준다.

| 지표 | 계산 | 비고 |
|---|---|---|
| 유창성 | 턴당 평균 단어 수, 지난 세션 대비 변화 | Daily Task B2가 이미 단어 수를 셈 |
| 정확성 | 교정 개수 ÷ 사용자 턴 수 | 교정 추출(기존) |
| 다양성 | 고유 단어 수 / 전체 단어 수 | 새 계산, 간단 |
| 발음 | **표시하지 않음** | STT confidence는 발음 점수가 아님. 발음 평가 API를 실호출로 검토한 뒤 결정 |

## 5. 결정이 필요한 것

1. P0-1의 레벨별 응답 길이와 "새 표현 1개 넣기" 규칙을 채택할지 (PM)
2. P0-1, P0-2를 같이 배포하는 일정 (BE + FE)
3. P1 중 무엇부터 할지. 추천은 **P1-1 내 실수로 복습**이다. 데이터와 파이프라인이 이미 있어 추가 비용이 가장 작다.
4. 오프너의 "과거 대화를 언급하지 않는다" 규칙을 복습 기능을 위해 완화할지 (AI·PM)
5. 오늘의 표현 콘텐츠를 누가 만들지 (PM)

## 참고 자료

- [Speak App Review 2026 — LanguaTalk](https://languatalk.com/blog/speak-app-review/)
- [Speak — tooldirectory.ai](https://tooldirectory.ai/tools/speak)
- [Best Speak App Alternatives — issen](https://www.issen.com/blog/speak-app-alternatives/)
- [Duolingo Max — Duolingo Blog](https://blog.duolingo.com/duolingo-max)
- [Praktika — Learning English with an AI Tutor](https://praktika.ai/learning-english-with-an-ai-tutor-how-it-works)
- [Loora — English Conversation Practice](https://loora.com/use-cases/english-conversation-practice)
- [Loora — tooldirectory.ai](https://tooldirectory.ai/tools/loora)
- [스픽·말해보카·듀오링고 차이점 — 유니콘팩토리](https://www.unicornfactory.co.kr/article/2025012314223538499)
- [AI 영어공부 앱 — 알체라](https://www.alchera.ai/resource/blog/AI-english-study)
