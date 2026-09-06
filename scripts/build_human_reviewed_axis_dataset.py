# -*- coding: utf-8 -*-
"""Convert a completed blind review CSV into labeled JSONL rows."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


AXIS_KEYS = ("Formality", "Energy", "Intimacy", "Humor", "Curiosity")
REVIEW_AXES = {
    "all": AXIS_KEYS,
    "energy-curiosity": ("Energy", "Curiosity"),
}


class ReviewError(ValueError):
    pass


def parse_score(row: dict[str, str], row_number: int, axis: str) -> int:
    value = (row.get(f"reviewed_{axis}") or "").strip()
    if not value:
        raise ReviewError(f"row {row_number}: missing reviewed_{axis}")
    try:
        score = int(float(value))
    except ValueError as exc:
        raise ReviewError(f"row {row_number}: invalid reviewed_{axis}={value!r}") from exc
    if not 0 <= score <= 100:
        raise ReviewError(f"row {row_number}: reviewed_{axis} must be between 0 and 100")
    return score


def convert_row(
    row: dict[str, str],
    candidate: dict[str, Any],
    row_number: int,
    labeler: str,
    axes: str = "all",
) -> dict[str, Any]:
    if (row.get("review_status") or "").strip().lower() != "completed":
        raise ReviewError(f"row {row_number}: review_status must be completed")
    review_set = (row.get("review_set") or "").strip()
    if review_set not in {"gold", "train"}:
        raise ReviewError(f"row {row_number}: review_set must be gold or train")
    review_axes = REVIEW_AXES[axes]
    utterance = (row.get("utterance") or "").strip()
    if utterance != str(candidate.get("utterance", "")).strip():
        raise ReviewError(f"row {row_number}: utterance does not match its candidate record")
    return {
        "utterance": utterance,
        "axes": {axis: parse_score(row, row_number, axis) for axis in review_axes},
        "style": "conversation",
        "split": "test" if review_set == "gold" else "train",
        "notes": row.get("reviewer_notes", ""),
        "source": candidate.get("source", "unknown"),
        "source_group": candidate.get("source_group", ""),
        "source_record_id": candidate.get("source_record_id", ""),
        "focus_bucket": candidate.get("focus_bucket", ""),
        "label_status": "human_reviewed_blind",
        "labeler": labeler,
        "reviewer_id": row.get("reviewer_id", ""),
        "review_set": review_set,
        "review_axes": list(review_axes),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def candidate_index(rows: list[dict[str, Any]], review_set: str) -> dict[str, dict[str, Any]]:
    return {f"{review_set}-{index:04d}": row for index, row in enumerate(rows, start=1)}


def load_review_csv(
    path: Path,
    candidates: list[dict[str, Any]],
    labeler: str,
    axes: str = "all",
) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ReviewError("review CSV is empty")
    review_set = (rows[0].get("review_set") or "").strip()
    if review_set not in {"gold", "train"}:
        raise ReviewError("review CSV has an invalid review_set")
    if any((row.get("review_set") or "").strip() != review_set for row in rows):
        raise ReviewError("review CSV mixes review sets")
    indexed_candidates = candidate_index(candidates, review_set)
    converted: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=1):
        review_id = (row.get("review_id") or "").strip()
        if review_id in seen_ids:
            raise ReviewError(f"row {row_number}: duplicate review_id {review_id!r}")
        candidate = indexed_candidates.get(review_id)
        if candidate is None:
            raise ReviewError(f"row {row_number}: unknown review_id {review_id!r}")
        candidate_partition = str(candidate.get("review_partition", review_set)).strip()
        if candidate_partition != review_set:
            raise ReviewError(f"row {row_number}: candidate partition does not match review_set")
        seen_ids.add(review_id)
        converted.append(convert_row(row, candidate, row_number, labeler, axes))
    return converted


def write_jsonl(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--labeler", default="human_blind_review")
    parser.add_argument("--axes", choices=tuple(REVIEW_AXES), default="all")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        rows = load_review_csv(args.input, load_jsonl(args.candidates), args.labeler, args.axes)
    except ReviewError as exc:
        raise SystemExit(f"review CSV is not complete: {exc}") from exc
    write_jsonl(rows, args.output)
    print(f"rows={len(rows)}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
