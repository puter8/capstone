# -*- coding: utf-8 -*-
"""
Evaluate rule-based and ML baseline axis analyzers.

Run from the repository root:
  python ai/evaluate_axis_analyzers.py
"""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.analyzers import RuleBasedAxisAnalyzer
from ai.contracts import AXIS_KEYS
from ai.ml_baseline import TfidfKnnAxisRegressor, load_default_axis_dataset


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


def _evaluate_rule_based() -> list[dict]:
    analyzer = RuleBasedAxisAnalyzer()
    rows = []
    for example in load_default_axis_dataset():
        rows.append(
            {
                "style": example.style,
                "utterance": example.utterance,
                "expected": example.label,
                "predicted": analyzer.analyze(example.utterance).to_axes_dict(),
            }
        )
    return rows


def _evaluate_ml_leave_one_out() -> list[dict]:
    examples = load_default_axis_dataset()
    rows = []
    for index, example in enumerate(examples):
        train_examples = examples[:index] + examples[index + 1 :]
        model = TfidfKnnAxisRegressor().fit(train_examples)
        rows.append(
            {
                "style": example.style,
                "utterance": example.utterance,
                "expected": example.label,
                "predicted": model.predict(example.utterance),
            }
        )
    return rows


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


def main() -> None:
    rule_rows = _evaluate_rule_based()
    ml_rows = _evaluate_ml_leave_one_out()
    _print_report("Rule-based baseline", rule_rows)
    _print_report("ML baseline: TF-IDF weighted k-NN, leave-one-out", ml_rows)

    rule_mae = sum(_mae(rule_rows).values()) / len(AXIS_KEYS)
    ml_mae = sum(_mae(ml_rows).values()) / len(AXIS_KEYS)
    delta = ml_mae - rule_mae
    print("\nSummary")
    print(f"  rule_avg_mae: {rule_mae:.2f}")
    print(f"  ml_avg_mae  : {ml_mae:.2f}")
    print(f"  delta       : {delta:+.2f} (negative means ML is better)")


if __name__ == "__main__":
    main()


