# 세션 인계 메모 — 2026-10-12 (배터리 종료로 긴급 저장)

다음 세션 시작 시 이 파일을 먼저 읽을 것. 브랜치: `feat/pally-opener-ai`.

## 지금 당장 할 일 (제일 중요, 미완료 상태)

`scripts/build_purpose_v3_combined_train.py`에서 코덱스가 방금 실제 버그 3개를 찾았고, **아직 하나도 안 고쳤다.** 다음 세션은 이것부터 고쳐야 한다.

### 버그 1 (제일 심각) — 회의 그룹 누출
`build_seed80_rows()`(약 117번째 줄)에서 `source_group = row.get("source_id")`로 넣고 있는데, 이 `source_id`는 **회의 ID가 아니라 발화 ID**다(예: `ES2005d.A.dialog-act.dharshi.52`). 그래서 그룹 중복 체크가 무의미했고, 실제로는:
- eval 파티션(31개)과 combined 학습셋 사이에 **회의 8개**가 겹침
- train/dev 분리에서도 **회의 8개**가 겹침

**고치는 법**: `source_id`를 `.`로 나눠서 첫 세그먼트만 `source_group`으로 써야 한다(예: `ES2005d.A.dialog-act.dharshi.52` → `ES2005d`). AMI/ICSI 쪽 다른 코드(`source_record_id`)도 같은 컨벤션 쓰는 걸 확인했음(`Bmr019.H.dialogueact1720` → `Bmr019`).

### 버그 2 — 빈 axes 행이 로더를 깨뜨림
워크북 28번 항목(`ES2009a.A.dialog-act.vkaraisk.213`)이 F/H/C 셋 다 `context_insufficient+provisional`이라 `axes={}`로 남는데, 이 상태로 출력에 그대로 들어가 있다. `ai/ml_baseline.py::_load_jsonl_axis_dataset(allow_partial=True)`가 `min_axes=1`을 요구해서 **로드 시점에 ValueError로 터진다.**

**고치는 법**: `build_v3_rows()`에서 axes가 끝까지 비면 그 행 자체를 출력에서 빼고 카운트만 남겨라.

### 버그 3 — context_insufficient인데 score_status가 비어서 안 걸러짐
현재 조건은 `case_type == "context_insufficient" and score_status == "provisional"`일 때만 축을 뺀다. 그런데 신규 150개 워크북에 **21행·35개 축**(Formality 21개, Curiosity 14개)이 `case_type=context_insufficient`인데 `score_status`가 그냥 비어있다(None) — 조건을 안 타서 그대로 "final"로 포함돼버렸다.

**고치는 법**: 조건을 `case_type == "context_insufficient"` 하나로만 바꿔라(score_status 값과 무관하게 제외). 주의: 이건 신규 150개에만 적용 — 기존 100개 시드(80개 train)는 사용자가 이미 "case_type/score_status 비어있는 거 전부 final로 취급"이라고 명시적으로 확정했으니 그 정책은 그대로 둔다(건드리지 마라).

### 이 세 개 고친 뒤 할 일
1. `scripts/build_purpose_v3_combined_train.py` 재실행 → `scripts/build_purpose_v3_dev_split.py` 재실행
2. 코덱스로 다시 교차검증(이번엔 "회의 ID 기준" 그룹 누출을 반드시 다시 확인하라고 명시할 것 — 문자열 교집합만 보지 말고)
3. 통과하면 v3.0 §7(모델 비교: TfidfKnn vs Ridge 어댑터[새로 만들어야 함, 논문 Ridge 번들이 이 스키마랑 안 맞음] vs RuleBasedAxisAnalyzer vs week2 포함/제외 ablation)로 진행
4. §7.1 게이트 측정 (구간 재현율, 인위적 확장 방지 등 — `docs/AI_TACTIC/Pally_RUBRIC_v3.1_md` §3 근처에 정리돼 있음)
5. §8 배포 어댑터 교체

## 전체 맥락 요약

### 우선순위 (사용자 확정, 변경 없음)
① Intimacy(완료) → ② F/H/C 능동학습(지금 이 단계, 라벨링은 끝났고 모델 재학습 파이프라인 구축 중) → ③ Energy(음성 억양, 별도 트랙으로 병행 진행 중)

### ① Intimacy — 완료
`ai/intimacy.py` (세션 수 기반 포화곡선), `backend/main.py`에서 EMA 이후 덮어쓰기로 연결 완료. 손댈 필요 없음.

### ② F/H/C — 라벨링은 완료, 모델 재학습 파이프라인 구축 중
- **라벨링 신뢰도 사고**: 150개 중 110개(기존 40개 제외)를 채점하면서 사용자가 "완료"라고 세 번 제출했는데 전부 AI 생성 라벨을 사람 라벨로 위장한 것이었음(`label_source` 필드 자체가 `ai_generated_provisional_not_human`이라고 적혀있었거나, 같은 Humor 분포가 파일명만 바뀌어 반복됨). 세 번째 지적 후 사용자가 실제로 다시 작업해서, item114 Humor 80→25로 정확히 고치는 등 진짜 재검토의 증거가 나왔고, 이후 반복 수정을 거쳐 **최종적으로 150/150 완료, `label_source=single_rater_v3_eunheay`로 통일, 실제 품질도 스팟체크 통과**. 이제 신뢰 문제는 해결된 상태 — 다음 세션에서 다시 의심할 필요 없음, 단 위 버그 3개(데이터 파이프라인 버그이지 라벨 품질 문제 아님)는 고쳐야 함.
- 최종 워크북: `data/fixtures/pally_purpose_v3_labeling_workbook.xlsx` (canonical, 150/150, `채점기준` 탭에 v2.2 전체 요약 있음)
- 중간 파일들(`pally_purpose_v3_labeling_filled.xlsx`, `_scored.xlsx`, `_eunheay.xlsx`, `_eunheay_2/3/4.xlsx`)은 전부 과거 시도 흔적, 지워도 됨(워크북에 이미 다 반영됨).
- 만든 스크립트: `scripts/build_purpose_v3_combined_train.py`(150라벨+기존100중train80 결합 → `pally_purpose_v3_combined_train.jsonl`, 현재 버그 있음), `scripts/build_purpose_v3_dev_split.py`(그룹 단위 train/dev 분리 → `pally_purpose_v3_train_dev_split_{train,dev}.jsonl`, 상위 버그로 인해 재실행 필요)
- 보호된 파일(절대 건드리지 말 것): `data/fixtures/pally_purpose_v3_eval_partition.jsonl` (31개, 최종 평가 1회용)

### ③ Energy — 별도 백그라운드 에이전트 진행 중
이번 세션에서 Agent를 하나 띄워서(`subagent_type: general-purpose`) pYIN 기반 피치 변화량 측정 파이프라인을 코덱스와 교차검증하며 만들게 시켰다. **이 에이전트가 세션 종료 시점까지 완료 안 됐을 수 있다** — 다음 세션에서 `ListAgents`로 살아있는지 확인하고, 있으면 이어서 메시지 보내고, 없어졌으면 아래 내용으로 새로 지시할 것.

**이미 발견한 것(에이전트에게 인계한 내용)**:
- librosa 1.0.0 설치 완료(`.venv`)
- CREMA-D(ODbL 1.0, 상업 이용 가능, 코덱스가 공식 라이선스 확인함)에서 같은 화자·같은 문장·다른 감정강도 쌍 2개 다운로드 완료: `.context/energy-audio-test/1001_IEO_HAP_{LO,HI}.wav` — **GitHub LFS 주의**: `raw.githubusercontent.com`은 130바이트짜리 포인터 텍스트만 줌, 반드시 `media.githubusercontent.com/media/...`로 받아야 실제 WAV가 옴.
- pYIN 파라미터 문제 발견: `frame_length=1024, hop_length=160`(10ms 해상도 노리고 설계)으로 하면 **두 파일 다 유성음 프레이임 0개**. 기본값(`frame_length=2048`)으로는 일부 검출됨. `frame_length=2048, hop_length=160`으로는 LO는 여전히 0개, HI는 41% 검출(median F0=232.4Hz, R20-80=12.54반음). **원인 미규명** — YIN 계열 알고리즘이 `frame_length >= 2*sr/fmin` 같은 제약이 있을 수 있다는 가설을 에이전트에게 조사하라고 지시해둠.
- `voiced_prob` 임계값(원래 설계는 tau=0.6)이 이 데이터에서는 거의 항상 0.01~0.15 수준이라 사실상 못 씀 — `voiced_flag`만 써야 할 것으로 보임.
- 설계 문서: `docs/AI_TACTIC/Pally_RUBRIC_v3.0_md` §2, `docs/AI_TACTIC/Pally_RUBRIC_v3.1_md` §11·§19.5 (pYIN 1차 특징, 반음 변환, 20-80백분위, 실패시 Energy=null 명시 반환 등 — 설계 자체는 바꾸지 않음)
- AMI/ICSI 실제 오디오로 확장할 때 쓸 시간 정보는 이미 로컬에 있음: `data/fixtures/ami_utterances.jsonl`, `icsi_utterances.jsonl`에 `source_record_id`로 조인하면 시작/종료초가 나옴(예: `IS1004b.B.dialog-act.dharshi.77` → 797.61–805.07초)
- 공식 오디오 다운로드처: https://groups.inf.ed.ac.uk/ami/download/ , https://groups.inf.ed.ac.uk/ami/icsi/download/ (CC BY 4.0, 상업 이용 가능, 회의당 수백MB~GB라 1-2개 회의만 받을 것)
- 정식 코드(`ai/`)는 아직 쓰지 말고 `.context/energy-audio-test/`에서 1회성 스크립트로 검증 계속하라고 지시함.

### 루브릭 문서 체계 (중요, 혼동 방지)
- `docs/AI_TACTIC/Pally_RUBRIC_v2.2_md`: **측정 정의 고정**(F/H/C 가중치·앵커·채점식). 절대 안 바뀜. 라벨링은 전부 이 기준.
- `docs/AI_TACTIC/Pally_RUBRIC_v3.0_md`: 능동학습 데이터 확보·평가 프로토콜(v2.2 위에 얹힌 운영 문서, v2.2를 대체 안 함)
- `docs/AI_TACTIC/Pally_RUBRIC_v3.1_md`: 강의 근거 + 선행연구(R01-R12) 통합 문서. §3에 출력 연결(아래 참고) 검증 기록, §20에 Energy 착수 시점 최종 결정(3주차 유지, 이번 세션에서 병행 착수로 사실상 앞당김) 있음.
- 사용자가 "이제 v2.2 참고 안 하고 v3 기준으로" 주장한 적 있는데, **이건 틀린 주장**이었고 v3.0/v3.1 문서 자체가 "v2.2 측정 정의 그대로 유지"라고 명시돼 있음 — 다음 세션에서 또 이 얘기 나오면 같은 설명 반복할 것.

### `ai/matrix_engine.py` 재설계 — 완료, 테스트 통과, **미커밋**
- `tone_casual = 100 - Formality`, `energy_level = Energy`, `humor_level = Humor`로 전면 교체(기존 가중합 폐기) — 화면(Canvas)과 대화 프롬프트가 같은 축을 다르게 해석하던 버그를 고친 것.
- `tests/test_matrix_engine.py` 6개 테스트, 전부 통과(**`PYTHONPATH=.` 필요**, 안 그러면 `ModuleNotFoundError: ai`).
- `git status`로 확인하면 `M ai/matrix_engine.py` — 작업트리에만 있고 커밋 안 됨. 사용자가 커밋하라고 하면 그때 하면 됨(먼저 하지 말 것).

### 지켜야 할 규칙 (CLAUDE.md, 이번 세션에서 실제로 걸렸던 것들)
- `git add .` 금지, 파일 개별 스테이징
- 커밋 메시지 끝에 `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`
- 사람 라벨에 AI 생성 라벨 섞는 거 절대 안 됨 — 위 라벨링 사고 참고, 이미 해결됐지만 비슷한 패턴 다시 보이면 바로 의심할 것
- 코덱스 호출 패턴: `codex exec "$(cat 프롬프트파일)" -c sandbox_mode="read-only" -c model_reasoning_effort="high" --json < /dev/null > 출력.jsonl 2>&1`를 Bash 도구로 `run_in_background: true`로 실행. **heredoc(`cat > file << 'EOF'`)과 `codex exec`를 같은 Bash 호출에 묶지 말 것**(백그라운드 처리 중 깨짐, 이미 한 번 겪음). `< /dev/null` 반드시 붙일 것(안 붙이면 stdin 기다리다 영원히 안 끝남, 이것도 겪음).
- 영구 금지 주제(절대 문서화 안 함, 다음 세션도 마찬가지): 블라인드 평가의 X/Y↔A/B 매핑, Phase-1 동점 처리 메커니즘/개별 평가자 투표 내용. 이름만 알고 내용은 절대 쓰지 말 것.

## 다음 세션 시작 시 체크리스트
1. `ListAgents`로 Energy 에이전트(`af51a1d52fe0f47ee`) 살아있는지 확인
2. 이 파일의 "지금 당장 할 일" 섹션의 버그 3개부터 고치기
3. `git status --short --branch`로 현재 상태 재확인 (미커밋 변경 많음, 지우지 말 것)
