# -*- coding: utf-8 -*-
"""
Week 2 ML baseline checks.

Run from the repository root:
  python tests/test_ai_week2_ml_baseline.py
"""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.analyzers import MLAxisAnalyzer, get_axis_analyzer
from ai.contracts import AXIS_KEYS
from ai.ml_baseline import TfidfKnnAxisRegressor, load_default_axis_dataset


def test_ml_axis_analyzer_returns_existing_contract() -> None:
    analyzer = MLAxisAnalyzer()
    result = analyzer.analyze("Could you explain why this phrase sounds casual?").to_axes_dict()
    assert tuple(result.keys()) == AXIS_KEYS
    assert all(0 <= value <= 100 for value in result.values())


def test_ml_baseline_uses_training_neighbors() -> None:
    examples = load_default_axis_dataset()
    model = TfidfKnnAxisRegressor(k=3).fit(examples)
    prediction = model.predict("no cap that was lowkey hilarious")
    assert prediction["Formality"] < 50
    assert prediction["Humor"] >= 20


def test_analyzer_factory_can_select_ml() -> None:
    analyzer = get_axis_analyzer("ml")
    result = analyzer.analyze("Please explain this sentence.").to_axes_dict()
    assert set(result) == set(AXIS_KEYS)


def run() -> None:
    test_ml_axis_analyzer_returns_existing_contract()
    test_ml_baseline_uses_training_neighbors()
    test_analyzer_factory_can_select_ml()
    print("Week 2 ML baseline checks passed.")


if __name__ == "__main__":
    run()
