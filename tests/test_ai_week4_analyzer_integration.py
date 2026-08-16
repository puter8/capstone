# -*- coding: utf-8 -*-
"""
Week 4 checks: analyzer selection (rule/ml/hybrid) and ML-failure fallback.

Run from the repository root:
  python tests/test_ai_week4_analyzer_integration.py
"""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.analyzers import (
    AXIS_KEYS,
    HybridAxisAnalyzer,
    MLAxisAnalyzer,
    RuleBasedAxisAnalyzer,
    get_axis_analyzer,
)

UTTERANCE = "yo what's up lol, wanna practice together?"


class _BrokenModel:
    def predict(self, utterance: str) -> dict:
        raise RuntimeError("simulated model failure")


def _assert_in_range(axes) -> None:
    dumped = axes.model_dump()
    for key in AXIS_KEYS:
        assert key in dumped, f"missing axis {key}"
        assert 0 <= dumped[key] <= 100, f"{key}={dumped[key]} out of 0-100"


def test_factory_selects_rule_ml_hybrid() -> None:
    assert isinstance(get_axis_analyzer("rule"), RuleBasedAxisAnalyzer)
    assert isinstance(get_axis_analyzer("ml"), MLAxisAnalyzer)
    assert isinstance(get_axis_analyzer("hybrid"), HybridAxisAnalyzer)


def test_factory_rejects_unknown_kind() -> None:
    try:
        get_axis_analyzer("nonsense")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unsupported analyzer kind")


def test_factory_reads_env_flag(monkeypatch) -> None:
    monkeypatch.setenv("PALLY_AXIS_ANALYZER", "hybrid")
    assert isinstance(get_axis_analyzer(), HybridAxisAnalyzer)


def test_ml_analyzer_falls_back_to_rule_on_model_failure() -> None:
    broken = MLAxisAnalyzer(model=_BrokenModel())
    rule = RuleBasedAxisAnalyzer()

    result = broken.analyze(UTTERANCE)
    expected = rule.analyze(UTTERANCE)

    _assert_in_range(result)
    assert result.model_dump() == expected.model_dump()


def test_hybrid_blends_rule_and_ml() -> None:
    hybrid = HybridAxisAnalyzer()
    rule = RuleBasedAxisAnalyzer().analyze(UTTERANCE)
    ml = MLAxisAnalyzer().analyze(UTTERANCE)

    blended = hybrid.analyze(UTTERANCE)
    _assert_in_range(blended)

    for key in AXIS_KEYS:
        expected = round((getattr(rule, key) + getattr(ml, key)) / 2)
        assert getattr(blended, key) == expected, f"{key}: expected {expected}"


def test_hybrid_degrades_to_rule_when_ml_unavailable() -> None:
    broken_ml = MLAxisAnalyzer(model=_BrokenModel())
    hybrid = HybridAxisAnalyzer(ml_analyzer=broken_ml)
    rule = RuleBasedAxisAnalyzer().analyze(UTTERANCE)

    result = hybrid.analyze(UTTERANCE)

    _assert_in_range(result)
    assert result.model_dump() == rule.model_dump()


def _run_all() -> None:
    test_factory_selects_rule_ml_hybrid()
    test_factory_rejects_unknown_kind()

    class _Ctx:
        def setenv(self, key, value):
            os.environ[key] = value

    test_factory_reads_env_flag(_Ctx())
    os.environ.pop("PALLY_AXIS_ANALYZER", None)

    test_ml_analyzer_falls_back_to_rule_on_model_failure()
    test_hybrid_blends_rule_and_ml()
    test_hybrid_degrades_to_rule_when_ml_unavailable()
    print("Week 4 analyzer integration checks passed.")


if __name__ == "__main__":
    _run_all()
