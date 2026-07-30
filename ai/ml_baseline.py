# -*- coding: utf-8 -*-
"""
Dependency-free ML baseline for Pally's five-axis scoring.

This is intentionally small: it gives us a measurable ML candidate without
adding deployment dependencies. The model uses TF-IDF vectors and weighted
nearest-neighbor regression over the labeled utterance dataset.
"""

import json
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.contracts import AXIS_KEYS
from data.dataset import DATASET

TOKEN_PATTERN = re.compile(r"[a-z']+|[!?]+")
WEEK2_DATASET_PATH = Path(ROOT) / "data" / "axis_dataset_week2.jsonl"


@dataclass(frozen=True)
class AxisTrainingExample:
    utterance: str
    label: dict[str, int]
    style: str


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _validate_axes(raw_axes: dict[str, Any]) -> dict[str, int]:
    axes = {key: int(raw_axes[key]) for key in AXIS_KEYS}
    for axis, value in axes.items():
        if value < 0 or value > 100:
            raise ValueError(f"{axis} score must be between 0 and 100")
    return axes


def _load_jsonl_axis_dataset(path: Path) -> list[AxisTrainingExample]:
    examples: list[AxisTrainingExample] = []
    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            item = json.loads(stripped)
            examples.append(
                AxisTrainingExample(
                    utterance=str(item["utterance"]),
                    label=_validate_axes(item["axes"]),
                    style=str(item.get("style", "conversation")),
                )
            )
    if not examples:
        raise ValueError(f"no examples found in {path}")
    return examples


def _load_legacy_axis_dataset() -> list[AxisTrainingExample]:
    return [
        AxisTrainingExample(
            utterance=item["utterance"],
            label=_validate_axes(item["label"]),
            style=item["style"],
        )
        for item in DATASET
    ]


def load_default_axis_dataset() -> list[AxisTrainingExample]:
    """Load the active ML dataset, preferring the conversation-first Week 2 JSONL."""
    if WEEK2_DATASET_PATH.exists():
        return _load_jsonl_axis_dataset(WEEK2_DATASET_PATH)
    return _load_legacy_axis_dataset()


class TfidfKnnAxisRegressor:
    def __init__(self, k: int = 5) -> None:
        if k <= 0:
            raise ValueError("k must be positive")
        self.k = k
        self.examples: list[AxisTrainingExample] = []
        self.idf: dict[str, float] = {}
        self.vectors: list[dict[str, float]] = []

    def fit(self, examples: list[AxisTrainingExample]) -> "TfidfKnnAxisRegressor":
        if not examples:
            raise ValueError("at least one training example is required")
        self.examples = examples
        doc_count = len(examples)
        document_frequency: Counter[str] = Counter()
        for example in examples:
            document_frequency.update(set(_tokenize(example.utterance)))
        self.idf = {
            token: math.log((doc_count + 1) / (count + 1)) + 1.0
            for token, count in document_frequency.items()
        }
        self.vectors = [self._vectorize(example.utterance) for example in examples]
        return self

    def predict(self, utterance: str) -> dict[str, int]:
        if not self.examples:
            raise RuntimeError("model is not fitted")
        query = self._vectorize(utterance)
        similarities = [
            (self._cosine(query, vector), index)
            for index, vector in enumerate(self.vectors)
        ]
        similarities.sort(reverse=True)
        neighbors = similarities[: min(self.k, len(similarities))]

        weights = [(similarity if similarity > 0 else 0.001, index) for similarity, index in neighbors]
        total_weight = sum(weight for weight, _ in weights)
        prediction: dict[str, int] = {}
        for axis in AXIS_KEYS:
            value = sum(weight * self.examples[index].label[axis] for weight, index in weights) / total_weight
            prediction[axis] = max(0, min(100, round(value)))
        return prediction

    def _vectorize(self, utterance: str) -> dict[str, float]:
        counts = Counter(_tokenize(utterance))
        if not counts:
            return {}
        max_count = max(counts.values())
        return {
            token: (count / max_count) * self.idf.get(token, 1.0)
            for token, count in counts.items()
        }

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        dot = sum(value * right.get(token, 0.0) for token, value in left.items())
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)