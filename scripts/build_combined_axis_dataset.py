# -*- coding: utf-8 -*-
"""Combine existing Pally labels with reviewed or draft NICT JLE labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_BASE = Path("data/axis_dataset_week2.jsonl")
DEFAULT_NICT = Path("data/fixtures/nict_jle_labeled_draft_600.jsonl")
DEFAULT_OUTPUT = Path("data/fixtures/axis_dataset_combined_nict_draft.jsonl")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def normalize_row(row: dict[str, Any], fallback_source: str) -> dict[str, Any]:
    return {
        "utterance": row["utterance"],
        "axes": row["axes"],
        "style": row.get("style", "conversation"),
        "split": row.get("split", "train"),
        "notes": row.get("notes", ""),
        "source": row.get("source", fallback_source),
        **({"label_status": row["label_status"]} if "label_status" in row else {}),
        **({"sample_bucket": row["sample_bucket"]} if "sample_bucket" in row else {}),
        **({"source_line": row["source_line"]} if "source_line" in row else {}),
    }


def combine(base_path: Path, nict_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path, fallback_source in ((base_path, "ai_generated"), (nict_path, "nict_jle_real")):
        for raw in load_jsonl(path):
            row = normalize_row(raw, fallback_source)
            key = row["utterance"].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    return rows


def write_jsonl(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--nict", type=Path, default=DEFAULT_NICT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = combine(args.base, args.nict)
    write_jsonl(rows, args.output)
    print(f"rows={len(rows)}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
