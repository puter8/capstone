# -*- coding: utf-8 -*-
"""
Week 2 ML baseline checks.

Run from the repository root:
  python tests/test_ai_week2_ml_baseline.py
"""

import os
import sys
import hashlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.analyzers import MLAxisAnalyzer, get_axis_analyzer
from ai.contracts import AXIS_KEYS
from ai.evaluate_axis_analyzers import split_by_source_group
from ai.ml_baseline import AxisTrainingExample, TfidfKnnAxisRegressor, load_default_axis_dataset


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


def test_ml_baseline_can_include_word_bigrams() -> None:
    examples = load_default_axis_dataset()
    model = TfidfKnnAxisRegressor(k=3, word_ngram_max=2).fit(examples)

    prediction = model.predict("could you explain this phrase")

    assert set(prediction) == set(AXIS_KEYS)
    assert all(0 <= value <= 100 for value in prediction.values())


def test_source_group_holdout_keeps_each_group_on_one_side() -> None:
    label = {axis: 50 for axis in AXIS_KEYS}
    holdout_group = next(
        f"meeting-{index}"
        for index in range(100)
        if int.from_bytes(hashlib.sha256(f"meeting-{index}".encode("utf-8")).digest()[:4], "big") % 10 == 0
    )
    examples = [
        AxisTrainingExample("First meeting turn", label, "conversation", source="ami", source_group="meeting-1"),
        AxisTrainingExample("Second meeting turn", label, "conversation", source="ami", source_group="meeting-1"),
        AxisTrainingExample("Independent turn", label, "conversation", source="ami", source_group=holdout_group),
    ]

    train, test = split_by_source_group(examples)
    training_groups = {example.source_group for example in train}
    test_groups = {example.source_group for example in test}

    assert training_groups.isdisjoint(test_groups)


def test_analyzer_factory_can_select_ml() -> None:
    analyzer = get_axis_analyzer("ml")
    result = analyzer.analyze("Please explain this sentence.").to_axes_dict()
    assert set(result) == set(AXIS_KEYS)


def test_ml_dataset_can_be_selected_by_env(monkeypatch) -> None:
    dataset_path = os.path.join(ROOT, "tests", ".tmp_axis_dataset.jsonl")
    try:
        with open(dataset_path, "w", encoding="utf-8") as handle:
            handle.write(
                '{"utterance":"Could you help me?","axes":{"Formality":55,"Energy":30,"Intimacy":35,"Humor":5,"Curiosity":80},"style":"learner_request"}\n'
            )
        monkeypatch.setenv("PALLY_AXIS_DATASET", dataset_path)

        examples = load_default_axis_dataset()
        assert len(examples) == 1
        assert examples[0].utterance == "Could you help me?"
    finally:
        if os.path.exists(dataset_path):
            os.remove(dataset_path)


def test_ml_dataset_relative_env_path_is_resolved_from_repo_root(monkeypatch) -> None:
    dataset_path = os.path.join(ROOT, "tests", ".tmp_relative_axis_dataset.jsonl")
    try:
        with open(dataset_path, "w", encoding="utf-8") as handle:
            handle.write(
                '{"utterance":"Please repeat that.","axes":{"Formality":55,"Energy":30,"Intimacy":35,"Humor":5,"Curiosity":80},"style":"learner_request"}\n'
            )
        monkeypatch.setenv("PALLY_AXIS_DATASET", "tests/.tmp_relative_axis_dataset.jsonl")

        examples = load_default_axis_dataset()
        assert len(examples) == 1
        assert examples[0].utterance == "Please repeat that."
    finally:
        if os.path.exists(dataset_path):
            os.remove(dataset_path)


def run() -> None:
    test_ml_axis_analyzer_returns_existing_contract()
    test_ml_baseline_uses_training_neighbors()
    test_analyzer_factory_can_select_ml()
    print("Week 2 ML baseline checks passed.")


if __name__ == "__main__":
    run()
