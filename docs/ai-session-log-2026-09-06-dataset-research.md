# Pally AI 5축 분석기 — 학습 데이터/모델 연구 세션 기록

**기록 목적**: 논문 작성용 상세 기록. 이 문서는 하나의 대화 세션 안에서 진행된 모든 작업을 시간순으로, 빠짐없이 기술한다.

**세션 기간 표시된 날짜**: 2026-08-15 ~ 2026-09-06 (대화 중 시스템이 세션 날짜 변경을 여러 차례 알림 — 실제로는 하나의 연속된 대화 세션)

**프로젝트 배경**: Pally(서비스명 CharaShift)는 이화여대 캡스톤 프로젝트(팀 puter8)로 개발 중인 영어 회화 학습 앱이다. 핵심 기능은 사용자 발화를 5개 축(Formality/격식도, Energy/에너지, Intimacy/친밀도, Humor/유머, Curiosity/호기심, 각 0~100점)으로 분석하고, 이 점수를 CHARACTER MATRIX(가중합 연산)로 변환해 AI 캐릭터 "Pally"의 시각적 형태·말투에 반영하는 것이다. 작성자(사용자)는 이 프로젝트의 AI 파트 담당자다.

---

## 1. 세션 초반 — API 명세 검토 및 BE 연동 작업

### 1.1 API 명세서 검토
- Pally API 명세서(§4.6 turns, §5 공통 타입, §7 결정사항)를 실제 코드(`ai/`, `backend/main.py`)와 대조 검토
- AI 파트가 BE/FE에 전달하려던 초안 중 3건이 실제로는 AI 파트가 먼저 처리했어야 할 항목으로 판단되어 수정:
  1. **Turn API feedback 통합**: BE에게 legacy 함수(`_call_gemini_feedback`, `{correction, tone_feedback, practice_prompt}` 형태) 재사용을 요청했던 것을, AI가 이미 구현한 `ai.generate_feedback.generate_feedback()`을 호출하도록 정정
  2. **FeedbackItem 스키마 동기화**: BE에게 `contracts.py`(AI 파트 소유 파일)에 모델을 추가해달라고 요청했던 것을, AI가 직접 `ai/contracts.py`에 `FeedbackItem` 모델을 추가하는 것으로 정정
  3. **Feedback 실패/partial 규칙**: 당시 `generate_feedback()`이 실패 신호를 주지 않는 상태였음에도 BE에게 partial 처리 규칙만 요구했던 것을 지적, AI가 먼저 실패 신호를 추가해야 한다고 정정

### 1.2 `generate_feedback()` 함수 개선
- 기존 함수 시그니처: `generate_feedback(utterance, pally_reply, level) -> list[dict]`
- 문제 발견: Gemini 호출이 실패해도 규칙 기반 fallback으로 조용히 넘어가 항상 리스트만 반환 → BE가 "교정 없음(정상)"과 "생성 실패"를 구분할 방법이 없음
- 수정: 반환 타입을 `(items, failed)` 튜플로 변경. `failed=True`는 Gemini 호출이 완전히 실패했음을 의미(빈 API 키, 네트워크 오류, 파싱 실패 등)
- 부수 발견 및 수정: `_fallback_rule_based()`의 정규식 버그 — `"I had no lunch. I'm on a diet."` 교정 시 두 번째 문장까지 삼키고 원문을 소문자로 매칭해 `I'm`이 `i'm`으로 깨지는 문제. 정규식을 `r"i had no ([^.!?]+)"`로 수정(원문 그대로 매칭, 문장 경계에서 정지)하여 해결
- `ai/contracts.py`에 `FeedbackItem` pydantic 모델 추가: `{original: str, corrected: str, explanation_ko: str}`

### 1.3 API 키 노출 사고 (2건)
- BE 질문에 답하려고 `generate_feedback()`의 실제 latency를 측정하는 과정에서, 사용자가 Google AI API 키(Gemini용)를 채팅에 직접 붙여넣는 사고 발생
- 세션 담당(AI, 즉 필자)이 즉시 키 노출을 지적하고 로테이션(재발급) 권고
- 측정은 진행했으나(실제 Gemini 2.5 Flash-Lite 호출, 8개 샘플 문장) 최초 답변("median 0.3~0.8s")이 실측이 아니었음을 확인 — 재측정 결과 **median 1565.3ms(약 1.6초), mean 1643.0ms, 범위 1252~2559ms**로 훨씬 느렸음을 확인, BE에 정정 전달
- 이후 STT/TTS latency 측정 때도 동일하게 Google Cloud API 키가 채팅에 노출되는 사고가 한 번 더 발생, 동일하게 즉시 로테이션 권고
- 실측 결과: **TTS median 2157.0ms(mean 2264.2ms), STT median 2091.1ms(mean 2170.3ms), TTS+STT 왕복 median 4445.8ms**(5개 문장 기준)

---

## 2. Week 4 작업 (AI 파트 자체 계획 문서 `docs/plan/2026-07-25-ai-ml-reddit-vocabulary-plan.md` 기준)

### 2.1 착수 전 발견한 문제 — 유실된 Week 2 산출물
- `ai/analyzers.py`가 `ai.ml_baseline` 모듈 부재로 **import 자체가 불가능한 상태**였음을 발견
- 원인 조사: git log 분석 결과, Week 2 산출물(`ai/ml_baseline.py`, `data/axis_dataset_week2.jsonl`, `docs/ai-labeling-guide.md`, `ai/evaluate_axis_analyzers.py`, `tests/test_ai_week2_ml_baseline.py`)이 커밋 `569b29a`(`Refine AI labels for spoken conversation`)에만 존재하며, 이 커밋은 `origin/gsd/phase-ai-ml-reddit-week1` 브랜치에만 있고 master(main)에는 merge된 적이 없었음
- Week 3 PR(#33, "Restore Week 3 AI/Reddit vocabulary work on a clean branch from origin/main")이 "클린 브랜치" 기준으로 재작성되면서 Week 2 산출물이 누락된 것으로 추정
- 해당 4개 파일을 커밋 `569b29a`에서 그대로 복원(git show로 개별 파일 추출). `ai/analyzer.py`, `data/dataset.py`는 master에서 이미 별도로 진화한 상태였으므로 건드리지 않음
- 복원 후 `python ai/evaluate_axis_analyzers.py` 실행 결과가 기존 Week 2 기록(`rule_avg_mae: 16.18`, `ml_avg_mae: 13.81`, `delta: -2.37`)과 정확히 일치함을 확인하여 복원 정합성 검증

### 2.2 Hybrid Analyzer 추가
- `ai/analyzers.py`에 `HybridAxisAnalyzer` 클래스 추가: rule-based와 ML의 축별 점수를 평균(`round((rule_pred[axis] + ml_pred[axis]) / 2)`)
- `MLAxisAnalyzer`에 실패 시 rule-based로 자동 fallback하는 로직 추가(모델 예측 실패 시 예외 처리)
- `get_axis_analyzer()` 팩토리 함수가 `PALLY_AXIS_ANALYZER=rule|ml|hybrid` 3가지 값을 지원하도록 확장(환경변수 미설정 시 기본값 `rule`)
- 테스트 파일 `tests/test_ai_week4_analyzer_integration.py` 신규 작성(6개 테스트: 팩토리 선택, 잘못된 kind 예외, env flag 인식, ML 실패시 fallback, hybrid 블렌딩 정확성, hybrid degrade 확인)

### 2.3 BE에게 analyzer 어댑터 전환 요청
- `backend/main.py`가 여전히 `ai.analyzer.analyze_utterance()`를 3곳(`/api/feedback`, `/api/chat`, `create_turn`)에서 직접 호출 중임을 발견
- BE 전달 메시지 작성: `ai.analyzers.get_axis_analyzer().analyze(text).model_dump()`로 교체 요청. `apply_ema()`/`compute_character()`는 dict를 그대로 받으므로 나머지 로직은 안 건드려도 됨을 명시

### 2.4 Reddit Vocabulary — Approved MemeTerm 함수
- `ai/reddit_vocabulary.py`에 `build_prompt_vocabulary_from_terms()` 함수 추가: 기존 `build_prompt_vocabulary()`(candidate 단계, 승인 전)와 구분하여, 사람/정책 승인이 끝난 `MemeTerm`(`status == "approved"`)만 받아 처리. `safety == "safe"`는 승인 여부와 별개로 항상 재검사(승인이 안전성 판정을 덮어쓰지 못하게)
- 테스트 파일 `tests/test_ai_week4_meme_term_prompt.py` 신규 작성(4개 테스트)

### 2.5 Regression Fixture 작성
- `data/fixtures/pally_regression_fixture.json` 신규 작성: rule-based analyzer + CHARACTER MATRIX golden case 5개(casual_greeting, formal_inquiry, curious_question, polite_request, excited_casual), EMA persona drift golden case 1개(casual→formal), generate_feedback rule-based fallback golden case 2개
- 실제 현재 코드 출력값을 실행해서 baseline으로 고정(예: casual_greeting "yo what's up lol, u wanna hang or nah?" → Formality:10, Energy:46, Intimacy:40, Humor:26, Curiosity:27; character: tone_casual:60, energy_level:50, humor_level:31) — README의 예전 문서화된 예시값과 실제로 다름을 확인(README가 stale임을 시사)
- 테스트 파일 `tests/test_ai_week4_regression_fixture.py` 신규 작성(3개 테스트)

### 2.6 STT/TTS 품질
- Week 4에서 이미 실측한 latency 수치를 재사용(위 1.3절 참고)

### 2.7 Week 4 커밋 및 push
- 브랜치 `gsd/phase-ai-ml-reddit-week4` 생성, git identity가 로컬에 설정되어 있지 않아 사용자에게 이름/이메일을 물어 repo-local로 설정(`BEAK EUNHEAY <bihunheay1@gmail.com>`, `--global` 아님)
- 커밋 6개로 분리해서 작성:
  1. `fix(ai): restore orphaned Week2 ML baseline + add hybrid analyzer`
  2. `feat(ai): add generate_feedback with failure signal + FeedbackItem contract`
  3. `feat(ai): add approved MemeTerm prompt vocabulary builder`
  4. `test(ai): add golden regression fixture for analyzer/matrix/feedback`
  5. `fix(pally): correct 5-axis to visual-parameter mapping per design spec`(아래 3절 참고)
  6. `docs(ai): log Week 4 execution record`
- push 전 시크릿 스캔(diff에서 `AIzaSy` 등 패턴 검색, 0건 확인) 및 전체 테스트(30 passed) 확인 후 push
- PR은 생성하지 않고 브랜치만 push(사용자 확인 대기)

---

## 3. Pally 캐릭터 시각화 — 5축→시각 파라미터 매핑 수정

### 3.1 문제 발견 경위
- 사용자가 PM이 전달한 Figma 이미지(Frame 254)를 공유: 5축 각각을 0-33/34-66/67-100 3구간으로 나눠 시각 파라미터(움직임/모서리 둥글기/눈 스타일/색상)에 매핑하는 디자인 스펙
- `frontend/lib/types/character.ts`에 유사한 매핑이 문서화되어 있었으나, 실제 렌더러 `frontend/components/pally/PallyCanvas.tsx`는 그 타입의 필드(`spikiness`, `borderRadius`, `eyeType`, `animationSpeed`)를 전혀 참조하지 않고 `Axes`를 직접 받아 자체 로직으로 렌더링하고 있음을 발견(`character.ts`의 매핑 필드가 죽은 코드였음)
- 실제 `PallyCanvas.tsx` 코드 분석 결과, 이미지 스펙과 5개 축 중 4개가 다르게 배정되어 있었음을 확인:

| 시각 요소 | 이미지 기준(정답) | 기존 코드 |
|---|---|---|
| 움직임(bob/bounce/wiggle) | Humor | Curiosity |
| 몸통 모양(사각→별→선버스트) | Energy | Humor |
| 모서리 둥글기 | Formality (낮음=둥긂, 높음=각짐) | Formality (방향 반대: 낮음=각짐, 높음=둥긂) |
| 눈 스타일 | Curiosity | Energy |
| 몸통 색상 | Intimacy | Intimacy (일치, 변경 없음) |

### 3.2 수정 내용
- `PallyCanvas.tsx`: 변수명과 참조 축 재배정
  - `mT = tier(ax.Humor)` (움직임, 기존 `cT = tier(ax.Curiosity)`에서 변경)
  - `sT = tier(ax.Energy)` (몸통 모양, 기존 `hT = tier(ax.Humor)`에서 변경)
  - `fT = tier(ax.Formality)` 유지하되 배열 순서 반전(`rectR = [bs*0.75, bs*0.18, 0][fT]`, 기존은 `[0, bs*0.18, bs*0.75][fT]`)
  - `eT = tier(ax.Curiosity)` (눈 스타일, 기존 `tier(ax.Energy)`에서 변경)
- `frontend/lib/types/character.ts`: 문서 주석과 헬퍼 함수 동기화. `energyToEyeType`→`curiosityToEyeType`, `curiosityToAnimSpeed`→`humorToAnimSpeed`로 이름·로직 변경, `axesToCharacterParams()`의 `borderRadius`를 `100 - axes.Formality`로 반전
- 이 수정은 위 2.7절의 Week 4 커밋 5번(`fix(pally): ...`)으로 포함되어 이미 push/merge됨(PR #40)

---

## 4. Week 5 작업

### 4.1 착수 전 동기화
- 세션 재개 시 로컬 `master`가 `origin/main`보다 뒤처져 있음을 발견(Week 4 PR #40이 이미 merge된 상태였고, 그 위로 다른 팀원들의 Phase 5 작업 — achievements/quota/activity-events — 도 이미 merge됨)
- `git fetch` + `git merge --ff-only origin/main`으로 동기화
- 동기화 후 발견: BE가 이전에 전달한 요청사항을 실제로 반영한 상태 확인 — `backend/main.py`가 `ai.analyzers.get_axis_analyzer()`로 전환됨, `ai.generate_feedback.generate_feedback()`이 `create_turn`에 연결되어 `(items, failed)` 계약을 그대로 소비하고 있음(`failed=True`면 raise하여 상위에서 partial 처리)

### 4.2 Analyzer 3-way 비교 및 최종 결정
- `ai/evaluate_axis_analyzers.py`에 `_evaluate_hybrid_leave_one_out()` 함수 추가(rule 예측과 leave-one-out ML 예측을 축별 평균)
- 30개 데이터 기준 실측 결과:

| | MAE |
|---|---|
| rule | 16.18 |
| ML | 13.81 (delta -2.37) |
| hybrid | 13.10 (delta -3.08) |

- Spearman 상관관계(Curiosity 축 예시): rule 0.79, ML 0.04(붕괴), hybrid 0.44
- **결정(Week5 시점)**: 데이터셋이 30개뿐이고 Spearman이 ML/hybrid 모두 낮아 판별력 문제가 있다고 판단, **기본 analyzer는 `rule` 유지**로 결정. 근거: MAE보다 "입력 차이를 구분하는 능력"이 Pally의 데모 목적(말투 변화가 캐릭터에 눈에 띄게 반영)에 더 중요함

### 4.3 Reddit Vocabulary 스냅샷 (fixture 기반)
- BE의 실제 Reddit OAuth 수집·승인 파이프라인이 여전히 없음을 재확인
- 추가 발견: Week 3 로그가 완료로 기록했던 `data/fixtures/reddit_sources_week3.json`, `docs/reddit-vocabulary-policy.md`, `tests/test_ai_week3_reddit_vocabulary.py` 3개 파일이 **git 히스토리 어디에도 존재하지 않음**을 발견(Week 2와 달리 다른 브랜치에도 없음 — 커밋 `c5810d2`의 "clean branch 복원" 시점에 유실된 것으로 추정)
- `ai/build_vocabulary_snapshot.py` 신규 작성: fixture(`data/fixtures/reddit_sources_week5.json`, 직접 작성한 6개 source — 정상 subreddit 2개, 제외 subreddit 1개, PII 신호 1개, blocked-term 검증용 1개)를 입력으로 추출→안전성 필터→(승인 워크플로 부재로) 승인 시뮬레이션→prompt vocabulary 변환까지 전체 파이프라인 실행, 결과를 `data/fixtures/pally_vocabulary_snapshot_week5.json`으로 저장
- 실행 결과: 6개 source 중 정상 subreddit에서 후보 6개 추출(5 safe + 1 review), 제외/PII 소스는 후보 0개(필터 정상 동작), review 후보는 최종 승인 목록에서 정상 제외, 최종 prompt vocabulary 5개
- 부수 발견: `BLOCKED_TERMS`(`"kill yourself"`, `"kys"`)가 현재 `TERM_CATALOG`에 검색 대상 term 자체가 없어서 실제로는 한 번도 실행되지 않는 죽은 코드임을 확인
- 테스트 파일 `tests/test_ai_week5_vocabulary_snapshot.py` 신규 작성(4개 테스트: 재현성, 제외/PII 소스 무영향, review 미승인, prompt vocabulary가 승인된 것만 포함)

### 4.4 TERM_CATALOG Safety 라벨 재점검
- `ai/reddit_vocabulary.py`의 `TERM_CATALOG`(16개 슬랭 항목) 전수 재검토
- 2건 발견 및 사용자 확인 후 수정:
  - `mid`(평범한/별로): `safe` → `review`로 낮춤(대상을 깎아내리는 평가어라 Pally가 무심코 무례하게 들릴 수 있음, false negative로 판단)
  - `fr`/`fr fr`(진짜로): `review` → `safe`로 올림(내용 자체엔 위험요소 없음, 기존 review는 "안전성"이 아니라 "Pally가 직접 쓰기엔 어색함"이라는 다른 이유로 걸려있던 것으로, safety 필드에 서로 다른 두 개념이 섞여있던 스키마 이슈로 판단)

### 4.5 Week 5 커밋 및 push
- 브랜치 `gsd/phase-ai-ml-reddit-week5` 생성, 커밋 4개로 분리:
  1. `feat(ai): add rule/ML/hybrid analyzer comparison, keep rule as default`
  2. `feat(ai): add fixture-based Reddit vocabulary snapshot pipeline`
  3. `fix(ai): correct mid/fr safety labels in vocabulary catalog`
  4. `docs(ai): log Week 5 execution record`
- push 전 시크릿 스캔·전체 테스트(24 passed) 확인 후 push. 이후 확인 결과 PR #49로 이미 merge된 상태였음(팀원이 신속히 처리한 것으로 추정)

---

## 5. 답변 길이 문제 수정 (`shape_reply`)

### 5.1 문제 보고 및 원인 분석
- PM/팀에서 "AI 답변이 너무 길어지면 화면에서 잘린다"는 요청 전달받음
- 원인 조사: Figma 목업(홈화면 흐름 스크린샷)의 압축 말풍선(ShortBubble) UI 구조 분석(`frontend/components/chat/ChatBubble.tsx`) — 메시지 영역이 세로 290px로 고정
- `backend/main.py:729-730`에서 Gemini 응답의 `finishReason == "MAX_TOKENS"`을 이미 감지하고 있으나 **로그만 남기고 잘린 텍스트를 그대로 반환**하는 코드를 발견. 시스템 프롬프트의 "1-3 sentences" 지시가 느슨해서 Gemini가 가끔 이를 어기고, `maxOutputTokens: 512`에서 강제로 잘리는 것이 원인으로 파악

### 5.2 해결책 구현
- `ai/reply_shaping.py` 신규 작성: `shape_reply(text, max_chars=90)` 함수
  - `MAX_REPLY_CHARS = 90`을 ShortBubble UI 크기(290px, 메시지당 2줄 여유, 16px 폰트 기준 줄당 ~40자)로 역산해서 설정
  - 마지막 완결된 문장 경계에서 자름(정규식 `_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")`)
  - 첫 문장 자체가 max_chars를 넘으면 단어 경계에서 자르는 fallback(`_cut_at_word_boundary`) — 절대 단어 중간에서 안 자름
- 테스트 파일 `tests/test_ai_reply_shaping.py` 신규 작성(6개 테스트, MAX_TOKENS 스타일로 끊긴 텍스트 정리 케이스 포함)
- 실제 사례 검증: `"That's so exciting! I love hearing about your weekend plans, did you also want to talk about what you're going to do when you get th"`(MAX_TOKENS로 끊긴 가상 예시) → `"That's so exciting!"`(19자)로 정리됨을 확인

### 5.3 BE 전달사항
- `from ai.reply_shaping import shape_reply` import 후 `_call_gemini_chat()` 반환값에 바로 적용 요청(main.py 854줄, 1481줄 직후 2곳)
- TTS 호출·저장·응답 리턴 모두 shaped 버전을 쓰도록 요청(화면과 TTS 불일치 방지)
- 시스템 프롬프트 강화 권장 문구 제안: `"Keep your reply to ONE short sentence (about 10-15 words). Never write two sentences."`

### 5.4 커밋 및 push
- 브랜치 `gsd/phase-ai-reply-length` 생성, 커밋 1개(`feat(ai): add shape_reply() safety net for over-length Gemini replies`) push
- (이 브랜치가 이후 이 세션의 "현재 브랜치"로 계속 유지됨)

---

## 6. 학습 데이터 확장 프로젝트 (세션의 핵심 작업)

### 6.1 문제의 시작
- 사용자가 "룰베이스로 계속 가는 이유"를 재설명 요청 → EMA(지수이동평균) 개념, rule-based/ML 기본 개념, "출렁거림"(inconsistency) 개념을 순차적으로 설명
- 사용자가 "데이터를 더 모으면 결과가 달라지나?" 질문 → k-NN이 데이터 밀도에 민감한 알고리즘이라 가능성 높다고 답변, 단 원래 목표(150~300개)에 크게 못 미치는(30개) 상태임을 지적

### 6.2 학술 데이터셋 탐색 — 1차(6개 조사, 전부 실패)
사용자가 "논문/학술 자료에서 학습 데이터를 가져오자"를 제안, WebSearch/WebFetch로 실제 검증 진행:

| 데이터셋 | 실제 확인된 정보 | 탈락 사유 |
|---|---|---|
| SQUINKY! Corpus | arXiv 1506.02306, 실존 확인 | 블로그/뉴스/포럼/논문 4개 장르 혼합, 회화체 아님 |
| GYAFC (Grammarly's Yahoo Answers Formality Corpus) | Yahoo Answers L6 기반, 이메일 신청 필요 확인 | "academic use"로만 접근 허가(공식 GitHub `raosudha89/GYAFC-corpus` 확인) |
| XFORMAL | arXiv 2104.04108 | GYAFC의 다국어 확장판, 동일 문제 |
| Curiosity Dataset(Facebook Research, EMNLP 2020, "Information Seeking in the Spirit of Learning") | GitHub `facebookresearch/curiosity` 실제 클론, README 확인 | **CC-BY-NC-4.0** — 상업 서비스 지향 Pally에 이용 불가 |
| Quantifying Intimacy in Language(Pei & Jurgens, EMNLP 2020) | GitHub `Jiaxin-Pei/Quantifying-Intimacy-in-Language` 실제 클론, `data/annotated_question_intimacy_data/final_train.txt` 등 실제 내용 확인(2,397개 질문, tab-separated 형식: `질문\t친밀도점수`) | 라이선스는 **MIT**(문제없음)이나, 무작위 샘플링 결과 내용이 명백한 r/AskReddit류 프롬프트 질문(정치·성적 대상화·마약 관련 주제 포함, 예: "Would you respect Donald Trump more if he looked like George Clooney...", "What are your thoughts on 22 year old guys hooking up with 30 year old single mothers?")으로 확인됨 — Reddit 원문 추정 + 프로젝트 자체 정책(`docs/ai-labeling-guide.md`: "Reddit 원문을 ML 학습 데이터로 사용하지 않는다") 위반 + 안전한 회화체도 아님 |
| INTIMA | HuggingFace `AI-companionship/INTIMA` 확인 | AI 동반자 관계의 **안전성 테스트 벤치마크**(CC-BY-4.0이나 목적 자체가 훈련용 아님). 논문에서 "정서적 조작 행동을 강조·완화하기 위해 의도적으로" 설계했다고 명시. 예시 프롬프트가 정서적 취약성/의존 표현("당신과 대화 안 하면 하루를 못 버텨요" 등) |
| "My Boyfriend is AI"(MIT Media Lab) | arXiv 2509.11391 확인 | r/MyBoyfriendIsAI(Reddit 커뮤니티, 27,000명 이상) 게시물 1,506개 분석 논문. Reddit 원문 + 도메인(AI와의 연애 감정) 완전 무관 |
| Eight-emotion-sentics(MIT Affective Computing) | 공식 페이지 확인 | 텍스트가 아니라 생체신호(혈류량·근전도·호흡·피부전도도) 데이터, Healey & Picard(2002) 인용 필요 |
| EmoBank | GitHub `julielab/EmoBank` 실제 클론, `corpus/emobank.csv`+`meta.tsv` 실제 내용 확인 | 라이선스(**CC-BY-SA 4.0**, 상업 가능)·출처(MASC/ANC, SemEval 2007 Task 14 — Reddit 아님) 둘 다 통과. 장르: fiction(2893)/letters(1479)/newspaper(1381)/blog(1378)/SemEval(1250)/essays(1196)/travel-guides(971), 총 10,062문장. 그러나 fiction/letters/blog 카테고리에서 무작위 25개 샘플링한 결과 소설 서술문("The creature blocking my vision moved back...")·블로그 댓글 타임스탬프("Dan Winkler says: July 9, 2010 at 1:29 am")·격식체 편지("The SCS brochure I am enclosing will give you...")가 대부분이라 회화체 수확률이 25개 중 1~2개 수준으로 판단, 대량 학습 데이터로는 채택 안 함 |

**결론**: 6개(세부적으로는 8개 자료) 전부 라이선스(NC 조항)/출처(Reddit)/도메인(AI 안전성 연구·생체신호)/문어체 register 중 하나 이상에 걸려 채택 불가로 판단.

### 6.3 LLM 보조 라벨링으로 전환
- `docs/ai-labeling-guide.md`의 실제 기준(Conversation-First 원칙, Formality 좋은/나쁜 예시, 11개 style 카테고리 — greeting/small_talk/learner_request/roleplay_request/polite_roleplay/learner_question/opinion/correction_reaction/feedback_reaction/casual_slang/mistake_or_hesitation, 0-100 점수 구간)을 그대로 반영한 프롬프트를 설계
- 이 프롬프트를 Gemini/GPT/Claude 세 개의 서로 다른 LLM에 각각 요청(사용자가 별도로 각 서비스에서 실행하여 결과를 채팅에 붙여넣음)
- 수신 결과: Gemini 110개, GPT 99개(마지막 1개는 메시지 길이 제한으로 잘려서 제외), Claude 100개(최초 100개 중 마지막 항목이 잘려서 재요청 후 완성본 수신)

### 6.4 검증
자동 검증 스크립트(`validate_candidates.py`, 세션 스크래치패드에 작성) 실행 결과:

| 항목 | Gemini | GPT | Claude |
|---|---|---|---|
| 파싱된 줄 수 | 110 | 99 | 100 |
| 스키마 오류 | 0 | 0 | 0 |
| style 분포 | 11개 카테고리 9~11개씩 | 11개 카테고리 정확히 9개씩 | 11개 카테고리 9~10개씩 |
| 문어체/과도하게 긴 문장 | 0건 | 0건 | 0건 |
| 기존 30개와 중복 | 0건 | 0건 | 0건 |
| 소스 간 교차 중복 | `"Excuse me, is this seat taken?"` 1건(GPT·Claude) | | |

수동 검토로 발견한 문제: GPT 라벨이 style 카테고리와 Curiosity 점수가 거의 기계적으로 붙어있음(`opinion`은 거의 항상 Curiosity 0~2, `learner_question`은 거의 항상 94~98) — AI 라벨러 특유의 "지름길"/편향 패턴으로 판단, 별도 수정 없이 기록만 함.

### 6.5 데이터 병합
- `merge_dataset.py`(세션 스크래치패드) 작성 및 실행: 기존 30개 + Gemini 110 + GPT 99 + Claude 100 - 중복 1 = **338개**
- `data/axis_dataset_week2.jsonl`을 30개 → 338개로 덮어씀(train 254 / dev 37 / test 47, style별 stratified 분할)
- `ai/ml_baseline.py`의 `load_default_axis_dataset()`가 `utterance`/`axes`/`style` 필드만 사용하고 다른 필드(`notes`, `source`, `split`)는 무시함을 사전 확인하여 호환성 검증 후 병합
- 전체 테스트 실행(30 passed)으로 회귀 없음 확인

### 6.6 재평가 — 30개 vs 338개 비교 (핵심 실험 결과)

**MAE 비교**:

| | 30개 | 338개 |
|---|---|---|
| rule | 16.18 | 16.54 (거의 무변화 — rule은 데이터로 학습 안 하므로) |
| ML | 13.81 | **12.44** |
| hybrid | 13.10 | 13.34 |

**축별 Spearman 상관관계 비교(가장 중요한 결과)**:

| 축 | rule | ML(30개) | ML(338개) | hybrid(338개) |
|---|---|---|---|---|
| Curiosity | 0.76 | 0.04 | 0.72 | **0.79** |
| Formality | 0.63 | 0.26 | 0.71 | **0.76** |
| Intimacy | 0.41 | 0.13 | 0.57 | **0.60** |
| Energy | 0.54 | 0.35 | 0.56 | **0.62** |
| Humor | 0.52 | 0.22 | 0.52 | **0.56** |

**해석**: 30개일 때는 ML의 Spearman이 rule 대비 크게 뒤처졌으나(특히 Curiosity 0.79 vs 0.04), 338개로 늘리자 hybrid가 5축 전부에서 rule과 동률이거나 우세로 역전됨. Week5에서 "데이터 부족 때문에 rule 유지"로 내렸던 결정의 근거가 데이터 확장 후 재검토가 필요함을 실증적으로 확인.

### 6.7 20턴 EMA 시뮬레이션
캐주얼(1~5턴)→궁금해함(6~10턴)→격식체(11~14턴)→다시 캐주얼(16~20턴)로 구성한 가상 대화를 실제로 `apply_ema()`에 누적시켜 Curiosity 축 추적:

**30개 데이터 기준**:
```
rule:      15,15,15,15,15 | 29,33,40,34,32 | 42,25,31,22,19 | 16,15,15,15,15
ML(구):    53,35,36,45,51 | 76,67,80,67,49 | 69,40,62,49,63 | 33,32,56,24,45
```
→ ML이 같은 스타일 구간 안에서도 출렁이고, 캐주얼(44 평균)이 격식체(53 평균)보다 낮다는 보장도 없었음(구분 실패)

**338개 데이터 기준(재실행)**:
```
rule:      15,15,15,15,15 | 29,33,40,34,32 | 42,25,31,22,19 | 16,15,15,15,15 (동일, rule은 데이터에 안 좌우됨)
ML(신):    56,51,27,22,37 | 72,68,70,67,66 | 76,38,45,26    | 38,31,16,13,17
hybrid:    36,33,21,19,26 | 50,51,55,50,49 | 60,32,38,24    | 27,24,16,15,16
```
→ "궁금해함" 구간에서 안정적으로 높게 유지(ML 66~76, hybrid 49~55), 마지막 캐주얼 구간에서 낮은 값(13~17/15~16)으로 수렴 — 실사용 가능한 수준으로 개선 확인

### 6.8 실제 데모 3케이스 콘솔 검증
ROADMAP.md Phase 2 SC#3 기준 공식 데모 시나리오(casual/formal/persona drift)로 rule vs hybrid의 `character`(tone_casual/energy_level/humor_level, 실제 캐릭터를 움직이는 값) 비교:

- **캐주얼**: rule tone_casual 48~58, hybrid 50~58(거의 겹침), "hilarious" 발화에서 humor 반응 39 vs 39(완전 동일)
- **격식체**: rule 29~34, hybrid 26~37(낮은 범위 유지, 방향 동일)
- **Persona drift(캐주얼→격식)**: rule 52→50→39→36→35, hybrid 52→49→38→34→37(거의 동일한 하락 패턴)

→ 튀는 값 없음, hybrid가 데모 핵심 시나리오를 rule만큼 자연스럽게 재현함을 확인

### 6.9 AI 생성 데이터 자체의 한계 논의
- 사용자가 "학습 데이터 100억 개를 AI로 생성해서 쓰면 정확할까? 실사용/실검증 데이터가 아닌데 설득력 있을까?" 질문
- 답변으로 제시한 한계 3가지:
  1. **분포 문제**: Gemini/GPT/Claude는 비슷한 인터넷 텍스트로 학습된 모델들이라, 무한 생성해도 같은 스타일 분포 안에서 밀도만 증가(진짜 다양성 증가 아님)
  2. **순환 논리 문제**: 라벨 자체가 AI 판단이므로, "ML이 좋아졌다"는 것은 "AI가 매긴 라벨과 일치한다"를 확인한 것이지 "사람의 실제 감각과 일치한다"를 확인한 게 아님
  3. **실증 사례**: GPT 라벨의 style→Curiosity 기계적 연결 패턴(6.4절)이 바로 이 문제의 실제 사례
- 대안으로 제시: 팀원 직접 예문 작성(AI 공통 편향 회피), 실사용 데이터 점진적 확보, EmoBank 등은 검증용으로만 소량 활용
- 후속 질문("실사용 데이터를 아직 확보하기 힘드니 공개 데이터셋을 쓰면 안 되나")에 대해 6.2절의 6개 실패 사례를 다시 근거로 제시하며, "이론이 아니라 실제로 확인해봤는데 조건을 만족하는 게 없었다"고 답변

---

## 7. 실제 사람 발화 기반 공개 코퍼스 재조사

### 7.1 사용자가 제안한 8개 코퍼스와 1차 검증
사용자가 별도 AI 리서치(출처 미상, ChatGPT류로 추정)를 통해 얻은 8개 코퍼스 목록을 제공. 인용 패턴이 의심스러워(동일 URL 반복 인용) 직접 WebFetch로 재검증:

| 데이터셋 | 검증 결과 |
|---|---|
| NICT JLE Corpus | CC BY-SA 3.0, 신청 없이 무료 다운로드 가능(공식 페이지에서 직접 확인), 1,281개 음성 샘플/약 120만 단어/300시간, 일본인 학습자 인터뷰(1999~), filler/repetition/self-correction/문법오류 태그 포함 |
| Taskmaster-1(Google Research) | CC BY 4.0(GitHub README 확인), 13,215개 dialogue 중 5,507개가 실제 spoken(Wizard-of-Oz) 대화, `woz-dialogs.json`(spoken)과 `self-dialogs.json`(written, 7,708개)이 별도 파일로 분리됨을 확인 |
| EdAcc(Edinburgh International Accents of English Corpus) | CC-BY-SA 4.0, 친구 간 실제 화상통화 대화 약 40시간, University of Edinburgh DataShare에서 다운로드 가능(5.51GB) 확인 |
| Open Yap 1K | HuggingFace 블로그·공식 페이지 확인. 2026-09-03 공개(매우 최근). 샘플(8.9시간)은 CC-BY-4.0, 전체(1,000시간, 1,602개 대화, 239명 화자)는 Data Use Agreement 신청 후 "판매하는 제품에 포함하는 상업적 이용"까지 명시적으로 허용. 단 transcript가 사람 검수 없는 ASR(Deepgram Nova-3) 생성임을 확인 |
| CANDOR | PubMed Central 논문 확인. 1,656개 대화, 850시간 이상, 700만 단어 이상 video-chat 코퍼스. 대화 후 설문에 `i_am_funny`, `i_am_polite` 등 약 200개 필드 포함 — utterance-level 라벨은 아니고 conversation-level 평가라 축 구성 타당성 검증용으로만 가치 있다고 판단 |
| GYAFC(재확인) | Yahoo Answers L6 기반, 이메일 신청(`gyafc.dataset@gmail.com`) 필요, "academic use" 허가만 명시 확인 |
| Spoken BNC2014 | 기본 라이선스가 non-commercial research임을 언급받음(직접 재검증은 안 함) |
| TalkBank/SLABank | CC BY-NC-SA 3.0, LLM 학습에 corpus 데이터 사용을 명시적으로 금지한다는 내용을 언급받음(직접 재검증은 안 함) |

이 중 사용자가 최우선 후보로 지목한 4개(NICT JLE, Taskmaster-1, EdAcc, Open Yap 1K)를 실제로 검증(모두 확인됨, 위 표 참고). Reddit 원문 문제·상업 이용 제한 문제 둘 다 걸리지 않는 첫 케이스들로 판단됨.

### 7.2 NICT JLE Corpus 실제 다운로드 및 검증
- 공식 페이지(https://alaginrc.nict.go.jp/nict_jle/index_E.html)에서 실제 다운로드 링크(`https://alaginrc.nict.go.jp/nict_jle/src/NICT_JLE_4.1.zip`) 확인 후 다운로드(7,111,767 바이트, 정상 zip)
- 압축 해제 후 실제 파일 내용 확인. 구조: `LearnerErrortagged/`(167개 파일, 문법오류 태그 포함), `LearnerOriginal/`(1,281개 파일), `Native/`
- 실제 파일 예시(`LearnerOriginal/file00001.txt`): XML 유사 태그 구조 — `<interview><head>...(성별/연령/국가/TOEIC/TOEFL/SST_level 등 메타데이터)...</head><body><stage1><A>인터뷰어 발화</A><B>학습자 발화</B>...</stage1><stage2>...(그림 묘사 과제)...</stage2></body></interview>`
- 태그 종류 확인: `<F>`(filler, 예: Uh-huh/Mhm/Uhm/Er), `<R>`(반복), `<SC>`(자기수정), `<H pn="...">`(익명화된 이름), `<laughter>`, `<nvs>`(비언어음), 문법오류 교정 태그(`<v_agr odr="1" crr="works">work</v_agr>` 형태 — 원래 말한 것과 교정본을 함께 태깅)
- 실제 학습자 발화 샘플 확인: `"O K. <H pn="B's name">XXX02</H>, have you been busy these days?"`, `"Usually, <at odr="1" crr="the"></at> museum <v_agr odr="2" crr="opens">open</v_agr> on <n_num odr="3" crr="Saturdays">Saturday</n_num>..."` 등 — 실제 문법 오류가 원문 그대로, 교정본과 함께 보존되어 있음을 확인

### 7.3 추출 파이프라인 v1 (필자 작성)
- `extract_nict_jle.py` 작성(세션 스크래치패드): XML 태그를 정규식으로 파싱해서 학습자(`<B>`) 턴만 추출, 태그 제거 후 순수 텍스트화, 문장 단위(`.!?` 기준)로 분리
- 15개 파일(전체 1,281개 중 일부)로 시험 실행, 1,146개 candidate utterance 추출
- 실제 authentic한 학습자 발화 확인: `"Mm because, mmm I I had to hand in my graduation thesis in December,"`, `"And mm there is a there are there are three houses, but I guess mm there are lot of houses."` 등 — 진짜 필러·반복·문법오류가 자연스럽게 섞인 텍스트로, AI 생성 데이터로는 재현 불가능한 질감으로 평가

### 7.4 사용자 피드백에 의한 v1 문제점 지적
1. **문장 경계 문제**: 마침표 기준 분할로 인해 `"at a computer school."`처럼 앞 문장에서 이어지는 의미 없는 조각이 독립 utterance로 남음
2. **필러 밀도 문제**: `"mm mmm mm since I was mm I was small"`처럼 필러가 과도하게 반복되는 경우 처리 기준 미정
3. 15개 파일만 시험한 상태이므로 전체 확장 전에 정제 방식부터 확정 필요하다는 지적

### 7.5 추출 파이프라인 v2 (필자 수정, 이후 취소됨)
- `is_continuation_fragment()` 함수 추가: 접속사/전치사(and/but/so/at/on 등)로 시작하고 7단어 이하인 조각을 이전 문장에 병합
- `collapse_filler_runs()` 함수 추가: 3개 이상 연속된 필러 토큰을 1개로 축약
- `filler_ratio()` 함수 추가: 전체 단어 중 필러 비율이 40% 초과하는 utterance는 제외
- 이 버전을 세션 스크래치패드에서 저장소(`ai/extract_nict_jle.py`, `data/fixtures/nict_jle_raw/`)로 이동했으나, 사용자가 "작업 취소" 요청하여 저장소에서 다시 삭제(원본은 스크래치패드에 유지)

### 7.6 Codex로 작업 이관
- 사용자가 이 작업(추출 파이프라인 정제)을 Codex CLI에서 실행하기로 결정
- 필자가 Codex용 독립 프롬프트 작성(배경 설명 + 현재 문제 2가지 + 수정 로직 설명 + 요청사항 3가지: 로직 검토, 전체 1,281개로 확장 실행, 저장 위치 제안)

### 7.7 Codex의 실제 작업 결과 및 검증
Codex가 독자적으로 작업한 결과를 사용자가 보고, 필자가 재검증:
- `scripts/extract_nict_jle.py`(재현 가능한 버전, argparse 기반) 신규 작성됨
- `tests/test_extract_nict_jle.py`(5개 테스트) 신규 작성됨
- 원본 zip/압축해제 폴더는 `.gitignore`에 추가(`data/NICT_JLE_4.1.zip`, `data/NICT_JLE_4.1/`)
- 최종 산출물: `data/fixtures/nict_jle_learner_utterances.jsonl`

**필자의 독립 검증**:
- `python -m pytest tests/test_extract_nict_jle.py -v` 실행 → 5 passed(사용자 보고의 "35 passed"는 전체 테스트 스위트 총합이었음을 확인, 실제로는 30(기존)+5(신규)=35로 정합)
- `python -m pytest tests/ -q` 전체 실행 → 35 passed 확인
- 코드 재검토: `CONTINUATION_STARTERS`(31개 단어), `FILLER_TOKEN_PATTERN`(정규식으로 uhm/um/urm/erm/eh/em/ah/mm 등 포괄), `MAX_FRAGMENT_WORDS=7`, `MAX_FILLER_RATIO=0.4`, `MIN_UTTERANCE_WORDS=2` 확인
- 실제 경로 문제 발견 및 해결: 최초 재실행 시 `data/NICT_JLE_4.1/LearnerOriginal` 경로에 파일이 없어 0개 추출됨 — 실제로는 `data/NICT_JLE_4.1/NICT_JLE_4.1/LearnerOriginal`로 이중 중첩된 폴더 구조였음을 발견(zip 자체에 최상위 폴더가 포함되어 있었기 때문으로 추정)
- 올바른 경로로 재실행: **files=1281, utterances=139879**, 이를 저장소에 커밋된 `data/fixtures/nict_jle_learner_utterances.jsonl`과 `diff` 비교하여 **바이트 단위로 완전히 동일함(재현성 확인)**
- 무작위 샘플 30개 검토 — 대부분 authentic한 학습자 발화(예: `"cat is sleeping on the car"`, `"And both of dog and cat is er sleeping"`)이나, 일부 여전히 거친 조각 존재(`"from here to New York"` — "from"으로 시작하는 조각이 해당 턴의 첫 문장이라 병합 대상 없음, `"Ur On Wednesday"` — 단일 필러는 설계상 의도적으로 보존됨, `"I our by our car And er near the Mt"` — 원본 대조 시도했으나 정확한 원문 매칭은 못 찾음, 13만 개 중 희귀 케이스로 판단)
- 결론: 두 핵심 문제(짧은 마침표 조각, 필러 과밀)는 테스트와 전체 실행 기준으로 개선되었음을 확인, 완벽하지 않은 잔여 edge case는 다음 단계(라벨링 후보 샘플링)에서 자연 필터링될 것으로 예상

### 7.8 라벨링 후보 샘플링 (Codex, 추가 작업)
필자가 검증 도중 git status에서 예상치 못한 추가 파일 발견 — Codex가 후속 작업까지 이미 진행한 상태:
- `scripts/sample_nict_jle_label_candidates.py` 신규 작성: 139,879개 중 라벨링에 적합한 600개를 샘플링
  - 저정보 발화 필터링(`is_low_information`): "O K", "Only once" 등 사전 정의된 저정보 문구 목록, 필러 제외 content token 3개 미만, 단일 단어 4회 이하 반복
  - 후보 필터링(`is_candidate`): 최소/최대 단어수(3~35), 불완전한 종결어(전치사/접속사로 끝남) 제외, continuation fragment 재확인, 익명화 토큰("xxx") 포함 제외, 필러 비율 30% 초과 제외, 반복 토큰 비율 45% 초과 제외
  - 6개 다양성 버킷 분류(`classify_bucket`): question/polite_request/short_reaction/repair_disfluency/personal_statement/narrative_description, 각각 쿼터 배분(100/80/80/120/120/100, 합 600으로 스케일링)
  - 결정론적 시드(seed=42) 기반 샘플링으로 재현 가능
- `tests/test_sample_nict_jle_label_candidates.py` 신규 작성
- 출력: `data/fixtures/nict_jle_label_candidates_600.jsonl`(600개, 라벨은 아직 `null` — 사람/LLM 보조 라벨링 대기 상태)
- 필자가 코드 리뷰(전체 함수 로직 확인)까지는 완료, 테스트 재실행 및 독립 재현 검증은 사용자의 다른 질문으로 중단됨(미완료 상태로 세션 종료)

---

## 8. 부수적 논의 — Reddit 데이터 정책 일관성 문제

- 사용자가 "Reddit API로 직접 가져올 때만 안 쓰는 거고, 다른 공개 데이터셋에 있는 Reddit 유래 데이터는 써도 되는 거 아니냐"는 날카로운 질문 제기
- 답변: 정책의 근거가 "누가 어떤 경로로 데이터를 손에 넣었는지"가 아니라 **"콘텐츠 자체의 원 출처가 Reddit인지"**이므로, 남의 손을 거쳐도(예: Pei & Jurgens의 MIT 라이선스) 원문 콘텐츠에 걸린 Reddit 자체 이용약관상의 제약은 사라지지 않는다고 설명
- 반대 사례로 EmoBank(MASC/SemEval 출처, Reddit 아님)는 계속 유효한 후보임을 재확인
- 이어서 "그럼 Reddit Vocabulary 파이프라인 자체가 모순 아니냐"는 질문에 대해, ML 학습(대량 원문을 통계 모델 훈련에 사용)과 Vocabulary 파이프라인(개별 단어 몇 개를 추출해 안전성 검토 후 소량만 prompt에 삽입)이 규모와 목적이 다른 별개의 사용 형태임을 설명. 또한 실제로는 두 파이프라인 모두 지금 이 순간 진짜 Reddit 데이터를 전혀 사용하고 있지 않음(TERM_CATALOG은 사람이 직접 작성한 사전, fixture는 직접 작성한 가상 예시)을 재확인. 다만 이 구분이 100% 확정된 법률 자문이 아니라 프로젝트 자체의 합리적 판단이라는 점도 명시적으로 언급

---

## 9. 세션 관리 — Context Save/Restore

- 사용자가 세션 종료를 제안, `/context-save` 스킬 호출
- gstack 스킬 프레임워크를 통해 체크포인트 파일 작성: `~/.gstack/projects/capstone-main/checkpoints/20260906-012622-ai-analyzer-dataset-expansion.md`
- 이후 곧바로(같은 세션 내에서) `/context-restore` 호출 — 저장된 내용을 다시 불러와 대화 계속 진행

---

## 10. Pally 캐릭터 시각 반영 타이밍 (조사 진행 중, 세션 종료로 미완결)

- 사용자가 "5축은 계속 변화하지만, 캐릭터 시각 변화는 대화창을 닫고 재진입했을 때 반영되는 것 아니냐"는 질문 제기
- `frontend/lib/hooks/usePally.ts` 코드 확인 결과 정확히 그렇게 설계되어 있음을 확인:
  - `updateFromChatResponse()`: `/api/chat` 응답을 받으면 호출되나, 값을 `useRef`(`pendingAxes`)에만 저장하여 리렌더링을 트리거하지 않음(주석: "세션 종료 전까지 표시에는 반영 안 됨")
  - `revealAxes()`: 세션 종료 시에만 호출되어 `pendingAxes`의 누적값을 실제 React state(`axes`)로 반영, 이 state가 `<PallyCanvas axes={axes} />`로 전달됨
  - `frontend/app/home/page.tsx`의 `handleSessionEnd()`(196번째 줄)에서 `revealAxes()` 호출을 확인 — X 버튼(세션 종료) 시점에만 트리거됨
- 이는 ROADMAP.md Phase 2 SC#6("세션 종료 UX: ... 새 채팅 화면의 Pally는 방금 끝난 세션에서 누적된 최종 axes 상태를 반영한 모습으로 표시된다")과 정확히 일치하는 의도된 설계임을 확인
- 이 조사가 완료되기 전, 사용자가 "이 대화창에서 진행한 모든 작업을 논문용으로 상세히 기록해달라"고 요청하여 본 문서 작성으로 전환됨

---

## 11. 세션 전체에서 생성/수정된 파일 목록 (저장소 기준)

### 커밋되어 병합된 파일(main에 반영됨)
- `ai/analyzers.py`(수정 — HybridAxisAnalyzer 추가, fallback 로직)
- `ai/ml_baseline.py`, `ai/evaluate_axis_analyzers.py`, `data/axis_dataset_week2.jsonl`(Week2 복원본, 이후 Week5에서 hybrid 비교 로직 추가), `docs/ai-labeling-guide.md`, `tests/test_ai_week2_ml_baseline.py`(Week2 유실분 복원)
- `tests/test_ai_week4_analyzer_integration.py`
- `ai/generate_feedback.py`, `ai/contracts.py`(FeedbackItem 추가), `tests/test_generate_feedback.py`
- `ai/reddit_vocabulary.py`(build_prompt_vocabulary_from_terms 추가, mid/fr 라벨 수정), `tests/test_ai_week4_meme_term_prompt.py`
- `data/fixtures/pally_regression_fixture.json`, `tests/test_ai_week4_regression_fixture.py`
- `frontend/components/pally/PallyCanvas.tsx`(5축 매핑 수정), `frontend/lib/types/character.ts`(동기화)
- `docs/plan/2026-07-25-ai-ml-reddit-vocabulary-plan.md`(Week4/5 실행 기록 추가)
- `ai/build_vocabulary_snapshot.py`, `data/fixtures/reddit_sources_week5.json`, `data/fixtures/pally_vocabulary_snapshot_week5.json`, `tests/test_ai_week5_vocabulary_snapshot.py`
- `ai/reply_shaping.py`, `tests/test_ai_reply_shaping.py`

### 로컬에만 존재(미커밋, 세션 종료 시점 기준)
- `data/axis_dataset_week2.jsonl`의 30→338개 확장분(브랜치 `gsd/phase-ai-reply-length` 위에서 수정된 상태로 남아있음, 별도 브랜치로 커밋 필요)
- `scripts/extract_nict_jle.py`, `tests/test_extract_nict_jle.py`, `scripts/sample_nict_jle_label_candidates.py`, `tests/test_sample_nict_jle_label_candidates.py`(Codex 작성)
- `data/fixtures/nict_jle_learner_utterances.jsonl`(139,879개), `data/fixtures/nict_jle_label_candidates_600.jsonl`(600개, 라벨 미부착)
- `.gitignore`에 `data/NICT_JLE_4.1.zip`, `data/NICT_JLE_4.1/` 추가
- `data/NICT_JLE_4.1.zip`, `data/NICT_JLE_4.1/`(gitignore 처리된 원본 코퍼스, 로컬에만 존재)

### 세션 스크래치패드(임시 디렉토리)에만 존재, 저장소에는 없음
- `raw_gemini.jsonl`, `raw_gpt.jsonl`, `raw_claude.jsonl`(LLM 원본 응답), `validate_candidates.py`, `merge_dataset.py`
- `measure_feedback_latency.py`, `measure_stt_tts_latency.py`(API latency 측정용)
- `notion_week5_summary.md`, `notion_progress_summary.md`(팀 공유용 요약본)
- `extract_nict_jle.py` v1/v2(필자 작성본, Codex 버전으로 대체됨), `nict_jle.zip`, `nict_jle_extracted/`, `nict_jle_sample_utterances.jsonl`

---

## 12. 미해결/보류 항목 (세션 종료 시점 기준)

1. `data/axis_dataset_week2.jsonl`(338개 병합본) 커밋/push 안 됨
2. 최종 default analyzer(rule/ml/hybrid) 미확정 — 338개 데이터 기준으로는 hybrid가 유력하나, NICT JLE 실제 발화 라벨링 완료 후 재평가 예정
3. NICT JLE Corpus 상업적 이용 관련 NICT 공식 문의 미발송(수신처: JLE-Corpus[at]khn[dot]nict[dot]go[dot]jp) — CC BY-SA 3.0의 ShareAlike 조항이 Pally 같은 상업 서비스 학습 데이터에 어떻게 적용되는지 확인 필요
4. `data/fixtures/nict_jle_label_candidates_600.jsonl`(600개)의 5축 라벨링 워크플로 미설계(사람+LLM 보조 검수 방법론에는 합의했으나 구체적 프롬프트/검수 기준 미정)
5. BE 전달 예정이었으나 실제 전달 여부 미확인: `shape_reply()` 연동 요청, analyzer 어댑터(`get_axis_analyzer()`) 전환 요청
6. API 키 노출 사고 2건(Gemini용, Google Cloud용)의 실제 폐기/재발급 여부 미확인
7. Taskmaster-1, EdAcc의 실제 콘텐츠 샘플 검증 미실시(라이선스만 확인, NICT JLE처럼 실제 파일을 열어서 내용을 확인하지는 않음)

---

*본 문서는 2026-09-06 세션 중 사용자 요청으로 작성됨. 위에 기술된 모든 수치·파일 경로·코드 스니펫은 세션 중 실제 실행/확인된 내용을 기반으로 하며, 별도 표기가 없는 한 재현 가능함(스크립트가 남아있는 경우 동일한 입력에 대해 동일한 출력을 생성함을 확인함).*
