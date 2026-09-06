# -*- coding: utf-8 -*-
"""Sample useful NICT JLE utterances for 5-axis human labeling."""

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

from scripts.extract_nict_jle import FILLER_TOKEN_RE, filler_ratio, is_continuation_fragment, words


DEFAULT_INPUT = Path("data/fixtures/nict_jle_learner_utterances.jsonl")
DEFAULT_OUTPUT = Path("data/fixtures/nict_jle_label_candidates_600.jsonl")
DEFAULT_SIZE = 600
DEFAULT_SEED = 42
MIN_WORDS = 3
MAX_WORDS = 35
MAX_CANDIDATE_FILLER_RATIO = 0.3

LOW_INFORMATION_PHRASES = {
    "o k",
    "ok",
    "okay",
    "yes",
    "yeah",
    "no",
    "nope",
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
    "i don't know",
    "i dont know",
}

QUESTION_STARTERS = {
    "what",
    "where",
    "when",
    "why",
    "who",
    "how",
    "can",
    "could",
    "do",
    "does",
    "did",
    "is",
    "are",
    "am",
    "would",
    "should",
    "may",
}
WH_QUESTION_STARTERS = {"what", "where", "why", "who", "how"}
AUX_QUESTION_STARTERS = {"can", "could", "do", "does", "did", "is", "are", "am", "would", "should", "may"}
QUESTION_SECOND_TOKENS = {
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "there",
    "this",
    "that",
    "the",
}

POLITE_MARKERS = {"please", "could", "would", "may"}
PERSONAL_MARKERS = {"i", "i'm", "ive", "i've", "my", "me", "we", "our"}
DESCRIPTION_MARKERS = {
    "there",
    "he",
    "she",
    "they",
    "this",
    "that",
    "picture",
    "man",
    "woman",
    "boy",
    "girl",
    "people",
    "person",
    "dog",
    "cat",
}
INCOMPLETE_ENDINGS = {
    "a",
    "an",
    "the",
    "to",
    "for",
    "of",
    "in",
    "on",
    "at",
    "by",
    "with",
    "and",
    "but",
    "or",
    "so",
    "because",
    "if",
    "when",
}
BUCKET_ORDER = [
    "question",
    "polite_request",
    "short_reaction",
    "repair_disfluency",
    "personal_statement",
    "narrative_description",
]
DEFAULT_QUOTAS = {
    "question": 100,
    "polite_request": 80,
    "short_reaction": 80,
    "repair_disfluency": 120,
    "personal_statement": 120,
    "narrative_description": 100,
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            row["_source_line"] = line_number
            rows.append(row)
    return rows


def normalize_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z' ]+", " ", text.lower())).strip()


def has_adjacent_repeat(tokens: list[str]) -> bool:
    return any(left == right for left, right in zip(tokens, tokens[1:]))


def repeated_token_ratio(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return repeated / len(tokens)


def is_low_information(text: str) -> bool:
    normalized = normalize_phrase(text)
    if normalized in LOW_INFORMATION_PHRASES:
        return True
    token_list = [token.lower() for token in words(text)]
    content_tokens = [token for token in token_list if not FILLER_TOKEN_RE.fullmatch(token)]
    if len(content_tokens) < MIN_WORDS:
        return True
    if len(set(content_tokens)) == 1 and len(content_tokens) <= 4:
        return True
    return False


def is_candidate(text: str) -> bool:
    token_list = [token.lower() for token in words(text)]
    core_tokens = strip_discourse_starters(token_list)
    if len(token_list) < MIN_WORDS or len(token_list) > MAX_WORDS:
        return False
    if token_list[-1] in INCOMPLETE_ENDINGS or FILLER_TOKEN_RE.fullmatch(token_list[-1]):
        return False
    if is_continuation_fragment(text) and not is_question_like(text, core_tokens):
        return False
    if "xxx" in text.lower():
        return False
    if filler_ratio(text) > MAX_CANDIDATE_FILLER_RATIO:
        return False
    if repeated_token_ratio(token_list) > 0.45:
        return False
    if is_low_information(text):
        return False
    return True


def classify_bucket(text: str) -> str:
    token_list = [token.lower() for token in words(text)]
    token_set = set(token_list)
    core_tokens = strip_discourse_starters(token_list)
    if is_question_like(text, core_tokens):
        return "question"
    if is_polite_request(core_tokens, token_set):
        return "polite_request"
    if len(token_list) <= 5:
        return "short_reaction"
    if has_adjacent_repeat(token_list):
        return "repair_disfluency"
    if token_set & PERSONAL_MARKERS:
        return "personal_statement"
    if token_set & DESCRIPTION_MARKERS or len(token_list) >= 12:
        return "narrative_description"
    return "personal_statement"


def strip_discourse_starters(tokens: list[str]) -> list[str]:
    while tokens and tokens[0] in {"and", "but", "so", "oh", "well", "um", "uh", "er", "err", "erm"}:
        tokens = tokens[1:]
    return tokens


def is_question_like(text: str, tokens: list[str]) -> bool:
    if "?" in text:
        return True
    if not tokens:
        return False
    if tokens[0] in WH_QUESTION_STARTERS:
        return len(tokens) <= 12 and (len(tokens) == 1 or tokens[1] in AUX_QUESTION_STARTERS | {"about", "kind"})
    if tokens[0] in AUX_QUESTION_STARTERS:
        return len(tokens) >= 2 and tokens[1] in QUESTION_SECOND_TOKENS
    return False


def is_polite_request(tokens: list[str], token_set: set[str]) -> bool:
    if "please" in token_set:
        return True
    return bool(len(tokens) >= 2 and tokens[0] in {"could", "would", "may"} and tokens[1] in {"you", "i"})


def sample_candidates(rows: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        text = str(row["utterance"]).strip()
        if not is_candidate(text):
            continue
        bucket = classify_bucket(text)
        enriched = {
            "utterance": text,
            "source": row.get("source", "nict_jle_real"),
            "axes": None,
            "sample_bucket": bucket,
            "word_count": len(words(text)),
            "filler_ratio": round(filler_ratio(text), 3),
            "source_line": row["_source_line"],
        }
        buckets[bucket].append(enriched)

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    quotas = scale_quotas(size)
    for bucket in BUCKET_ORDER:
        bucket_rows = buckets[bucket]
        rng.shuffle(bucket_rows)
        for row in bucket_rows[: quotas[bucket]]:
            key = normalize_phrase(row["utterance"])
            if key not in seen:
                selected.append(row)
                seen.add(key)

    if len(selected) < size:
        remainder = [
            row
            for bucket in BUCKET_ORDER
            for row in buckets[bucket]
            if normalize_phrase(row["utterance"]) not in seen
        ]
        rng.shuffle(remainder)
        for row in remainder:
            if len(selected) >= size:
                break
            selected.append(row)
            seen.add(normalize_phrase(row["utterance"]))

    return selected[:size]


def scale_quotas(size: int) -> dict[str, int]:
    total = sum(DEFAULT_QUOTAS.values())
    quotas = {bucket: round(quota * size / total) for bucket, quota in DEFAULT_QUOTAS.items()}
    diff = size - sum(quotas.values())
    index = 0
    while diff != 0:
        bucket = BUCKET_ORDER[index % len(BUCKET_ORDER)]
        if diff > 0:
            quotas[bucket] += 1
            diff -= 1
        elif quotas[bucket] > 0:
            quotas[bucket] -= 1
            diff += 1
        index += 1
    return quotas


def write_jsonl(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def print_summary(rows: list[dict[str, Any]]) -> None:
    bucket_counts = Counter(row["sample_bucket"] for row in rows)
    print(f"candidates={len(rows)}")
    for bucket in BUCKET_ORDER:
        print(f"{bucket}={bucket_counts[bucket]}")
    if rows:
        avg_words = sum(row["word_count"] for row in rows) / len(rows)
        print(f"avg_words={avg_words:.2f}")
        print(f"max_filler_ratio={max(row['filler_ratio'] for row in rows):.3f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = sample_candidates(load_jsonl(args.input), args.size, args.seed)
    write_jsonl(rows, args.output)
    print_summary(rows)
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
