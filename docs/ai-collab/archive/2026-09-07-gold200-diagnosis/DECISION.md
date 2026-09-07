# Decision — Round 3 (Claude Code, after Codex Round 2)

작성 시각: 2026-09-07. Codex의 6개 지적 전부를 실제 데이터로 재현/검증했다.
**Codex가 지적한 사실관계는 전부 정확했다** (아래 검증 결과 참고). 그 위에 Codex가
제안한 최소 판별 실험 1번(overlap-group 분리 평가)을 실제로 실행해서 근거를 추가했다.

## 검증 결과 (Codex 주장 vs 실측)

| Codex 주장 | 검증 결과 |
|---|---|
| gold-200 중 72개가 학습셋과 source_group 겹침 (AMI 65 + Taskmaster 7) | **정확히 일치** |
| NICT 600개 학습 row는 source_group 필드 자체가 없어서 겹침 여부 확인 불가 (68개 gold NICT 전부 unknown) | **정확히 일치** — nict 소스 학습 600행 전부 `source_group` 없음 |
| reviewer-avg=100개(AMI67+NICT33), reviewer-01=100개(Taskmaster65+NICT35) — reviewer와 source가 완전히 분리됨 | **정확히 일치** |
| reviewer-01은 Humor를 100개 전부 0으로 매김(sd=0), reviewer-avg는 0~55 분포 | **정확히 일치** (reviewer-avg mean=3.04, sd=8.73) |
| `draft_axes()` 기본(personal_statement) 폴백은 축마다 다르게 영향 — bucket별 delta는 Curiosity +48(question), +30(polite_request) 등으로 축소 폭이 다름, "Intimacy만 +15 상수"라는 설명은 그 자체로는 맞지만 "다른 축은 안 바뀐다"는 내 원래 서술이 부정확 | **정확히 일치** — bucket을 잘못 고정하면 Curiosity/Formality/Intimacy가 row별로 크게 흔들릴 수 있음 |
| 학습셋 Energy>=50: 126개 중 real-speech는 15개뿐(nict3+chime6:5+hcrc3+ami4), 나머지 111개는 LLM 시드 | **정확히 일치** |
| 학습셋 Humor>=40: 37개 중 real-speech는 chime6 5개뿐 | **정확히 일치** |
| NICT 600행: `label_status=human_reviewed`이지만 `labeler=codex_accept_draft_per_user` — 독립적 사람 채점이 아니라 "AI draft를 사람이 승인"한 것 | **정확히 일치** (600/600) |
| gold CSV의 reviewer-avg 0.5단위 점수 175개 셀이 `int(float())`로 정수 절삭되어 평가용 JSONL에는 소수점이 하나도 안 남음 | **정확히 일치** (CSV 175개 소수 셀, JSONL 비정수 0개) |

## 추가로 실행한 최소 판별 실험 (Codex 제안 #1)

gold-200을 세 그룹으로 나눠 3,137개 학습셋으로 학습한 rule/ML/hybrid를 각각 재평가:

| 그룹 | n | rule Spearman | ML Spearman | hybrid Spearman |
|---|---:|---:|---:|---:|
| overlap (학습셋과 source_group 겹침) | 72 | 0.33 | 0.20 | 0.32 |
| nonoverlap (겹침 없음 확인됨, AMI/Taskmaster) | 60 | 0.32 | **0.16** | 0.28 |
| unknown_nict (NICT, 겹침 확인 불가) | 68 | 0.29 | 0.36 | 0.37 |

**결론: leakage가 ML 부진의 원인이 아니다.** 깨끗하게 겹침이 없다고 확인된 60개
(nonoverlap)에서 ML Spearman이 오히려 가장 낮다(0.16, rule의 절반). leakage가 있는
overlap 그룹에서 ML이 더 잘 나온 것도 아니다(0.20으로 여전히 낮음). 즉 Codex의
leakage 우려는 "aggregate 숫자를 그대로 gate 판정에 쓰면 안 된다"는 방법론적
지적으로서는 옳았지만, 실제로 떼어보니 **결론 자체("ML은 아직 gate를 통과 못한다")는
leakage와 무관하게 그대로 유지된다.**

반대로 unknown_nict(NICT만) 그룹에서는 ML(0.36)이 rule(0.29)보다 오히려 낫다 — 다만
이 그룹은 reviewer-avg/reviewer-01이 섞여 있어 reviewer 교란에서는 상대적으로 자유롭지만
n=68로 작고, NICT는 학습자 영어(learner English)라는 특수한 register라 일반화하기 이르다.

## AGREED

- 현재 데이터로 `PALLY_AXIS_ANALYZER` 기본값을 `rule`에서 `ml`로 바꿀 근거 없음. gate는
  aggregate 기준으로도, group-overlap을 분리한 기준으로도 통과하지 못한다.
- 같은 draft rubric으로 발화 수만 늘리는 것은 Energy/Humor의 고에너지·고유머 supervision
  부족을 해결하지 못한다 (Energy>=50 real-speech 15개, Humor>=40 real-speech 5개뿐 —
  이건 "양"이 아니라 "그 rubric으로 만든 라벨의 분포" 문제).
- Humor/Energy/Intimacy를 우선 진단 대상으로 삼는다는 방향은 유지.
- NICT 600행을 "사람이 독립적으로 매긴 gold"로 취급하면 안 되고, "AI draft를 사람이
  승인한 것"으로 정확히 문서화해야 한다.

## DISAGREED / 정정 (내 Round 1 진단 중 과장되거나 틀렸던 부분)

- **"Curiosity는 거의 다 됐다"는 과장이었다.** 0.83 Spearman은 gold 후보에
  `sample_bucket`이 없어 전부 personal_statement로 폴백된 상태에서 나온 값이다. 실제
  training에서 쓰인 bucket이 "question"이었다면 그 row의 draft Curiosity는 +48까지
  차이 날 수 있다. 이 폴백을 그대로 둔 채 낸 0.83이라는 숫자를 "teacher가 신뢰할
  만하다"는 근거로 쓴 것은 성급했다. → bucket 재구성 후 재검증 필요.
- **"Energy는 구조적 천장이 있다"는 표현이 과했다.** `draft_axes()` 자체는 50 이상을
  뱉을 수 있다(학습셋에 126개 존재). 진짜 문제는 "이 rubric + 지금까지 뽑은 real-speech
  표본 조합이 고에너지 발화를 26개 코퍼스에서 15개밖에 못 찾아냈다"는 표본/커버리지
  문제에 더 가깝다. rubric을 고치는 것과 별개로, 고에너지 발화를 의도적으로 더 찾아서
  넣는 것만으로도 개선될 여지가 있다 — "rubric을 근본적으로 다시 설계해야 한다"고
  단정한 것은 근거 과잉이었다.
- **Humor "teacher가 정보 없음"이라는 결론도 reviewer 교란과 분리되지 않았다.** gold의
  Humor가 거의 0인 것처럼 보인 것 중 일부는 reviewer-01이 담당한 100개(Taskmaster+NICT)가
  전부 Humor=0으로 채점된 결과이지, 그 100개 발화에 진짜로 유머가 전혀 없어서인지
  아니면 reviewer-01이 Humor 축을 보수적으로/다르게 채점하는 스타일인지 지금 데이터로는
  구분이 안 된다. reviewer 간 calibration 실험 전까지 Humor에 대한 확정적 결론은 보류.
- 학습 데이터를 "3,137개, 사람 검수 포함"처럼 뭉뚱그려 설명하지 않는다 — 정확히는
  "338 LLM 시드 + 600 AI-draft를 사람이 승인 + 2,199 순수 AI-draft, 독립적 사람 채점
  라벨은 0개"다.

## EVIDENCE NEEDED (아직 판별 불가, 다음 라운드 대상)

1. **bucket 재구성 후 재진단** — `ml_transition_gold_stratified_candidates_200.jsonl`의
   실제 텍스트/맥락으로 `sample_bucket`을 휴리스틱 재구성(`classify_bucket()` 신규 작성
   필요)해서 `diagnose_gold_vs_ai_draft.py`를 다시 돌리고, "bucket sensitivity analysis"로
   라벨링해서 보고 (Codex 제안 그대로). 이건 여전히 ground truth가 아니라 민감도 분석임을
   명시.
2. **reviewer calibration** — 같은 balanced/source-mixed 30~50개 subset을 두 reviewer
   프로토콜이 각각 독립 채점해서 axis별 agreement와 mean-scale 차이를 계산. 이게 없으면
   Humor/다른 축의 reviewer-01 vs reviewer-avg 차이가 "진짜 소스 차이"인지 "채점자 차이"인지
   영원히 못 가른다.
3. **NICT provenance 복구** — 활성 학습셋의 NICT 600행에 `source_group`(또는 대응되는
   interview/session ID)을 복구해서, 68개 unknown_nict gold row의 겹침 여부를 실제로
   판정 가능하게 만들기.
4. **다음 acceptance test는 지금 학습셋에 없는 source_group만으로 구성** — 남은 400개
   gold candidate 중 학습셋과 완전히 disjoint한 그룹만 선별해서 최종 blind test로 예약.

## ACTION (지금 바로 할 수 있는 것 / 순서)

1. `docs/ml-transition-plan.md`에 이번 라운드 결과 반영: gold-200의 역할을
   "final held-out test" → **"human dev/diagnosis set"**으로 재정의(사용자가 이전에
   요청한 바와 동일), overlap-split 결과와 reviewer confound를 정식 기록.
2. NICT `source_group` 복구는 우선순위 낮음(68개 중 어차피 학습에 반영 안 된 항목이라
   급하지 않음) — 그보다 3번을 먼저.
3. **train-120(Energy/Curiosity) 검수는 이대로 진행해도 무방** — 이번 실험에서
   nonoverlap Energy/Curiosity 성능이 여전히 rule/hybrid에 못 미치는 걸 재확인했고,
   Energy는 "표본 커버리지" 문제라는 재해석과도 방향이 맞는다(사람이 실제로 고에너지
   발화에 점수를 매겨주면 학습 신호가 생김). 단, 결과 해석 시 "이걸로 5축 게이트를
   통과했다"고 말하지 않는다(Codex #6과 동일 — Energy/Curiosity 두 축 calibration용으로만
   씀).
4. Humor에 대한 예산/노력 배분은 reviewer calibration 결과가 나오기 전까지 보류.
   지금 바로 "Humor용 발화를 추가로 마이닝하자"고 확정하지 않는다 — reviewer 교란을
   먼저 풀어야 그 판단이 의미 있다.
5. bucket 재구성 스크립트(`classify_bucket()`)는 다음 Claude Code 라운드에서 구현 —
   새 코드이므로 사용자 승인 후 진행.
