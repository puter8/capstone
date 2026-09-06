# -*- coding: utf-8 -*-
"""Export source-blind review CSV files from real-speech candidates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


AXIS_KEYS = ("Formality", "Energy", "Intimacy", "Humor", "Curiosity")
REVIEW_FIELDS = (
    "review_set",
    "review_id",
    "utterance",
    "previous_turn",
    "next_turn",
    "reviewed_Formality",
    "reviewed_Energy",
    "reviewed_Intimacy",
    "reviewed_Humor",
    "reviewed_Curiosity",
    "reviewer_id",
    "review_status",
    "reviewer_notes",
)
ENERGY_CURIOSITY_FIELDS = (
    "review_set",
    "review_id",
    "utterance",
    "previous_turn",
    "next_turn",
    "reviewed_Energy",
    "reviewed_Curiosity",
    "reviewer_id",
    "review_status",
    "reviewer_notes",
)


def review_fields(axes: str) -> tuple[str, ...]:
    if axes == "all":
        return REVIEW_FIELDS
    if axes == "energy-curiosity":
        return ENERGY_CURIOSITY_FIELDS
    raise ValueError(f"unsupported review axes: {axes}")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def review_row(row: dict[str, Any], review_set: str, index: int, axes: str = "all") -> dict[str, str]:
    fields = review_fields(axes)
    return {
        "review_set": review_set,
        "review_id": f"{review_set}-{index:04d}",
        "utterance": str(row["utterance"]),
        "previous_turn": str(row.get("previous_turn") or ""),
        "next_turn": str(row.get("next_turn") or ""),
        **{f"reviewed_{axis}": "" for axis in AXIS_KEYS if f"reviewed_{axis}" in fields},
        "reviewer_id": "",
        "review_status": "pending",
        "reviewer_notes": "",
    }


def write_review_csv(rows: list[dict[str, Any]], review_set: str, output_path: Path, axes: str = "all") -> None:
    fields = review_fields(axes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(review_row(row, review_set, index, axes) for index, row in enumerate(rows, start=1))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review-set", choices=("gold", "train"), required=True)
    parser.add_argument("--axes", choices=("all", "energy-curiosity"), default="all")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = load_jsonl(args.input)
    write_review_csv(rows, args.review_set, args.output, args.axes)
    print(f"rows={len(rows)}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
