# -*- coding: utf-8 -*-
"""Combine the seed set and provisional real-speech labels into one JSONL set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_BASE = Path("data/axis_dataset_week2.jsonl")
DEFAULT_OUTPUT = Path("data/fixtures/axis_dataset_combined_real_speech_provisional.jsonl")
PROVENANCE_KEYS = (
    "label_status",
    "labeler",
    "sample_bucket",
    "source_line",
    "source_record_id",
    "source_group",
    "raw_split",
    "session_id",
    "speaker",
    "location",
    "start_time",
    "end_time",
    "reference",
    "annotation_events",
    "dialogue_id",
    "participant_role",
    "utterance_id",
    "move_label",
    "conversation_id",
    "instruction_id",
    "dialogue_turn_index",
    "meeting_id",
    "speaker_id",
    "speaker_native_language",
    "speaker_role",
    "dialogue_act",
    "dialogue_act_gloss",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def normalize_row(row: dict[str, Any], fallback_source: str) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "utterance": str(row["utterance"]),
        "axes": row["axes"],
        "style": str(row.get("style", "conversation")),
        "split": str(row.get("split", "train")),
        "notes": str(row.get("notes", "")),
        "source": str(row.get("source", fallback_source)),
    }
    for key in PROVENANCE_KEYS:
        if key in row:
            normalized[key] = row[key]
    return normalized


def combine(paths: Iterable[Path]) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates = 0
    for path in paths:
        for raw in load_jsonl(path):
            row = normalize_row(raw, "ai_generated")
            key = row["utterance"].strip().lower()
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            rows.append(row)
    return rows, duplicates


def write_jsonl(rows: Iterable[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--labels", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows, duplicates = combine([args.base, *args.labels])
    write_jsonl(rows, args.output)
    print(f"rows={len(rows)}")
    print(f"deduplicated_rows={duplicates}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
