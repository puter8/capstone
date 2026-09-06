# -*- coding: utf-8 -*-
"""Select small, auditable annotation sets from the ML-transition pools.

The train selection uses current ML-versus-hybrid disagreement only to make
human Energy/Curiosity labels informative. The gold selection is independently
stratified random and never uses predicted scores or disagreement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.analyzers import RuleBasedAxisAnalyzer
from ai.contracts import AXIS_KEYS
from ai.ml_baseline import AxisTrainingExample, TfidfKnnAxisRegressor
from scripts.sample_ml_transition_candidates import group_key


DEFAULT_MODEL_DATASET = Path("data/fixtures/axis_dataset_combined_real_speech_experimental.jsonl")
DEFAULT_TRAIN_CANDIDATES = Path("data/fixtures/ml_transition_train_candidates_1200.jsonl")
DEFAULT_GOLD_CANDIDATES = Path("data/fixtures/ml_transition_gold_candidates_600.jsonl")
DEFAULT_TRAIN_OUTPUT = Path("data/fixtures/ml_transition_train_active_ec_candidates_120.jsonl")
DEFAULT_GOLD_OUTPUT = Path("data/fixtures/ml_transition_gold_stratified_candidates_200.jsonl")
DEFAULT_SEED = 20260906
TRAIN_REASON_QUOTAS = (
    ("energy_disagreement", 40),
    ("curiosity_disagreement", 40),
    ("energy_extreme", 15),
    ("curiosity_extreme", 15),
    ("random_control", 10),
)
MAX_ACTIVE_PER_GROUP = 1


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(rows: Iterable[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_model_examples(path: Path) -> list[AxisTrainingExample]:
    examples: list[AxisTrainingExample] = []
    for row_number, row in enumerate(load_jsonl(path), start=1):
        raw_axes = row.get("axes")
        if not isinstance(raw_axes, dict):
            raise ValueError(f"model dataset row {row_number} has no axis labels")
        try:
            labels = {axis: int(raw_axes[axis]) for axis in AXIS_KEYS}
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"model dataset row {row_number} has incomplete axis labels") from exc
        examples.append(
            AxisTrainingExample(
                utterance=str(row["utterance"]),
                label=labels,
                style=str(row.get("style", "conversation")),
                source=str(row.get("source", "")),
                source_group=str(row.get("source_group", "")),
            )
        )
    if not examples:
        raise ValueError(f"no model examples in {path}")
    return examples


def stable_tie_break(row: dict[str, Any], seed: int) -> str:
    text = f"{seed}|{group_key(row)}|{row.get('source_record_id', '')}|{row['utterance']}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def score_train_candidates(
    rows: list[dict[str, Any]],
    model: TfidfKnnAxisRegressor,
) -> list[dict[str, Any]]:
    rule_analyzer = RuleBasedAxisAnalyzer()
    scored: list[dict[str, Any]] = []
    for row in rows:
        utterance = str(row["utterance"])
        ml_axes = model.predict(utterance)
        rule_axes = rule_analyzer.analyze(utterance).to_axes_dict()
        hybrid_axes = {axis: round((rule_axes[axis] + ml_axes[axis]) / 2) for axis in AXIS_KEYS}
        enriched = dict(row)
        enriched["selection_ml_axes"] = ml_axes
        enriched["selection_hybrid_axes"] = hybrid_axes
        enriched["selection_energy_disagreement"] = abs(ml_axes["Energy"] - hybrid_axes["Energy"])
        enriched["selection_curiosity_disagreement"] = abs(ml_axes["Curiosity"] - hybrid_axes["Curiosity"])
        enriched["selection_energy_extremeness"] = abs(ml_axes["Energy"] - 50)
        enriched["selection_curiosity_extremeness"] = abs(ml_axes["Curiosity"] - 50)
        scored.append(enriched)
    return scored


def take_ranked(
    rows: list[dict[str, Any]],
    count: int,
    reason: str,
    metric: Callable[[dict[str, Any]], int],
    selected_keys: set[str],
    group_counts: Counter[str],
    seed: int,
) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []
    ranked = sorted(rows, key=lambda row: (-metric(row), stable_tie_break(row, seed)))
    for row in ranked:
        utterance_key = str(row["utterance"]).casefold().strip()
        group = group_key(row)
        if utterance_key in selected_keys or group_counts[group] >= MAX_ACTIVE_PER_GROUP:
            continue
        enriched = dict(row)
        enriched["selection_method"] = "active_disagreement"
        enriched["selection_reason"] = reason
        picked.append(enriched)
        selected_keys.add(utterance_key)
        group_counts[group] += 1
        if len(picked) == count:
            return picked
    raise ValueError(f"only selected {len(picked)} rows for {reason}; requested {count}")


def select_active_training(rows: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_keys: set[str] = set()
    group_counts: Counter[str] = Counter()
    metric_names = {
        "energy_disagreement": "selection_energy_disagreement",
        "curiosity_disagreement": "selection_curiosity_disagreement",
        "energy_extreme": "selection_energy_extremeness",
        "curiosity_extreme": "selection_curiosity_extremeness",
    }
    for reason, count in TRAIN_REASON_QUOTAS:
        if reason == "random_control":
            rng = random.Random(seed)
            random_order = {id(row): rng.randrange(1_000_000_000) for row in rows}
            selected.extend(
                take_ranked(
                    rows,
                    count,
                    reason,
                    lambda row: random_order[id(row)],
                    selected_keys,
                    group_counts,
                    seed,
                )
            )
            continue
        metric_name = metric_names[reason]
        selected.extend(
            take_ranked(
                rows,
                count,
                reason,
                lambda row, name=metric_name: int(row[name]),
                selected_keys,
                group_counts,
                seed,
            )
        )
    return selected


def question_flag(row: dict[str, Any]) -> str:
    return "question" if str(row["utterance"]).rstrip().endswith("?") else "statement"


def length_band(row: dict[str, Any]) -> str:
    count = int(row.get("word_count") or len(str(row["utterance"]).split()))
    if count <= 7:
        return "short_4_7"
    if count <= 15:
        return "medium_8_15"
    return "long_16_plus"


def gold_stratum(row: dict[str, Any]) -> str:
    return "|".join(
        (
            str(row.get("source", "unknown")),
            str(row.get("focus_bucket", "unknown")),
            length_band(row),
            question_flag(row),
        )
    )


def select_stratified_gold(rows: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    if size <= 0:
        raise ValueError("gold size must be positive")
    if size > len(rows):
        raise ValueError(f"only {len(rows)} gold candidates available; requested {size}")
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[gold_stratum(row)].append(row)
    rng = random.Random(seed)
    for bucket in buckets.values():
        rng.shuffle(bucket)

    strata = sorted(buckets)
    if len(strata) > size:
        raise ValueError(f"{len(strata)} strata exceed requested gold size {size}")

    total = len(rows)
    quotas = {stratum: 1 for stratum in strata}
    remaining = size - len(strata)
    desired_extra = {
        stratum: max(0.0, size * len(buckets[stratum]) / total - 1)
        for stratum in strata
    }
    while remaining:
        eligible = [stratum for stratum in strata if quotas[stratum] < len(buckets[stratum])]
        if not eligible:
            raise ValueError("not enough rows to fill stratified gold selection")
        stratum = max(
            eligible,
            key=lambda name: (desired_extra[name] - (quotas[name] - 1), len(buckets[name]), name),
        )
        quotas[stratum] += 1
        remaining -= 1

    selected: list[dict[str, Any]] = []
    group_counts: Counter[str] = Counter()
    deferred: list[dict[str, Any]] = []
    for stratum in strata:
        chosen = 0
        for row in buckets[stratum]:
            if group_counts[group_key(row)] >= 2:
                deferred.append(row)
                continue
            enriched = dict(row)
            enriched["selection_method"] = "stratified_random"
            enriched["selection_stratum"] = stratum
            selected.append(enriched)
            group_counts[group_key(row)] += 1
            chosen += 1
            if chosen == quotas[stratum]:
                break
        if chosen != quotas[stratum]:
            raise ValueError(f"could not satisfy stratum {stratum}")
    if len(selected) != size:
        raise AssertionError("stratified gold selection did not reach requested size")
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dataset", type=Path, default=DEFAULT_MODEL_DATASET)
    parser.add_argument("--train-candidates", type=Path, default=DEFAULT_TRAIN_CANDIDATES)
    parser.add_argument("--gold-candidates", type=Path, default=DEFAULT_GOLD_CANDIDATES)
    parser.add_argument("--train-output", type=Path, default=DEFAULT_TRAIN_OUTPUT)
    parser.add_argument("--gold-output", type=Path, default=DEFAULT_GOLD_OUTPUT)
    parser.add_argument("--gold-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    model = TfidfKnnAxisRegressor(word_ngram_max=2).fit(load_model_examples(args.model_dataset))
    scored_train = score_train_candidates(load_jsonl(args.train_candidates), model)
    active_train = select_active_training(scored_train, args.seed)
    expected_train_size = sum(count for _, count in TRAIN_REASON_QUOTAS)
    if len(active_train) != expected_train_size:
        raise SystemExit(f"active train selection is {len(active_train)}; expected {expected_train_size}")
    gold = select_stratified_gold(load_jsonl(args.gold_candidates), args.gold_size, args.seed)
    write_jsonl(active_train, args.train_output)
    write_jsonl(gold, args.gold_output)
    print(f"train_active_candidates={len(active_train)}")
    print("train_reasons=" + ", ".join(f"{key}:{Counter(row['selection_reason'] for row in active_train)[key]}" for key, _ in TRAIN_REASON_QUOTAS))
    print(f"gold_stratified_candidates={len(gold)}")
    print(f"gold_strata={len({row['selection_stratum'] for row in gold})}")
    print(f"train_output={args.train_output}")
    print(f"gold_output={args.gold_output}")


if __name__ == "__main__":
    main()
