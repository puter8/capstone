# -*- coding: utf-8 -*-
"""
감정 MATRIX 핵심 기술 테스트
==============================
사용자 발화 → Rule-Based 분석기 → 5축 수치 → 가중합 행렬 연산 → AI 캐릭터 성격 변화

실행:
  python3 test_matrix.py        # 데모 출력 (교수님 시연용)
  pytest test_matrix.py -v -s   # 차별화 검증 PASS/FAIL
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from analyzer import analyze_utterance
from matrix_engine import compute_character, describe_character

# ---------------------------------------------------------------------------
# 테스트 케이스: 발화 / 근거 설명 / AI 응답
# 5축 수치는 analyzer.py (Rule-Based 분석기)가 실시간으로 산출
# ---------------------------------------------------------------------------
TEST_CASES = [
    {
        "utterance": "yo what's up lol, u wanna hang or nah?",
        "reason": "슬랭(yo, lol, nah) 다수 사용, 높은 친밀도, 캐주얼한 제안",
        "ai_response": "omg yess let's hang!! lol I've literally been so bored today 😂 where u tryna go tho??",
    },
    {
        "utterance": "I would like to formally inquire about the implications of this matter.",
        "reason": "고격식 어휘(formally inquire, implications), 완전한 문장 구조",
        "ai_response": "Thank you for your inquiry. I would be happy to provide a thorough explanation of the matter and its implications. Could you kindly specify which aspect you would like me to address first?",
    },
    {
        "utterance": "omg have you seen that new meme?? it literally made me cry laughing 😂😂",
        "reason": "밈 언급, 과장 표현(literally, omg), 이모지 사용, 높은 유머 에너지",
        "ai_response": "LMAOOO yes I saw it and I literally cannot 💀💀 the way I sent it to everyone immediately — peak internet content fr fr",
    },
]

AXIS_LABELS = {
    "Formality": "격식도",
    "Energy":    "에너지",
    "Intimacy":  "친밀도",
    "Humor":     "유머  ",
    "Curiosity": "탐구심",
}


def run_demo():
    print("=" * 62)
    print("   감정 MATRIX 핵심 기술 데모")
    print("   같은 AI가 발화 스타일에 따라 성격이 달라지는 것을 확인")
    print("=" * 62)

    for case in TEST_CASES:
        # 1단계: Rule-Based 분석기로 5축 수치 산출
        axes = analyze_utterance(case["utterance"])
        char = compute_character(axes)
        tone, energy, humor = describe_character(char)

        print(f"\n{'=' * 62}")
        print(f" 발화: \"{case['utterance']}\"")
        print(f"{'=' * 62}")

        print("\n[1단계] 5축 수치 분석 결과")
        for key, label in AXIS_LABELS.items():
            val = axes[key]
            bar = "#" * (val // 10)
            print(f"  {key:<10} ({label}): {val:>3}/100  {bar}")
        print(f"  근거: {case['reason']}")

        v = [axes[k] for k in ["Formality", "Energy", "Intimacy", "Humor", "Curiosity"]]
        print(f"\n[2단계] 가중합 행렬 연산  W x [F, E, I, H, C]T + bias")
        print(f"  입력 벡터: {v}")
        print(f"\n  → tone_casual  : {char['tone_casual']:>3}/100  ({tone})")
        print(f"  → energy_level : {char['energy_level']:>3}/100  ({energy})")
        print(f"  → humor_level  : {char['humor_level']:>3}/100  ({humor})")

        print(f"\n[3단계] AI 캐릭터 응답")
        print(f"  \"{case['ai_response']}\"")

    print(f"\n{'=' * 62}")
    print(" 결론: 발화 스타일 → 5축 수치 → 행렬 연산 → AI 성격 변화")
    print(f"{'=' * 62}")


# ---------------------------------------------------------------------------
# pytest 테스트: 차별화 검증
# 서로 다른 발화 스타일이 서로 다른 캐릭터 파라미터를 만드는지 확인
# ---------------------------------------------------------------------------

def test_differentiation():
    """다른 발화 스타일 → 다른 캐릭터 파라미터"""
    casual = compute_character(analyze_utterance(TEST_CASES[0]["utterance"]))
    formal = compute_character(analyze_utterance(TEST_CASES[1]["utterance"]))
    meme   = compute_character(analyze_utterance(TEST_CASES[2]["utterance"]))

    print("\n  [차별화 검증] 스타일별 캐릭터 파라미터 비교")
    print(f"  {'스타일':<8}  {'tone_casual':>12}  {'energy_level':>12}  {'humor_level':>12}")
    print(f"  {'-'*50}")
    print(f"  {'캐주얼':<8}  {casual['tone_casual']:>12}  {casual['energy_level']:>12}  {casual['humor_level']:>12}")
    print(f"  {'격식체':<8}  {formal['tone_casual']:>12}  {formal['energy_level']:>12}  {formal['humor_level']:>12}")
    print(f"  {'밈/유머':<8}  {meme['tone_casual']:>12}  {meme['energy_level']:>12}  {meme['humor_level']:>12}")

    assert casual["tone_casual"] > formal["tone_casual"], \
        f"캐주얼 tone({casual['tone_casual']}) > 격식 tone({formal['tone_casual']}) 실패"
    print(f"\n  캐주얼 tone({casual['tone_casual']}) > 격식 tone({formal['tone_casual']})  PASS")

    assert meme["humor_level"] > formal["humor_level"], \
        f"밈 humor({meme['humor_level']}) > 격식 humor({formal['humor_level']}) 실패"
    print(f"  밈 humor({meme['humor_level']}) > 격식 humor({formal['humor_level']})  PASS")

    assert meme["energy_level"] > formal["energy_level"], \
        f"밈 energy({meme['energy_level']}) > 격식 energy({formal['energy_level']}) 실패"
    print(f"  밈 energy({meme['energy_level']}) > 격식 energy({formal['energy_level']})  PASS")

    assert casual != formal, "캐주얼과 격식이 동일한 캐릭터 파라미터를 생성함"
    assert meme != formal,   "밈과 격식이 동일한 캐릭터 파라미터를 생성함"
    print(f"  3개 스타일 → 3개 서로 다른 캐릭터 확인  PASS")


if __name__ == "__main__":
    run_demo()
