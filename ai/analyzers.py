# -*- coding: utf-8 -*-
"""
Analyzer interface for the 5-axis Pally style scoring pipeline.

The existing rule-based analyzer stays as the stable baseline/fallback. ML
implementations plug into the same interface so `/api/chat` can keep returning
the same axes/character contract.
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
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
    """Week 2 dependency-free TF-IDF + weighted k-NN baseline.

    Falls back to the rule-based analyzer if the model fails to predict
    (unfitted model, unexpected input, etc.) so a transient ML error never
    breaks the `/api/chat` turn.
    """

    def __init__(self, model: TfidfKnnAxisRegressor | None = None) -> None:
        self.model = model or TfidfKnnAxisRegressor().fit(
            load_default_axis_dataset(), require_full_axes=True
        )
        self._fallback = RuleBasedAxisAnalyzer()

    def analyze(self, utterance: str, context: dict[str, Any] | None = None) -> AxisResult:
        try:
            return AxisResult.model_validate(self.model.predict(utterance))
        except Exception:
            return self._fallback.analyze(utterance, context)


class HybridAxisAnalyzer(AxisAnalyzer):
    """Averages rule-based and ML axes per key.

    Uses `MLAxisAnalyzer`, which already falls back to rule-based on its own
    failure — so if ML is unavailable, hybrid degrades to the rule-based
    result instead of raising.
    """

    def __init__(self, ml_analyzer: MLAxisAnalyzer | None = None) -> None:
        self._rule = RuleBasedAxisAnalyzer()
        self._ml = ml_analyzer or MLAxisAnalyzer()

    def analyze(self, utterance: str, context: dict[str, Any] | None = None) -> AxisResult:
        rule_axes = self._rule.analyze(utterance, context)
        ml_axes = self._ml.analyze(utterance, context)
        blended = {
            key: round((getattr(rule_axes, key) + getattr(ml_axes, key)) / 2)
            for key in AXIS_KEYS
        }
        return AxisResult.model_validate(blended)


class ResearchedAxisAnalyzer(AxisAnalyzer):
    """Explicit local F/H/C artifact, preserving the existing other-axis pipeline.

    Loading and prediction failures propagate. The opt-in artifact must be a
    trusted local training output; joblib artifacts must never come from uploads.
    Optional ML dependencies are loaded only when this analyzer is selected.
    """

    _FHC = ('Formality', 'Humor', 'Curiosity')
    _ROOT = Path(__file__).resolve().parents[1]
    _DEFAULT_ARTIFACT = 'data/models/full-corpus-fhc/improvement/research_round/model.joblib'

    def __init__(self, model: Any = None, *, artifact_path: str | Path | None = None,
                 encoder_path: str | Path | None = None) -> None:
        if model is not None:
            if artifact_path is not None or encoder_path is not None:
                raise ValueError('Supply either a model or artifact configuration')
            self.model = model
        else:
            from ai.researched_axis_model import ResearchedAxisModel

            configured_artifact = artifact_path if artifact_path is not None else os.getenv(
                'PALLY_RESEARCHED_MODEL_PATH', self._DEFAULT_ARTIFACT)
            configured_encoder = encoder_path if encoder_path is not None else os.getenv(
                'PALLY_RESEARCHED_ENCODER_PATH')
            path = self._local_path(configured_artifact)
            if not path.is_file():
                raise FileNotFoundError(f'Researched axis model artifact not found: {path}')
            encoder = self._local_path(configured_encoder) if configured_encoder is not None else None
            self.model = ResearchedAxisModel.from_artifact(path, encoder_path=encoder)
        self._rule = RuleBasedAxisAnalyzer()

    @classmethod
    def _local_path(cls, value: str | Path) -> Path:
        if not str(value).strip():
            raise ValueError('Researched model paths must not be blank')
        path = Path(value).expanduser()
        return (path if path.is_absolute() else cls._ROOT / path).resolve()

    def analyze(self, utterance: str, context: dict[str, Any] | None = None) -> AxisResult:
        if not isinstance(utterance, str) or not utterance.strip():
            raise ValueError('A nonblank utterance is required for researched scoring')
        predicted = self.model.predict_partial(utterance)
        if not isinstance(predicted, dict) or set(predicted) != set(self._FHC):
            raise ValueError('Researched model must return exactly Formality, Humor and Curiosity')
        for axis, value in predicted.items():
            if type(value) is not int or not 0 <= value <= 100 or value % 5:
                raise ValueError(f'Invalid researched {axis} score')
        existing = self._rule.analyze(utterance, context)
        return AxisResult.model_validate({**predicted, 'Energy': existing.Energy,
                                          'Intimacy': existing.Intimacy})


def get_axis_analyzer(kind: str | None = None) -> AxisAnalyzer:
    analyzer_kind = (kind or os.getenv("PALLY_AXIS_ANALYZER", "rule")).strip().lower()
    if analyzer_kind == "rule":
        return RuleBasedAxisAnalyzer()
    if analyzer_kind == "ml":
        return MLAxisAnalyzer()
    if analyzer_kind == "hybrid":
        return HybridAxisAnalyzer()
    if analyzer_kind == "researched":
        return ResearchedAxisAnalyzer()
    raise ValueError(f"Unsupported PALLY_AXIS_ANALYZER={analyzer_kind!r}")


def assert_axes_contract(axes: AxisResult | dict[str, int]) -> AxisResult:
    result = axes if isinstance(axes, AxisResult) else AxisResult.model_validate(axes)
    missing = [key for key in AXIS_KEYS if key not in result.model_dump()]
    if missing:
        raise ValueError(f"Missing axis keys: {missing}")
    return result
