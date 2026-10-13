# -*- coding: utf-8 -*-
"""F/H/C-only Ridge regression adapter for the v3.0 Rubric §7 model comparison.

Reuses the exact feature/model spec from scripts/train_purpose_axis_models.py
(PM final design Sec. 10.2: word TF-IDF 1-2gram + char TF-IDF 3-5gram ->
Ridge(alpha=1.0) per axis, output clipped [0,100]) -- but as a standalone
path with the purpose classifier removed, since Ridge itself never used
purpose as a feature; only the joint classifier+regressor training script
required purpose_primary (2026-10-12 Codex cross-check confirmed this, see
docs/AI_TACTIC/Pally_RUBRIC_v3.1_md and the v3.0 Rubric §4 known-gap note).

Also, unlike the original script (which required every row to carry all
three axes), this adapter fits each axis's Ridge model only on the rows that
actually carry that axis -- matching ai/ml_baseline.py's partial-label
convention for the v3.0 combined training set.
"""
from __future__ import annotations

from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge

from ai.ml_baseline import AxisTrainingExample

AXES = ("Formality", "Humor", "Curiosity")


class RidgeAxisAdapter:
    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha
        self.word_vec: TfidfVectorizer | None = None
        self.char_vec: TfidfVectorizer | None = None
        self.axis_models: dict[str, Ridge] = {}

    def _vectorize(self, texts: list[str]):
        return hstack([self.word_vec.transform(texts), self.char_vec.transform(texts)])

    def fit(self, examples: list[AxisTrainingExample]) -> "RidgeAxisAdapter":
        if not examples:
            raise ValueError("at least one training example is required")
        texts = [example.utterance for example in examples]
        self.word_vec = TfidfVectorizer(ngram_range=(1, 2), analyzer="word")
        self.char_vec = TfidfVectorizer(ngram_range=(3, 5), analyzer="char")
        self.word_vec.fit(texts)
        self.char_vec.fit(texts)

        for axis in AXES:
            axis_examples = [e for e in examples if axis in e.label]
            if not axis_examples:
                continue  # no training signal for this axis at all
            X = self._vectorize([e.utterance for e in axis_examples])
            y = [e.label[axis] for e in axis_examples]
            model = Ridge(alpha=self.alpha)
            model.fit(X, y)
            self.axis_models[axis] = model
        return self

    def predict_partial(self, utterance: str) -> dict[str, float | None]:
        if not self.axis_models:
            raise RuntimeError("model is not fitted")
        X = self._vectorize([utterance])
        result: dict[str, float | None] = {}
        for axis in AXES:
            model = self.axis_models.get(axis)
            if model is None:
                result[axis] = None
                continue
            raw = float(model.predict(X)[0])
            clipped = max(0.0, min(100.0, raw))
            result[axis] = round(clipped / 5) * 5  # matches train_purpose_axis_models.py::predict()
        return result
