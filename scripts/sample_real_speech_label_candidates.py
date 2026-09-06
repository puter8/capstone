# -*- coding: utf-8 -*-
"""Select balanced, information-rich real-speech utterances for 5-axis labels.

This sampler is for corpora whose records are already speaker turns. Unlike the
NICT sentence sampler, it never rejects a short turn merely because it starts
with a conjunction or preposition: in conversational corpora, "Because I was
tired" can be a complete, meaningful answer.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.extract_nict_jle import FILLER_TOKEN_RE, filler_ratio, words


DEFAULT_SEED = 42
MIN_WORDS = 3
MAX_WORDS = 45
MAX_FILLER_RATIO = 0.30
MAX_PER_SOURCE_GROUP = 45

LOW_INFORMATION_PHRASES = {
    "o k",
    "ok",
    "okay",
    "yes",
    "yeah",
    "yep",
    "no",
    "nope",
    "right",
    "sure",
    "please",
    "yes please",
    "no problem",
    "thank you",
    "thanks",
    "thank you very much",
    "only once",
    "once",
    "twice",
    "i see",
    "i dont know",
    "i don't know",
    "all right",
}
DISCOURSE_STARTERS = {"and", "but", "so", "oh", "well", "then", "um", "uh", "er", "erm"}
QUESTION_WORDS = {"what", "where", "when", "why", "who", "how", "can", "could", "do", "does", "did", "is", "are", "am", "would", "should", "may", "will"}
QUESTION_SUBJECTS = {"i", "you", "he", "she", "it", "we", "they", "this", "that", "these", "those", "there", "anyone", "anybody", "someone", "somebody", "everybody"}
POLITE_MARKERS = {"please", "could", "would", "may", "sorry", "excuse"}
PERSONAL_MARKERS = {"i", "i'm", "ive", "i've", "my", "me", "we", "our", "us"}
INCOMPLETE_ENDINGS = {"a", "an", "the", "to", "for", "of", "in", "on", "at", "by", "with", "and", "but", "or", "so", "because", "if", "when", "like"}
BUCKET_ORDER = ["question", "polite_request", "short_reaction", "repair_disfluency", "personal_statement", "narrative_description"]
DEFAULT_QUOTAS = {
    "question": 100,
    "polite_request": 80,
    "short_reaction": 80,
    "repair_disfluency": 120,
    "personal_statement": 120,
    "narrative_description": 100,
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def normalize_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z' ]+", " ", text.lower())).strip()


def strip_discourse_starters(tokens: list[str]) -> list[str]:
    while tokens and tokens[0] in DISCOURSE_STARTERS:
        tokens = tokens[1:]
    return tokens


def is_question_like(text: str, tokens: list[str]) -> bool:
    if "?" in text:
        return True
    if not tokens:
        return False
    first = tokens[0]
    if first in {"can", "could", "do", "does", "did", "is", "are", "am", "would", "should", "may", "will"}:
        # Without a question mark, accept inversion only when the auxiliary is
        # followed by a plausible subject. This keeps statements such as
        # "Could be really light" and imperatives such as "Do your own" out.
        return len(tokens) >= 2 and tokens[1] in QUESTION_SUBJECTS
    if first in {"what", "where", "why", "who"}:
        return len(tokens) >= 2 and tokens[1] in {"is", "are", "do", "does", "did", "can", "could", "would", "should", "about", "kind", "time", "else"}
    if first == "how":
        return len(tokens) >= 2 and tokens[1] in {"is", "are", "do", "does", "did", "can", "could", "would", "should", "much", "many", "long", "far", "often"}
    if first == "when":
        return len(tokens) >= 2 and tokens[1] in {"is", "are", "do", "does", "did", "can", "could", "would", "should"}
    return False


def is_direct_request(tokens: list[str]) -> bool:
    if "please" in tokens:
        return True
    return len(tokens) >= 2 and tokens[0] in {"could", "would", "can", "may"} and tokens[1] in {"you", "i"}


def has_adjacent_repeat(tokens: list[str]) -> bool:
    return any(left == right for left, right in zip(tokens, tokens[1:]))


def repeated_token_ratio(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    return sum(count - 1 for count in counts.values() if count > 1) / len(tokens)


def has_speech_event(row: dict[str, Any]) -> bool:
    return bool(row.get("annotation_events"))


def is_low_information(tokens: list[str], text: str) -> bool:
    if normalize_phrase(text) in LOW_INFORMATION_PHRASES:
        return True
    content = [token for token in tokens if not FILLER_TOKEN_RE.fullmatch(token)]
    return len(content) < MIN_WORDS or (len(set(content)) == 1 and len(content) <= 4)


def candidate_rejection_reason(row: dict[str, Any]) -> str | None:
    text = str(row.get("utterance", "")).strip()
    tokens = [token.lower() for token in words(text)]
    if len(tokens) < MIN_WORDS:
        return "too_short"
    if len(tokens) > MAX_WORDS:
        return "too_long"
    if "xxx" in text.lower() or "[" in text or "]" in text:
        return "unresolved_annotation"
    if (tokens[-1] in INCOMPLETE_ENDINGS and not text.rstrip().endswith("?")) or FILLER_TOKEN_RE.fullmatch(tokens[-1]):
        return "incomplete_ending"
    if str(row.get("source", "")) == "chime6_real" and not re.search(r"[.!?]$", text):
        tail = text.rsplit(" ", maxsplit=1)[-1]
        if re.fullmatch(r"[A-Z][a-z]{0,2}", tail):
            return "truncated_tail"
    if filler_ratio(text) > MAX_FILLER_RATIO:
        return "filler_heavy"
    if repeated_token_ratio(tokens) > 0.45:
        return "repetition_heavy"
    if is_low_information(tokens, text):
        return "low_information"
    return None


def classify_bucket(row: dict[str, Any]) -> str:
    text = str(row["utterance"])
    tokens = [token.lower() for token in words(text)]
    core_tokens = strip_discourse_starters(tokens)
    if is_question_like(text, core_tokens) or str(row.get("move_label", "")) in {"check", "clarify", "query_w", "query_y"}:
        return "question"
    if is_direct_request(core_tokens):
        return "polite_request"
    if has_speech_event(row) or filler_ratio(text) >= 0.12 or has_adjacent_repeat(tokens):
        return "repair_disfluency"
    if len(tokens) <= 5:
        return "short_reaction"
    if set(tokens) & PERSONAL_MARKERS:
        return "personal_statement"
    return "narrative_description"


def scale_quotas(size: int) -> dict[str, int]:
    total = sum(DEFAULT_QUOTAS.values())
    quotas = {bucket: round(quota * size / total) for bucket, quota in DEFAULT_QUOTAS.items()}
    difference = size - sum(quotas.values())
    for index in range(abs(difference)):
        bucket = BUCKET_ORDER[index % len(BUCKET_ORDER)]
        quotas[bucket] += 1 if difference > 0 else -1
    return quotas


def _select(rows: list[dict[str, Any]], limit: int, seen: set[str], group_counts: Counter[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        if len(selected) >= limit:
            break
        key = normalize_phrase(str(row["utterance"]))
        group = str(row.get("source_group", row.get("source", "unknown")))
        if key in seen or group_counts[group] >= MAX_PER_SOURCE_GROUP:
            continue
        seen.add(key)
        group_counts[group] += 1
        selected.append(row)
    return selected


def sample_candidates(rows: list[dict[str, Any]], size: int, seed: int) -> tuple[list[dict[str, Any]], Counter[str]]:
    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rejections: Counter[str] = Counter()
    for row in rows:
        reason = candidate_rejection_reason(row)
        if reason:
            rejections[reason] += 1
            continue
        enriched = dict(row)
        enriched["utterance"] = str(row["utterance"]).strip()
        enriched["axes"] = None
        enriched["sample_bucket"] = classify_bucket(enriched)
        enriched["word_count"] = len(words(enriched["utterance"]))
        enriched["filler_ratio"] = round(filler_ratio(enriched["utterance"]), 3)
        buckets[enriched["sample_bucket"]].append(enriched)

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    group_counts: Counter[str] = Counter()
    for bucket in BUCKET_ORDER:
        rng.shuffle(buckets[bucket])
        selected.extend(_select(buckets[bucket], scale_quotas(size)[bucket], seen, group_counts))

    if len(selected) < size:
        remainder = [row for bucket in BUCKET_ORDER for row in buckets[bucket]]
        rng.shuffle(remainder)
        selected.extend(_select(remainder, size - len(selected), seen, group_counts))
    if len(selected) < size:
        raise ValueError(f"only {len(selected)} usable, diverse candidates available; requested {size}")
    return selected, rejections


def write_jsonl(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = load_jsonl(args.input)
    sampled, rejections = sample_candidates(rows, args.size, args.seed)
    write_jsonl(sampled, args.output)
    bucket_counts = Counter(row["sample_bucket"] for row in sampled)
    print(f"input_rows={len(rows)}")
    print(f"candidates={len(sampled)}")
    print("buckets=" + ", ".join(f"{bucket}:{bucket_counts[bucket]}" for bucket in BUCKET_ORDER))
    print("rejections=" + ", ".join(f"{reason}:{rejections[reason]}" for reason in sorted(rejections)))
    print(f"avg_words={sum(row['word_count'] for row in sampled) / len(sampled):.2f}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
