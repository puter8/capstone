# Claude Code Review — Round 1 (Diagnosis)

작성 시각: 2026-09-07. 근거는 전부 `CONTEXT.md` 5-2, 5-3의 실측치와
`scripts/diagnose_gold_vs_ai_draft.py` 실행 결과. 코드는 수정하지 않았다.

## 진단 요약

gold-200 결과가 나쁜 원인은 "ML이 데이터가 부족해서 덜 학습됐다"가 아니라,
**학습 라벨을 만든 teacher rubric(`draft_axes()`) 자체가 축마다 신뢰도가 완전히 다르고,
Humor/Intimacy/Energy 세 축에서는 사실상 무정보에 가깝다**는 것이다.

이 결론은 in-domain 평가(leave-one-out, source-group-holdout)만 봤을 때는 보이지 않았다.
그 평가들은 같은 teacher가 만든 라벨끼리 비교하는 순환평가라서, teacher 자체의 편향은
가려진다. gold-200(진짜 사람 라벨)을 넣고 나서야 teacher 품질 문제가 드러났다.

## 축별 근거

### Humor — teacher가 사실상 상수 함수 (Spearman 0.00)

`draft_axes()`는 `HUMOR_WORDS = {"funny","laugh","laughing","joke","joking","hilarious"}`
키워드 매치 여부로만 Humor에 신호를 준다. gold-200 200개 중 199개가 draft 출력값이
정확히 6으로 동일하다(quantile p10=p90=6). 즉 이 rubric으로 만든 학습 라벨은 거의 전부
같은 값이라, ML이 이 라벨로 무엇을 학습하든 "Humor는 대충 6 근처"라는 상수 함수를
배우는 것 외에 할 수 있는 게 없다. 실제로 런타임 ML의 Humor Spearman이 -0.04로 나온 것과
정합적이다.

**이건 데이터 양 문제가 아니다.** 같은 rubric으로 라벨링한 utterance를 10배 늘려도
여전히 199/200이 6으로 찍힐 것이다. 실제 유머가 드러나는 발화 자체가 이 rubric으로
검출이 안 되는 게 문제다.

### Energy — teacher에 구조적 천장이 있음 (Spearman 0.22, 하지만 진짜 문제는 confusion matrix)

threshold=50 기준 confusion에서 `human_high_draft_high=0`, `human_low_draft_high=0` —
즉 draft 값이 **200개 중 단 하나도 50을 넘지 않았다** (p90=40). `draft_axes()`를 보면
`HIGH_ENERGY_WORDS` 키워드, 문장 길이, 쉼표 개수 정도만 보고, 느낌표(`!`)나 대문자
비율, 반복 문자(`sooo`, `reallyyy`) 같은 텍스트 강도 신호를 전혀 안 본다. 그래서
"이 rubric이 표현할 수 있는 Energy의 최댓값" 자체가 사람이 실제로 매기는 high-energy
발화보다 한참 낮은 곳에 갇혀 있다.

이건 Energy 학습 데이터를 늘려도 못 고친다. rubric에 강도 신호를 추가하거나,
사람이 직접 매긴 라벨로 이 축의 학습 데이터를 갈아끼워야 한다.

### Intimacy — teacher가 거의 무정보 (Spearman 0.09, bias +27.39)

`draft_axes()`의 Intimacy 가산 조건 중 `\b(i|i'm|my|me|we|our)\b` 정규식이 거의 모든
대화체 발화에 걸린다. 그 결과 draft 값이 37~49 사이에 몰려 있다(사람 라벨은 0~42,
중앙값 12). 이 축은 "대명사가 있으면 친밀도가 높다"는 지나치게 단순한 가정이 rubric
안에 박혀 있어서, 실제로는 어떤 문장이 와도 비슷한 값을 뱉는다.

### Formality — 쓸만하지만 재보정 필요 (Spearman 0.49, sd_ratio 0.54)

방향은 맞지만 압축(사람 표준편차 13.16 vs draft 7.11)돼 있고 +7.47만큼 전반적으로
높게 찍는다. 5축 중 유일하게 "일단 쓸 수 있는데 스케일만 고치면 되는" 축.

### Curiosity — teacher가 제일 신뢰할 만함 (Spearman 0.83)

물음표 검출 기반 신호가 강해서 순위는 매우 정확하다. 스케일 압축(18~36 vs 사람
0~90)은 있지만 Spearman이 스케일 불변 지표라 rank-based로는 문제가 없다. 런타임 ML의
Curiosity Spearman이 0.68로 5축 중 가장 높게 나온 것과 일치한다.

## 우선순위 제안 (근거 기반, 확정 아님 — Codex 검토 필요)

```
Humor     > Energy > Intimacy   >>   Formality > Curiosity
(rubric 자체 재설계 필요)      (재보정만 필요)   (거의 그대로 OK)
```

## Risks / Uncertainties (내가 확신 못 하는 부분)

- **gold 후보에 `sample_bucket`이 없어서** `draft_axes()`를 기본 bucket("personal_statement")으로
  강제 실행했다. bucket 조건부 가산은 모든 200개 행에 동일하게 적용되므로 이론상 상수
  오프셋만 만들고 순위(Spearman)는 왜곡하지 않아야 하지만, **이걸 실제로 다른 bucket
  값을 넣어서 재현 확인해보진 않았다.** Codex가 이 가정 자체를 의심해볼 가치가 있다.
- 3,137개 학습셋에 있는 실제 draft 라벨(gold-200과 다른 utterance들)과, 지금 gold-200에
  사후적으로 다시 계산한 draft 라벨이 완전히 같은 분포라는 보장은 없다. 코퍼스 구성비가
  다를 수 있음 (학습셋은 NICT/AMI/CHiME-6/HCRC/Taskmaster 5개, gold candidate reservoir는
  NICT/AMI/Taskmaster 3개만).
- Humor/Energy/Intimacy 세 축 모두 "rubric이 나쁘다"까지는 확인했지만, "그래서 사람이
  직접 라벨링하면 학습 가능한 신호가 나온다"는 건 아직 검증 안 됐다. 사람 라벨끼리도
  Humor는 애초에 발화 빈도가 낮아서(rule Spearman도 0.09로 나쁨) 근본적으로 어려운
  축일 수 있다.
- 이 진단은 "text만 보고 매긴 5축"의 한계다. Energy 특히, 음성 신호(pitch, rate,
  intensity)를 못 쓰는 상태에서의 상한선일 수 있다 — 텍스트만으로 개선해도 한계가
  있을 수 있음.

## Next Experiment (내가 결정할 수 없는 부분 — Codex/사용자 판단 필요)

1. `sample_bucket`을 gold 발화의 실제 내용에 맞게 재분류해서 `draft_axes()`를 다시
   돌려봤을 때 Spearman이 유의미하게 달라지는지 확인 (위 risk 1번 검증).
2. train-120 (Energy/Curiosity) 검수를 실제로 진행했을 때, Energy 학습 신호가
   개선되는지 별도로 측정 — 단, confusion matrix 문제(천장 자체가 낮음)를 고려하면
   rubric 수정 없이 라벨만 사람 것으로 바꾸는 게 근본 해결책이 아닐 수 있음.
3. Humor는 라벨링보다 "Humor가 실제로 드러나는 발화를 어떻게 찾을 것인가"(oversampling
   전략)가 먼저 필요해 보임 — 이건 방법론 설계 문제라 Codex 의견이 필요.
