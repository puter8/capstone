# Pally AI 파트 8월 말 실행 계획: ML 전환과 Reddit Vocabulary

> 대상 기간: 2026-07-25 ~ 2026-08-31
>
> 대상 역할: AI 담당자
>
> 기준 상태: MVP에서 STT/TTS, `/api/chat`, 5축 룰베이스 분석, Pally character payload, Feedback 화면용 피드백 생성 흐름은 이미 동작한다.

## 1. 결론

AI 파트는 앞으로도 프론트엔드와 백엔드 전체 구현을 기다리지 않고 독립적으로 진행할 수 있다. 다만 독립 개발의 전제는 **입출력 계약을 고정하는 것**이다.

이번 계획의 목표는 두 가지다.

1. 현재 룰베이스 5축 분석기를 ML 기반 분석기로 교체 가능한 구조까지 발전시킨다.
2. Reddit에서 허용된 방식으로 수집된 source item을 이용해 meme/slang vocabulary 후보를 추출하고, 안전성·품질 검수를 거친 term만 Pally 대화에 사용할 수 있게 한다.

핵심 원칙은 다음과 같다.

- 프론트엔드는 내부가 룰베이스인지 ML인지 몰라도 된다.
- 백엔드는 AI 엔진 호출 경계와 저장 필드만 알면 된다.
- AI 담당자는 fixture, CLI, test로 먼저 엔진을 고도화하고 마지막에 기존 API contract 뒤에 갈아끼운다.
- Reddit 원문은 기본적으로 ML 학습 데이터로 사용하지 않는다.
- 승인되지 않은 slang/meme 후보는 Pally prompt에 넣지 않는다.

```text
Frontend
  → Backend API contract
    → AI Engine interface
      ├→ Axis Analyzer: rule-based → ML candidate → selected analyzer
      ├→ Feedback Generator
      ├→ STT/TTS
      └→ Meme Vocabulary Context
```

## 2. 다른 파트와의 관계

### 2.1 프론트엔드와의 관련

프론트엔드와 AI 파트의 직접 관련은 거의 출력 contract뿐이다.

프론트엔드가 계속 기대하는 응답 형태는 유지한다.

```ts
export type FeedbackItem = {
  original: string;
  corrected: string;
  explanationKo: string;
};

export type ChatResponseForFrontend = {
  status: "ok";
  transcript: string;
  reply: string;
  tts_audio: string;
  axes: {
    Formality: number;
    Energy: number;
    Intimacy: number;
    Humor: number;
    Curiosity: number;
  };
  character: {
    tone_casual: number;
    energy_level: number;
    humor_level: number;
  };
  feedback: FeedbackItem[];
};
```

프론트엔드는 다음 사실을 몰라도 된다.

- 5축 분석이 룰베이스인지 ML인지
- Reddit vocabulary가 어떤 extractor로 만들어졌는지
- safety filter가 규칙 기반인지 모델 기반인지
- STT/TTS 품질 개선이 어떤 provider parameter로 이루어졌는지

프론트엔드와 맞춰야 하는 것은 다음뿐이다.

- `axes`, `character`, `feedback`, `tts_audio` 필드 이름과 타입을 깨지 않는다.
- 에러 시 빈 화면이 아니라 기존 error state가 표시될 수 있도록 안전한 오류 메시지를 반환한다.
- 캐릭터 변화 범위는 기존 Pally renderer가 처리할 수 있는 0~100 범위를 유지한다.

### 2.2 백엔드와의 관련

백엔드와 AI 파트의 관련은 API 경계, 저장 필드, Reddit source item 전달 방식이다.

백엔드가 알아야 하는 것은 다음이다.

- AI 엔진을 어떤 함수 또는 adapter로 호출하는지
- `/api/chat`에서 저장할 `axes`, `character`, `feedback` 구조
- Reddit collector가 만든 source item을 AI extractor에 어떤 shape로 넘기는지
- 승인된 `MemeTerm`을 Pally prompt context로 어떻게 조회하는지

백엔드가 몰라도 되는 것은 다음이다.

- ML 모델 내부 구조
- feature engineering 방식
- 학습 파라미터
- 후보 term scoring 로직의 세부 구현
- STT/TTS 품질 튜닝의 내부 실험 결과

백엔드와 반드시 고정해야 하는 최소 contract는 다음이다.

```ts
export type RedditSourceItem = {
  sourceId: string;
  sourceUrl: string;
  subreddit: string;
  title?: string;
  text: string;
  observedAt: string;
};

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

### 2.3 AI가 독립적으로 할 수 있는 것

다음 작업은 AI 파트 내부에서 독립적으로 진행한다.

- 5축 분석 ML 모델 실험
- 데이터셋 설계, 라벨링 가이드 작성, 샘플 라벨링
- 룰베이스 baseline과 ML candidate의 evaluation
- Reddit slang/meme 후보 추출기 구현
- term 정규화, confidence scoring, safety filter
- 승인된 vocabulary를 Pally prompt context로 변환
- STT/TTS latency와 품질 측정
- fixture 기반 contract test, CLI demo, regression test

### 2.4 반드시 맞춰야 하는 것

다음 항목은 프론트엔드 또는 백엔드와 합의 없이 바꾸지 않는다.

- `/api/chat` 응답 shape
- DB에 저장되는 `axes`, `character`, `feedback` 구조
- Reddit collector가 넘겨주는 `RedditSourceItem` format
- 승인된 vocabulary만 prompt에 들어간다는 정책
- 캐릭터 파라미터 범위와 의미

정리하면 현재 포지션은 다음과 같다.

> **AI는 독립 개발 가능. 단, 입출력 계약은 백엔드/프론트엔드와 고정해야 한다.**

## 3. ML 전환 전략

### 3.1 목표

MVP의 5축 룰베이스 분석기를 바로 제거하지 않는다. 먼저 동일한 입력과 동일한 출력 contract를 만족하는 ML analyzer를 추가하고, evaluation에서 충분히 낫다고 판단될 때만 default analyzer를 바꾼다.

```text
User utterance
→ Analyzer interface
  ├→ RuleBasedAxisAnalyzer
  └→ MLAxisAnalyzer
→ Axes
→ Character Matrix
→ CharacterParams
```

### 3.2 Analyzer interface

AI 파트 내부에서는 분석기를 다음처럼 교체 가능하게 둔다.

```python
class AxisAnalyzer:
    def analyze(self, utterance: str, context: dict | None = None) -> AxisResult:
        ...
```

`AxisResult`는 기존 `axes` contract와 동일한 5축 0~100 값을 반환한다.

```python
class AxisResult(BaseModel):
    Formality: int
    Energy: int
    Intimacy: int
    Humor: int
    Curiosity: int
```

### 3.3 데이터셋 계획

초기 데이터셋은 세 층으로 구성한다.

| 데이터 | 용도 | 비고 |
|---|---|---|
| 기존 수작업 예문 | baseline 재현 | 현재 `data/dataset.py` 확장 |
| 직접 작성/라벨링 발화 | supervised 학습/검증 | 영어 학습자 발화 중심 |
| synthetic utterance | coverage 보강 | 모델 학습보다 evaluation 보강에 우선 사용 |

Reddit 원문은 기본적으로 ML 학습에 사용하지 않는다. Reddit source는 meme/slang 후보 추출과 vocabulary 품질 검수에만 사용한다.

### 3.4 라벨링 기준

각 발화는 5개 축에 대해 0~100 점수를 갖는다.

| 축 | 낮음 | 높음 |
|---|---|---|
| Formality | casual, slang, 줄임말 | polite, structured, formal |
| Energy | 차분함, 짧은 반응 | 감탄, 강한 표현, high arousal |
| Intimacy | 거리감, 정보 전달 | 친근함, 자기노출, 호칭 |
| Humor | 농담 없음 | joke, irony, meme, playful |
| Curiosity | 단정/요청 | 질문, 탐구, 이유 묻기 |

라벨링 산출물은 CSV 또는 JSONL로 둔다.

```json
{
  "utterance": "yo what's up lol, wanna practice together?",
  "axes": {
    "Formality": 5,
    "Energy": 70,
    "Intimacy": 65,
    "Humor": 45,
    "Curiosity": 20
  },
  "notes": "casual greeting, friendly tone"
}
```

### 3.5 모델 후보

8월 말까지는 과한 모델 서빙보다 교체 가능한 baseline을 우선한다.

| 후보 | 장점 | 리스크 | 8월 목표 |
|---|---|---|---|
| Rule-based v2 | 빠르고 설명 가능 | 표현 다양성 한계 | fallback 유지 |
| TF-IDF + multi-output regressor | 가볍고 학습 쉬움 | 문맥 이해 약함 | 1차 ML baseline |
| sentence embedding + regressor | 의미 반영 가능 | 의존성/서빙 복잡도 | 가능하면 실험 |
| LLM scoring | 품질 좋을 수 있음 | 비용/latency/일관성 | evaluation judge 용도 |

기본 방향은 `TF-IDF + multi-output regressor`를 먼저 만들고, 성능과 의존성 부담을 본 뒤 embedding 기반 후보를 추가한다.

### 3.6 Evaluation

ML 전환은 감으로 하지 않는다. 최소한 다음 지표를 남긴다.

- 축별 MAE
- 축별 Spearman correlation
- 룰베이스 대비 개선/악화 케이스
- casual/formal/persona drift demo case 재현성
- inference latency
- 실패 시 fallback 가능 여부

완료 기준은 다음이다.

- 동일 fixture에서 항상 0~100 axes를 반환한다.
- 룰베이스보다 명백히 나빠지는 핵심 demo case가 없다.
- backend adapter에서 rule-based와 ML analyzer를 env flag로 전환할 수 있다.
- 실패 시 rule-based fallback이 가능하다.

## 4. Reddit Vocabulary 전략

### 4.1 목표

Reddit vocabulary는 모델 학습용 데이터셋이 아니라, Pally가 최신 meme/slang을 더 자연스럽게 이해하고 제한적으로 사용할 수 있도록 만드는 controlled vocabulary다.

```text
Reddit API source item
→ Meme Candidate Extractor
→ Normalize
→ Meaning/Context/Safety/Confidence
→ Human or policy approval
→ Active MemeTerm
→ Pally prompt context
```

### 4.2 Reddit 접근 원칙

2026-07-25 기준으로 공식 문서를 확인했다.

- Reddit Data API Wiki는 Data API 사용 시 Developer Terms와 Data API Terms를 확인하라고 안내한다.
- Reddit Data API Terms는 2026-07-20 개정본이며, OAuth identity를 사용해야 하고 API limit을 우회하면 안 된다는 제한을 포함한다.
- User Content를 ML/AI 모델 학습에 사용하는 것은 별도 권리자 허용 없이 금지될 수 있으므로, 이 계획에서는 Reddit 원문을 ML 학습에 사용하지 않는다.

참고:

- Reddit Data API Wiki: https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
- Reddit Data API Terms: https://redditinc.com/policies/data-api-terms
- Reddit Developer Terms: https://redditinc.com/policies/developer-terms

구현 전에는 반드시 다시 확인한다.

- 인증 방식
- rate limit
- 허용 use case
- 저장 가능한 필드와 보관 기간
- attribution 요구사항
- 앱/프로젝트 승인 필요 여부

### 4.3 저장하지 않는 것

다음은 기본 저장 대상이 아니다.

- 작성자 이름
- 작성자 id
- 원문 전체의 장기 보관
- 댓글 전체 thread
- 개인정보 또는 개인 식별 가능 정보

필요한 경우에도 보관 기간과 삭제 절차를 먼저 정한다.

### 4.4 Extractor 출력

AI extractor는 `RedditSourceItem[]`을 받아 `MemeTermCandidate[]`를 반환한다.

```python
def extract_meme_candidates(
    sources: list[RedditSourceItem],
) -> list[MemeTermCandidate]:
    ...
```

후보 생성 시 다음을 포함한다.

- `term`: 관측된 표현
- `normalizedTerm`: canonical term
- `meaningKo`: 한국어 의미
- `usageContext`: 어떤 맥락에서 쓰이는지
- `confidence`: 0~1
- `safety`: `safe`, `review`, `blocked`

### 4.5 Safety 기준

자동 사용 가능한 term은 제한한다.

| safety | 의미 | Pally prompt 사용 |
|---|---|---|
| `safe` | 일반적이고 학습 맥락에서 안전 | 승인 후 사용 가능 |
| `review` | 의미가 애매하거나 오해 가능 | 사람 검수 전 사용 금지 |
| `blocked` | 욕설, 혐오, 성적 표현, 위험 표현 | 사용 금지 |

`confidence`가 높더라도 `review` 또는 `blocked`면 prompt에 넣지 않는다.

### 4.6 Pally prompt 반영 방식

승인된 vocabulary는 대화마다 전부 넣지 않는다. 사용자의 레벨, 대화 맥락, 최신성에 맞춰 소량만 넣는다.

```text
Available safe meme vocabulary:
- term: "lowkey"
  meaning: "은근히, 살짝"
  usage: "casual conversation, not formal writing"
  caution: "avoid in formal/business context"
```

Pally는 slang을 남발하지 않는다. 목표는 사용자의 casual 표현을 이해하고, 필요한 경우 자연스럽게 설명하는 것이다.

## 5. 8월 말까지 일정

### Week 1: 2026-07-25 ~ 2026-08-02

목표: AI contract와 실험 기반을 고정한다.

- 현재 `ai/`, `backend/main.py`, `/api/chat` 응답 shape 확인
- `AxisAnalyzer` interface 설계
- 기존 룰베이스를 `RuleBasedAxisAnalyzer`로 감싸기
- ML 학습용 dataset format 결정
- Reddit `RedditSourceItem` fixture 작성
- `MemeTermCandidate` fixture 작성
- Reddit API 접근 조건 재확인

완료 기준:

- rule-based analyzer가 새 interface 뒤에서 기존과 같은 axes를 반환한다.
- fixture 기반 extractor test가 존재한다.
- 프론트/백엔드와 맞춰야 할 contract 목록이 문서화된다.

### Week 2: 2026-08-03 ~ 2026-08-09

목표: 데이터셋과 ML baseline을 만든다.

- 기존 25개 예문 확장
- 라벨링 가이드 작성
- 최소 150~300개 발화 라벨링 목표
- train/dev/test split
- TF-IDF + multi-output regressor baseline 구현
- 룰베이스 baseline과 같은 evaluation script 작성

완료 기준:

- `python` 명령 하나로 rule-based와 ML baseline 평가가 가능하다.
- 축별 MAE와 개선/악화 케이스가 출력된다.

### Week 3: 2026-08-10 ~ 2026-08-16

목표: Reddit candidate extractor를 실제 source shape에 맞춘다.

- 백엔드가 제공할 `RedditSourceItem` shape 확정
- 허용된 실제 Reddit API 응답 1 batch 확인
- fixture에 원문 전체를 남기지 않는 sample 구조 확정
- 후보 term 추출 로직 구현
- 정규화 로직 구현
- safety filter v1 구현

완료 기준:

- 실제 또는 축약된 allowed source batch에서 `MemeTermCandidate[]`가 생성된다.
- 같은 source를 다시 처리해도 normalized term 기준 중복을 제어할 수 있다.
- `blocked` 후보가 prompt context로 들어가지 않는다.

### Week 4: 2026-08-17 ~ 2026-08-23

목표: AI engine 통합 후보를 만든다.

- ML analyzer를 backend adapter 뒤에 붙일 수 있게 정리
- env flag 또는 config로 `rule`, `ml`, `hybrid` 선택 가능하게 설계
- ML 실패 시 rule-based fallback
- approved `MemeTerm`을 prompt context로 변환하는 함수 구현
- Pally reply/feedback 품질 regression fixture 작성
- STT/TTS latency 측정 script 정리

완료 기준:

- `/api/chat` contract를 깨지 않고 analyzer만 교체 가능하다.
- approved vocabulary가 prompt context에 제한적으로 들어간다.
- demo case에서 기존보다 나빠지는 회귀가 기록된다.

### Week 5: 2026-08-24 ~ 2026-08-31

목표: 안정화와 최종 선택을 한다.

- rule-based vs ML vs hybrid 결과 비교
- 최종 default analyzer 결정
- Reddit vocabulary snapshot 생성
- safety false positive/false negative 점검
- STT/TTS 품질 개선 사항 정리
- 8월 말 AI 파트 결과 보고서 작성

완료 기준:

- default analyzer와 fallback analyzer가 결정된다.
- evaluation 결과가 재현 가능하다.
- Reddit vocabulary는 approved term만 Pally prompt에 들어간다.
- 프론트/백엔드 contract 변경 없이 통합 가능한 상태다.

## 6. 산출물

### 코드 산출물

- `ai/analyzers/` 또는 동등한 analyzer abstraction
- `RuleBasedAxisAnalyzer`
- `MLAxisAnalyzer` baseline
- evaluation script
- labeled dataset 또는 dataset fixture
- Reddit meme candidate extractor
- safety filter
- prompt context builder
- contract tests

### 문서 산출물

- ML 라벨링 가이드
- evaluation 결과 요약
- Reddit 접근 조건 확인 메모
- vocabulary safety 기준
- AI/BE contract 메모
- 8월 말 결과 보고서

## 7. Definition of Done

8월 말 완료는 다음 조건을 모두 만족해야 한다.

- `/api/chat`의 프론트엔드 응답 shape가 깨지지 않는다.
- axes와 character는 기존 0~100 의미를 유지한다.
- rule-based analyzer를 fallback으로 유지한다.
- ML analyzer의 성능과 한계가 숫자로 정리되어 있다.
- Reddit source에서 meme/slang 후보를 추출할 수 있다.
- Reddit 원문을 ML 학습에 사용하지 않는다.
- 개인정보와 원문 전체를 필요 이상 저장하지 않는다.
- safe/approved term만 Pally prompt에 들어간다.
- fixture와 CLI/test로 백엔드/프론트엔드 없이 AI 결과를 재현할 수 있다.

## 8. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| ML baseline이 룰베이스보다 나쁨 | hybrid 또는 rule-based fallback 유지 |
| 라벨 데이터가 부족함 | demo case 중심 라벨을 먼저 늘리고 synthetic은 evaluation 보강에만 사용 |
| Reddit 접근 승인이 지연됨 | fake source fixture로 extractor 개발, 실제 수집 완료로 처리하지 않음 |
| Reddit terms 변경 | 구현 전 공식 문서 재확인, use case가 애매하면 수집 중단 |
| slang safety 오탐/미탐 | `review` 기본값을 보수적으로 사용하고 승인 전 prompt 사용 금지 |
| STT/TTS latency 증가 | 측정 script로 provider 단계별 latency를 분리해 기록 |

## 9. 다음 액션

1. 현재 `/api/chat` response와 `ai/analyzer.py`, `ai/matrix_engine.py`의 실제 출력 shape를 다시 확인한다.
2. `AxisAnalyzer` interface와 evaluation fixture를 먼저 만든다.
3. Reddit source fixture와 `MemeTermCandidate` extractor skeleton을 만든다.
4. Week 2 전에 라벨링 가이드와 초기 dataset format을 동결한다.


## 10. Week 1 실행 기록

**실행일:** 2026-07-25

### 10.1 7/19 팀 조율 문서 확인 결과

7/19 문서 기준으로 AI 파트의 작업 경계는 다음처럼 확인했다.

- AI contract, prompt, structured output, evaluation은 AI 담당자가 gatekeeper다.
- Reddit 데이터 수집과 접근 정책은 백엔드가 담당한다.
- Reddit meme/slang 후보 추출, 정규화, 안전성, 승인 기준은 AI가 담당한다.
- AI는 Supabase에 직접 접근하지 않고 결과만 반환한다.
- 백엔드가 내려가 있거나 Supabase가 준비되지 않아도 AI는 fixture로 독립 검증한다.

현재 Railway trial 만료로 배포 백엔드가 내려가 있어 STT/TTS 배포 환경 테스트는 보류한다. 이 보류는 AI 엔진 로컬 작업의 blocker가 아니다.

### 10.2 완료한 작업

- `ai/contracts.py` 추가
  - `AxisResult`
  - `RedditSourceItem`
  - `MemeTermCandidate`
  - `MemeTerm`
- `ai/analyzers.py` 추가
  - `AxisAnalyzer` interface
  - `RuleBasedAxisAnalyzer`
  - Week 2용 `MLAxisAnalyzer` placeholder
  - `PALLY_AXIS_ANALYZER` 기반 analyzer 선택 함수
- `ai/reddit_vocabulary.py` 추가
  - Reddit source fixture를 받아 meme/slang candidate를 만드는 extractor skeleton
  - `safe`, `review`, `blocked` safety 구분
  - `safe` term만 prompt vocabulary로 변환하는 함수
- `data/fixtures/reddit_sources_week1.json` 추가
- `data/fixtures/meme_term_candidates_week1.json` 추가
- `tests/test_ai_week1_contracts.py` 추가
  - 기존 `analyze_utterance()`와 `RuleBasedAxisAnalyzer` 출력 일치 검증
  - axes와 character의 0~100 contract 검증
  - Reddit fixture -> `MemeTermCandidate[]` 변환 검증
  - `review` term이 prompt vocabulary에 들어가지 않는지 검증

### 10.3 검증 결과

```bash
python tests/test_ai_week1_contracts.py
# Week 1 AI contract checks passed.

python tests/test_matrix.py
# 기존 CHARACTER MATRIX 데모 정상 실행

python -m compileall ai tests
# 컴파일 통과
```

### 10.4 보류한 작업

- STT/TTS 배포 endpoint 실검증
  - 사유: Railway trial expired로 백엔드 서비스가 paused 상태다.
  - 재개 조건: 백엔드 담당자가 Railway 업그레이드 또는 다른 배포 URL을 제공한 뒤 `/api/health`, `/api/stt`, `/api/chat`, `/api/tts` 순서로 확인한다.
- Reddit 실제 API 호출
  - 사유: 7/19 문서상 Reddit 접근 승인·credential·collector는 백엔드 담당 영역이다.
  - 현재는 fake source fixture로 extractor contract만 검증한다.

### 10.5 Week 2 진입 조건

- 라벨링 가이드 작성
- 기존 25개 예문을 기준으로 dataset format 동결
- rule-based baseline evaluation script 작성
- ML baseline 후보를 `MLAxisAnalyzer` 뒤에 연결




## 11. Week 2 실행 기록

**실행일:** 2026-07-31

### 11.1 7/19 팀 조율 문서 확인 결과

7/19 문서 기준으로 이번 주 작업도 AI 내부에서 독립적으로 진행했다.

- 프론트엔드 contract는 `axes`, `character`, `feedback`, `tts_audio` 형태를 유지한다.
- 백엔드는 AI analyzer 내부 구현을 몰라도 되며, `/api/chat` 경계만 유지하면 된다.
- Reddit 실제 수집, credential, collector, 저장은 백엔드 담당이다.
- AI는 Supabase에 직접 접근하지 않고 fixture와 local test로 검증한다.

### 11.2 완료한 작업

- `ai/ml_baseline.py` 추가
  - dependency-free TF-IDF + weighted k-NN axis regressor 구현
  - 회화 중심 `data/axis_dataset_week2.jsonl`을 우선 학습 데이터로 로드하고, 파일이 없을 때만 기존 legacy dataset으로 fallback
- `ai/analyzers.py` 업데이트
  - `MLAxisAnalyzer` placeholder를 실제 Week 2 baseline으로 연결
  - `get_axis_analyzer("ml")`로 ML analyzer 선택 가능
- `ai/evaluate_axis_analyzers.py` 추가
  - rule-based baseline과 ML baseline을 같은 dataset에서 평가
  - 축별 MAE, Spearman correlation, worst case, 평균 MAE delta 출력
- `docs/ai-labeling-guide.md` 추가
  - 5축 라벨링 기준, 점수 구간, JSONL format, 주의사항 정리
  - Reddit 원문을 ML 학습 데이터로 쓰지 않는 원칙 명시
- `data/axis_dataset_week2.jsonl` 추가
  - Week 2용 JSONL dataset seed를 회화 중심 30개로 재작성
  - `train`, `dev`, `test` split 포함
- `tests/test_ai_week2_ml_baseline.py` 추가
  - ML analyzer가 기존 0~100 axes contract를 지키는지 검증
  - ML baseline이 training neighbor를 사용해 예측하는지 검증
  - analyzer factory에서 `ml` 선택이 되는지 검증

### 11.3 검증 결과

```bash
$env:PYTHONDONTWRITEBYTECODE='1'; python tests/test_ai_week1_contracts.py
# Week 1 AI contract checks passed.

$env:PYTHONDONTWRITEBYTECODE='1'; python tests/test_ai_week2_ml_baseline.py
# Week 2 ML baseline checks passed.

$env:PYTHONDONTWRITEBYTECODE='1'; python tests/test_matrix.py
# 기존 CHARACTER MATRIX 데모 정상 실행

$env:PYTHONDONTWRITEBYTECODE='1'; python ai/evaluate_axis_analyzers.py
# rule_avg_mae: 16.18
# ml_avg_mae  : 13.81
# delta       : -2.37
```

`data/axis_dataset_week2.jsonl`은 JSONL로 파싱 가능하며 현재 30개 row와 `train/dev/test` split을 가진다. 모든 row는 Pally 음성 회화에서 사용자가 실제로 말할 법한 발화로 제한한다.

### 11.4 평가 판단

회화 중심 dataset 기준으로 현재 ML baseline은 rule-based baseline보다 평균 MAE가 낮다.

- rule-based average MAE: `16.18`
- ML baseline average MAE: `13.81`
- delta: `-2.37`

다만 seed가 아직 30개라 Week 2 결과만으로는 ML analyzer를 default로 전환하지 않는다. 현재 권장 상태는 다음과 같다.

```text
PALLY_AXIS_ANALYZER=rule  # default 유지
PALLY_AXIS_ANALYZER=ml    # 실험/평가용
```

ML baseline은 아직 측정 가능한 후보일 뿐이며, rule-based analyzer는 계속 baseline/fallback으로 유지한다.

### 11.5 보류한 작업

- STT/TTS 배포 endpoint 실검증
  - 사유: Railway trial expired로 배포 백엔드가 paused 상태다.
- Reddit 실제 API 호출
  - 사유: 7/19 문서상 Reddit 접근 승인, credential, collector는 백엔드 담당 영역이다.
- 150~300개 전체 라벨링 완료
  - 사유: Week 2에서는 format과 baseline을 먼저 고정했다. 이후에도 learner-style spoken utterance를 중심으로 추가 라벨링해야 한다.

### 11.6 Week 3 진입 조건

- `RedditSourceItem` 실제 source shape를 백엔드와 재확인
- Reddit fixture를 더 실제 응답 shape에 가깝게 확장
- `MemeTermCandidate` 정규화와 safety rule 보강
- ML dataset row를 learner-style 중심으로 계속 확장

## 12. PM 정책 문서에서 AI 파트가 계속 참고할 사항

**기준 문서:** Pally PM 정책 확정 문서 v1.0, 2026-07-25

PM 정책 문서는 주로 Achievements, Daily Task, Streak, 결제 정책을 다룬다. AI가 직접 구현할 영역은 아니지만, AI 출력값과 사용자 발화 데이터가 일부 정책 계산에 사용되므로 아래 사항은 앞으로 계속 유지해야 한다.

### 12.1 AI 출력 contract 유지

Daily Task와 Streak 일부 항목은 AI 분석 결과 또는 사용자 발화 텍스트를 기준으로 계산될 수 있다. 따라서 AI analyzer가 rule-based에서 ML로 바뀌더라도 아래 contract는 유지한다.

- `axes.Formality`
- `axes.Energy`
- `axes.Intimacy`
- `axes.Humor`
- `axes.Curiosity`
- 사용자 발화 원문 또는 transcript
- Feedback 화면에서 사용할 `feedback: FeedbackItem[]`

특히 `Intimacy`는 PM 정책의 Daily Task E4에서 어제 대비 상승 여부를 판단하는 데 쓰일 수 있으므로, ML 전환 후에도 축 의미를 바꾸지 않는다.

### 12.2 Achievements 계산에 영향을 주는 데이터

아래 Daily Task는 AI 결과 또는 발화 데이터와 연결된다.

| Task | AI와 관련된 데이터 |
|---|---|
| B1-B3: 대화 중 질문하기 | 사용자 발화의 `?`, 질문 표현, transcript |
| B4-B6: 긴 문장 말하기 | 사용자 발화 단어 수 |
| E4: Intimacy 축이 어제보다 상승하기 | 세션/일자별 `Intimacy` snapshot |
| E5: 지난 세션보다 더 긴 문장으로 말하기 | 세션별 평균 발화 단어 수 |

AI는 위 task 계산을 직접 구현하지 않는다. 다만 백엔드가 계산할 수 있도록 일관된 `axes`와 transcript를 반환해야 한다.

### 12.3 axis_snapshots 저장 기준은 백엔드와 합의 필요

PM 정책에는 `axis_snapshots`라는 측정 데이터가 등장한다. 현재 AI 작업에서는 DB를 직접 다루지 않으므로, 실제 저장 방식은 백엔드가 결정해야 한다.

AI 관점에서 필요한 합의는 다음이다.

- turn마다 raw axes를 저장할지
- EMA 적용 후 axes만 저장할지
- session-end 기준 최종 axes snapshot을 저장할지
- Daily Task E4는 어떤 기준의 `Intimacy`를 비교할지

AI 기본 입장은 다음과 같다.

```text
raw_axes: 현재 발화 자체의 5축
smoothed_axes: EMA 적용 후 세션 누적 5축
character: smoothed_axes 기반 Pally 파라미터
```

Daily Task와 Streak 계산에는 `smoothed_axes` 또는 session-end snapshot을 쓰는 것이 더 안정적이다.

### 12.4 Quota와 결제 정책은 백엔드에서 AI 호출 전에 처리

PM 정책상 무료 사용자는 1일 20턴, Pro 사용자는 무제한이다. 이 정책은 AI가 구현하지 않는다.

백엔드는 quota 초과 사용자의 요청을 AI/STT/TTS 호출 전에 차단해야 한다. 그래야 불필요한 provider 비용이 발생하지 않는다.

AI 파트는 다음만 보장한다.

- quota 여부를 추측하지 않는다.
- 백엔드가 호출한 요청에 대해서만 STT/chat/TTS 결과를 생성한다.
- quota 초과 UX나 결제 상태는 AI contract에 임의로 추가하지 않는다.

### 12.5 AI가 직접 맡지 않는 영역

아래는 PM 정책상 중요하지만 AI 담당 구현 범위가 아니다.

- Daily Task 3개 선택 로직
- KST 기준 날짜 계산
- Streak 증가/초기화
- Streak Freeze
- 무료/Pro 사용자 구분
- RevenueCat, StoreKit2, Kakao Pay Billing
- 결제 성공/실패 처리
- 화면 진입 로그 기반 task 완료 판정

필요한 경우 AI는 contract와 데이터 의미를 설명하고, 구현은 백엔드/프론트엔드 담당자와 나눠 진행한다.
## 13. Conversation-First 라벨링 보정 기록

**실행일:** 2026-07-31

사용자 피드백에 따라 Week 2 ML dataset 방향을 다시 잡았다. Pally는 회화 앱이므로, ML 라벨링 기준은 글쓰기/비즈니스/학술 문장이 아니라 사용자가 실제 음성 대화 중 말할 법한 발화여야 한다.

### 13.1 앞으로 유지할 원칙

- Pally의 5축 분석은 spoken conversation utterance를 기준으로 한다.
- 높은 `Formality`는 논문체나 공문체가 아니라, 예의 있고 조심스러운 구어체를 뜻한다.
- `I would like to formally inquire...`, `Furthermore...`, `Please be advised...` 같은 문장은 core training seed로 사용하지 않는다.
- 학습 데이터에는 인사, 설명 요청, 다시 말해달라는 요청, 역할극, 교정 요청, 피드백 반응, 실수/머뭇거림, 자연스러운 slang 질문을 우선 넣는다.
- Reddit vocabulary도 실제 회화에서 말하거나 이해할 가능성이 있는 표현만 후보로 본다.
- learner error는 버릴 데이터가 아니라 Pally가 다뤄야 하는 핵심 입력이다.

### 13.2 수정한 작업

- `docs/ai-labeling-guide.md`에 Conversation First 원칙을 추가했다.
- Formality high score 설명에서 academic/businesslike 기준을 제거하고 polite spoken English로 재정의했다.
- `data/axis_dataset_week2.jsonl`을 회화 중심 30개 seed로 재작성했다.
- legacy demo용 `data/dataset.py`도 같은 회화 중심 seed로 맞췄다.
- `ai/analyzer.py`의 formal keyword를 학술/공문체가 아니라 polite spoken English 중심으로 조정했다.
- `ai/ml_baseline.py`가 Week 2 JSONL dataset을 우선 로드하도록 수정했다.
- 기존 legacy dataset은 JSONL이 없을 때만 fallback으로 사용한다.

### 13.3 이유

기존 seed에는 회화 앱 사용자가 실제로 말하지 않을 법한 문장이 섞여 있었다. 이런 데이터로 모델을 평가하면 Pally가 실제 사용자 발화보다 격식 있는 글쓰기 패턴에 끌릴 수 있다. 그래서 ML 전환의 첫 기준을 “잘 쓴 영어 문장”이 아니라 “실제 대화에서 들어올 입력”으로 바꿨다.

### 13.4 팀 전달 포인트

- 프론트엔드: 응답 contract는 그대로 유지된다. `axes`, `character`, `feedback` 표시 방식은 바뀌지 않는다.
- 백엔드: `/api/chat` 경계는 그대로 유지된다. AI 내부 dataset과 analyzer 실험만 회화 중심으로 바뀐다.
- 공통: 앞으로 테스트 문장과 fixture를 만들 때 글쓰기 문장보다 음성 대화 문장을 우선 사용한다.
