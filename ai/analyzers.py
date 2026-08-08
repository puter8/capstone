# -*- coding: utf-8 -*-
"""
Analyzer interface for the 5-axis Pally style scoring pipeline.

The existing rule-based analyzer stays as the stable baseline/fallback. ML
implementations plug into the same interface so `/api/chat` can keep returning
the same axes/character contract.
"""

import os
from abc import ABC, abstractmethod
from typing import Any

from ai.analyzer import analyze_utterance
from ai.contracts import AXIS_KEYS, AxisResult
from ai.ml_baseline import TfidfKnnAxisRegressor, load_default_axis_dataset


class AxisAnalyzer(ABC):
    @abstractmethod
    def analyze(self, utterance: str, context: dict[str, Any] | None = None) -> AxisResult:
        """Return the five Pally axes in the existing 0-100 contract."""


class RuleBasedAxisAnalyzer(AxisAnalyzer):
    def analyze(self, utterance: str, context: dict[str, Any] | None = None) -> AxisResult:
        del context
        return AxisResult.model_validate(analyze_utterance(utterance))


class MLAxisAnalyzer(AxisAnalyzer):
    """Week 2 dependency-free TF-IDF + weighted k-NN baseline."""

    def __init__(self, model: TfidfKnnAxisRegressor | None = None) -> None:
        self.model = model or TfidfKnnAxisRegressor().fit(load_default_axis_dataset())

    def analyze(self, utterance: str, context: dict[str, Any] | None = None) -> AxisResult:
        del context
        return AxisResult.model_validate(self.model.predict(utterance))


def get_axis_analyzer(kind: str | None = None) -> AxisAnalyzer:
    analyzer_kind = (kind or os.getenv("PALLY_AXIS_ANALYZER", "rule")).strip().lower()
    if analyzer_kind == "rule":
        return RuleBasedAxisAnalyzer()
    if analyzer_kind == "ml":
        return MLAxisAnalyzer()
    raise ValueError(f"Unsupported PALLY_AXIS_ANALYZER={analyzer_kind!r}")


def assert_axes_contract(axes: AxisResult | dict[str, int]) -> AxisResult:
    result = axes if isinstance(axes, AxisResult) else AxisResult.model_validate(axes)
    missing = [key for key in AXIS_KEYS if key not in result.model_dump()]
    if missing:
        raise ValueError(f"Missing axis keys: {missing}")
    return result
