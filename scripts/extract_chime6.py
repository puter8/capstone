# -*- coding: utf-8 -*-
"""Extract participant turns from the CHiME-6 transcript JSON files.

The aligned CHiME-6 transcript rows are already speaker turns, so this script
only removes bracketed non-speech annotations and preserves the timing and
speaker provenance needed to trace every cleaned utterance back to the source.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.conversation_context import add_adjacent_turn_context
except ModuleNotFoundError:
    from conversation_context import add_adjacent_turn_context


SOURCE_NAME = "chime6_real"
DEFAULT_INPUT = Path("data/external_raw/chime6_transcriptions/transcriptions/transcriptions")
DEFAULT_OUTPUT = Path("data/fixtures/chime6_utterances.jsonl")
BRACKETED_EVENT_RE = re.compile(r"\[[^\]]+\]")
PARTIAL_TOKEN_RE = re.compile(r"\b[A-Za-z]+-+(?=\s|$)")
WHITESPACE_RE = re.compile(r"\s+")


def clean_words(text: str) -> tuple[str, list[str]]:
    """Remove transcript event markers while retaining them as provenance."""
    events = [match.group(0).strip("[]").lower() for match in BRACKETED_EVENT_RE.finditer(text)]
    cleaned = BRACKETED_EVENT_RE.sub(" ", text)
    cleaned = PARTIAL_TOKEN_RE.sub(" ", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip(" -,:;")
    return cleaned, events


def iter_transcript_files(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.rglob("*.json") if path.is_file())


def extract_file(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        raw_rows = json.load(handle)

    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows):
        text, events = clean_words(str(raw.get("words", "")))
        if not text:
            continue
        session_id = str(raw.get("session_id", path.stem))
        speaker = str(raw.get("speaker", "unknown"))
        start_time = str(raw.get("start_time", ""))
        rows.append(
            {
                "utterance": text,
                "source": SOURCE_NAME,
                "axes": None,
                "source_record_id": f"{session_id}:{speaker}:{start_time}:{index}",
                "source_group": speaker,
                "raw_split": path.parent.name,
                "session_id": session_id,
                "speaker": speaker,
                "location": raw.get("location"),
                "start_time": start_time,
                "end_time": str(raw.get("end_time", "")),
                "reference": raw.get("ref"),
                "annotation_events": events,
            }
        )
    return rows


def extract_corpus(input_dir: Path) -> tuple[int, list[dict[str, Any]]]:
    files = iter_transcript_files(input_dir)
    rows: list[dict[str, Any]] = []
    for path in files:
        rows.extend(extract_file(path))
    return len(files), add_adjacent_turn_context(rows, "session_id", "start_time")


def write_jsonl(rows: Iterable[dict[str, Any]], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    file_count, rows = extract_corpus(args.input)
    count = write_jsonl(rows, args.output)
    splits = Counter(str(row["raw_split"]) for row in rows)
    print(f"files={file_count}")
    print(f"utterances={count}")
    print("splits=" + ", ".join(f"{split}:{splits[split]}" for split in sorted(splits)))
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
