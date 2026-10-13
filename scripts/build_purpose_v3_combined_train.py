# -*- coding: utf-8 -*-
"""Combine the 150-item v3 active-learning labels with the 100-item paper
train-80 seed into one JSONL for ai/ml_baseline.py (v3.0 Rubric §6).

- week2 338 is excluded by default (v3.0 §6 — ablation-only, not in the base set).
- The 31-item eval partition is never read here; it stays untouched until §5's
  one-time final evaluation.
- v2.2 §13: an axis whose case_type is context_insufficient gets regression
  weight 0 -- implemented by omitting that axis key from the row's "axes" dict
  (ai/ml_baseline.py's partial-label support treats a missing axis as "no
  training signal for this axis from this row", not as 0). We exclude on
  case_type alone, not case_type+score_status=="provisional": a 2026-10-12
  Codex cross-check found 21 rows in the new 150-item workbook where case_type
  is context_insufficient but score_status was left blank (not explicitly
  "provisional") -- that blank is a labeling-completeness gap, not a signal
  that the row is safe to treat as final, so it must not slip through.
- A row whose axes dict ends up empty (all three axes excluded) is dropped
  entirely rather than emitted with axes={} -- ai/ml_baseline.py's partial-label
  loader requires at least one axis per row and raises otherwise (also found by
  the 2026-10-12 Codex cross-check, which hit this on workbook item
  ES2009a.A.dialog-act.vkaraisk.213).
"""
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "data/fixtures/pally_purpose_v3_active_train_candidates.jsonl"
WORKBOOK_PATH = ROOT / "data/fixtures/pally_purpose_v3_labeling_workbook.xlsx"
SEED_100_PATH = ROOT / "data/fixtures/pally_purpose_v1_items_100.jsonl"
EVAL_PARTITION_PATH = ROOT / "data/fixtures/pally_purpose_v3_eval_partition.jsonl"
OUT_PATH = ROOT / "data/fixtures/pally_purpose_v3_combined_train.jsonl"

AXES_V3 = ["Formality", "Humor", "Curiosity"]  # this round's scope (v3.0 title)


def load_candidates() -> dict:
    by_id = {}
    with CANDIDATES_PATH.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            by_id[row["source_record_id"]] = row
    return by_id


def load_workbook_rows() -> list[dict]:
    wb = openpyxl.load_workbook(WORKBOOK_PATH)
    ws = wb["v3_labeling"]
    headers = [c.value for c in ws[1]]
    idx = {h: i for i, h in enumerate(headers)}
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        rows.append({h: row[i] for h, i in idx.items()})
    return rows


def build_v3_rows() -> list[dict]:
    candidates = load_candidates()
    wb_rows = load_workbook_rows()
    missing_candidate = []
    dropped_empty_rows = []
    out = []
    for r in wb_rows:
        item_id = r["item_id"]
        cand = candidates.get(item_id)
        if cand is None:
            missing_candidate.append(item_id)
            continue

        axes = {}
        label_source = {}
        dropped_provisional = []
        for axis in AXES_V3:
            score = r.get(axis)
            if score is None:
                continue
            case_type = r.get(f"{axis}_case_type")
            if case_type == "context_insufficient":
                dropped_provisional.append(axis)
                continue  # v2.2 13: regression weight 0 -> omit the axis key
            axes[axis] = int(score)
            label_source[axis] = str(r.get("label_source") or "single_rater_v3_eunheay")

        if not axes:
            dropped_empty_rows.append(item_id)
            continue  # all axes excluded -- nothing left to train on from this row

        out.append({
            "item_id": item_id,
            "utterance": cand["utterance"],
            "axes": axes,
            "label_source": label_source,
            "style": "conversation",
            "source": cand["source"],
            "source_group": cand["source_group"],
            "dropped_provisional_axes": dropped_provisional,
            "primary_function": r.get("primary_function"),
            "language_form": r.get("language_form"),
            "rubric_version": "v2.2",
            "protocol_version": "v3.0",
            "acquisition_round": "2026-10-active-r1",
        })
    if missing_candidate:
        raise ValueError(f"{len(missing_candidate)} workbook item_id(s) not found in candidates file: {missing_candidate[:5]}...")
    if dropped_empty_rows:
        print(f"[build_v3_rows] dropped {len(dropped_empty_rows)} row(s) with no usable axis: {dropped_empty_rows}")
    return out


def _meeting_group(source_id: str) -> str:
    """AMI/ICSI/Santa Barbara record IDs are '<meeting>.<speaker>.<...>' --
    the meeting is the first dot-segment (matches source_group convention used
    by scripts/select_purpose_v3_active_candidates.py and the eval partition,
    e.g. 'ES2005d.A.dialog-act.dharshi.52' -> 'ES2005d'). A 2026-10-12 Codex
    cross-check found the seed-80 rows were using the *whole* source_id
    (utterance-level) as source_group, which never collides even for two
    utterances from the same meeting -- that defeated both the eval-partition
    leak check and the train/dev group split (8 meetings leaked each way)."""
    return source_id.split(".")[0] if source_id else ""


def build_seed80_rows() -> list[dict]:
    out = []
    with SEED_100_PATH.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("split") != "train":
                continue
            axes = {}
            label_source = {}
            src = str(row.get("label_source") or "")
            for axis_key, out_key in (("formality", "Formality"), ("humor", "Humor"), ("curiosity", "Curiosity")):
                val = row.get(axis_key)
                if val is None:
                    continue
                axes[out_key] = int(val)
                label_source[out_key] = src
            out.append({
                "item_id": row["item_id"],
                "utterance": row["target_turn"],
                "axes": axes,
                "label_source": label_source,
                "style": "conversation",
                "source": row.get("_source_corpus", ""),
                "source_group": _meeting_group(row.get("source_id", "")),
                "dropped_provisional_axes": [],
                "primary_function": None,
                "language_form": row.get("language_form"),
                "rubric_version": "v2.2",
                "protocol_version": "v1_paper_seed",
                "acquisition_round": "paper_seed_100",
            })
    return out


def load_eval_groups() -> set:
    groups = set()
    with EVAL_PARTITION_PATH.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            groups.add(row.get("source_group"))
    return groups


def main() -> None:
    v3_rows = build_v3_rows()
    seed_rows = build_seed80_rows()
    eval_groups = load_eval_groups()

    # The 150-item v3 set was selected with eval's groups already excluded
    # (scripts/select_purpose_v3_active_candidates.py) -- any leak there is a
    # real bug and must hard-fail. The 100-item paper seed predates the v3
    # eval partition and was never checked against it, so an overlap there is
    # expected and handled by exclusion, not a crash (2026-10-12 Codex
    # cross-check found 8 such meetings).
    v3_leaked = [r["item_id"] for r in v3_rows if r["source_group"] in eval_groups]
    if v3_leaked:
        raise ValueError(f"{len(v3_leaked)} v3-labeled row(s) share a source_group with the eval partition (should be impossible by selection design): {v3_leaked[:5]}")

    seed_leaked = [r for r in seed_rows if r["source_group"] in eval_groups]
    seed_kept = [r for r in seed_rows if r["source_group"] not in eval_groups]
    if seed_leaked:
        print(f"[main] excluding {len(seed_leaked)} seed-80 row(s) that share a meeting with the eval partition: {[r['item_id'] for r in seed_leaked]}")

    combined = v3_rows + seed_kept

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in combined:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"v3 labeled rows: {len(v3_rows)}")
    print(f"seed-80 rows kept: {len(seed_kept)} (excluded {len(seed_leaked)} for eval overlap)")
    print(f"combined total: {len(combined)} -> {OUT_PATH}")
    dropped_total = sum(len(r["dropped_provisional_axes"]) for r in v3_rows)
    print(f"axes dropped as context_insufficient: {dropped_total}")
    print(f"eval-partition group overlap check: 0 leaked (of {len(eval_groups)} protected groups)")


if __name__ == "__main__":
    main()
