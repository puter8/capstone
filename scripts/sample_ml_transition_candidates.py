# -*- coding: utf-8 -*-
"""Create leakage-resistant Energy x Curiosity review sets for ML transition.

The outputs are raw real-speech candidates, not labels. Entire provenance
groups (a learner interview, meeting, or dialogue) are assigned to either the
blind gold-review set or the training-review set before sampling, so one group
cannot leak across the eventual final evaluation boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.extract_nict_jle import filler_ratio, is_continuation_fragment, words
from scripts.sample_real_speech_label_candidates import (
    candidate_rejection_reason,
    is_direct_request,
    is_question_like,
    normalize_phrase,
    strip_discourse_starters,
)


DEFAULT_INPUTS = (
    Path("data/fixtures/nict_jle_learner_utterances.jsonl"),
    Path("data/fixtures/ami_utterances.jsonl"),
    Path("data/fixtures/taskmaster1_woz_user_utterances.jsonl"),
)
DEFAULT_EXCLUDE = Path("data/fixtures/axis_dataset_combined_real_speech_experimental.jsonl")
DEFAULT_GOLD_OUTPUT = Path("data/fixtures/ml_transition_gold_candidates_600.jsonl")
DEFAULT_TRAIN_OUTPUT = Path("data/fixtures/ml_transition_train_candidates_1200.jsonl")
DEFAULT_GOLD_SIZE = 600
DEFAULT_TRAIN_SIZE = 1200
DEFAULT_SEED = 20260906
MAX_PER_TRANSITION_GROUP = 12
FOCUS_ORDER = (
    "high_energy_high_curiosity",
    "high_energy_low_curiosity",
    "low_energy_high_curiosity",
    "low_energy_low_curiosity",
)
FOCUS_WEIGHTS = {
    "high_energy_high_curiosity": 1,
    "high_energy_low_curiosity": 3,
    "low_energy_high_curiosity": 3,
    "low_energy_low_curiosity": 1,
}
STRONG_ENERGY_MARKERS = {
    "absolutely",
    "amazing",
    "angry",
    "awesome",
    "awful",
    "brilliant",
    "definitely",
    "desperate",
    "excited",
    "fantastic",
    "great",
    "hate",
    "horrible",
    "love",
    "ridiculous",
    "terrible",
    "wonderful",
}
INTENSIFIERS = {"absolutely", "really", "so", "totally", "very"}
EMOTION_WORDS = {"amazing", "angry", "awesome", "awful", "excited", "fantastic", "great", "hate", "horrible", "love", "terrible", "wonderful"}
CURIOSITY_NOUN_MARKERS = {"curious", "question", "wonder", "wondering"}
PARTIAL_FRAGMENT_TOKENS = {"b", "c", "ch", "d", "f", "h", "k", "ki", "m", "n", "s", "sh", "t", "th", "w", "wh"}
TRANSITION_INCOMPLETE_ENDINGS = {"about", "against", "around", "between", "during", "except", "without"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def group_key(row: dict[str, Any]) -> str:
    source = str(row.get("source", "unknown"))
    group = str(row.get("source_group") or row.get("source_record_id") or row.get("source_file") or row["utterance"])
    return f"{source}:{group}"


def review_partition(row: dict[str, Any]) -> str:
    """Assign every source group to gold or train with a stable 1:2 split."""
    digest = hashlib.sha256(group_key(row).encode("utf-8")).digest()
    return "gold" if int.from_bytes(digest[:4], "big") % 3 == 0 else "train"


def has_high_energy_signal(text: str, row: dict[str, Any]) -> bool:
    token_list = [token.lower() for token in words(text)]
    tokens = set(token_list)
    return (
        "!" in text
        or bool(tokens & STRONG_ENERGY_MARKERS)
        or any(
            left in INTENSIFIERS and right in EMOTION_WORDS
            for left, right in zip(token_list, token_list[1:])
        )
    )


def has_high_curiosity_signal(text: str) -> bool:
    tokens = [token.lower() for token in words(text)]
    core_tokens = strip_discourse_starters(tokens)
    lexical_request = bool(
        re.search(r"\b(?:can|could|would|will)\s+(?:you\s+)?(?:explain|clarify)\b", text, re.IGNORECASE)
        or re.match(r"^\s*(?:please\s+)?(?:explain|clarify)\b", text, re.IGNORECASE)
    )
    return (
        is_question_like(text, core_tokens)
        or is_direct_request(core_tokens)
        or lexical_request
        or bool(set(core_tokens) & CURIOSITY_NOUN_MARKERS)
    )


def focus_bucket(row: dict[str, Any]) -> str:
    energy = "high_energy" if has_high_energy_signal(str(row["utterance"]), row) else "low_energy"
    curiosity = "high_curiosity" if has_high_curiosity_signal(str(row["utterance"])) else "low_curiosity"
    return f"{energy}_{curiosity}"


def rejection_reason(row: dict[str, Any]) -> str | None:
    reason = candidate_rejection_reason(row)
    if reason:
        return reason
    text = str(row["utterance"])
    tokens = [token.lower() for token in words(text)]
    if len(tokens) < 4:
        return "too_short_transition"
    if str(row.get("dialogue_act", "")) in {"fra", "stl"}:
        return "minor_dialogue_act"
    if any(token in PARTIAL_FRAGMENT_TOKENS for token in tokens):
        return "partial_fragment"
    if tokens[-1] in TRANSITION_INCOMPLETE_ENDINGS:
        return "incomplete_ending_transition"
    if str(row.get("source")) == "nict_jle_real" and is_continuation_fragment(text) and not is_question_like(text, strip_discourse_starters(tokens)):
        return "nict_continuation_fragment"
    return None


def split_quota(size: int, labels: tuple[str, ...]) -> dict[str, int]:
    base, remainder = divmod(size, len(labels))
    return {label: base + (index < remainder) for index, label in enumerate(labels)}


def focus_quota(size: int) -> dict[str, int]:
    """Keep each axis marginally balanced while accepting a scarce cell."""
    if size < sum(FOCUS_WEIGHTS.values()):
        return split_quota(size, FOCUS_ORDER)
    total_weight = sum(FOCUS_WEIGHTS.values())
    floors = {focus: size * FOCUS_WEIGHTS[focus] // total_weight for focus in FOCUS_ORDER}
    remainder = size - sum(floors.values())
    fractions = sorted(
        FOCUS_ORDER,
        key=lambda focus: (size * FOCUS_WEIGHTS[focus] % total_weight, -FOCUS_ORDER.index(focus)),
        reverse=True,
    )
    for focus in fractions[:remainder]:
        floors[focus] += 1
    return floors


def build_quotas(
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]],
    partition: str,
    size: int,
    sources: tuple[str, ...],
) -> dict[tuple[str, str], int]:
    """Balance source totals and focus totals without forcing impossible cells."""
    source_remaining = split_quota(size, sources)
    focus_remaining = focus_quota(size)
    capacities = {
        (source, focus): len(buckets[(partition, source, focus)])
        for source in sources
        for focus in FOCUS_ORDER
    }
    quotas = {(source, focus): 0 for source in sources for focus in FOCUS_ORDER}

    while sum(focus_remaining.values()):
        available_by_focus = {
            focus: sum(
                capacities[(source, focus)] - quotas[(source, focus)]
                for source in sources
                if source_remaining[source] > 0
            )
            for focus in FOCUS_ORDER
            if focus_remaining[focus] > 0
        }
        focus = min(
            available_by_focus,
            key=lambda item: (available_by_focus[item] / focus_remaining[item], FOCUS_ORDER.index(item)),
        )
        candidates = [
            source
            for source in sources
            if source_remaining[source] > 0 and capacities[(source, focus)] > quotas[(source, focus)]
        ]
        if not candidates:
            raise ValueError(f"not enough usable {partition} rows for focus bucket {focus}")
        source = max(
            candidates,
            key=lambda item: (source_remaining[item], capacities[(item, focus)] - quotas[(item, focus)]),
        )
        quotas[(source, focus)] += 1
        source_remaining[source] -= 1
        focus_remaining[focus] -= 1
    return quotas


def _select(
    rows: list[dict[str, Any]],
    limit: int,
    seen_text: set[str],
    group_counts: Counter[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        if len(selected) >= limit:
            break
        text_key = normalize_phrase(str(row["utterance"]))
        key = group_key(row)
        if text_key in seen_text or group_counts[key] >= MAX_PER_TRANSITION_GROUP:
            continue
        seen_text.add(text_key)
        group_counts[key] += 1
        selected.append(row)
    return selected


def sample_transition_sets(
    rows: list[dict[str, Any]],
    gold_size: int,
    train_size: int,
    seed: int,
    excluded_texts: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    rng = random.Random(seed)
    excluded_texts = excluded_texts or set()
    sources = tuple(sorted({str(row.get("source", "unknown")) for row in rows}))
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    rejections: Counter[str] = Counter()
    for row in rows:
        text = str(row.get("utterance", "")).strip()
        if normalize_phrase(text) in excluded_texts:
            rejections["already_in_experiment"] += 1
            continue
        enriched = dict(row)
        enriched["utterance"] = text
        reason = rejection_reason(enriched)
        if reason:
            rejections[reason] += 1
            continue
        enriched["review_partition"] = review_partition(enriched)
        enriched["focus_bucket"] = focus_bucket(enriched)
        enriched["word_count"] = len(words(text))
        enriched["filler_ratio"] = round(filler_ratio(text), 3)
        buckets[(enriched["review_partition"], str(enriched.get("source", "unknown")), enriched["focus_bucket"])].append(enriched)

    for bucket_rows in buckets.values():
        rng.shuffle(bucket_rows)

    seen_text = set(excluded_texts)
    selected_sets: dict[str, list[dict[str, Any]]] = {"gold": [], "train": []}
    for partition, size in (("gold", gold_size), ("train", train_size)):
        group_counts: Counter[str] = Counter()
        quotas = build_quotas(buckets, partition, size, sources)
        for (source, focus), quota in quotas.items():
            selected = _select(buckets[(partition, source, focus)], quota, seen_text, group_counts)
            if len(selected) != quota:
                raise ValueError(
                    f"only {len(selected)} usable {partition} rows for {source}/{focus}; requested {quota}"
                )
            selected_sets[partition].extend(selected)
    return selected_sets["gold"], selected_sets["train"], rejections


def write_jsonl(rows: Iterable[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", default=list(DEFAULT_INPUTS))
    parser.add_argument("--exclude", type=Path, default=DEFAULT_EXCLUDE)
    parser.add_argument("--gold-output", type=Path, default=DEFAULT_GOLD_OUTPUT)
    parser.add_argument("--train-output", type=Path, default=DEFAULT_TRAIN_OUTPUT)
    parser.add_argument("--gold-size", type=int, default=DEFAULT_GOLD_SIZE)
    parser.add_argument("--train-size", type=int, default=DEFAULT_TRAIN_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = [row for path in args.inputs for row in load_jsonl(path)]
    excluded = {normalize_phrase(row["utterance"]) for row in load_jsonl(args.exclude)} if args.exclude.exists() else set()
    gold_rows, train_rows, rejections = sample_transition_sets(rows, args.gold_size, args.train_size, args.seed, excluded)
    write_jsonl(gold_rows, args.gold_output)
    write_jsonl(train_rows, args.train_output)
    for name, selected in (("gold", gold_rows), ("train", train_rows)):
        focus_counts = Counter(row["focus_bucket"] for row in selected)
        source_counts = Counter(str(row["source"]) for row in selected)
        print(f"{name}_candidates={len(selected)}")
        print(f"{name}_focus=" + ", ".join(f"{focus}:{focus_counts[focus]}" for focus in FOCUS_ORDER))
        print(f"{name}_sources=" + ", ".join(f"{source}:{source_counts[source]}" for source in sorted(source_counts)))
    print("rejections=" + ", ".join(f"{reason}:{rejections[reason]}" for reason in sorted(rejections)))
    print(f"gold_output={args.gold_output}")
    print(f"train_output={args.train_output}")


if __name__ == "__main__":
    main()
