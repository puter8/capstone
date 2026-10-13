# -*- coding: utf-8 -*-
"""
Matrix Engine — CHARACTER MATRIX 핵심 연산 모듈
=================================================
5축 점수를 입력받아 AI 캐릭터 파라미터를 계산하는 행렬 연산 모듈.

핵심 연산: 가중합(Weighted Sum)
  character_params = W × [F, E, I, H, C]^T + BIAS
  → 5축 점수(입력)를 캐릭터 반응 파라미터(출력)로 변환

출력 파라미터 3개:
  tone_casual  : 캐주얼 말투 정도 (0=격식체, 100=슬랭 자유 사용)
  energy_level : 반응 에너지 수준 (0=차분, 100=매우 활발)
  humor_level  : 유머/장난기 정도 (0=진지, 100=밈·유머 모드)

추가 기능:
  - EMA(지수이동평균) 스무딩: 발화가 쌓일수록 급격한 변화 없이 점진적으로 캐릭터 조정
"""

# ---------------------------------------------------------------------------
# 가중치 행렬 W (Weight Matrix): 3출력 × 5입력
#
# 행(Row): 출력 파라미터 → [tone_casual, energy_level, humor_level]
# 열(Col): 입력 5축    → [Formality, Energy, Intimacy, Humor, Curiosity]
#
# 2026-10-06 전면 재설계 — 가중합 폐기, 세 출력 모두 자기 축의 단순 변환:
#   tone_casual  = 100 - Formality  (가중치 없음, 부호만 반전)
#   energy_level = Energy           (그대로 통과)
#   humor_level  = Humor            (그대로 통과)
#
# 재설계 이유 (Pally_RUBRIC_v3.0_md §7.1/§9):
#   화면(PallyCanvas.tsx::tier())은 항상 원본 축 값을 직접 쓰는데, 기존
#   persona_prompt()는 5축을 섞은 가중합(W·v+BIAS)을 썼다. 둘이 같은 축을
#   놓고 서로 다른 값을 봐서, 화면은 "차분함/격식체"인데 대화 지시는
#   "upbeat/캐주얼"인 불일치가 실측됨:
#     - Energy: 8,181개 조합 중 18.2% 불일치 (경계 구간 + 다른 축 극단값일 때)
#     - Formality: 24,543개 조합 중 41.4% 불일치 (전 구간에서 상시 발생 —
#       BIAS=50이 가중치(-0.45)보다 커서 Formality 혼자서는 중립 구간을
#       못 벗어남)
#     - Humor: 24,543개 조합 중 35.2% 불일치 (중간~고구간에서 다른 축이
#       극단값일 때)
#   1차로 Energy만 가중치 비중을 올리는 절충을 시도했으나(E 0.40→0.65) 경계
#   불일치가 남아 폐기 — 세 축 모두 "화면과 프롬프트가 같은 값을 보게"가
#   유일한 완전한 해결책이라 섞지 않는 쪽으로 확정(사용자 결정, 2026-10-06).
#   Intimacy/Curiosity는 원래부터 persona_prompt()에서 compute_character()를
#   거치지 않고 raw 값을 직접 밴딩해서 애초에 이 문제가 없었다(변경 없음).
# ---------------------------------------------------------------------------

W = [
    [-1.00,  0.00,  0.00,  0.00,  0.00],  # tone_casual  = 100 - Formality
    [ 0.00,  1.00,  0.00,  0.00,  0.00],  # energy_level = Energy
    [ 0.00,  0.00,  0.00,  1.00,  0.00],  # humor_level  = Humor
]

# 편향(Bias): tone_casual만 100 - Formality를 만들기 위해 100이 필요하고,
# 나머지는 축 값을 그대로 통과시키므로 0이다.
BIAS = [100, 0, 0]

# EMA 스무딩 계수 (0 < alpha <= 1)
# alpha=0.3: 새 발화 30% + 이전 누적 70% → 급격한 캐릭터 변화 방지
# → 사용자가 한 번 슬랭을 써도 캐릭터가 갑자기 바뀌지 않고 서서히 적응
DEFAULT_ALPHA = 0.7


def compute_character(axes: dict) -> dict:
    """
    [핵심 연산] 가중합 행렬 연산: 5축 점수 → 캐릭터 파라미터 변환

    수식: params[i] = sum(W[i][j] * v[j] for j in 0..4) + BIAS[i]
    즉, 각 출력 파라미터는 5축 점수의 가중합 + 편향으로 계산됨.

    예시:
      입력: {Formality:5, Energy:85, Intimacy:60, Humor:90, Curiosity:35}
      v = [5, 85, 60, 90, 35]

      tone_casual  = (-1×5) + 100 = 95
      energy_level = (1×85) = 85
      humor_level  = (1×90) = 90

      (2026-10-06부터 세 출력 모두 다른 축과 섞이지 않는다 — 위 "재설계" 주석 참고)

    Args:
        axes: analyzer.py가 반환한 5축 점수 dict
              키: Formality, Energy, Intimacy, Humor, Curiosity (각 0~100)

    Returns:
        dict: tone_casual, energy_level, humor_level (각 0~100, 클리핑 적용)
    """
    # 5축 점수를 순서대로 벡터로 변환
    v = [
        axes["Formality"],
        axes["Energy"],
        axes["Intimacy"],
        axes["Humor"],
        axes["Curiosity"],
    ]
    params = []
    for i, row in enumerate(W):
        # W[i] 행과 v 벡터의 내적(dot product) + BIAS[i]
        val = sum(row[j] * v[j] for j in range(5)) + BIAS[i]
        params.append(max(0.0, min(100.0, val)))  # 0~100 클리핑
    return {
        "tone_casual":  round(params[0]),   # 캐주얼 말투 정도
        "energy_level": round(params[1]),   # 반응 에너지 수준
        "humor_level":  round(params[2]),   # 유머/장난기 정도
    }


def apply_ema(prev: dict, new_axes: dict, alpha: float = DEFAULT_ALPHA) -> dict:
    """
    [EMA 스무딩] 지수이동평균으로 5축 점수를 점진적으로 업데이트

    목적:
      발화 1개로 캐릭터가 급격히 바뀌는 것을 방지.
      예: 평소 격식체 사용자가 한 번 "lol"을 썼다고 바로 캐주얼 캐릭터로 바뀌지 않도록.

    수식: updated[k] = alpha × new[k] + (1 - alpha) × prev[k]
      alpha=0.3일 때:
        → 새 발화 30% 반영 + 이전 누적 70% 유지
        → 발화가 쌓일수록 서서히 캐릭터 성격이 드러남

    Args:
        prev:     이전까지 누적된 5축 점수 (첫 발화 전엔 기본값으로 초기화)
        new_axes: 현재 발화에서 analyzer.py가 측정한 새 5축 점수
        alpha:    스무딩 계수 (0~1). 높을수록 새 발화에 빠르게 반응.

    Returns:
        EMA 블렌딩 후 업데이트된 5축 점수 dict
    """
    keys = ["Formality", "Energy", "Intimacy", "Humor", "Curiosity"]
    return {
        k: round(alpha * new_axes[k] + (1 - alpha) * prev[k])
        for k in keys
    }


def describe_character(char: dict) -> tuple:
    """
    [출력 해석] 캐릭터 파라미터 수치를 사람이 읽을 수 있는 레이블로 변환

    임계값 기준:
      >60 → 해당 특성이 강하게 드러남
      <30 → 해당 특성이 거의 없음
      나머지 → 중립/보통

    Returns:
        (tone_label, energy_label, humor_label) 문자열 튜플
    """
    # tone_casual: 캐주얼 말투 정도
    tone = (
        "Very casual (slang freely used)"   if char["tone_casual"] > 60   # 슬랭 자유 사용
        else "Formal (polite and respectful)" if char["tone_casual"] < 30  # 격식체 유지
        else "Neutral"                                                       # 중립
    )
    # energy_level: 반응 에너지 수준
    energy = (
        "Very active (enthusiastic)"  if char["energy_level"] > 60  # 매우 활발
        else "Calm (quiet and measured)" if char["energy_level"] < 30  # 차분
        else "Moderate"                                                   # 보통
    )
    # humor_level: 유머/장난기 정도
    humor = (
        "Humor/meme mode"      if char["humor_level"] > 60   # 밈·유머 적극 활용
        else "Serious and direct" if char["humor_level"] < 30  # 진지하고 직접적
        else "Occasional wit"                                    # 가끔 위트
    )
    return tone, energy, humor
