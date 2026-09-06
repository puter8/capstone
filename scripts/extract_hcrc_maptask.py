# -*- coding: utf-8 -*-
"""Extract human dialogue turns from HCRC Map Task timed-unit annotations.

HCRC stores timed words separately from dialogue-move labels. Turn boundaries
come from the original ``utt`` attribute; move labels are joined back as useful
provenance, never used to fabricate text.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.conversation_context import add_adjacent_turn_context
except ModuleNotFoundError:
    from conversation_context import add_adjacent_turn_context


SOURCE_NAME = "hcrc_maptask_real"
DEFAULT_INPUT = Path("data/external_raw/hcrc_maptask/maptaskv2-1/Data")
DEFAULT_OUTPUT = Path("data/fixtures/hcrc_maptask_utterances.jsonl")
HREF_RANGE_RE = re.compile(r"#id\(([^)]+)\)(?:\.\.id\(([^)]+)\))?")
PARTIAL_WORD_RE = re.compile(r"\b[A-Za-z]+--(?=\s|$)")
WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Remove truncated-token notation while keeping the completed words."""
    text = PARTIAL_WORD_RE.sub(" ", text)
    text = text.replace('"', "")
    return WHITESPACE_RE.sub(" ", text).strip(" -,.!?:;")


def parse_move_labels(move_path: Path, unit_ids: list[str]) -> dict[str, str]:
    if not move_path.exists():
        return {}
    ordered_index = {unit_id: index for index, unit_id in enumerate(unit_ids)}
    root = ET.parse(move_path).getroot()
    labels: dict[str, str] = {}
    for move in root.findall("move"):
        label = move.get("label")
        if not label:
            continue
        for child in move:
            href = child.get("href", "")
            match = HREF_RANGE_RE.search(href)
            if not match:
                continue
            start_id, end_id = match.groups()
            if start_id not in ordered_index:
                continue
            start = ordered_index[start_id]
            end = ordered_index.get(end_id, start) if end_id else start
            if end < start:
                start, end = end, start
            for unit_id in unit_ids[start : end + 1]:
                labels.setdefault(unit_id, label)
    return labels


def extract_file(timed_path: Path, moves_dir: Path) -> list[dict[str, Any]]:
    root = ET.parse(timed_path).getroot()
    units: list[dict[str, str]] = []
    for element in root.findall("tu"):
        utterance_id = element.get("utt")
        text = (element.text or "").strip()
        if utterance_id and text:
            units.append(
                {
                    "id": element.get("id", ""),
                    "utt": utterance_id,
                    "text": text,
                    "start": element.get("start", ""),
                    "end": element.get("end", ""),
                }
            )

    labels = parse_move_labels(moves_dir / timed_path.name.replace(".timed-units.xml", ".moves.xml"), [unit["id"] for unit in units])
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for unit in units:
        grouped[unit["utt"]].append(unit)

    dialogue_id, role, *_ = timed_path.stem.split(".")
    rows: list[dict[str, Any]] = []
    for utterance_id, utterance_units in grouped.items():
        text = clean_text(" ".join(unit["text"] for unit in utterance_units))
        if not text:
            continue
        move_labels = [labels[unit["id"]] for unit in utterance_units if unit["id"] in labels]
        move_label = Counter(move_labels).most_common(1)[0][0] if move_labels else None
        rows.append(
            {
                "utterance": text,
                "source": SOURCE_NAME,
                "axes": None,
                "source_record_id": f"{dialogue_id}:{role}:{utterance_id}",
                "source_group": dialogue_id,
                "dialogue_id": dialogue_id,
                "speaker": role,
                "participant_role": role,
                "utterance_id": utterance_id,
                "move_label": move_label,
                "start_time": utterance_units[0]["start"],
                "end_time": utterance_units[-1]["end"],
            }
        )
    return rows


def extract_corpus(input_dir: Path) -> tuple[int, list[dict[str, Any]]]:
    timed_dir = input_dir / "timed-units"
    moves_dir = input_dir / "moves"
    files = sorted(timed_dir.glob("*.timed-units.xml"))
    rows: list[dict[str, Any]] = []
    for path in files:
        rows.extend(extract_file(path, moves_dir))
    return len(files), add_adjacent_turn_context(rows, "dialogue_id", "start_time")


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
    roles = Counter(str(row["participant_role"]) for row in rows)
    print(f"files={file_count}")
    print(f"utterances={count}")
    print("roles=" + ", ".join(f"{role}:{roles[role]}" for role in sorted(roles)))
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
