# -*- coding: utf-8 -*-
"""
감정 MATRIX 핵심 기술 테스트 (오프라인 데모 버전)
==================================================
사용자 발화 -> 5축 수치화 -> 가중합 행렬 연산 -> AI 캐릭터 성격 변화 시연

실행: python test_matrix.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# ── 가중치 행렬 (5축 → 3개 캐릭터 파라미터) ──────────────
# 행: [tone_casual, energy_level, humor_level]
# 열: [Formality, Energy, Intimacy, Humor, Curiosity]
W = [
    [-0.8,  0.2,  0.3,  0.3,  0.0],  # tone_casual  (격식 낮을수록 캐주얼)
    [ 0.1,  0.7,  0.3,  0.2,  0.2],  # energy_level (에너지 높을수록 활발)
    [ 0.0,  0.1,  0.2,  0.9,  0.1],  # humor_level  (유머 높을수록 재밌게)
]
BIAS = [50, 30, 20]

# ── 테스트 케이스: 발화 / 5축 수치 / AI 응답 ──────────────
TEST_CASES = [
    {
        "utterance": "yo what's up lol, u wanna hang or nah?",
        "axes": {
            "Formality": 10, "Energy": 75, "Intimacy": 70,
            "Humor": 65, "Curiosity": 20,
            "reason": "슬랭(yo, lol, nah) 다수 사용, 높은 친밀도, 캐주얼한 제안"
        },
        "ai_response": "omg yess let's hang!! lol I've literally been so bored today 😂 where u tryna go tho??"
    },
    {
        "utterance": "I would like to formally inquire about the implications of this matter.",
        "axes": {
            "Formality": 95, "Energy": 20, "Intimacy": 5,
            "Humor": 5, "Curiosity": 70,
            "reason": "고격식 어휘(formally inquire, implications), 완전한 문장 구조"
        },
        "ai_response": "Thank you for your inquiry. I would be happy to provide a thorough explanation of the matter and its implications. Could you kindly specify which aspect you would like me to address first?"
    },
    {
        "utterance": "omg have you seen that new meme?? it literally made me cry laughing 😂😂",
        "axes": {
            "Formality": 8, "Energy": 90, "Intimacy": 65,
            "Humor": 95, "Curiosity": 35,
            "reason": "밈 언급, 과장 표현(literally, omg), 이모지 사용, 높은 유머 에너지"
        },
        "ai_response": "LMAOOO yes I saw it and I literally cannot 💀💀 the way I sent it to everyone immediately — peak internet content fr fr"
    },
]


def compute_character(axes: dict) -> dict:
    """가중합 행렬 연산으로 캐릭터 파라미터 계산 (핵심 알고리즘)"""
    v = [axes["Formality"], axes["Energy"], axes["Intimacy"], axes["Humor"], axes["Curiosity"]]
    params = []
    for i, row in enumerate(W):
        val = sum(row[j] * v[j] for j in range(5)) + BIAS[i]
        params.append(max(0, min(100, val)))  # 0~100 클리핑
    return {
        "tone_casual":  round(params[0]),
        "energy_level": round(params[1]),
        "humor_level":  round(params[2]),
    }


def describe_character(char: dict) -> str:
    """캐릭터 파라미터를 사람이 읽기 쉬운 설명으로 변환"""
    tone  = "매우 캐주얼 (슬랭 자유 사용)" if char["tone_casual"]  > 60 else \
            "격식체 (공손하고 정중)"        if char["tone_casual"]  < 30 else "중립"
    energy = "매우 활발 (열정적, 적극적)"  if char["energy_level"] > 60 else \
             "차분 (조용하고 신중)"         if char["energy_level"] < 30 else "보통"
    humor  = "유머/밈 적극 사용"           if char["humor_level"]  > 60 else \
             "진지하고 직설적"              if char["humor_level"]  < 30 else "가끔 위트"
    return tone, energy, humor


def run_test(case: dict):
    utterance = case["utterance"]
    axes      = {k: v for k, v in case["axes"].items() if k != "reason"}
    reason    = case["axes"]["reason"]
    ai_resp   = case["ai_response"]

    print(f"\n{'='*62}")
    print(f" 발화: \"{utterance}\"")
    print(f"{'='*62}")

    # 1단계: 5축 수치
    print("\n[1단계] 5축 수치 분석 결과")
    print(f"  Formality  (격식도): {axes['Formality']:>3}/100  {'#' * (axes['Formality'] // 10)}")
    print(f"  Energy     (에너지): {axes['Energy']:>3}/100  {'#' * (axes['Energy'] // 10)}")
    print(f"  Intimacy   (친밀도): {axes['Intimacy']:>3}/100  {'#' * (axes['Intimacy'] // 10)}")
    print(f"  Humor      (유머  ): {axes['Humor']:>3}/100  {'#' * (axes['Humor'] // 10)}")
    print(f"  Curiosity  (탐구심): {axes['Curiosity']:>3}/100  {'#' * (axes['Curiosity'] // 10)}")
    print(f"  근거: {reason}")

    # 2단계: 행렬 연산
    print("\n[2단계] 가중합 행렬 연산  W x [F, E, I, H, C]T + bias")
    v = [axes["Formality"], axes["Energy"], axes["Intimacy"], axes["Humor"], axes["Curiosity"]]
    print(f"  입력 벡터: {v}")
    char = compute_character(axes)
    tone, energy, humor = describe_character(char)
    print(f"\n  → tone_casual  : {char['tone_casual']:>3}/100  ({tone})")
    print(f"  → energy_level : {char['energy_level']:>3}/100  ({energy})")
    print(f"  → humor_level  : {char['humor_level']:>3}/100  ({humor})")

    # 3단계: AI 응답
    print(f"\n[3단계] AI 캐릭터 응답")
    print(f"  \"{ai_resp}\"")


if __name__ == "__main__":
    print("=" * 62)
    print("   감정 MATRIX 핵심 기술 데모")
    print("   같은 AI가 발화 스타일에 따라 성격이 달라지는 것을 확인")
    print("=" * 62)

    for case in TEST_CASES:
        run_test(case)

    print(f"\n{'='*62}")
    print(" 결론: 발화 스타일 → 5축 수치 → 행렬 연산 → AI 성격 변화")
    print(f"{'='*62}")
