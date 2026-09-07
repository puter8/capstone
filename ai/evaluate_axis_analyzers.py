# -*- coding: utf-8 -*-
"""
Evaluate rule-based and ML baseline axis analyzers.

Run from the repository root:
  python ai/evaluate_axis_analyzers.py
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.analyzers import RuleBasedAxisAnalyzer
from ai.contracts import AXIS_KEYS
from ai.ml_baseline import TfidfKnnAxisRegressor, _load_jsonl_axis_dataset, load_default_axis_dataset

DEFAULT_GOLD_PATH = os.path.join(ROOT, "data", "fixtures", "ml_transition_gold_human_200.jsonl")


def _mae(rows: list[dict]) -> dict[str, float]:
    return {
        axis: sum(abs(row["predicted"][axis] - row["expected"][axis]) for row in rows) / len(rows)
        for axis in AXIS_KEYS
    }


def _rank(values: list[float]) -> list[float]:
    sorted_values = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    index = 0
    while index < len(sorted_values):
        end = index
        while end + 1 < len(sorted_values) and sorted_values[end + 1][0] == sorted_values[index][0]:
            end += 1
        average_rank = (index + end + 2) / 2
        for _, original_index in sorted_values[index : end + 1]:
            ranks[original_index] = average_rank
        index = end + 1
    return ranks


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("correlation inputs must have equal non-zero length")
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_den = sum((a - left_mean) ** 2 for a in left) ** 0.5
    right_den = sum((b - right_mean) ** 2 for b in right) ** 0.5
    if left_den == 0 or right_den == 0:
        return 0.0
    return numerator / (left_den * right_den)


def _spearman(rows: list[dict]) -> dict[str, float]:
    result: dict[str, float] = {}
    for axis in AXIS_KEYS:
        expected = [row["expected"][axis] for row in rows]
        predicted = [row["predicted"][axis] for row in rows]
        result[axis] = _pearson(_rank(expected), _rank(predicted))
    return result


def _evaluate_rule_based(examples: list | None = None) -> list[dict]:
    analyzer = RuleBasedAxisAnalyzer()
    rows = []
    for example in examples or load_default_axis_dataset():
        rows.append(
            {
                "style": example.style,
                "utterance": example.utterance,
                "expected": example.label,
                "predicted": analyzer.analyze(example.utterance).to_axes_dict(),
            }
        )
    return rows


def _evaluate_ml_leave_one_out(word_ngram_max: int) -> list[dict]:
    examples = load_default_axis_dataset()
    rows = []
    for index, example in enumerate(examples):
        train_examples = examples[:index] + examples[index + 1 :]
        model = TfidfKnnAxisRegressor(word_ngram_max=word_ngram_max).fit(train_examples)
        rows.append(
            {
                "style": example.style,
                "utterance": example.utterance,
                "expected": example.label,
                "predicted": model.predict(example.utterance),
            }
        )
    return rows


def _evaluate_hybrid_leave_one_out(word_ngram_max: int) -> list[dict]:
    """Same rule prediction as _evaluate_rule_based, blended per-axis with the
    leave-one-out ML prediction — matches HybridAxisAnalyzer's averaging."""
    rule_analyzer = RuleBasedAxisAnalyzer()
    examples = load_default_axis_dataset()
    rows = []
    for index, example in enumerate(examples):
        train_examples = examples[:index] + examples[index + 1 :]
        ml_model = TfidfKnnAxisRegressor(word_ngram_max=word_ngram_max).fit(train_examples)
        rule_pred = rule_analyzer.analyze(example.utterance).to_axes_dict()
        ml_pred = ml_model.predict(example.utterance)
        blended = {axis: round((rule_pred[axis] + ml_pred[axis]) / 2) for axis in AXIS_KEYS}
        rows.append(
            {
                "style": example.style,
                "utterance": example.utterance,
                "expected": example.label,
                "predicted": blended,
            }
        )
    return rows


def split_by_source_group(examples: list) -> tuple[list, list]:
    """Reserve deterministic whole source groups for a leakage-resistant check."""
    train: list = []
    test: list = []
    for example in examples:
        key = example.source_group or f"{example.source}:{example.utterance.lower()}"
        bucket = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:4], "big") % 10
        (test if bucket == 0 else train).append(example)
    if not train or not test:
        raise ValueError("source-group holdout requires non-empty train and test splits")
    return train, test


def _predicted_rows(examples: list, predictions: list[dict[str, int]]) -> list[dict]:
    return [
        {
            "style": example.style,
            "utterance": example.utterance,
            "expected": example.label,
            "predicted": prediction,
        }
        for example, prediction in zip(examples, predictions)
    ]


def _evaluate_ml_holdout(word_ngram_max: int, train_examples: list, test_examples: list) -> list[dict]:
    model = TfidfKnnAxisRegressor(word_ngram_max=word_ngram_max).fit(train_examples)
    return _predicted_rows(test_examples, [model.predict(example.utterance) for example in test_examples])


def _evaluate_hybrid_holdout(word_ngram_max: int, train_examples: list, test_examples: list) -> list[dict]:
    rule_analyzer = RuleBasedAxisAnalyzer()
    model = TfidfKnnAxisRegressor(word_ngram_max=word_ngram_max).fit(train_examples)
    predictions = []
    for example in test_examples:
        rule_prediction = rule_analyzer.analyze(example.utterance).to_axes_dict()
        ml_prediction = model.predict(example.utterance)
        predictions.append({axis: round((rule_prediction[axis] + ml_prediction[axis]) / 2) for axis in AXIS_KEYS})
    return _predicted_rows(test_examples, predictions)


def _total_error(row: dict) -> int:
    return sum(abs(row["predicted"][axis] - row["expected"][axis]) for axis in AXIS_KEYS)


def _print_report(name: str, rows: list[dict]) -> None:
    print(f"\n{name}")
    print("-" * len(name))
    print("MAE")
    for axis, value in _mae(rows).items():
        print(f"  {axis:<10}: {value:5.2f}")
    print("Spearman")
    for axis, value in _spearman(rows).items():
        print(f"  {axis:<10}: {value:5.2f}")

    worst = sorted(rows, key=_total_error, reverse=True)[:3]
    print("Worst cases")
    for row in worst:
        utterance = row["utterance"].encode("ascii", "backslashreplace").decode("ascii")
        print(f"  [{row['style']}] err={_total_error(row):3d} {utterance}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--word-ngram-max",
        type=int,
        default=1,
        choices=(1, 2),
        help="maximum word n-gram size for the ML-only feature set",
    )
    parser.add_argument(
        "--mode",
        choices=("leave-one-out", "source-group-holdout", "gold-holdout"),
        default="leave-one-out",
        help=(
            "evaluation mode; source-group-holdout is fast and keeps whole dialogue/source groups together; "
            "gold-holdout trains on the configured dataset (PALLY_AXIS_DATASET) and evaluates against the "
            "frozen human-reviewed gold set, which is never used for training"
        ),
    )
    parser.add_argument(
        "--gold-path",
        default=DEFAULT_GOLD_PATH,
        help="path to the frozen human-reviewed gold JSONL (only used with --mode gold-holdout)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    evaluation_label = "leave-one-out"
    if args.mode == "leave-one-out":
        rule_rows = _evaluate_rule_based()
        ml_rows = _evaluate_ml_leave_one_out(args.word_ngram_max)
        hybrid_rows = _evaluate_hybrid_leave_one_out(args.word_ngram_max)
    elif args.mode == "gold-holdout":
        train_examples = load_default_axis_dataset()
        gold_examples = _load_jsonl_axis_dataset(Path(args.gold_path))
        print(f"gold_holdout_train={len(train_examples)} test={len(gold_examples)} gold_path={args.gold_path}")
        evaluation_label = "gold holdout (frozen human-reviewed, never trained on)"
        rule_rows = _evaluate_rule_based(gold_examples)
        ml_rows = _evaluate_ml_holdout(args.word_ngram_max, train_examples, gold_examples)
        hybrid_rows = _evaluate_hybrid_holdout(args.word_ngram_max, train_examples, gold_examples)
    else:
        train_examples, test_examples = split_by_source_group(load_default_axis_dataset())
        print(f"source_group_holdout_train={len(train_examples)} test={len(test_examples)}")
        evaluation_label = "source-group holdout"
        rule_rows = _evaluate_rule_based(test_examples)
        ml_rows = _evaluate_ml_holdout(args.word_ngram_max, train_examples, test_examples)
        hybrid_rows = _evaluate_hybrid_holdout(args.word_ngram_max, train_examples, test_examples)
    _print_report("Rule-based baseline", rule_rows)
    _print_report(f"ML baseline: TF-IDF word 1-{args.word_ngram_max} gram weighted k-NN, {evaluation_label}", ml_rows)
    _print_report(f"Hybrid: rule + word 1-{args.word_ngram_max} gram ML ({evaluation_label}) averaged per axis", hybrid_rows)

    rule_mae = sum(_mae(rule_rows).values()) / len(AXIS_KEYS)
    ml_mae = sum(_mae(ml_rows).values()) / len(AXIS_KEYS)
    hybrid_mae = sum(_mae(hybrid_rows).values()) / len(AXIS_KEYS)
    rule_spearman = sum(_spearman(rule_rows).values()) / len(AXIS_KEYS)
    ml_spearman = sum(_spearman(ml_rows).values()) / len(AXIS_KEYS)
    hybrid_spearman = sum(_spearman(hybrid_rows).values()) / len(AXIS_KEYS)
    print("\nSummary")
    print(f"  rule_avg_mae  : {rule_mae:.2f}")
    print(f"  ml_avg_mae    : {ml_mae:.2f} (delta vs rule: {ml_mae - rule_mae:+.2f})")
    print(f"  hybrid_avg_mae: {hybrid_mae:.2f} (delta vs rule: {hybrid_mae - rule_mae:+.2f})")
    best_mae = min(("rule", rule_mae), ("ml", ml_mae), ("hybrid", hybrid_mae), key=lambda kv: kv[1])
    best_spearman = max(
        ("rule", rule_spearman),
        ("ml", ml_spearman),
        ("hybrid", hybrid_spearman),
        key=lambda kv: kv[1],
    )
    print(f"  rule_avg_spearman  : {rule_spearman:.2f}")
    print(f"  ml_avg_spearman    : {ml_spearman:.2f}")
    print(f"  hybrid_avg_spearman: {hybrid_spearman:.2f}")
    print(f"  best_by_mae        : {best_mae[0]} ({best_mae[1]:.2f})")
    print(f"  best_by_spearman   : {best_spearman[0]} ({best_spearman[1]:.2f})")


if __name__ == "__main__":
    main()


