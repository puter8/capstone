# -*- coding: utf-8 -*-
"""
Analyzer interface for the 5-axis Pally style scoring pipeline.

Week 1 goal: keep the existing rule-based analyzer as a stable fallback while
creating the seam where an ML analyzer can later be swapped in without changing
`/api/chat` response fields.
"""

import os
from abc import ABC, abstractmethod
from typing import Any

from ai.analyzer import analyze_utterance
from ai.contracts import AXIS_KEYS, AxisResult


class AxisAnalyzer(ABC):
    @abstractmethod
    def analyze(self, utterance: str, context: dict[str, Any] | None = None) -> AxisResult:
        """Return the five Pally axes in the existing 0-100 contract."""


class RuleBasedAxisAnalyzer(AxisAnalyzer):
    def analyze(self, utterance: str, context: dict[str, Any] | None = None) -> AxisResult:
        del context
        return AxisResult.model_validate(analyze_utterance(utterance))


class MLAxisAnalyzer(AxisAnalyzer):
    """Placeholder for the Week 2 ML baseline.

    Keeping this explicit makes unsupported ML usage fail loudly instead of
    silently falling back and hiding an unfinished integration.
    """

    def analyze(self, utterance: str, context: dict[str, Any] | None = None) -> AxisResult:
        del utterance, context
        raise NotImplementedError("MLAxisAnalyzer is planned for Week 2.")


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

