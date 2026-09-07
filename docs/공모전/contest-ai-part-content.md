# Pally 공모전 제출 — 백은혜 담당 카드 7개 산출물

> Notion 스프린트 보드 기준, 백은혜 배정 카드 7개를 그대로 매칭해서 작성. 모든 수치는 이 세션에서 실제 실행·검증된 값(2026-09-06/07).

---

## 카드 1 — 5축·MATRIX·EMA 핵심 증거 선정

### 산출물 A: 알고리즘 근거

Pally는 사용자 발화를 Formality/Energy/Intimacy/Humor/Curiosity 5축(0~100)으로 분석한다.
`params = W(3×5) × [F,E,I,H,C]ᵀ + BIAS` — CHARACTER MATRIX 연산으로 3개 캐릭터 파라미터(tone_casual, energy_level, humor_level) 산출.
`updated[k] = 0.7 × new[k] + 0.3 × prev[k]` — EMA로 턴 간 급격한 변화 완충(alpha=0.7, 데모용 상향).

### 산출물 B: 대화 출력 3건 (실제 실행 결과, hybrid analyzer 기준)

| # | 시나리오 | 입력 발화 | 5축(F/E/I/H/C) | 캐릭터(tone_casual/energy/humor) |
|---|---|---|---|---|
| 1 | 캐주얼 | "hey what's up!!" | 14 / 54 / 40 / 16 / 38 | 58 / 54 / 27 |
| 2 | 격식체 | "Good afternoon. Could you help me practice a formal conversation?" | 58 / 29 / 14 / 0 / 52 | 29 / 42 / 15 |
| 3 | Persona drift 최종 턴(캐주얼→격식 전환 후) | "Thank you, that was a very helpful and structured session." | 48 / 37 / 29 / 5 / 22 | 37 / 44 / 18 |

→ 캐주얼(tone_casual 58)에서 격식체(29)로 뚜렷하게 하락, drift 시나리오는 최종적으로 격식 쪽에 수렴(37)하면서도 완전히 격식 초기값(29)까지는 안 내려가는 EMA 완충 효과가 보임.

### 산출물 C: Pally 시각 상태 3종

축→시각 매핑(PallyCanvas.tsx 기준: Formality=모서리, Energy=몸통모양, Humor=움직임, Curiosity=눈, Intimacy=색상):

| # | 상태명 | 모서리(Formality) | 몸통(Energy) | 움직임(Humor) | 눈(Curiosity) | 색상(Intimacy) |
|---|---|---|---|---|---|---|
| 1 | 캐주얼 상태 | 둥긂(F14) | 별모양(E54) | 거의 정지(H16) | 중간(C38) | 청록 계열(I40) |
| 2 | 격식 상태 | 중간~각짐(F58) | 사각형(E29) | 정지(H0) | 중간(C52) | 차가운 파랑(I14) |
| 3 | Drift 후 안정 상태 | 중간(F48) | 별모양(E37) | 정지(H5) | 단순(C22) | 파랑 쪽(I29) |

**체크리스트 완료**: 5축·MATRIX·EMA 설명 범위 확정 ✅ / 대화 출력 3건 선정 ✅ / Pally 시각 상태 3종 선정 ✅

---

## 카드 2 — AI 분석→Pally 변화 장면 제공 (이찬희 전달용)

이찬희에게 그대로 전달할 수 있는 캡션 3세트(위 카드 1의 대화 출력 3건과 1:1 대응):

1. **캐주얼 캡션**: "사용자가 캐주얼하게 말하면(`hey what's up!!`) → Pally가 별모양 몸통에 청록빛으로 반응"
2. **격식 캡션**: "사용자가 정중하게 말하면(`Could you help me practice...`) → Pally가 각지고 차가운 파란색으로 안정"
3. **Drift 캡션**: "한 세션 안에서 캐주얼→격식으로 바뀌면 → Pally가 서서히(EMA) 격식 쪽으로 이동, 급변하지 않음"

**주의**: 실제 화면에서 Pally 시각 변화는 대화 중 실시간이 아니라 **세션 종료(X 버튼) 시점에 한 번에 반영**됨(`usePally.ts`의 `revealAxes()`). 영상 촬영 시 이 타이밍을 맞춰야 함 — 이찬희에게 꼭 전달.

**체크리스트**: 5축 분석 결과 화면 준비 ✅(위 표) / Pally 변화 장면 준비 ✅(위 표) / 기술 캡션 ✅

---

## 카드 3 — AI·MATRIX·EMA 기술 검수

자체 검수 결과(실제 코드 대조):

| 검토 항목 | 결과 |
|---|---|
| CHARACTER MATRIX 공식 | `ai/matrix_engine.py` W(3×5)/BIAS 값과 일치 확인 |
| EMA alpha 값 | 코드 기본값 `DEFAULT_ALPHA = 0.7` 확인(문서에 "0.3이 일반적, 데모용으로 0.7 상향"이라고 정확히 명시할 것 — 다르게 쓰면 사실 오류) |
| 5축→시각 매핑 표 | `PallyCanvas.tsx` 실제 코드와 일치(이번 세션에 수정 완료: Formality→모서리, Energy→몸통, Humor→움직임, Curiosity→눈, Intimacy→색) |
| analyzer 기본값 | `PALLY_AXIS_ANALYZER` 미설정 시 `rule` — 문서에 "ML 적용 중"이라고 쓰면 사실 오류, 반드시 "rule 기본, hybrid 검증 중"으로 기술 |
| 수치 근거 | MAE/Spearman 수치는 `ai/evaluate_axis_analyzers.py` 실행 결과(아래 카드 7)로 추적 가능 |

**수정 사항 없음** — 이전에 만든 초안(위 카드들)이 실제 코드와 일치함을 확인.

---

## 카드 4 — 개발보고서 p8·11 작성

### p8. 5축·MATRIX·EMA·Pally 렌더러

(카드 1의 "알고리즘 근거" + "Pally 시각 3종" 표를 산문으로 풀어서 배치 — `contest-ai-part-content.md` 이전 버전의 1·2절 내용 그대로 사용 가능)

### p11. AI 문제·해결·학습 내용

**문제 1 — 학습 데이터 부족**: 초기 데이터 30개로는 ML 분석기가 입력 차이를 구분하지 못함(Curiosity 축 Spearman 0.04). **해결**: LLM 보조 라벨링으로 338개까지 확장, 이후 실제 발화 코퍼스 5종(NICT JLE, AMI, CHiME-6, HCRC Map Task, Taskmaster-1 WoZ)에서 표본을 뽑아 총 3,137개 학습셋으로 확장. **학습**: AI가 만든 데이터·라벨은 초안일 뿐이므로, 실제 반영 전 사람 검수 단계를 반드시 거치도록 설계함.

**문제 1-1 — "데이터를 늘리면 해결된다"는 가정 자체가 틀렸음을 발견**: gold 200건 사람 검수를 완료(2026-09-07)하고 이 진짜 인간 라벨로 ML을 재평가하자, 이전에 같은 AI가 만든 라벨끼리 비교한 순환평가(ML MAE 7.55)와 전혀 다른 결과(ML MAE 14.90, rule 14.54, hybrid 14.26)가 나왔다. 원인을 추적한 결과 문제는 데이터 "양"이 아니라 **학습 라벨을 만든 rubric(teacher) 자체의 품질이 축마다 달랐다는 것**이었다 — Energy·Humor는 학습셋에 고에너지·고유머 발화 표본 자체가 희소했고(real-speech 기준 Energy≥50 15개, Humor≥40 5개뿐), Curiosity·Formality는 이미 신뢰할 만한 신호였다. **해결**: 축마다 다른 처방이 필요하다는 결론에 따라, `PALLY_AXIS_ANALYZER` 기본값은 `rule`로 유지하고 축별 우선순위를 다시 세웠다.

**문제 1-2 — AI의 자체 진단도 검증 없이 믿지 않기**: 위 진단을 세운 뒤 그 결론(특히 "Intimacy rubric은 대명사 때문에 사실상 상수")을 다른 AI(Codex)에게 비판적으로 검토시키는 절차(`docs/ai-collab/`)를 도입했다. 그 결과 이 결론 중 하나가 실제로 틀렸음이 밝혀졌다 — Intimacy 판별 신호는 gold 200건 중 51%(102건)에만 걸리는 이분법적 신호였고 학습 데이터에도 17개 서로 다른 값이 있었는데, 처음 진단이 이를 "거의 상수"로 오독한 것이었다. **학습**: 한 AI의 결론을 다른 AI가 실제 코드·데이터로 재검증하게 하는 과정에서 실질적인 오류를 잡아냈다 — AI가 내놓은 진단·수치도 최종 결정 전에 반드시 교차검증한다는 원칙을 세웠다.

**문제 2 — 응답이 화면에서 잘리는 문제**: Gemini가 길게 응답하면 UI 말풍선 크기(290px)에서 문장 중간에 잘림. **해결**: `shape_reply()`로 문장 경계 기준 90자 제한 로직 추가.

**문제 3 — 피드백 생성 실패와 정상 무교정을 구분 못함**: `generate_feedback()`이 항상 리스트만 반환해 실패와 "교정할 것 없음"을 구분 불가. **해결**: `(items, failed)` 튜플로 반환 구조 변경.

**체크리스트**: 5축·MATRIX·EMA 설명 ✅ / Pally 렌더러 설명 ✅ / AI 문제와 해결 내용 ✅

---

## 카드 5 — 아키텍처·DB 최종 QA

이건 **다른 팀원(김민주 등)이 작성한 아키텍처·ERD·API·DB·보안 문서를 백은혜가 교차 검증**하는 역할이라, 그 문서 원본이 있어야 실제 검수가 가능해. 지금 나한테 없는 자료야 — `docs/`에 있는 아키텍처/ERD 관련 산출물 파일을 알려주면 그때 대조 검토할 수 있어. **이 카드는 보류.**

---

## 카드 6 — 제작설계서 s12·16 작성

### s12. 5축·MATRIX·EMA 알고리즘 (1장 흐름도)

```
사용자 발화
   ↓
5축 분석 (Formality/Energy/Intimacy/Humor/Curiosity, 0~100)
   ↓
CHARACTER MATRIX: params = W(3×5) × axes + BIAS
   ↓
EMA 스무딩: updated = 0.7×new + 0.3×prev
   ↓
캐릭터 파라미터 (tone_casual / energy_level / humor_level)
   ↓
PallyCanvas 렌더링 (모양·색·움직임·눈)
```

### s16. 핵심 AI 코드·GitHub 근거

| 기능 | 파일 경로 |
|---|---|
| 5축 분석(rule-based) | `ai/analyzer.py` |
| CHARACTER MATRIX + EMA | `ai/matrix_engine.py` |
| Analyzer 어댑터(rule/ml/hybrid) | `ai/analyzers.py` |
| ML 베이스라인 | `ai/ml_baseline.py` |
| 내부 평가 파이프라인 | `ai/evaluate_axis_analyzers.py` |
| Pally 렌더러 | `frontend/components/pally/PallyCanvas.tsx` |
| 답변 길이 안전장치 | `ai/reply_shaping.py` |
| Feedback 생성 | `ai/generate_feedback.py` |
| AI-draft teacher rubric vs 사람 gold 진단 | `scripts/diagnose_gold_vs_ai_draft.py` |
| 다중 AI 교차검증(Claude+Codex) 오케스트레이터 | `scripts/dual_ai_review.py`, `docs/ai-collab/` |

**체크리스트**: 알고리즘 흐름 1장 ✅ / 핵심 AI 코드 근거 정리 ✅ / 설명 캡션 ✅

---

## 카드 7 — 현재 모델 내부 평가 1회 실행

`python ai/evaluate_axis_analyzers.py --mode gold-holdout` 실제 재실행 결과(2026-09-07,
**사람이 직접 검수한 gold 200건**으로 평가 — 3,137개 AI-draft 학습셋으로 학습하고, 학습에
전혀 쓰지 않은 진짜 human label 200개로 채점):

| Analyzer | 평균 MAE | 평균 Spearman |
|---|---:|---:|
| Rule-based | 14.54 | 0.37 |
| ML | 14.90 | 0.28 |
| Hybrid | **14.26**(최저 MAE) | **0.39**(최고 Spearman) |

축별로 보면 결과가 갈린다 — Formality는 ML(0.46)이 가장 정확하고 Curiosity는 세
analyzer가 모두 준수(0.68~0.77)하지만, Energy(rule 0.45 vs ML 0.03)와 Humor(전부 0.1
이하), Intimacy(hybrid 0.45 vs ML 0.27)에서는 ML이 확실히 약하다.

**과장 없는 해석 3줄**:
1. AI-draft 라벨끼리 비교한 이전 순환평가(338개 데이터셋 기준 ML MAE 7.55)는 실제
   사람 라벨 앞에서 재현되지 않았다 — 진짜 human gold로 평가하니 ML이 rule/hybrid보다
   못했다(평균 Spearman 0.28 vs 0.37/0.39). 순환평가만으로 analyzer 우열을 판단하면 안
   된다는 걸 이번에 직접 확인했다.
2. 현재 서비스 기본값은 여전히 `rule`이며, 이 표는 전환 여부를 결정하기 위한 참고
   자료일 뿐 전환 완료를 의미하지 않는다. 5축을 하나로 뭉뚱그리면 안 보이지만, 축별로는
   ML이 이미 쓸만한 축(Formality)과 아직 부족한 축(Energy/Humor/Intimacy)이 뚜렷이
   갈린다.
3. 이 gold 200건은 다른 AI(Codex)의 방법론적 교차검증을 거쳤다 — 예를 들어 gold 200건
   중 72건이 기존 학습셋과 코퍼스 그룹이 겹쳐 있어 결과 해석에 주의가 필요하다는 지적을
   받았고, 실제로 겹치지 않는 부분집합만 따로 떼어 재평가해도 ML이 여전히 rule/hybrid에
   못 미친다는 것을 확인해 결론은 유지했다. 다음 최종 판정에는 학습셋과 완전히 겹치지
   않는 새 후보군으로 다시 평가할 예정이다.

**체크리스트**: 평가 파이프라인 1회 실행 ✅ / 결과 표 작성 ✅ / 과장 없는 해석 3줄 ✅

---

## 정리 — 카드별 상태

| 카드 | 상태 |
|---|---|
| 1. 5축·MATRIX·EMA 핵심 증거 선정 | ✅ 완료 |
| 2. AI 분석→Pally 변화 장면 제공 | ✅ 완료(이찬희에게 전달만 하면 됨) |
| 3. AI·MATRIX·EMA 기술 검수 | ✅ 완료(수정사항 없음) |
| 4. 개발보고서 p8·11 작성 | ✅ 완료 |
| 5. 아키텍처·DB 최종 QA | ⏸ 보류 — 대상 문서 필요 |
| 6. 제작설계서 s12·16 작성 | ✅ 완료 |
| 7. 현재 모델 내부 평가 1회 실행 | ✅ 완료 |

카드 5만 다른 팀원 산출물(아키텍처/ERD/API/DB 문서)이 있어야 진행 가능해 — 해당 파일 있으면 바로 보내줘.
