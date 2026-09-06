# -*- coding: utf-8 -*-
"""Extract learner utterances from the NICT JLE Corpus.

The output JSONL preserves the source file as a learner-level provenance group:
  {"utterance": "...", "source": "nict_jle_real", "axes": null,
   "source_record_id": "...", "source_group": "...", "source_file": "..."}
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any, Iterable


SOURCE_NAME = "nict_jle_real"
MAX_FRAGMENT_WORDS = 7
MAX_FILLER_RATIO = 0.4
MIN_UTTERANCE_WORDS = 2

CONTINUATION_STARTERS = {
    "and",
    "but",
    "or",
    "so",
    "because",
    "cause",
    "if",
    "when",
    "while",
    "although",
    "though",
    "then",
    "than",
    "to",
    "for",
    "of",
    "in",
    "on",
    "at",
    "by",
    "with",
    "from",
    "about",
    "as",
    "like",
    "into",
    "after",
    "before",
    "until",
    "through",
    "over",
    "under",
}

FILLER_TOKEN_PATTERN = r"(?:u+h+m*|u+m+|u+r+m*|u{2,}m*|u+n+to+|e+to+|m+to+|e+r+m*|e+h+|e+m+|e{2,}|a+h+|m+h*m+|m+)"
FILLER_TOKEN_RE = re.compile(rf"^{FILLER_TOKEN_PATTERN}$", re.IGNORECASE)
FILLER_RUN_RE = re.compile(
    rf"\b({FILLER_TOKEN_PATTERN})\b(?:[\s,.;:!?-]+\b{FILLER_TOKEN_PATTERN}\b){{2,}}",
    re.IGNORECASE,
)

TURN_RE = re.compile(r"<([AB])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"</?[^>]+>")
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)")


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932", "shift_jis", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def learner_turns(raw_text: str) -> list[str]:
    return [content for speaker, content in interview_turns(raw_text) if speaker == "B"]


def interview_turns(raw_text: str) -> list[tuple[str, str]]:
    return [(match.group(1).upper(), match.group(2)) for match in TURN_RE.finditer(raw_text)]


def clean_turn(turn: str) -> str:
    text = html.unescape(turn)
    text = re.sub(r"<(?:\.|\.\.)\s*>\s*</(?:\.|\.\.)\s*>", ". ", text)
    text = re.sub(r"<(?:laughter|nvs|CO)\b[^>]*>.*?</(?:laughter|nvs|CO)>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return collapse_filler_runs(text)


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def split_sentences(text: str) -> list[str]:
    candidates = [match.group(0).strip(" .!?") for match in SENTENCE_RE.finditer(text)]
    return [candidate for candidate in candidates if candidate]


def is_continuation_fragment(text: str) -> bool:
    tokens = [token.lower() for token in words(text)]
    if not tokens or len(tokens) > MAX_FRAGMENT_WORDS:
        return False
    return tokens[0] in CONTINUATION_STARTERS


def merge_continuation_fragments(sentences: Iterable[str]) -> list[str]:
    merged: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if merged and is_continuation_fragment(sentence):
            merged[-1] = f"{merged[-1]} {sentence}".strip()
        else:
            merged.append(sentence)
    return merged


def collapse_filler_runs(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        first = re.search(FILLER_TOKEN_PATTERN, match.group(0), re.IGNORECASE)
        return first.group(0) if first else match.group(0)

    collapsed = FILLER_RUN_RE.sub(replace, text)
    collapsed = re.sub(rf"\b({FILLER_TOKEN_PATTERN}),\s+", r"\1 ", collapsed, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", collapsed).strip()


def filler_ratio(text: str) -> float:
    tokens = words(text)
    if not tokens:
        return 0.0
    filler_count = sum(1 for token in tokens if FILLER_TOKEN_RE.fullmatch(token))
    return filler_count / len(tokens)


def keep_utterance(text: str) -> bool:
    tokens = words(text)
    if len(tokens) < MIN_UTTERANCE_WORDS:
        return False
    if filler_ratio(text) > MAX_FILLER_RATIO:
        return False
    return True


def extract_utterances_from_file(path: Path) -> list[str]:
    return [record["utterance"] for record in extract_records_from_file(path)]


def extract_records_from_file(path: Path) -> list[dict[str, Any]]:
    """Extract usable sentences while retaining the learner interview file."""
    records: list[dict[str, Any]] = []
    cleaned_turns = [(speaker, clean_turn(turn)) for speaker, turn in interview_turns(read_text(path))]
    learner_turn_index = 0
    for conversation_turn_index, (speaker, cleaned) in enumerate(cleaned_turns):
        if speaker != "B":
            continue
        learner_turn_index += 1
        previous = cleaned_turns[conversation_turn_index - 1] if conversation_turn_index else None
        following = cleaned_turns[conversation_turn_index + 1] if conversation_turn_index + 1 < len(cleaned_turns) else None
        sentences = merge_continuation_fragments(split_sentences(cleaned))
        for sentence_index, utterance in enumerate(sentences, start=1):
            if not keep_utterance(utterance):
                continue
            records.append(
                {
                    "utterance": utterance,
                    "source": SOURCE_NAME,
                    "axes": None,
                    "source_record_id": f"{path.stem}:{learner_turn_index}:{sentence_index}",
                    "source_group": path.stem,
                    "source_file": path.name,
                    "conversation_id": path.stem,
                    "speaker": "B",
                    "speaker_id": path.stem,
                    "turn_index": conversation_turn_index,
                    "previous_turn": previous[1] if previous else None,
                    "previous_turn_speaker": previous[0] if previous else None,
                    "next_turn": following[1] if following else None,
                    "next_turn_speaker": following[0] if following else None,
                }
            )
    return records


def extract_utterances_from_file_legacy(path: Path) -> list[str]:
    """Compatibility helper for callers that only need cleaned text."""
    utterances: list[str] = []
    for turn in learner_turns(read_text(path)):
        cleaned = clean_turn(turn)
        utterances.extend(merge_continuation_fragments(split_sentences(cleaned)))
    return [utterance for utterance in utterances if keep_utterance(utterance)]


def iter_input_files(input_dir: Path, limit: int | None = None) -> list[Path]:
    files = sorted(path for path in input_dir.rglob("*.txt") if path.is_file())
    if limit is not None:
        return files[:limit]
    return files


def write_jsonl(records: Iterable[dict[str, Any]], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def extract_corpus(input_dir: Path, output_path: Path, limit: int | None = None) -> tuple[int, int]:
    files = iter_input_files(input_dir, limit)
    all_records: list[dict[str, Any]] = []
    for path in files:
        all_records.extend(extract_records_from_file(path))
    return len(files), write_jsonl(all_records, output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="Path to the NICT JLE LearnerOriginal directory.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/fixtures/nict_jle_learner_utterances.jsonl"),
        help="Output JSONL path.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional file limit for smoke tests.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    file_count, utterance_count = extract_corpus(args.input_dir, args.output, args.limit)
    print(f"files={file_count}")
    print(f"utterances={utterance_count}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
