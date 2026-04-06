# -*- coding: utf-8 -*-
"""
CHARACTER MATRIX 핵심 기술 테스트
==============================
발화 -> 5축 분석 -> 가중합 행렬 연산 -> AI 캐릭터 성격 변화 시연

모듈 구성:
  analyzer.py      - 규칙 기반 5축 분석기 (추후 LLM으로 교체)
  matrix_engine.py - 가중합 행렬 연산
  dataset.py       - ground truth 학습 데이터셋

실행:
  python tests/test_matrix.py   # 데모 출력 + 캐릭터 시각화
"""

import sys
import os
import webbrowser

# 루트 경로 추가 (analyzer, matrix_engine, dataset import용)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding='utf-8')

from analyzer import analyze_utterance
from matrix_engine import compute_character, describe_character
from dataset import DATASET

# ── AI 응답 생성 (규칙 기반) ────────────────────────────────
def build_ai_response(char: dict, utterance: str) -> str:
    text = utterance.lower()
    if char["tone_casual"] > 60 and char["humor_level"] > 60:
        if "meme" in text or "funny" in text or "laugh" in text:
            return "LMAOOO yes I saw it and I literally cannot stop laughing 💀💀 peak internet content fr fr"
        return "omg yess let's gooo!! lol I've literally been so bored today 😂 what's the plan tho??"
    elif char["tone_casual"] < 30:
        if "inquire" in text or "formally" in text or "implications" in text:
            return "Thank you for your inquiry. I would be happy to provide a thorough explanation. Could you kindly specify which aspect you would like me to address first?"
        return "I appreciate you reaching out. I would be glad to assist you with that matter."
    else:
        return "That's interesting! I'd love to hear more about what you're thinking. What made you bring that up?"


# ── 단일 발화 파이프라인 실행 ────────────────────────────────
def run_test(utterance: str, ground_truth: dict = None):
    print(f"\n{'='*62}")
    print(f" 발화: \"{utterance}\"")
    print(f"{'='*62}")

    axes = analyze_utterance(utterance)
    print("\n[1단계] 5축 수치 분석 결과")

    keys   = ["Formality", "Energy", "Intimacy", "Humor", "Curiosity"]
    labels = ["격식도", "에너지", "친밀도", "유머  ", "탐구심"]
    for key, label in zip(keys, labels):
        val = axes[key]
        bar = "#" * (val // 10)
        gt  = f"  (정답: {ground_truth[key]})" if ground_truth else ""
        print(f"  {key:<10} ({label}): {val:>3}/100  {bar}{gt}")

    v = [axes[k] for k in keys]
    print(f"\n[2단계] 가중합 행렬 연산  W x [F, E, I, H, C]T + bias")
    print(f"  입력 벡터: {v}")
    char = compute_character(axes)
    tone, energy, humor = describe_character(char)
    print(f"\n  -> tone_casual  : {char['tone_casual']:>3}/100  ({tone})")
    print(f"  -> energy_level : {char['energy_level']:>3}/100  ({energy})")
    print(f"  -> humor_level  : {char['humor_level']:>3}/100  ({humor})")

    print(f"\n[3단계] AI 캐릭터 응답")
    print(f"  \"{build_ai_response(char, utterance)}\"")


# ── 데모: 스타일별 대표 발화 ────────────────────────────────
DEMO_STYLES = ["casual", "formal", "humor", "curious"]

def run_demo():
    print("=" * 62)
    print("   CHARACTER MATRIX 핵심 기술 데모")
    print("   [5축 분석: 규칙 기반 분류기 -> 추후 LLM으로 교체 예정]")
    print(f"   [학습 데이터셋: {len(DATASET)}개 라벨 데이터 준비됨]")
    print("=" * 62)

    seen = set()
    for item in DATASET:
        if item["style"] in DEMO_STYLES and item["style"] not in seen:
            run_test(item["utterance"], ground_truth=item["label"])
            seen.add(item["style"])
        if len(seen) == len(DEMO_STYLES):
            break

    print(f"\n{'='*62}")
    print(" 결론: 발화 스타일 -> 5축 수치 -> 행렬 연산 -> AI 성격 변화")
    print(f"{'='*62}")

    viz_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "visualizer.html")
    )
    if os.path.exists(viz_path):
        print(f"\n 캐릭터 시각화 열기: {viz_path}")
        webbrowser.open(f"file:///{viz_path}")


if __name__ == "__main__":
    run_demo()
