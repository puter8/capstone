# -*- coding: utf-8 -*-
"""Diagnose the AI-draft "teacher" labeler against frozen human gold labels.

This does not use any human review. It re-applies the same draft_axes()
rubric that produced the 3,137-row experimental training set's AI-draft rows
(scripts/draft_label_nict_jle_candidates.py, reused verbatim across NICT,
AMI, CHiME-6, HCRC Map Task, and Taskmaster-1 WoZ during dataset construction)
to the 200 gold utterances, then compares that reconstructed draft label to
the real human-reviewed gold label per axis.

The gold candidates were never given a `sample_bucket` (they used a
different `focus_bucket` energy/curiosity scheme for stratified sampling
instead), so draft_axes() falls back to its default bucket
("personal_statement") for every row here. That only shifts each axis's
mean by a constant, bucket-driven offset -- it does not add per-row noise --
so it does not distort rank correlation (Spearman) or the shape of the error
distribution, only the additive mean bias, which this script reports
separately anyway.

Run from the repository root:
  python scripts/diagnose_gold_vs_ai_draft.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.contracts import AXIS_KEYS
from scripts.draft_label_nict_jle_candidates import draft_axes

DEFAULT_GOLD_PATH = Path(ROOT) / "data" / "fixtures" / "ml_transition_gold_human_200.jsonl"
HIGH_LOW_THRESHOLD = 50


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


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
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_den = sum((a - left_mean) ** 2 for a in left) ** 0.5
    right_den = sum((b - right_mean) ** 2 for b in right) ** 0.5
    if left_den == 0 or right_den == 0:
        return 0.0
    return numerator / (left_den * right_den)


def _spearman(human: list[float], draft: list[float]) -> float:
    return _pearson(_rank(human), _rank(draft))


def _std(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def _quantiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    n = len(ordered)

    def pick(q: float) -> float:
        position = q * (n - 1)
        lower = int(position)
        upper = min(lower + 1, n - 1)
        fraction = position - lower
        return ordered[lower] * (1 - fraction) + ordered[upper] * fraction

    return {"p10": pick(0.10), "p25": pick(0.25), "p50": pick(0.50), "p75": pick(0.75), "p90": pick(0.90)}


def _confusion(human: list[float], draft: list[float], threshold: int) -> dict[str, int]:
    counts = {"human_high_draft_high": 0, "human_high_draft_low": 0, "human_low_draft_high": 0, "human_low_draft_low": 0}
    for h, d in zip(human, draft):
        human_high = h >= threshold
        draft_high = d >= threshold
        if human_high and draft_high:
            counts["human_high_draft_high"] += 1
        elif human_high and not draft_high:
            counts["human_high_draft_low"] += 1
        elif not human_high and draft_high:
            counts["human_low_draft_high"] += 1
        else:
            counts["human_low_draft_low"] += 1
    return counts


def main() -> None:
    gold_rows = load_jsonl(DEFAULT_GOLD_PATH)
    print(f"gold_rows={len(gold_rows)}")
    print(f"gold_path={DEFAULT_GOLD_PATH}")
    print("draft rubric: scripts/draft_label_nict_jle_candidates.py:draft_axes() (same teacher used to build the 3,137-row training set)")
    print("note: gold rows carry no sample_bucket -> draft_axes() falls back to its default bucket for every row here")
    print()

    per_axis_human: dict[str, list[float]] = {axis: [] for axis in AXIS_KEYS}
    per_axis_draft: dict[str, list[float]] = {axis: [] for axis in AXIS_KEYS}

    for row in gold_rows:
        draft = draft_axes({"utterance": row["utterance"]})
        for axis in AXIS_KEYS:
            if axis not in row["axes"]:
                continue
            per_axis_human[axis].append(float(row["axes"][axis]))
            per_axis_draft[axis].append(float(draft[axis]))

    header = f"{'Axis':<10} {'n':>4} {'Spearman':>9} {'MAE':>7} {'bias':>7} {'human_sd':>9} {'draft_sd':>9} {'sd_ratio':>9}"
    print(header)
    print("-" * len(header))
    summary_rows = []
    for axis in AXIS_KEYS:
        human = per_axis_human[axis]
        draft = per_axis_draft[axis]
        if not human:
            continue
        n = len(human)
        spearman = _spearman(human, draft)
        mae = sum(abs(d - h) for h, d in zip(human, draft)) / n
        bias = sum(d - h for h, d in zip(human, draft)) / n
        human_sd = _std(human)
        draft_sd = _std(draft)
        sd_ratio = draft_sd / human_sd if human_sd else float("inf")
        print(f"{axis:<10} {n:>4} {spearman:>9.2f} {mae:>7.2f} {bias:>+7.2f} {human_sd:>9.2f} {draft_sd:>9.2f} {sd_ratio:>9.2f}")
        summary_rows.append((axis, spearman, mae, bias, human_sd, draft_sd, sd_ratio))

    print()
    print("Quantiles (human vs draft)")
    for axis in AXIS_KEYS:
        human = per_axis_human[axis]
        draft = per_axis_draft[axis]
        if not human:
            continue
        hq = _quantiles(human)
        dq = _quantiles(draft)
        print(f"  {axis}")
        print(f"    human p10/p25/p50/p75/p90 = {hq['p10']:.1f} / {hq['p25']:.1f} / {hq['p50']:.1f} / {hq['p75']:.1f} / {hq['p90']:.1f}")
        print(f"    draft p10/p25/p50/p75/p90 = {dq['p10']:.1f} / {dq['p25']:.1f} / {dq['p50']:.1f} / {dq['p75']:.1f} / {dq['p90']:.1f}")

    print()
    print(f"High/low confusion at threshold={HIGH_LOW_THRESHOLD}")
    for axis in AXIS_KEYS:
        human = per_axis_human[axis]
        draft = per_axis_draft[axis]
        if not human:
            continue
        counts = _confusion(human, draft, HIGH_LOW_THRESHOLD)
        print(f"  {axis}: {counts}")

    print()
    print("Interpretation guide")
    print("  Spearman low + bias near 0            -> teacher is noisy but roughly unbiased (more data may help)")
    print("  Spearman low + sd_ratio << 1           -> teacher collapses toward a narrow band (regression-to-mean teacher; more data will not fix this)")
    print("  Spearman low + |bias| large            -> teacher is systematically offset (a scale/calibration bug, not a volume problem)")


if __name__ == "__main__":
    main()
