# -*- coding: utf-8 -*-
"""Build the calibration (B1) and Energy/Humor pilot (B2) candidate sets.

Both draw from the 1,200-row train candidate reservoir. The reservoir shares
no ``canonical_group`` with the gold reservoir, so the reserved final-test
pool cannot leak here, but the exclusion is still asserted.

Fixed policy (recorded in the manifest; do not change after CSVs go out):

B2 pilot arms are allocated first, each removing its groups from the pool:
  1. event      -- every AMI row with a 'laugh' annotation event that survives
                   the train-120 and reserved-group exclusion (actual yield,
                   currently 14; NOT padded to a round number).
  2. ami_control-- the same count of AMI rows with NO annotation event, so the
                   'laughter' signal can be separated from a plain AMI-source
                   effect.
  3. disagree   -- top rows by |rule - ML| on Energy and on Humor, an equal
                   per-axis quota fixed at 8 + 8 = 16.
  4. residual   -- 16 rows drawn at random from whatever is left ("residual
                   control").
  pilot axes: Energy, Humor. dataset_partition = train.

B1 calibration then takes 16 rows per source (AMI / NICT / Taskmaster) from
the still-unused groups, one row per canonical group, deterministic.
  calibration axes: all five. dataset_partition = dev.
  Explicitly NOT a natural-distribution performance estimate.

Run from the repository root:
  python scripts/build_calibration_pilot_sets.py
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

from ai.analyzers import RuleBasedAxisAnalyzer
from ai.ml_baseline import TfidfKnnAxisRegressor, load_default_axis_dataset

DEFAULT_RESERVOIR = Path("data/fixtures/ml_transition_train_candidates_1200.jsonl")
DEFAULT_EC120 = Path("data/fixtures/ml_transition_train_active_ec_candidates_120.jsonl")
DEFAULT_RESERVED_POOL = Path("data/fixtures/ml_transition_reserved_final_test_pool.jsonl")
DEFAULT_CALIB_OUT = Path("data/fixtures/ml_transition_calibration_candidates_48.jsonl")
DEFAULT_PILOT_OUT = Path("data/fixtures/ml_transition_pilot_eh_candidates.jsonl")
DEFAULT_SEED = 20260910

CALIB_PER_SOURCE = 16
DISAGREE_PER_AXIS = 8
RESIDUAL_COUNT = 16
DISAGREE_AXES = ("Energy", "Humor")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def canonical_group(row: dict[str, Any]) -> str:
    source = str(row.get("source", "unknown"))
    group = row.get("source_group") or row.get("source_record_id") or row.get("source_file")
    if not group:
        return f"{source}:utt:{str(row['utterance']).strip().casefold()}"
    return f"{source}:{group}"


def _hash_key(seed: int, text: str) -> str:
    return hashlib.sha256(f"{seed}|{text}".encode()).hexdigest()


def _has_laugh(row: dict[str, Any]) -> bool:
    events = row.get("annotation_events") or []
    if isinstance(events, str):
        events = [events]
    return "laugh" in [str(event).lower() for event in events]


def _has_any_event(row: dict[str, Any]) -> bool:
    events = row.get("annotation_events") or []
    return bool(events)


def _take_by_hash(rows: list[dict[str, Any]], count: int, seed: int, used_groups: set[str]) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda r: _hash_key(seed, canonical_group(r) + "|" + str(r["utterance"])))
    picked: list[dict[str, Any]] = []
    for row in ordered:
        group = canonical_group(row)
        if group in used_groups:
            continue
        picked.append(row)
        used_groups.add(group)
        if len(picked) == count:
            break
    return picked


def build_sets(
    reservoir: list[dict[str, Any]],
    ec120_groups: set[str],
    reserved_groups: set[str],
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    blocked = ec120_groups | reserved_groups
    leak = [r for r in reservoir if canonical_group(r) in reserved_groups]
    if leak:
        raise SystemExit(f"reservoir overlaps the reserved final-test pool on {len(leak)} rows -- aborting")

    pool = [r for r in reservoir if canonical_group(r) not in blocked]
    used_groups: set[str] = set()

    # --- B2 arm 1: event (actual yield, not padded) ---
    event_rows = _take_by_hash([r for r in pool if r["source"] == "ami_real" and _has_laugh(r)], 10_000, seed, used_groups)
    event_count = len(event_rows)

    # --- B2 arm 2: AMI non-event control, matched count ---
    control_rows = _take_by_hash(
        [r for r in pool if r["source"] == "ami_real" and not _has_any_event(r)],
        event_count,
        seed,
        used_groups,
    )

    # --- B2 arm 3: model disagreement, fixed per-axis quota ---
    rule = RuleBasedAxisAnalyzer()
    ml = TfidfKnnAxisRegressor().fit(load_default_axis_dataset(), require_full_axes=True)
    scored: list[tuple[dict[str, Any], dict[str, float]]] = []
    remaining = [r for r in pool if canonical_group(r) not in used_groups]
    for row in remaining:
        rule_axes = rule.analyze(row["utterance"]).to_axes_dict()
        ml_axes = ml.predict(row["utterance"])
        scored.append((row, {axis: abs(rule_axes[axis] - ml_axes[axis]) for axis in DISAGREE_AXES}))

    disagree_rows: list[dict[str, Any]] = []
    for axis in DISAGREE_AXES:
        ranked = sorted(
            scored,
            key=lambda pair: (pair[1][axis], _hash_key(seed, str(pair[0]["utterance"]))),
            reverse=True,
        )
        for row, diffs in ranked:
            group = canonical_group(row)
            if group in used_groups:
                continue
            row = dict(row)
            row["_disagree_axis"] = axis
            row["_disagree_delta"] = diffs[axis]
            disagree_rows.append(row)
            used_groups.add(group)
            if sum(1 for r in disagree_rows if r["_disagree_axis"] == axis) == DISAGREE_PER_AXIS:
                break

    # --- B2 arm 4: residual random ---
    residual_pool = [r for r in pool if canonical_group(r) not in used_groups]
    rng = random.Random(f"{seed}|residual")
    rng.shuffle(residual_pool)
    residual_rows = _take_by_hash(residual_pool, RESIDUAL_COUNT, seed, used_groups)

    pilot_rows: list[dict[str, Any]] = []
    for arm, rows in (("event", event_rows), ("ami_control", control_rows), ("disagree", disagree_rows), ("residual", residual_rows)):
        for row in rows:
            tagged = {k: v for k, v in row.items() if not k.startswith("_")}
            tagged["annotation_batch"] = "pilot"
            tagged["dataset_partition"] = "train"
            tagged["pilot_arm"] = arm
            tagged["review_axes"] = ["Energy", "Humor"]
            if "_disagree_axis" in row:
                tagged["disagree_axis"] = row["_disagree_axis"]
                tagged["disagree_delta"] = row["_disagree_delta"]
            pilot_rows.append(tagged)

    # --- B1 calibration: 16 per source from still-unused groups ---
    calib_rows: list[dict[str, Any]] = []
    calib_plan: dict[str, int] = {}
    for source in ("ami_real", "nict_jle_real", "taskmaster1_woz_user_real"):
        source_pool = [r for r in pool if r["source"] == source and canonical_group(r) not in used_groups]
        picked = _take_by_hash(source_pool, CALIB_PER_SOURCE, seed, used_groups)
        calib_plan[source] = len(picked)
        if len(picked) < CALIB_PER_SOURCE:
            raise SystemExit(f"calibration {source}: only {len(picked)}/{CALIB_PER_SOURCE} groups available")
        for row in picked:
            tagged = dict(row)
            tagged["annotation_batch"] = "calibration"
            tagged["dataset_partition"] = "dev"
            tagged["review_axes"] = ["Formality", "Energy", "Intimacy", "Humor", "Curiosity"]
            calib_rows.append(tagged)

    manifest = {
        "seed": seed,
        "reservoir_rows": len(reservoir),
        "blocked_groups": {"ec120": len(ec120_groups), "reserved": len(reserved_groups)},
        "pool_rows_after_block": len(pool),
        "pilot": {
            "event_yield": event_count,
            "ami_control": len(control_rows),
            "disagree": {axis: sum(1 for r in disagree_rows if r["_disagree_axis"] == axis) for axis in DISAGREE_AXES},
            "residual": len(residual_rows),
            "total": len(pilot_rows),
            "axes": ["Energy", "Humor"],
            "source_mix": dict(Counter(r["source"] for r in pilot_rows)),
        },
        "calibration": {
            "per_source": calib_plan,
            "total": len(calib_rows),
            "axes": ["Formality", "Energy", "Intimacy", "Humor", "Curiosity"],
        },
        "note": "calibration is not a natural-distribution performance estimate; it measures inter-rater agreement and scale bias.",
    }
    return calib_rows, pilot_rows, manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reservoir", type=Path, default=DEFAULT_RESERVOIR)
    parser.add_argument("--ec120", type=Path, default=DEFAULT_EC120)
    parser.add_argument("--reserved-pool", type=Path, default=DEFAULT_RESERVED_POOL)
    parser.add_argument("--calibration-output", type=Path, default=DEFAULT_CALIB_OUT)
    parser.add_argument("--pilot-output", type=Path, default=DEFAULT_PILOT_OUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    reservoir = load_jsonl(args.reservoir)
    ec120_groups = {canonical_group(r) for r in load_jsonl(args.ec120)}
    reserved_groups = {r.get("canonical_group") or canonical_group(r) for r in load_jsonl(args.reserved_pool)}

    calib_rows, pilot_rows, manifest = build_sets(reservoir, ec120_groups, reserved_groups, args.seed)

    write_jsonl(calib_rows, args.calibration_output)
    write_jsonl(pilot_rows, args.pilot_output)
    manifest_path = args.pilot_output.with_name("ml_transition_calibration_pilot.plan.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"calibration_output={args.calibration_output}  ({len(calib_rows)} rows)")
    print(f"pilot_output={args.pilot_output}  ({len(pilot_rows)} rows)")
    print(f"plan={manifest_path}")


if __name__ == "__main__":
    main()
