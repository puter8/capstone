# -*- coding: utf-8 -*-
"""
Week 4 checks: golden-fixture regression tests for the rule-based analyzer,
CHARACTER MATRIX, EMA persona drift, and the deterministic feedback fallback.

These lock in current output so a later change to ai/analyzer.py,
ai/matrix_engine.py, or ai/generate_feedback.py can't silently drift demo
behavior. Failing this test after an intentional change is expected —
update data/fixtures/pally_regression_fixture.json deliberately and note why.

Run from the repository root:
  python tests/test_ai_week4_regression_fixture.py
"""

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.analyzer import analyze_utterance
from ai.generate_feedback import _fallback_rule_based
from ai.matrix_engine import apply_ema, compute_character

FIXTURE_PATH = os.path.join(ROOT, "data", "fixtures", "pally_regression_fixture.json")


def _load_fixture() -> dict:
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _cases_by_name(fixture: dict) -> dict:
    return {case["name"]: case for case in fixture["cases"]}


def test_analyzer_and_character_match_fixture() -> None:
    fixture = _load_fixture()
    for case in fixture["cases"]:
        axes = analyze_utterance(case["utterance"])
        character = compute_character(axes)
        assert axes == case["axes"], f"{case['name']}: axes drifted -> {axes}"
        assert character == case["character"], f"{case['name']}: character drifted -> {character}"


def test_persona_drift_matches_fixture() -> None:
    fixture = _load_fixture()
    cases = _cases_by_name(fixture)
    for drift in fixture["persona_drift_cases"]:
        prev_axes = cases[drift["prev_case"]]["axes"]
        new_axes = cases[drift["new_case"]]["axes"]

        drifted_axes = apply_ema(prev_axes, new_axes)
        drifted_character = compute_character(drifted_axes)

        assert drifted_axes == drift["drifted_axes"], f"{drift['name']}: drifted axes changed -> {drifted_axes}"
        assert drifted_character == drift["drifted_character"], (
            f"{drift['name']}: drifted character changed -> {drifted_character}"
        )


def test_feedback_fallback_matches_fixture() -> None:
    fixture = _load_fixture()
    for case in fixture["feedback_fallback_cases"]:
        items = _fallback_rule_based(case["utterance"])
        assert items == case["expected_items"], f"{case['name']}: fallback feedback changed -> {items}"


def _run_all() -> None:
    test_analyzer_and_character_match_fixture()
    test_persona_drift_matches_fixture()
    test_feedback_fallback_matches_fixture()
    print("Week 4 regression fixture checks passed.")


if __name__ == "__main__":
    _run_all()
