# Pally 5축 커뮤니케이션 스타일 분석기 연구 기록

> 목적: 이 문서는 Pally의 5축 분석기와 실제 발화 데이터셋 구축 과정을
> 논문 작성 및 다음 작업의 기준점으로 남기는 단일 운영 기록이다.
>
> 마지막 갱신: 2026-09-06
> 현재 단계: 실제 발화 추출 및 블라인드 사람 검수 준비 완료, gold 검수 대기

## 1. 연구 문제와 범위

Pally는 영어 학습자가 한 발화를 다음 5개 축의 `0~100` 점수로 측정한다.

| 축 | 낮은 점수 | 높은 점수 |
|---|---|---|
| Formality | 캐주얼하고 비격식적 | 공손하고 격식적 |
| Energy | 차분하고 절제됨 | 강조, 흥분, 활기 |
| Intimacy | 거리감 있고 과업 중심 | 개인적, 따뜻함, 친밀함 |
| Humor | 유머 없음 | 농담, 장난, 유희성 |
| Curiosity | 탐색/질문 없음 | 질문, 확인, 설명 요청, 탐색 |

이 연구의 현재 범위는 **발화에서 커뮤니케이션 상태를 측정하는 모델**이다.
사용자와 Pally가 얼마나 비슷하게 말해야 학습 효과가 좋은지는 별도의
adaptation-policy 연구 문제이며, 현재 모델의 정답 라벨이나 기본 동작으로
가정하지 않는다.

## 2. 전체 진행 흐름

```text
공개 실제 발화 코퍼스
  -> 태그/비발화 정제 및 provenance 보존
  -> 저정보 발화 제거와 다양성 표본화
  -> AI 초안 라벨 실험 데이터 (모델 탐색 전용)
  -> source-group 분리 후보 풀
  -> 블라인드 사람 검수
  -> 고정 gold에서 rule / ML / hybrid 비교
  -> 기준 충족 시에만 ML 단독 전환
```

### 완료한 작업

- NICT JLE의 1,281개 실제 일본인 영어 학습자 인터뷰에서 학습자(B) 발화만
  추출했다.
- CHiME-6, HCRC Map Task, Taskmaster-1 WoZ, AMI의 실제 대화 발화를 추가했다.
- 발화 텍스트뿐 아니라 대화/화자/시간 provenance와 인접 턴 문맥을 보존했다.
- AI 초안 라벨 데이터로 rule, TF-IDF k-NN ML, hybrid를 비교했다.
- 누수 없는 gold/train 후보 풀을 만들고, 사람 검수량을 줄이기 위한 active
  selection과 gold 계층화 무작위 표본화를 구현했다.
- 블라인드 검수 CSV에서 출처, 샘플링 버킷, AI 초안, 모델 점수를 숨겼다.

### 아직 하지 않은 작업

- gold 200개에 대한 실제 독립 사람 검수
- E/C 120개에 대한 사람 검수
- 사람 gold 기준의 ML 단독 전환 판정
- Curiosity 문맥 모델, Energy 음성 특징 모델, adaptation policy의 효과 검증

## 3. 실제 발화 데이터셋

### 3.1 현재 원본 규모

| 코퍼스 | 실제 발화 수 | 역할 |
|---|---:|---|
| NICT JLE | 139,772 | 실제 영어 학습자 구술 인터뷰 |
| CHiME-6 | 87,539 | 다자간 일상 대화 |
| HCRC Map Task | 20,686 | 과업 지향 대화 |
| Taskmaster-1 WoZ USER | 60,347 | 사용자 발화 중심 과업 대화 |
| AMI | 98,475 | 다자간 회의 대화 |
| **합계** | **406,819** | 원본 실제 발화 |

원본 발화 파일은 모두 `data/fixtures/*_utterances.jsonl`에 저장되어 있다.
정확한 파일 경로, 공식 URL, 라이선스 상태는
[`data/fixtures/real_speech_corpus_manifest.json`](../data/fixtures/real_speech_corpus_manifest.json)에 기록한다.

### 3.2 라이선스 및 사용 경계

| 코퍼스 | 기록된 라이선스 상태 | 현재 사용 원칙 |
|---|---|---|
| NICT JLE | CC BY-SA 3.0 | 상용/공개 모델 반영 전 호환성 재확인 필요 |
| CHiME-6 | CC BY-SA 4.0 | 귀속 및 ShareAlike 의무 검토 필요 |
| Taskmaster-1 WoZ | CC BY 4.0 | 귀속 조건 확인 후 사용 가능 후보 |
| AMI | CC BY 4.0 | 귀속 조건 확인 후 사용 가능 후보 |
| HCRC Map Task | CC BY 4.0 페이지와 로컬 CC BY-NC-SA 2.5 기록 충돌 | 권리자 확인 전 상용 학습/배포 금지 |

라이선스는 모델 성능과 별개인 별도 gate다. 이 기록은 법률 자문이 아니며,
배포 전 원문 라이선스와 기관 확인을 다시 해야 한다.

## 4. 추출 및 정제 방법

### 4.1 NICT JLE

스크립트: `scripts/extract_nict_jle.py`

- XML 유사 태그에서 학습자 `<B>...</B>` 턴만 추출한다.
- filler, 반복, 자기수정, 문법 오류 태그를 텍스트로 정리하되 실제 학습자
  발화의 특징은 가능한 유지한다.
- 문장 분할 뒤 `and`, `but`, `at`, `on` 같은 의존적 시작어로 시작하는 7단어
  이하 조각은 직전 발화에 병합한다.
- `mm`, `mmm`, `um`, `uhm`, `erm` 등 3개 이상 연속 filler는 하나로 줄이고,
  filler 비율이 40%를 초과하는 발화는 제외한다. `hmm`은 의미 있는 감탄사일
  수 있어 filler로 제거하지 않는다.
- 각 행에 learner interview 파일을 `source_group`과 `speaker_id`로 보존한다.

### 4.2 공통 provenance 및 문맥

모든 추출기는 가능한 경우 다음 필드를 보존한다.

```text
source, source_group, source_record_id
conversation_id, speaker 또는 speaker_id, turn_index
previous_turn, previous_turn_speaker
utterance
next_turn, next_turn_speaker
시간 정보 또는 audio/reference metadata
```

이 구조는 현재 모델이 문맥 없이 학습되더라도, 후속 Curiosity 문맥 ablation과
Energy의 prosody 확장을 위해 원본 대화 구조를 잃지 않도록 한다.

## 5. 라벨 데이터의 상태

### 5.1 AI 초안 실험 데이터

파일: `data/fixtures/axis_dataset_combined_real_speech_experimental.jsonl`

총 **3,137개**이며, 구성은 기존 seed 338개, NICT accepted-draft 600개,
CHiME-6/HCRC/Taskmaster/AMI에서 추출한 AI 초안 2,200개다.

이 데이터는 모델 구조를 비교하는 실험용이다. AI가 만든 점수 또는 AI 초안을
승인한 값이 포함되어 있으므로, 독립적인 사람 gold 정답이나 최종 전환 근거로
사용하지 않는다. 특히 과거 파일명에 `human`이 들어간
`nict_jle_labeled_human_600.jsonl`은 독립 블라인드 사람 재검수가 아니라
accepted draft pass다.

### 5.2 사람 검수 후보 풀

기존 3,137개와 정규화 텍스트가 겹치지 않도록 NICT, AMI, Taskmaster에서
후보를 추출했다. source group을 먼저 gold 또는 train으로 나눈 뒤 샘플링했기
때문에 인터뷰/회의/대화 그룹이 두 영역에 동시에 들어가지 않는다.

| 단계 | 파일 | 수 | 목적 |
|---|---|---:|---|
| Gold 후보 reservoir | `ml_transition_gold_candidates_600.jsonl` | 600 | 최종 평가 후보 |
| Train 후보 reservoir | `ml_transition_train_candidates_1200.jsonl` | 1,200 | active-learning 후보 |
| Gold 계층화 표본 | `ml_transition_gold_stratified_candidates_200.jsonl` | 200 | 5축 사람 gold 검수 |
| Train active 표본 | `ml_transition_train_active_ec_candidates_120.jsonl` | 120 | Energy/Curiosity 사람 검수 |

후보 reservoir는 600 gold group과 1,200 train group이 분리되어 있고,
정규화 텍스트 중복도 없다. 최종 검수 표본도 120 train group과 161 gold group이
분리되어 있다.

### 5.3 사람 검수 현재 상태

| 파일 | 축 | 상태 |
|---|---|---|
| `data/fixtures/ml_transition_gold_blind_review_200.csv` | 5축 전체 | 200 pending / 0 completed |
| `data/fixtures/ml_transition_train_active_ec_review_120.csv` | Energy, Curiosity | 120 pending / 0 completed |

gold 200은 최종 비교를 위한 고정 시험지다. 모델 학습 또는 모델 선택에 사용하면
안 된다. Train 120은 현 hybrid와 ML의 불일치가 큰 사례를 우선 선택한 부분 라벨
데이터이므로, 현 5축 완전 라벨 학습기에 바로 넣으면 안 된다.

검수 CSV는 다음만 보여 준다.

```text
review_id, utterance, previous_turn, next_turn,
적용 축의 reviewed_* 점수, reviewer_id, review_status, reviewer_notes
```

출처, 화자/그룹, focus bucket, AI 초안, 모델 점수, active-selection 이유는
검수자에게 보이지 않는다. 점수는 영어 능숙도나 문법 정확도가 아니라 그 순간의
커뮤니케이션 방식을 기준으로 기록한다.

## 6. 모델과 실험 결과

### 6.1 비교 모델

| 모델 | 설명 |
|---|---|
| Rule-based | 기존 휴리스틱 분석기 |
| ML | 1~2 word n-gram TF-IDF + weighted k-NN 회귀 |
| Hybrid | Rule과 ML의 축별 평균. ML 실패 시 rule 결과로 저하 |

세 구현은 `ai/analyzers.py`의 동일한 contract를 따르며,
`PALLY_AXIS_ANALYZER=rule|ml|hybrid`로 선택할 수 있다.

### 6.2 현재 실험 결과

AI 초안 실험 데이터 3,137개에서의 결과다. 사람 gold 결과가 아니므로 최종 성능
주장에 사용하지 않는다.

| 평가 | Rule MAE / Spearman | ML MAE / Spearman | Hybrid MAE / Spearman |
|---|---:|---:|---:|
| Leave-one-out | 10.05 / 0.30 | **7.55 / 0.44** | 7.95 / **0.45** |
| Source-group holdout | - | **7.62 / 0.45** | 7.86 / 0.45 |

해석:

- ML은 평균 절대오차(MAE)에서 가장 낮다.
- Hybrid는 leave-one-out 순위 상관(Spearman)에서 가장 높고, source holdout에서는
  ML과 동률이다.
- 특히 Energy와 Curiosity는 hybrid 우위 가능성이 남아 있어, 현 시점에 ML 단독을
  확정할 근거가 없다.

### 6.3 현재 제품 결정

현재 런타임 기본값은 **rule-based**다. `hybrid`는 다음 운영/실험 후보이고,
`ml`은 최종 목표이지만 아직 기본값이 아니다.

ML 단독 전환은 사람 검수 gold에서 아래를 모두 만족할 때만 논의한다.

1. ML 평균 MAE가 hybrid보다 `0.20`보다 크게 나쁘지 않다.
2. ML 평균 Spearman이 hybrid 이상이다.
3. 어느 한 축도 hybrid보다 Spearman이 `0.03`보다 크게 낮지 않다.
4. source group을 바꾼 holdout에서도 같은 결론이 재현된다.

## 7. 사람 검수 및 재평가 절차

### 7.1 gold 200 검수

1. `ml_transition_gold_blind_review_200.csv`에서 각 행의 5개 `reviewed_*`
   값을 `0~100` 정수로 작성한다.
2. 모든 행에 동일한 익명 `reviewer_id`를 입력한다. 예: `reviewer-01`.
3. 완료 행의 `review_status`를 `completed`로 바꾼다.
4. 최소 20%는 두 사람이 중복 검수해 축별 일치도를 계산하는 것을 권장한다.
5. 완료 CSV를 JSONL로 변환한다.

```powershell
.\.venv\Scripts\python.exe scripts\build_human_reviewed_axis_dataset.py `
  --input data\fixtures\ml_transition_gold_blind_review_200.csv `
  --candidates data\fixtures\ml_transition_gold_stratified_candidates_200.jsonl `
  --output data\fixtures\ml_transition_gold_human_200.jsonl `
  --axes all
```

### 7.2 E/C 120 검수

gold 검수 후 또는 병행하여 Energy와 Curiosity만 채운다.

```powershell
.\.venv\Scripts\python.exe scripts\build_human_reviewed_axis_dataset.py `
  --input data\fixtures\ml_transition_train_active_ec_review_120.csv `
  --candidates data\fixtures\ml_transition_train_active_ec_candidates_120.jsonl `
  --output data\fixtures\ml_transition_train_human_ec_120.jsonl `
  --axes energy-curiosity
```

그 다음 per-axis partial-label 학습을 추가해 E/C 개선 실험에만 사용한다.
Formality, Intimacy, Humor를 AI 초안으로 채워 5축 완전 라벨처럼 취급하면 안 된다.

## 8. 선행연구에서 반영한 설계 원칙

제공된 user-chatbot similarity, personality-matched educational agent,
text-personality tutor, learner-agent adaptation 연구의 검토 결과는 다음
원칙으로 반영했다.

- **측정과 적응의 분리:** 5축 분석기는 사용자 상태를 측정한다. Pally의 말투를
  맞추는 정책은 별도의 outcome 실험으로 검증한다.
- **완전 미러링을 기본값으로 두지 않음:** similarity가 항상 학습 성과를 높인다는
  전제를 두지 않고, fixed / partial mirror / complementary 조건을 비교한다.
- **baseline과 current state 분리:** `ai/style_state.py`는 장기 baseline과 최근
  current state, 스타일 거리를 계산한다. 아직 제품 응답 정책에 연결하지 않았다.
- **Curiosity는 문맥 ablation 대상:** 현재 발화 단독과 previous turn + current
  turn을 비교할 수 있도록 대화 문맥을 보존한다.
- **Energy의 text-only 한계 기록:** Energy가 사람 gold에서 계속 약하면 데이터
  부족으로 단정하지 않고 speech rate, pitch, intensity, pause, laughter 등
  음성 특징의 필요성을 별도로 검증한다.
- **Big Five와 5축을 혼동하지 않음:** Big Five는 외부 construct validation
  참고값일 뿐 Pally 5축의 정답 라벨이나 직접 대응 축이 아니다.

상세 계획은 [`docs/communication-style-adaptation-plan.md`](communication-style-adaptation-plan.md)에 있다.

## 9. 논문 작성 시 사용할 근거와 한계

### 사용할 수 있는 근거

- 실제 발화 406,819개를 확보하고 provenance를 보존한 추출 파이프라인
- NICT JLE의 실제 영어 학습자 구술 인터뷰 데이터
- source/speaker/conversation group 기반 누수 방지 분할
- AI 초안 데이터에서의 rule, ML, hybrid 비교 수치
- 사람 검수 전에 샘플링 정보와 초안 정보를 숨긴 블라인드 검수 설계
- 문맥/음성/적응 정책을 구분한 단계적 연구 설계

### 반드시 제한점으로 쓸 내용

- 현재 3,137개 실험 라벨은 독립적인 사람 gold가 아니다.
- gold 200 사람 검수 전의 ML/hybrid 수치는 내부 모델 탐색 근거이지 최종 성능
  또는 교육 효과의 증거가 아니다.
- HCRC는 라이선스 충돌이 해결되기 전 상용 데이터로 사용할 수 없다.
- Pally의 스타일 적응이 학습 성과를 높인다는 주장은 아직 검증하지 않았다.
- text-only Energy와 utterance-only Curiosity에는 관측 가능한 정보 한계가 있다.

## 10. 다음 작업 체크리스트

- [ ] Gold 200개 5축 사람 검수 완료
- [ ] Gold 중복 검수 표본의 일치도 산출
- [ ] Gold JSONL 변환 및 rule / ML / hybrid 재평가
- [ ] ML 단독 전환 gate 판정
- [ ] E/C 120개 사람 검수 완료
- [ ] E/C partial-label 학습 및 Energy/Curiosity 개선 실험
- [ ] char n-gram, 문장 형태, sentiment/arousal proxy feature ablation
- [ ] current utterance 대 context Curiosity ablation
- [ ] 원본 audio 사용 가능 코퍼스의 Energy prosody feasibility 및 라이선스 검토
- [ ] interaction outcome 데이터로 fixed / partial mirror / complementary 정책 비교

## 11. 핵심 파일 지도

| 용도 | 파일 |
|---|---|
| NICT 추출 | `scripts/extract_nict_jle.py` |
| 외부 코퍼스 추출 | `scripts/extract_chime6.py`, `extract_hcrc_maptask.py`, `extract_taskmaster1_woz.py`, `extract_ami.py` |
| 문맥 부착 공통 로직 | `scripts/conversation_context.py` |
| 후보 reservoir 생성 | `scripts/sample_ml_transition_candidates.py` |
| 120/200 annotation 선택 | `scripts/select_ml_transition_annotation_sets.py` |
| 블라인드 CSV export | `scripts/export_axis_review_csv.py` |
| 완료 CSV -> JSONL | `scripts/build_human_reviewed_axis_dataset.py` |
| 분석기 구현 | `ai/analyzers.py`, `ai/ml_baseline.py` |
| baseline/current state 도구 | `ai/style_state.py` |
| 실험 평가 | `ai/evaluate_axis_analyzers.py` |
| 데이터/라이선스 manifest | `data/fixtures/real_speech_corpus_manifest.json` |

## 12. 관련 세부 문서

- [`docs/ml-transition-plan.md`](ml-transition-plan.md): ML 전환 gate와 검수 파일 사용법
- [`docs/communication-style-adaptation-plan.md`](communication-style-adaptation-plan.md): 문맥, 음성, adaptation policy 후속 연구
- [`docs/real-speech-corpus-benchmark.md`](real-speech-corpus-benchmark.md): 외부 코퍼스 추출과 AI 초안 실험
- [`docs/nict-jle-labeling-evaluation.md`](nict-jle-labeling-evaluation.md): NICT 초안 라벨링 이력
- [`data/fixtures/real_speech_corpus_manifest.json`](../data/fixtures/real_speech_corpus_manifest.json): 코퍼스별 공식 URL 및 라이선스 기록
