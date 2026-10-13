# -*- coding: utf-8 -*-
"""Carve a group-safe dev partition out of the combined v3 training pool
(v3.0 Rubric 4-3 / 7: model comparison happens on dev, never on the 31-item
eval partition). Deterministic hash split, same pattern as
scripts/select_purpose_v3_active_candidates.py's eval_or_train().
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMBINED_PATH = ROOT / "data/fixtures/pally_purpose_v3_combined_train.jsonl"
DEV_FRACTION_MOD = 5  # 1/5 of groups -> dev (~20%)
TRAIN_OUT = ROOT / "data/fixtures/pally_purpose_v3_train_dev_split_train.jsonl"
DEV_OUT = ROOT / "data/fixtures/pally_purpose_v3_train_dev_split_dev.jsonl"


def group_bucket(group: str) -> int:
    digest = hashlib.sha256(group.encode("utf-8")).hexdigest()
    return int(digest, 16) % DEV_FRACTION_MOD


def main() -> None:
    rows = []
    with COMBINED_PATH.open(encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))

    train_rows, dev_rows = [], []
    for row in rows:
        bucket = group_bucket(row["source_group"])
        (dev_rows if bucket == 0 else train_rows).append(row)

    with TRAIN_OUT.open("w", encoding="utf-8") as f:
        for row in train_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with DEV_OUT.open("w", encoding="utf-8") as f:
        for row in dev_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    train_groups = {r["source_group"] for r in train_rows}
    dev_groups = {r["source_group"] for r in dev_rows}
    overlap = train_groups & dev_groups
    print(f"train: {len(train_rows)} rows / {len(train_groups)} groups -> {TRAIN_OUT.name}")
    print(f"dev:   {len(dev_rows)} rows / {len(dev_groups)} groups -> {DEV_OUT.name}")
    print(f"group overlap between train/dev: {len(overlap)}")
    if overlap:
        raise AssertionError(f"group leakage between train/dev: {sorted(overlap)[:5]}")


if __name__ == "__main__":
    main()
