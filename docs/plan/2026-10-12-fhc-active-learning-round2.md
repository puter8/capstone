# F/H/C 능동학습 2라운드 — Gemini 의사라벨(pseudo-label) 보강 실험

작성: 2026-10-12~13 · 브랜치 `feat/pally-opener-ai` · 커밋 안 함
`rubric_version` v2.2(불변) · `protocol_version` v3.1(신규 라운드) · 라벨 출처 `gemini_ai_scored`

> **이 문서가 다루는 것의 정확한 이름:** "사람 dev 라벨로 평가한, 별도의 Gemini 의사라벨 보강 실험"이다. v2.2 §13에 따라 LLM 의사라벨은 사람 기반 주 실험에서 가중치 0이므로 여기 결과는 사람 기반 주 실험 결과와 섞어 보고하지 않는다. 의사라벨이 사람 라벨과 일치한다는 것은 **정답이라는 뜻이 아니다**.

## 1. 목적과 제약

- 목적: 5축 신뢰도 순위를 정하기 위해 F/H/C의 신뢰도 근거를 보강한다(가장 신뢰할 수 있는 축을 가장 눈에 띄는 캐릭터 요소에 연결).
- 제약: 사람 추가 라벨링 금지(소유자 결정) → 2라운드 라벨은 Gemini(`gemini-2.5-flash-lite`)가 매긴다. 의사라벨은 **학습 전용**이고, 평가는 기존 **사람 dev 35개**와 기존 게이트(`scripts/compare_purpose_v3_models.py::evaluate()`)로만 한다. 보호된 최종 평가 파티션(31개)은 학습에도 평가에도 쓰지 않았다.
- Gemini 호출은 운영 앱과 같은 프로젝트 쿼터를 쓰므로 **분당 10회**로 제한했다(재시도를 포함해 요청 시작 간격 6초 이상).

## 2. 선행 작업 — Humor rescue 감사 수정 (Task 1)

- `data/fixtures/pally_humor_rescue_candidates_ai_scored.csv`를 제자리에서 이전했다. pool `no_laugh_hard_negative`를 `no_laugh_random_negative_candidate`로 바꾸고, `fhc_partition` 열을 item_id 기준으로 추가했다(dev 12행, protected_final_eval 10행). `humor_score_0_100`은 `ai_humor_score_0_100`으로, `notes`는 `ai_evidence`로 이름을 바꿨다. 빈 `ai_error` 열과 `prompt_sha256` 열도 추가했다. `prompt_sha256` 값은 해시 기록 전의 70행이므로 `unrecorded_before_2026-10-12_schema_fix`로 명시했다. 비어 있는 사람 점수 열은 원래 없어서 삭제할 것이 없었다.
- 검증: 이전 전 백업과 대조해 70행 × 기존 19열, 1,330칸이 모두 동일함을 확인했다(이름 변경과 pool 수정은 반영). Codex도 백업과 대조해 70개 점수와 구성요소가 모두 그대로이고 가중 산식으로 재현됨을 확인했다. 분포는 low 62 / mid 4 / high 4, provisional 19이다.
- `scripts/score_humor_rescue_candidates.py` 수정 내용:
  - 출력 스키마를 고정했다(`ai_error`가 중간에 생겨 DictWriter가 터지던 문제를 해결).
  - 행마다 flush와 fsync로 기록하고, 이어서 실행(resume)할 수 있게 했다. 오류 행은 감사 기록으로 남기고 해당 항목만 재시도한다. 잘린 행과 중복 성공 행은 실행을 거부하고, 다른 프롬프트 해시의 파일에 이어 쓰는 것도 거부한다.
  - API 키를 URL 대신 헤더로 보낸다. 타임아웃과 연결 오류도 오류 행으로 남긴다.
  - finishReason이 `STOP`이 아니면 실패로 처리한다.
  - 구성요소는 정확히 int만 받는다(bool이나 2.0은 거부). 필수 boolean 플래그와 문자열 근거를 검사한다.
- 2행 실호출 테스트에서 기존 행과 구성요소, 점수, 근거 문장이 같게 재현됐다. 기본 실행은 "70개 완료, 0건 호출"로 끝난다.

## 3. 설계 (Codex 승인본)

### 3.1 후보 풀과 누출 방지 — `scripts/fhc_round2_select.py`
- 풀: AMI, ICSI, Santa Barbara(SB). 1라운드의 `load_exclusions()`와 `eval_or_train()` 로직을 재사용했다.
- 보호 회의(73개): 최종 평가 파티션, dev split, 시드 100의 legacy final-test 20이 속한 회의. 여기에 **이 회의들의 AMI 시나리오 시리즈 형제 회의**(예: ES2008a–d는 같은 화자이고 같은 과제)를 추가로 제외했다. 1라운드는 회의 단위였으므로 이번이 더 엄격하다. ICSI는 회의 단위로 남겼는데, 모든 회의가 한 연구 그룹이라 시리즈 단위 제외가 불가능하기 때문이다(한계).
- 1라운드 eval 브랜치 해시 그룹 전체와 구 트랙 gold-200/reserved 그룹을 제외했다.
- 텍스트 제외(완전 일치): seed 100, week2 338, 구 combined 풀, 1라운드 150, Humor rescue 70, dev 35, eval 31.
- 근접 중복: 단어 집합 Jaccard ≥ 0.8이면 제외했다(유니코드와 아포스트로피 정규화 후). 비교 대상은 위 텍스트 전부와 이미 선택된 행이다. 의미적 독립을 보장하지는 않는 보수적 어휘 필터다. 실제로 9건이 제외됐다.
- 결과: 적격 풀 56,177행 / 113회의 → **250개 선택(95회의, 회의당 최대 4개)**.

### 3.2 선택 쿼터 (채우는 순서대로)
- 선택 신호: Ridge(사람 train186으로 재학습)와 규칙 분석기, 그리고 코퍼스 주석(웃음 이벤트, 질문 대화행위 태그)이다. **선택에만 쓰고 Gemini에는 보내지 않았다.**

| 쿼터 | 개수 | 기준 |
|---|---:|---|
| random_reference | 30 | 그룹 상한 하의 무작위 참조 표본. 먼저 뽑는다. 대조군이 아니다 |
| humor_high_enrich | 55 | 웃음 이벤트가 붙은 발화. max(ridge, rule) Humor 순 |
| curiosity_high_enrich | 55 | 질문 대화행위(AMI el.\*, ICSI qw/qo/qr/qy, SB는 질문형 판별). 개방형 질문 우선 |
| formality_low_extreme / high_extreme | 30 / 30 | min / max(ridge, rule) Formality |
| F/H/C disagreement | 20 / 15 / 15 | \|ridge − rule\| |

- Ridge의 Humor 예측은 풀의 96%에서 0 또는 5라서 사실상 신호가 없었다. Humor 표적은 웃음 단서, 규칙 Humor, 무작위로 정해졌다.

### 3.3 Gemini 오라클 — `scripts/fhc_round2_label.py`
- 발화당 **승인된 주석 1개**를 받는다. 전송 오류는 최대 4회까지 재시도하고 모든 시도를 행에 기록한다.
- 입력은 대상 발화 한 문장뿐이다(v2.2 §2). 출력은 responseSchema 구조화 출력, temperature 0, thinkingBudget 0이다.
- 모델이 기록하는 것:
  - primary/secondary function, function_ambiguous, language_form;
  - 축별 구성요소(§5의 **정수 0–4**. Codex 판정: 0/2/4로 제한하면 루브릭 위반), case_type, confidence 0–4(점수와 가중치에 쓰지 않음), 근거;
  - Curiosity 기능(§10 표).
- 계산은 전부 코드가 한다. 가중합은 정수로 계산하고, round_to_5는 **반올림 half-up**(사람 워크북의 Excel ROUND와 동일, 32.5→35)이며, 그다음 Curiosity 기능별 범위를 적용한다. `raw_score`와 `rounded_before_clamp`도 보존한다.
- `context_insufficient`이면 provisional로 표시하고 숫자는 감사용으로 보존한다(자동 50 금지). 학습에는 쓰지 않는다.
- 출처 기록: `label_source=gemini_ai_scored`, `annotator_model`, 반환된 `model_version`, `finish_reason`(STOP 필수), 시도별 시각과 상태, `prompt_sha256=ad8c4daec88102f1…`, `scorer_code_sha256=6e3e2d5fa5d9…`, `input_manifest_sha256`, `acquisition_round`. 메타데이터는 허용 목록 필드만 복사한다.
- **SB(CC BY-ND, 공개 저장소 금지 규칙):** 공개 파일의 SB 행에는 발화, 원응답, 근거, 오류 상세가 없고, `raw_response_sha256`와 `private_audit=true`만 남긴다. SB 원응답과 근거는 저장소 밖 세션 scratchpad의 private audit JSONL(calibration 32행, batch 87행)에 있다. 장기 보존하려면 소유자가 gitignore된 경로(예: `data/external_raw/`)로 옮겨야 한다. 공개 파일 3개의 SB 206행에서 텍스트 필드 0건, calibration SB 32행에서 원문 접두어 0건임을 검증했다.

### 3.4 사전 등록 보정 게이트 (D7, 보정 호출 전에 고정)
- 보정 대상은 1라운드 split의 사람 행 221개(train186 + dev35)다. legacy final20과 보호 평가 31은 라벨링하지 않았다.
- **게이트 모집단:** 사람 TRAIN split 중 1라운드 워크북 41–150번(앞 발화를 보지 않은 단일 발화 사람 라벨) 92개.
  - 워크북 1–40번은 앞 발화가 보이는 상태로 채점됐다(워크북 일러두기).
  - **시드 100의 4인 합의 라벨도 채점 시트에 `context_before` 열이 있었다.** 둘 다 v2.2 §2와 다르므로 진단용으로만 썼다.
  - dev는 결정을 파일에 쓴 뒤 진단으로만 출력했다.
- 축별 통과 조건: Spearman ≥ .40, 3구간 QWK ≥ .40, false-high ≤ 10%, n ≥ 10인 사람 구간마다 recall ≥ 50%, Gemini 오류 ≤ 5%. 지표가 정의되지 않으면 실패다.
- 결정은 `data/fixtures/pally_purpose_v3_round2_calibration_gate.json`에 기록했다. batch는 프롬프트와 코드 해시가 일치하고 통과 축이 1개 이상일 때만 실행된다.

### 3.5 학습과 평가 — `scripts/fhc_round2_compare.py`
- R1은 1라운드 조건 그대로다. R2는 사람 train186에 **게이트를 통과한 축의 final 의사라벨만**(단위 가중치) 더한 것이다.
- 탈락한 축은 R1 모델로 예측한다. 공유 TF-IDF 통계 때문에 생기는 간접 변화를 막기 위해서다.
- `evaluate()`를 부르기 전에 모든 dev 정답 축에 유한한 예측이 있는지 확인한다.
- 의사라벨 산출물을 엄격하게 검증한다: 프롬프트, 코드, 입력 매니페스트, 라운드가 게이트와 일치해야 하고, 후보 250개를 모두 포함해야 하며, 보호 회의와 시리즈가 섞이면 안 된다.
- 모든 학습 입력(train186, week2, pseudo)과 dev/eval 텍스트의 겹침을 점검한다.
- R2−R1 차이는 AMI 시리즈/회의 클러스터 단위로 2,000회 짝지은 부트스트랩을 했다.

## 4. Codex 판정

1. **1차 설계 검토: NOT APPROVED.** 주요 지적과 반영 내용:
   - (D7) dev와 legacy final20 라벨로 게이트를 정하면 R2에 누출된다 → 게이트 모집단을 train의 블라인드 항목으로 제한했다.
   - (D5) `utterance`만 빼면 SB 텍스트가 근거와 원응답에 남는다 → private audit로 분리했다.
   - 타임아웃이 오류 행이 아니라 예외로 터진다; 이어서 실행할 때 다른 실험이 섞일 수 있다; finishReason을 무시한다; 검증이 느슨하다 → 모두 수정했다.
   - (D2) legacy final20 회의를 보호하고, 구 combined 풀을 근접 중복 참조에 추가한다.
   - (D1) 무작위 표본을 먼저 뽑고, "대조군"이라는 표현을 쓰지 않는다.
   - (D3) 0–4 척도를 승인하고 secondary_function, function_ambiguous, confidence를 추가한다.
   - (D8) 탈락 축은 R1으로 예측하고, 예측 커버리지를 확인한다.
   - (D9) 전역 선택 배치를 재사용하는 GroupKFold CV는 선택 오염이 있으므로 **이번 라운드에서 하지 않는다.**
   - 주장 정정: 앵커 일치는 14/15가 아니라 13/15였다(Humor 25→35도 구간을 넘음). 앵커는 프롬프트 안에 있으므로 API·루브릭 스모크일 뿐 일치 근거가 아니다.
2. **2차 재검토: APPROVED WITH CHANGES.** 재시도까지 포함한 분당 10회 간격 강제, batch 전 게이트 확인, 보정·의사라벨 산출물의 계보와 커버리지 엄격 검증, 쌍이 없을 때 실패 처리를 요구했고 모두 반영했다. 쿼터는 변경하지 않는다(사후에 바꾸면 다른 실험이 되므로). Humor가 구조적으로 실패하더라도 250개 전부 실행한다(F/C 라벨은 얻을 수 있으므로).
3. 최종 Codex 검증은 리드가 통합 실행한다(요청 사항은 §10).

## 5. 실호출 결과

### 5.1 스모크 (최종 동결 프롬프트, 루브릭 앵커 15문장)
15/15 성공(STOP, `gemini-2.5-flash-lite`, 약 2.5초/호출). 의도한 구간과 맞은 것은 **12/15**다. 빗나간 것은 Formality 25→50("Can you fix this for me?"를 §6의 "통상 요청 = 완화 2"로 처리), Humor 25→35, Humor 50→70이다. 프롬프트는 튜닝하지 않았다. 이 결과는 일치 근거가 아니다.

### 5.2 보정: 사람 라벨 대비 Gemini (221개 호출, 오류 0)
Gemini는 221개 전부에서 `context_insufficient`을 한 번도 쓰지 않았다(provisional 0). 사람 라벨과 대비되는 점이다.

**사전 등록 게이트 결과** (모집단: train, 워크북 41–150번):

| 축 | n | 사람 구간(저/중/고) | ρ | QWK | MAE | Gemini−사람 편향 | 판정 |
|---|---:|---|---:|---:|---:|---:|---|
| Formality | 76 | 4/72/0 | 정의 불가 | 0.000 | 10.7 | +10.3 | **FAIL** |
| Humor | 92 | 92/0/0 | 0.584 | 0.000 | 0.5 | −0.3 | **FAIL** |
| Curiosity | 83 | 60/14/9 | **0.835** | **0.791** | 10.4 | +8.2 | **PASS** |

- Formality: Gemini가 221개 중 207개를 구성요소 (2,2,2)=50, 즉 "대인 행위 없는 중립 진술"의 기본값으로 처리했다. 게이트 모집단 76개는 전부 50이었다(사람 점수는 25–40에 몰림). 회의 발화에 대해 **Gemini Formality는 변별력이 없다.**
- Humor: 사람 블라인드 라벨에 저구간이 아닌 항목이 하나도 없어 **검증 자체가 불가능**하다. 저구간 일치(99%)는 둘 다 0이라는 뜻일 뿐이다.
- Curiosity: 구간 recall은 저 83%(n60), 중 57%(n14), 고 100%(n9)이고 false-high는 2%다.

**진단** (결정 이후에 계산, 결정에는 쓰지 않음):
- Curiosity는 모든 하위집단에서 일관됐다. dev35는 ρ .640 / QWK .625, 시드 합의(앞 발화 노출)는 ρ .779 / QWK .549, 코퍼스별로 AMI .776 / ICSI .682 / SB .829.
- Formality에서는 사람 출처 간 척도 차이가 드러났다. 시드 합의 대비 Gemini 편향은 +17.4이고, 1–40번(앞 발화 노출) 대비는 −31.5다. 1–40번 사람 라벨은 24/30이 고구간이다. 즉 사람 Formality 라벨 자체가 출처마다 다른 척도를 쓴다. 풀링한 지표로는 이를 구분할 수 없다.
- Humor: 시드 합의(사람 중/고 5개)에서 ρ .537 / QWK .426이지만 앞 발화가 노출된 라벨이고 n이 너무 작다.

### 5.3 의사라벨 배치 (250개 호출, 오류 0, 재시도 1건, finish 모두 STOP)
- Curiosity: 채택 247개(저 154 / 중 40 / **고 53**), provisional 3개. 고구간 53개 중 41개는 `curiosity_high_enrich`에서 나왔다. 표적 선택이 Curiosity 고구간 확보에 효과가 있었다(단, Gemini 기준의 고구간이다).
- Formality(게이트 탈락, 학습 미사용): 저 8 / 중 240 / 고 2. 240개가 다시 (2,2,2)였다. 양극단을 겨냥한 쿼터도 Gemini 라벨에서는 극단이 나오지 않았다.
- Humor(게이트 탈락, 학습 미사용): 저 246 / 중 4 / 고 0. 웃음 단서 표적에서도 중구간은 2개뿐이었다.
- 학습 입력과 dev/eval 텍스트의 겹침: train186, week2, pseudo 모두 완전 일치 0, 근접 중복 0.

## 6. R2 vs R1 — 사람 dev 35개 (`evaluate()` 원출력에서 발췌)
R2 = 사람 train186 + Curiosity 의사라벨 247개. Formality와 Humor는 탈락했으므로 R2 = R1이다(설계상 동일, 실측도 동일).

**Curiosity** (dev 사람 구간 24/6/0. 고구간 0개 → 모든 조건이 INSUFFICIENT_EVIDENCE)

| 모델 | R1 macro recall | R2 macro recall | 저구간 recall (n24) | 중구간 recall (n6) | R2−R1 (95% 클러스터 부트스트랩 CI) |
|---|---:|---:|---|---|---|
| TfidfKnn | 89.58% | 72.92% | 96%→96% | 83%→50% | −16.7%p (−40.0..+0.0) |
| TfidfKnn + week2 | 64.58% | 85.42% | 79%→88% | 50%→83% | +20.8%p (+0.0..+45.2) |
| RidgeAxisAdapter | 56.25% | **91.67%** | 96%→100% | 17%→83% | **+35.4%p (+12.5..+53.8)** |
| RuleBased(학습 없음) | 70.83% | 70.83% | 92% | 50% | — |

- R2에서는 false-high가 3개 조건 모두 0%다(R1 knn+week2는 4.17%).
- Ridge R2는 중구간을 1/6에서 5/6으로 맞혔다. 신뢰구간은 0을 넘지만 **차이는 6개 항목의 중구간에서 결정된다.** kNN 단독은 오히려 나빠졌다(중구간 5/6 → 3/6, 2개를 고구간으로 예측).
- Formality(dev 8/17/5): R1 = R2. 가장 좋은 것은 RuleBased 68.14% FAIL(중구간 recall 29%, n17)이고, kNN 64.12% FAIL, Ridge 53.04% FAIL, kNN+week2 52.99% FAIL(false-high 12.5%)이다.
- Humor(dev 34/1/0): R1 = R2. 모든 모델이 50.00%로 INSUFFICIENT_EVIDENCE다.

## 7. 신뢰도 요약 (5축 순위용 F/H/C 입력)

| 축 | 근거가 지지하는 것 | 근거가 지지하지 않는 것 |
|---|---|---|
| **Curiosity** | 세 축 중 가장 강하다. Gemini 오라클은 블라인드 사람 라벨과 높게 일치한다(ρ .835, QWK .791, 고구간 9/9). 일치는 정답이 아니다. Gemini 의사라벨을 더하면 Ridge의 dev macro recall이 56→92%가 되고 CI가 0을 넘는다. 다만 저/중 2구간, 중구간 n=6 기준이다. | dev에 사람 고구간이 0개라 **고구간 재현은 평가된 적이 없다**. 3구간 게이트는 INSUFFICIENT_EVIDENCE이고, v3.0 §7.1의 "구간당 독립 사례 ≥10"도 고·중구간 모두 미달이다. kNN에서는 개선이 재현되지 않았다. |
| **Formality** | 사람 dev에서 모든 모델이 FAIL이다(최고 RuleBased 68.14%, 중구간 29%). 사람 라벨 출처 간 척도 불일치(시드 합의 vs 1라운드 단일 평가자, 앞 발화 노출 1–40번)가 측정됐다. Gemini는 회의 발화에서 Formality를 거의 상수(50)로 매겨 오라클로 쓸 수 없다. | 2라운드는 Formality를 개선하지 못했다(축 탈락). dev 구간 8/17/5는 3구간 강한 주장에는 부족하다. |
| **Humor** | 텍스트 코퍼스(회의, SB)에는 중/고 Humor가 사람과 Gemini 모두에서 매우 드물다. Gemini 배치 250개 중 중구간 4, 고구간 0. 블라인드 사람 라벨은 92/0/0. | 어떤 신뢰도 주장도 할 수 없다. dev 34/1/0이고 보정도 불가능했다. 의사라벨 학습으로는 없는 평가 근거를 만들 수 없다. |

5축 순위에 쓸 결론: 텍스트 3축 중 **Curiosity > Formality > Humor** 순으로 근거가 강하다. Formality는 "측정이 실패함"이, Humor는 "측정 근거가 없음"이 근거로 확인된 상태다. 어느 것도 한국 ESL 학습자 STT 트래픽에서의 신뢰도를 보장하지 않는다(코퍼스는 AMI/ICSI 회의와 SB 원어민 대화).

## 8. 한계

- R1 vs R2는 데이터 추가, Gemini 감독, 표적 선택, 코퍼스 혼합(SB 87/250)을 **한꺼번에** 비교한다. 능동 선택 자체의 효과는 분리되지 않는다.
- dev 35개 중 17개는 앞 발화가 노출된 사람 라벨이다(1–40번 9개 + 시드 8개).
- 1라운드에서 물려받은 겹침은 고치지 않고 공개만 한다: train186 중 13행이 dev와, 23행이 보호 평가와 AMI 시리즈를 공유하고, 17행이 legacy final20과 같은 회의다. 회의 단위 겹침은 0이지만 화자·시리즈 독립성은 확립되지 않았다.
- 1라운드 산출물(`pally_purpose_v3_combined_train.jsonl`, `..._train_dev_split_{train,dev}.jsonl`)에는 SB 원문이 들어 있는데 **gitignore되어 있지 않다.** 커밋하면 PM 규칙(SB 원문 GitHub 금지) 위반이다. 2라운드 공개 파일에는 SB 원문이 없다.
- SB private audit는 세션 scratchpad에만 있다. 영구 보존하려면 gitignore 경로로 옮겨야 한다.
- 보정 게이트 모집단(92개)은 1라운드의 불일치·극단 쿼터로 뽑힌 항목이라 2라운드 후보 분포를 대표하지 않는다. 임계값은 탐색적 채택 규칙이다.
- Gemini는 `context_insufficient`을 한 번도 쓰지 않았다. 사람 라벨링 관행(1라운드 22/15축)과 다른 체계적 차이다.

## 9. 재현

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/fhc_round2_select.py            # 후보 250 (결정적, seed 20261012)
.venv/Scripts/python.exe scripts/fhc_round2_label.py selfcheck
.venv/Scripts/python.exe scripts/fhc_round2_label.py smoke
.venv/Scripts/python.exe scripts/fhc_round2_label.py calibration --private-audit <저장소 밖 경로>
.venv/Scripts/python.exe scripts/fhc_round2_label.py report    # 게이트 결정 → calibration_gate.json, 이후 진단
.venv/Scripts/python.exe scripts/fhc_round2_label.py batch --private-audit <저장소 밖 경로>
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/fhc_round2_compare.py
```

주의: `fhc_round2_label.py`를 수정하면 코드 해시가 바뀌어 batch와 compare가 기존 게이트를 거부한다(의도된 동작).

산출물: `data/fixtures/pally_purpose_v3_round2_candidates.jsonl`, `..._calibration_gemini.jsonl`, `..._calibration_gate.json`, `..._pseudo_labels.jsonl`.

## 10. 리드의 통합 Codex 검증에서 확인할 것

1. `fhc_round2_compare.py`를 재실행했을 때 §6 수치가 재현되는지, R1 수치가 1라운드 `compare_purpose_v3_models.py` 출력과 같은지.
2. 게이트 JSON의 지표가 보정 파일에서 재계산되는지. 게이트 모집단이 train ∩ 워크북 41–150번(앞 발화 비노출)인지. dev 진단이 결정에 영향을 주지 않았는지.
3. 의사라벨 계보: 250행의 prompt/code/input/round 해시가 게이트와 일치하는지. 보호 회의 73개와 AMI 시리즈 형제 회의에서 온 행이 0인지. dev/eval 텍스트와의 완전 일치·근접 중복이 0인지.
4. 공개 파일 3개의 SB 행에 원문, 원응답, 근거가 없는지(206행).
5. Curiosity 산식 검증: 가중합과 half-up 반올림, 기능 범위 적용 결과가 `components`에서 재계산되는지.
6. Humor CSV(70행)가 백업과 동일한지(1,330칸)와 수정된 scorer의 오류·재시도 경로.
7. 이 문서의 주장이 과장되지 않았는지. 특히 Curiosity 개선이 중구간 n=6에 의존한다는 점과 고구간 미평가라는 점.
