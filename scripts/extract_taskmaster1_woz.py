# -*- coding: utf-8 -*-
"""Extract transcribed spoken USER turns from Taskmaster-1 Wizard-of-Oz data."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


SOURCE_NAME = "taskmaster1_woz_user_real"
DEFAULT_INPUT = Path("data/external_raw/taskmaster_woz-dialogs.json")
DEFAULT_OUTPUT = Path("data/fixtures/taskmaster1_woz_user_utterances.jsonl")
WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def extract_dialogues(dialogues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dialogue in dialogues:
        conversation_id = str(dialogue.get("conversation_id", "unknown"))
        instruction_id = str(dialogue.get("instruction_id", "unknown"))
        turns = dialogue.get("utterances", [])
        for position, utterance in enumerate(turns):
            if utterance.get("speaker") != "USER":
                continue
            text = clean_text(str(utterance.get("text", "")))
            if not text:
                continue
            index = int(utterance.get("index", -1))
            previous = turns[position - 1] if position else None
            following = turns[position + 1] if position + 1 < len(turns) else None
            rows.append(
                {
                    "utterance": text,
                    "source": SOURCE_NAME,
                    "axes": None,
                    "source_record_id": f"{conversation_id}:{index}",
                    "source_group": conversation_id,
                    "conversation_id": conversation_id,
                    "instruction_id": instruction_id,
                    "dialogue_turn_index": index,
                    "turn_index": index,
                    "speaker": "USER",
                    "previous_turn": clean_text(str(previous.get("text", ""))) if previous else None,
                    "previous_turn_speaker": str(previous.get("speaker", "")) if previous else None,
                    "next_turn": clean_text(str(following.get("text", ""))) if following else None,
                    "next_turn_speaker": str(following.get("speaker", "")) if following else None,
                }
            )
    return rows


def load_dialogues(input_path: Path) -> list[dict[str, Any]]:
    with input_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"expected a JSON list in {input_path}")
    return payload


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
    dialogues = load_dialogues(args.input)
    rows = extract_dialogues(dialogues)
    count = write_jsonl(rows, args.output)
    domains = Counter(str(row["instruction_id"]).split("-")[0] for row in rows)
    print(f"dialogues={len(dialogues)}")
    print(f"user_utterances={count}")
    print("domains=" + ", ".join(f"{name}:{domains[name]}" for name in sorted(domains)))
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
