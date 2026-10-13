# -*- coding: utf-8 -*-
"""Active-learning candidate selection for Pally Rubric v3.0 (F/H/C data expansion).

See docs/AI_TACTIC/Pally_RUBRIC_v3.0_md section 4-5 for the full protocol this
implements. Summary:

1. Partition the unused AMI/ICSI pool into an eval branch and a train branch
   BY GROUP (meeting_id), before any model touches the data. This is a pure
   hash-based split, independent of predictions -- it is what makes the eval
   partition a legitimate held-out set later (section 5).
2. Within the train branch only, score every surviving candidate with both
   the already-deployed seed model (data/models/purpose_axis_models.joblib,
   trained on the official 100-item human-labeled set) and the existing
   rule-based analyzer, and select by disagreement/extremeness quotas -- this
   is the actual "active learning" step (section 4).
3. The eval branch is NEVER touched by a model. A small stratified-random
   sample is drawn from it purely for later held-out reporting (section 5).

Excludes: anything already in the 100-item set, the week2 338-item set, the
old ml-transition combined training pool (text-level), and every group that
belongs to the old track's gold-200 / reserved-176 pools (group-level, so
neighboring utterances from the same meeting can't leak in either).

Model predictions are used ONLY to pick which candidates a human should look
at next. They are never written into the output as a label -- every row here
still needs a real blind human score before it can train anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.sample_real_speech_label_candidates import candidate_rejection_reason
from scripts.train_purpose_axis_models import predict as seed_model_predict
from ai.analyzers import RuleBasedAxisAnalyzer

AXES = ("formality", "humor", "curiosity")
AXIS_KEY_MAP = {"formality": "Formality", "humor": "Humor", "curiosity": "Curiosity"}

DEFAULT_POOL_PATHS = (
    Path("data/fixtures/ami_utterances.jsonl"),
    Path("data/fixtures/icsi_utterances.jsonl"),
)
DEFAULT_SEED_MODEL = Path("data/models/purpose_axis_models.joblib")
DEFAULT_ITEMS_100 = Path("data/fixtures/pally_purpose_v1_items_100.jsonl")
DEFAULT_WEEK2 = Path("data/axis_dataset_week2.jsonl")
DEFAULT_OLD_COMBINED = Path("data/fixtures/axis_dataset_combined_real_speech_experimental.jsonl")
DEFAULT_OLD_GOLD_200 = Path("data/fixtures/ml_transition_gold_human_200.jsonl")
DEFAULT_OLD_RESERVED = Path("data/fixtures/ml_transition_reserved_final_test_pool.jsonl")

DEFAULT_TRAIN_OUT = Path("data/fixtures/pally_purpose_v3_active_train_candidates.jsonl")
DEFAULT_EVAL_OUT = Path("data/fixtures/pally_purpose_v3_eval_partition.jsonl")

DEFAULT_SEED = 20261006
EVAL_TARGET = 40
TRAIN_TARGET = 150
MAX_PER_GROUP = 2  # AMI+ICSI combined have only 214 distinct meetings total (confirmed
                   # by direct count); the old ml-transition track's eval pools alone
                   # already touch ~160-180 of them, so MAX_PER_GROUP=1 cannot reach a
                   # 150+40-item target. 2 per meeting (each meeting runs ~30-60 min
                   # with hundreds of candidate turns) is a deliberate, documented
                   # loosening -- not silently dropped.
EVAL_PARTITION_FRACTION = 5  # 1-in-N groups go to eval, by hash

# Quota sizes within the train-branch selection (sums to TRAIN_TARGET default).
TRAIN_QUOTAS = {
    "formality_disagreement": 25,
    "formality_extreme": 15,
    "humor_disagreement": 20,
    "humor_high_enrich": 25,   # Humor is scarce in meeting corpora -- deliberately oversample predicted-high
    "humor_low_control": 10,
    "curiosity_disagreement": 25,
    "curiosity_extreme": 15,
    "random_control": 15,
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_text(text: str) -> str:
    return " ".join(str(text).lower().split())


def group_key(row: dict[str, Any]) -> str:
    source = str(row.get("source", "unknown"))
    group = str(row.get("source_group") or row.get("meeting_id") or row.get("source_record_id") or row["utterance"])
    return f"{source}:{group}"


def eval_or_train(row: dict[str, Any]) -> str:
    digest = hashlib.sha256(group_key(row).encode("utf-8")).digest()
    return "eval" if int.from_bytes(digest[:4], "big") % EVAL_PARTITION_FRACTION == 0 else "train"


def load_exclusions() -> tuple[set[str], set[str]]:
    """Returns (excluded_texts, excluded_groups)."""
    excluded_texts: set[str] = set()
    excluded_groups: set[str] = set()

    for row in load_jsonl(DEFAULT_ITEMS_100):
        excluded_texts.add(normalize_text(row.get("target_turn", "")))
    for row in load_jsonl(DEFAULT_WEEK2):
        excluded_texts.add(normalize_text(row.get("utterance", "")))
    for row in load_jsonl(DEFAULT_OLD_COMBINED):
        excluded_texts.add(normalize_text(row.get("utterance", "")))
        # Group-level exclusion intentionally NOT applied here: this pool was the old
        # track's TRAINING data, not a held-out evaluation set, so reusing one of its
        # meetings for new candidates carries no leakage risk. Only gold-200/reserved
        # below (the old track's actual eval pools) get the group-level exclusion --
        # AMI+ICSI only have 214 meetings total, so excluding every group the old
        # *training* pool ever touched would eat most of the corpus for no real reason.
    for row in load_jsonl(DEFAULT_OLD_GOLD_200):
        excluded_groups.add(group_key(row))
    if DEFAULT_OLD_RESERVED.exists():
        for row in load_jsonl(DEFAULT_OLD_RESERVED):
            excluded_groups.add(group_key(row))

    excluded_texts.discard("")
    return excluded_texts, excluded_groups


def score_candidates(rows: list[dict[str, Any]], seed_model_path: Path) -> list[dict[str, Any]]:
    """Attach rule-based and seed-model F/H/C predictions, plus disagreement, to each row."""
    texts = [row["utterance"] for row in rows]
    seed_preds = seed_model_predict(seed_model_path, texts)
    rule_analyzer = RuleBasedAxisAnalyzer()

    scored = []
    for row, seed_pred in zip(rows, seed_preds):
        rule_axes = rule_analyzer.analyze(row["utterance"]).model_dump()
        entry = dict(row)
        entry["seed_predicted_purpose"] = seed_pred["predicted_purpose"]
        for axis in AXES:
            ml_value = seed_pred["predicted_axes"][axis]
            rule_value = rule_axes[AXIS_KEY_MAP[axis]]
            entry[f"_ml_{axis}"] = ml_value
            entry[f"_rule_{axis}"] = rule_value
            entry[f"_disagreement_{axis}"] = abs(ml_value - rule_value)
        scored.append(entry)
    return scored


def select_by_quota(
    scored: list[dict[str, Any]],
    quotas: dict[str, int],
    rng: random.Random,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    group_counts: Counter[str] = Counter()
    used_ids: set[int] = set()

    def take(ranked: list[dict[str, Any]], reason: str, n: int) -> None:
        count = 0
        for row in ranked:
            rid = id(row)
            if rid in used_ids:
                continue
            gk = group_key(row)
            if group_counts[gk] >= MAX_PER_GROUP:
                continue
            row["_selection_reason"] = reason
            selected.append(row)
            used_ids.add(rid)
            group_counts[gk] += 1
            count += 1
            if count >= n:
                return

    by_formality_dis = sorted(scored, key=lambda r: -r["_disagreement_formality"])
    take(by_formality_dis, "formality_disagreement", quotas["formality_disagreement"])

    by_formality_extreme = sorted(scored, key=lambda r: -abs(r["_ml_formality"] - 50))
    take(by_formality_extreme, "formality_extreme", quotas["formality_extreme"])

    by_humor_dis = sorted(scored, key=lambda r: -r["_disagreement_humor"])
    take(by_humor_dis, "humor_disagreement", quotas["humor_disagreement"])

    by_humor_high = sorted(scored, key=lambda r: -r["_ml_humor"])
    take(by_humor_high, "humor_high_enrich", quotas["humor_high_enrich"])

    by_humor_low = [r for r in scored if r["_ml_humor"] <= 20]
    rng.shuffle(by_humor_low)
    take(by_humor_low, "humor_low_control", quotas["humor_low_control"])

    by_curiosity_dis = sorted(scored, key=lambda r: -r["_disagreement_curiosity"])
    take(by_curiosity_dis, "curiosity_disagreement", quotas["curiosity_disagreement"])

    by_curiosity_extreme = sorted(scored, key=lambda r: -abs(r["_ml_curiosity"] - 50))
    take(by_curiosity_extreme, "curiosity_extreme", quotas["curiosity_extreme"])

    remaining = [r for r in scored if id(r) not in used_ids]
    rng.shuffle(remaining)
    take(remaining, "random_control", quotas["random_control"])

    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, nargs="+", default=list(DEFAULT_POOL_PATHS))
    parser.add_argument("--seed-model", type=Path, default=DEFAULT_SEED_MODEL)
    parser.add_argument("--train-out", type=Path, default=DEFAULT_TRAIN_OUT)
    parser.add_argument("--eval-out", type=Path, default=DEFAULT_EVAL_OUT)
    parser.add_argument("--eval-target", type=int, default=EVAL_TARGET)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    rng = random.Random(args.seed)

    print("Loading pool...")
    pool: list[dict[str, Any]] = []
    for path in args.pool:
        pool.extend(load_jsonl(path))
    print(f"  {len(pool)} raw rows from {len(args.pool)} file(s)")

    print("Loading exclusions...")
    excluded_texts, excluded_groups = load_exclusions()
    print(f"  {len(excluded_texts)} excluded texts, {len(excluded_groups)} excluded groups")

    print("Filtering (quality + exclusions)...")
    eligible: list[dict[str, Any]] = []
    rejection_counts: Counter[str] = Counter()
    for row in pool:
        if normalize_text(row.get("utterance", "")) in excluded_texts:
            rejection_counts["already_used_text"] += 1
            continue
        if group_key(row) in excluded_groups:
            rejection_counts["old_track_group"] += 1
            continue
        reason = candidate_rejection_reason(row)
        if reason:
            rejection_counts[reason] += 1
            continue
        eligible.append(row)
    print(f"  {len(eligible)} eligible after filtering")
    print(f"  rejection breakdown: {dict(rejection_counts.most_common(10))}")

    print("Partitioning by group (eval vs train, before any model touches the data)...")
    eval_pool = [r for r in eligible if eval_or_train(r) == "eval"]
    train_pool = [r for r in eligible if eval_or_train(r) == "train"]
    print(f"  eval-eligible groups pool: {len(eval_pool)} rows")
    print(f"  train-eligible pool: {len(train_pool)} rows")

    print(f"Drawing {args.eval_target} eval items (pure stratified random, no model)...")
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in eval_pool:
        by_source.setdefault(str(row.get("source", "unknown")), []).append(row)
    eval_selected: list[dict[str, Any]] = []
    used_eval_groups: set[str] = set()
    sources = sorted(by_source)
    per_source_target = max(1, args.eval_target // max(1, len(sources)))
    for source in sources:
        rows = by_source[source]
        rng.shuffle(rows)
        count = 0
        for row in rows:
            gk = group_key(row)
            if gk in used_eval_groups:
                continue
            eval_selected.append(row)
            used_eval_groups.add(gk)
            count += 1
            if count >= per_source_target:
                break
    rng.shuffle(eval_selected)
    eval_selected = eval_selected[: args.eval_target]
    print(f"  selected {len(eval_selected)} eval items across sources {sources}")

    print(f"Scoring train-eligible pool with seed model ({args.seed_model}) + rule analyzer...")
    print("  (this touches the seed model and rule analyzer only -- eval partition above was never scored)")
    scored_train = score_candidates(train_pool, args.seed_model)

    print("Selecting active-learning training candidates by quota...")
    selected_train = select_by_quota(scored_train, TRAIN_QUOTAS, rng)
    print(f"  selected {len(selected_train)} train candidates (target was {sum(TRAIN_QUOTAS.values())})")
    reason_counts = Counter(r["_selection_reason"] for r in selected_train)
    print(f"  by reason: {dict(reason_counts)}")

    # Strip model-score fields before writing the labeling-facing file -- these
    # must never leak into the blind workbook (rubric v3.0 section 4 leakage guard).
    clean_train = []
    for row in selected_train:
        clean = {
            "utterance": row["utterance"],
            "source": row.get("source"),
            "source_group": row.get("source_group") or row.get("meeting_id"),
            "source_record_id": row.get("source_record_id"),
            "previous_turn": row.get("previous_turn"),
            "selection_reason": row["_selection_reason"],
            "protocol_version": "v3.0",
        }
        clean_train.append(clean)

    clean_eval = []
    for row in eval_selected:
        clean_eval.append({
            "utterance": row["utterance"],
            "source": row.get("source"),
            "source_group": row.get("source_group") or row.get("meeting_id"),
            "source_record_id": row.get("source_record_id"),
            "previous_turn": row.get("previous_turn"),
            "selection_reason": "eval_partition_stratified_random",
            "protocol_version": "v3.0",
        })

    write_jsonl(clean_train, args.train_out)
    write_jsonl(clean_eval, args.eval_out)
    print(f"Wrote {len(clean_train)} train candidates -> {args.train_out}")
    print(f"Wrote {len(clean_eval)} eval candidates -> {args.eval_out}")

    # Also keep the full score detail (with model predictions) in a separate
    # internal-only file for diagnostics -- NOT for the labeling workbook.
    diag_path = args.train_out.with_name(args.train_out.stem + "_diagnostic.jsonl")
    write_jsonl(selected_train, diag_path)
    print(f"Wrote diagnostic (with model scores, internal only) -> {diag_path}")


if __name__ == "__main__":
    main()
