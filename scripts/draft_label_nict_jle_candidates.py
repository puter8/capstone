# -*- coding: utf-8 -*-
"""Create draft 5-axis labels for sampled real-speech utterances.

These labels are intended for human review before becoming evaluation or
training gold data. The rubric here is separate from the active analyzer so
the draft file does not simply copy the model we want to evaluate later.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.contracts import AXIS_KEYS
from scripts.extract_nict_jle import FILLER_TOKEN_RE, filler_ratio, words


DEFAULT_INPUT = Path("data/fixtures/nict_jle_label_candidates_600.jsonl")
DEFAULT_OUTPUT = Path("data/fixtures/nict_jle_labeled_draft_600.jsonl")
DRAFT_LABELER = "codex_rubric_draft_v2"

STYLE_BY_BUCKET = {
    "question": "learner_question",
    "polite_request": "learner_request",
    "short_reaction": "short_reaction",
    "repair_disfluency": "mistake_or_hesitation",
    "personal_statement": "personal_statement",
    "narrative_description": "narrative_description",
}

PROVENANCE_KEYS = (
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

DISCOURSE_STARTERS = {"and", "but", "so", "oh", "well", "then"}
POLITE_WORDS = {"please", "sorry", "excuse", "thank", "thanks", "could", "would", "may"}
INTIMATE_WORDS = {"friend", "family", "father", "mother", "brother", "sister", "husband", "wife", "home"}
HIGH_ENERGY_WORDS = {"very", "really", "definitely", "love", "like", "desperate", "angry", "sad", "happy"}
MILD_PLAY_WORDS = {"happy", "enjoy", "interesting", "party", "movie"}
HUMOR_WORDS = {"funny", "laugh", "laughing", "joke", "joking", "hilarious"}
QUESTION_WORDS = {"what", "where", "when", "why", "who", "how", "can", "could", "do", "does", "did", "is", "are", "should", "would"}


def clamp(value: int) -> int:
    return max(0, min(100, value))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def token_set(text: str) -> set[str]:
    return {token.lower() for token in words(text)}


def starts_with_question(text: str) -> bool:
    tokens = [token.lower() for token in words(text)]
    while tokens and tokens[0] in DISCOURSE_STARTERS:
        tokens.pop(0)
    return bool(tokens and tokens[0] in QUESTION_WORDS)


def has_repair(text: str) -> bool:
    tokens = [token.lower() for token in words(text)]
    adjacent_repeat = any(left == right for left, right in zip(tokens, tokens[1:]))
    # The source tokeniser drops hyphens, so a one-letter non-word is the only
    # reliable remaining sign of a cut-off token. Normal words such as "is"
    # and "to" must not turn an otherwise fluent sentence into a repair.
    partial_word = any(len(token) == 1 and token not in {"i", "a"} and not FILLER_TOKEN_RE.fullmatch(token) for token in tokens)
    return adjacent_repeat or partial_word or filler_ratio(text) >= 0.12


def sentence_is_direct_request(text: str) -> bool:
    lowered = text.lower()
    tokens = [token.lower() for token in words(text)]
    return "please" in tokens or lowered.startswith(("could you", "would you", "can you", "may i", "can i"))


def draft_axes(row: dict[str, Any]) -> dict[str, int]:
    text = str(row["utterance"])
    bucket = str(row.get("sample_bucket", "personal_statement"))
    tokens = [token.lower() for token in words(text)]
    tset = set(tokens)
    wc = len(tokens)
    repair = has_repair(text)
    direct_question = "?" in text or starts_with_question(text)
    direct_request = sentence_is_direct_request(text)

    formality = 38
    energy = 28
    intimacy = 24
    humor = 6
    curiosity = 18

    if bucket == "question":
        curiosity += 48
        formality += 5
    elif bucket == "polite_request":
        formality += 24
        curiosity += 30
        intimacy += 6
    elif bucket == "short_reaction":
        formality -= 4
        energy -= 3
        humor += 2
    elif bucket == "repair_disfluency":
        formality -= 8
        energy += 4
        intimacy += 6
        humor += 3
    elif bucket == "personal_statement":
        intimacy += 15
    elif bucket == "narrative_description":
        formality += 4
        energy += 2

    if direct_question:
        curiosity += 18
    if direct_request:
        formality += 10
        curiosity += 8
    if tset & POLITE_WORDS:
        formality += 10
        intimacy += 2
    if tset & INTIMATE_WORDS:
        intimacy += 10
    if tset & HIGH_ENERGY_WORDS:
        energy += 8
    if tset & MILD_PLAY_WORDS:
        humor += 4
    if tset & HUMOR_WORDS:
        humor += 45
        energy += 10
    if repair:
        formality -= 7
        energy += 3
    if wc <= 5:
        energy -= 4
        intimacy -= 2
    if wc >= 18:
        formality += 6
        energy += 4
    if re.search(r"\b(i|i'm|my|me|we|our)\b", text, re.IGNORECASE):
        intimacy += 8
    if re.search(r"\b(very|really|so)\b", text, re.IGNORECASE):
        energy += 4
    if text.count(",") >= 2:
        formality -= 3
        energy += 2

    return {
        "Formality": clamp(round(formality)),
        "Energy": clamp(round(energy)),
        "Intimacy": clamp(round(intimacy)),
        "Humor": clamp(round(humor)),
        "Curiosity": clamp(round(curiosity)),
    }


def make_notes(row: dict[str, Any], axes: dict[str, int]) -> str:
    signals: list[str] = [str(row.get("sample_bucket", "unknown"))]
    if axes["Curiosity"] >= 65:
        signals.append("question/request signal")
    if axes["Formality"] >= 60:
        signals.append("polite spoken form")
    if axes["Intimacy"] >= 40:
        signals.append("personal or direct-address speech")
    if has_repair(str(row["utterance"])):
        signals.append("learner disfluency/repair")
    if axes["Humor"] >= 40:
        signals.append("humor marker")
    return "draft label for human review: " + ", ".join(signals)


def label_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labeled: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        axes = draft_axes(row)
        item = {
            "utterance": row["utterance"],
            "axes": axes,
            "style": STYLE_BY_BUCKET.get(str(row.get("sample_bucket")), "conversation"),
            "split": split_for_index(index),
            "notes": make_notes(row, axes),
            "source": row.get("source", "nict_jle_real"),
            "label_status": "ai_draft_needs_human_review",
            "labeler": DRAFT_LABELER,
            "sample_bucket": row.get("sample_bucket"),
        }
        for key in PROVENANCE_KEYS:
            if key in row:
                item[key] = row[key]
        labeled.append(item)
    return labeled


def split_for_index(index: int) -> str:
    remainder = index % 10
    if remainder < 8:
        return "train"
    if remainder == 8:
        return "dev"
    return "test"


def validate_rows(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows, start=1):
        axes = row.get("axes")
        if set(axes) != set(AXIS_KEYS):
            raise ValueError(f"row {index} has invalid axes keys")
        for axis in AXIS_KEYS:
            value = axes[axis]
            if not isinstance(value, int) or not 0 <= value <= 100:
                raise ValueError(f"row {index} has invalid {axis}: {value!r}")


def write_jsonl(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def print_summary(rows: list[dict[str, Any]]) -> None:
    print(f"labeled={len(rows)}")
    for axis in AXIS_KEYS:
        values = [row["axes"][axis] for row in rows]
        print(f"{axis}_min={min(values)} max={max(values)} avg={sum(values) / len(values):.1f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = label_rows(load_jsonl(args.input))
    validate_rows(rows)
    write_jsonl(rows, args.output)
    print_summary(rows)
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
