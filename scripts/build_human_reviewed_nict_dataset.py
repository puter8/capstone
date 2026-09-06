# -*- coding: utf-8 -*-
"""Convert the human-reviewed NICT CSV into gold JSONL labels."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

AXIS_KEYS = ("Formality", "Energy", "Intimacy", "Humor", "Curiosity")

DEFAULT_INPUT = Path("data/fixtures/nict_jle_labeled_draft_600_review.csv")
DEFAULT_OUTPUT = Path("data/fixtures/nict_jle_labeled_human_600.jsonl")
DEFAULT_LABELER = "codex_accept_draft_per_user"


class ReviewError(ValueError):
    pass


def parse_axis_score(row: dict[str, str], row_number: int, axis: str) -> int:
    field = f"reviewed_{axis}"
    raw_value = (row.get(field) or "").strip()
    if raw_value == "":
        raise ReviewError(f"row {row_number}: missing {field}")
    try:
        value = int(float(raw_value))
    except ValueError as exc:
        raise ReviewError(f"row {row_number}: invalid {field}={raw_value!r}") from exc
    if not 0 <= value <= 100:
        raise ReviewError(f"row {row_number}: {field} must be between 0 and 100, got {value}")
    return value


def convert_row(row: dict[str, str], row_number: int, labeler: str) -> dict[str, Any]:
    axes = {axis: parse_axis_score(row, row_number, axis) for axis in AXIS_KEYS}
    return {
        "utterance": row["utterance"],
        "axes": axes,
        "style": row.get("style") or "conversation",
        "split": "train",
        "notes": row.get("notes", ""),
        "source": "nict_jle_real",
        "label_status": "human_reviewed",
        "labeler": labeler,
        "sample_bucket": row.get("sample_bucket", ""),
        "source_line": int(row["source_line"]) if (row.get("source_line") or "").strip() else None,
    }


def load_review_csv(path: Path, labeler: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=1):
            rows.append(convert_row(row, row_number, labeler))
    return rows


def write_jsonl(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--labeler", default=DEFAULT_LABELER)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        rows = load_review_csv(args.input, args.labeler)
    except ReviewError as exc:
        raise SystemExit(f"review CSV is not complete: {exc}") from exc
    write_jsonl(rows, args.output)
    print(f"rows={len(rows)}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
