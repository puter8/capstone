# -*- coding: utf-8 -*-
"""F/H/C active-learning round 2 -- candidate selection for the Gemini oracle.

Round 1 (scripts/select_purpose_v3_active_candidates.py) left tiers without
evidence: dev Humor is 34 low / 1 mid / 0 high and dev has no high Curiosity;
Formality failed. Round 2 re-uses round 1's exclusion and partition logic and
selects a training-only batch whose labels come from Gemini (fhc_round2_label.py),
because further human labeling is banned.

Leakage guards (one explicit manifest, built in eligible_pool()):
- protected meetings: the protected final-eval partition, the current dev
  split, and the legacy final-test 20 of the seed-100 set; plus the AMI
  scenario-series siblings of all of them (ES2008a-d share the same speakers
  and task) -- stricter than round 1, which was meeting-level. ICSI stays
  meeting-level: its meetings share one research group, so series-level
  exclusion is not possible (a documented limitation);
- the whole round-1 eval branch (eval_or_train() hash) and round 1's
  old-track gold-200/reserved-176 groups (load_exclusions());
- text-level exact match and word-set Jaccard >= NEAR_DUP_JACCARD near-
  duplicates against: seed 100, week2 338, the old combined pool, round-1 150,
  the Humor-rescue 70, dev 35, eval 31, and rows already selected. Jaccard is
  a conservative lexical filter, not proof of semantic independence.

Selection signals (used only to choose rows; Gemini never sees them):
Ridge (ai/ridge_axis_adapter.py) refit on the human train split, the rule
analyzer, and corpus annotations -- laughter events and dialogue-act question
tags (acquisition cues, not labels). A group-capped random reference sample is
drawn FIRST; then quotas target the missing tiers: mid/high Humor, high
Curiosity, both Formality extremes, then disagreement.

Santa Barbara is CC BY-ND and gitignored: SB rows are written with
utterance=null and re-hydrated from the local fixture by hydrate_text();
previews never print SB text.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.analyzers import RuleBasedAxisAnalyzer
from ai.ml_baseline import _load_jsonl_axis_dataset
from ai.ridge_axis_adapter import RidgeAxisAdapter
from scripts.sample_real_speech_label_candidates import (
    candidate_rejection_reason,
    is_question_like,
    strip_discourse_starters,
)
from scripts.select_purpose_v3_active_candidates import (
    DEFAULT_OLD_COMBINED,
    eval_or_train,
    group_key,
    load_exclusions,
    load_jsonl,
    normalize_text,
    write_jsonl,
)

AMI = ROOT / "data/fixtures/ami_utterances.jsonl"
ICSI = ROOT / "data/fixtures/icsi_utterances.jsonl"
SB = ROOT / "data/fixtures/santa_barbara_utterances.jsonl"  # gitignored (CC BY-ND)
R1_CANDIDATES = ROOT / "data/fixtures/pally_purpose_v3_active_train_candidates.jsonl"
HUMOR_RESCUE = ROOT / "data/fixtures/pally_humor_rescue_candidates.csv"
EVAL_PARTITION = ROOT / "data/fixtures/pally_purpose_v3_eval_partition.jsonl"
DEV_SPLIT = ROOT / "data/fixtures/pally_purpose_v3_train_dev_split_dev.jsonl"
TRAIN_SPLIT = ROOT / "data/fixtures/pally_purpose_v3_train_dev_split_train.jsonl"
SEED_100 = ROOT / "data/fixtures/pally_purpose_v1_items_100.jsonl"
WEEK2 = ROOT / "data/axis_dataset_week2.jsonl"
OUT = ROOT / "data/fixtures/pally_purpose_v3_round2_candidates.jsonl"

SEED = 20261012
SB_SOURCE = "santa_barbara_real"
MAX_PER_GROUP = 4  # training-only pseudo-labels: diversity cap, not a leakage guard
NEAR_DUP_JACCARD = 0.8
# Fill order matters: the random reference goes first (before caps fill up),
# then scarce-tier quotas, then disagreement.
QUOTAS = {
    "random_reference": 30,
    "humor_high_enrich": 55,
    "curiosity_high_enrich": 55,
    "formality_low_extreme": 30,
    "formality_high_extreme": 30,
    "formality_disagreement": 20,
    "humor_disagreement": 15,
    "curiosity_disagreement": 15,
}
LAUGH_EVENTS = {"laugh", "while laughing", "breath-laugh", "laughter"}
ICSI_QUESTION_DA = {"qw", "qo", "qr", "qy", "qrr"}  # qh (rhetorical) deliberately excluded
OPEN_QUESTION_RE = re.compile(
    r"\b(why|how come|what if|what do you think|how would|how could|how does|how do|what would)\b", re.I)
AXES = ("Formality", "Humor", "Curiosity")


def ami_series(meeting: str) -> str:
    # AMI scenario meetings come in a-d series with the same speakers (ES2008a..d).
    return meeting[:6] if meeting[:2] in ("ES", "IS", "TS") else meeting


def word_set(text: str) -> frozenset:
    text = unicodedata.normalize("NFKC", text).replace("’", "'").replace("‘", "'").lower()
    return frozenset(re.findall(r"[a-z0-9']+", text))


def is_near_dup(ws: frozenset, refs: list[frozenset]) -> bool:
    return any(ws and r and len(ws & r) / len(ws | r) >= NEAR_DUP_JACCARD for r in refs)


def hydrate_text(rows: list[dict]) -> list[dict]:
    """Fill utterance for text-free Santa Barbara rows from the gitignored fixture."""
    need = {r["source_record_id"] for r in rows if r.get("utterance") is None}
    if not need:
        return rows
    texts = {}
    with SB.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["source_record_id"] in need:
                texts[rec["source_record_id"]] = rec["utterance"]
    missing = need - set(texts)
    if missing:
        raise ValueError(f"{len(missing)} SB rows not found in {SB.name}: {sorted(missing)[:3]}")
    return [dict(r, utterance=texts[r["source_record_id"]]) if r.get("utterance") is None else r for r in rows]


def reserved_texts() -> list[str]:
    """Labeled, reserved or previously used texts a candidate must not copy."""
    texts = [r["target_turn"] for r in load_jsonl(SEED_100)]
    texts += [r["utterance"] for r in load_jsonl(WEEK2)]
    texts += [r["utterance"] for r in load_jsonl(ROOT / DEFAULT_OLD_COMBINED)]
    texts += [r["utterance"] for r in load_jsonl(R1_CANDIDATES)]
    texts += [r["utterance"] for r in load_jsonl(DEV_SPLIT)]
    texts += [r["utterance"] for r in load_jsonl(EVAL_PARTITION)]
    with HUMOR_RESCUE.open(encoding="utf-8") as f:
        texts += [r["utterance"] for r in csv.DictReader(f)]
    return texts


def protected_meetings() -> set[str]:
    """Meetings no training row may come from: eval partition, dev split, legacy final-test 20."""
    meetings = {r["source_group"] for r in load_jsonl(EVAL_PARTITION)}
    meetings |= {r["source_group"] for r in load_jsonl(DEV_SPLIT)}
    meetings |= {r["source_id"].split(".")[0] for r in load_jsonl(SEED_100) if r["split"] == "final_test"}
    return meetings


def question_cue(row: dict) -> bool:
    da = str(row.get("dialogue_act") or "")
    if row["source"] == "ami_real":
        return da.startswith("el.")
    if row["source"] == "icsi_real":
        return da.split("^")[0] in ICSI_QUESTION_DA
    tokens = re.findall(r"[a-z']+", row["utterance"].lower())
    return is_question_like(row["utterance"], strip_discourse_starters(tokens))


def eligible_pool() -> tuple[list[dict], Counter]:
    excluded_texts, old_track_groups = load_exclusions()
    excluded_texts |= {normalize_text(t) for t in reserved_texts()}
    protected = protected_meetings()
    protected_series = {ami_series(g) for g in protected}

    stats: Counter = Counter()
    pool = []
    for path in (AMI, ICSI, SB):
        for row in load_jsonl(path):
            group = row["source_group"]
            if normalize_text(row.get("utterance", "")) in excluded_texts:
                reason = "text_already_used_or_reserved"
            elif group_key(row) in old_track_groups:
                reason = "old_track_eval_group"
            elif group in protected:
                reason = "protected_meeting(eval/dev/legacy_final20)"
            elif eval_or_train(row) == "eval":
                reason = "eval_branch_hash_group"
            elif ami_series(group) in protected_series:
                reason = "ami_series_sibling_of_protected"
            else:
                reason = candidate_rejection_reason(row)
            if reason:
                stats[reason] += 1
                continue
            stats[f"eligible:{row['source']}"] += 1
            pool.append(row)
    return pool, stats


def attach_signals(pool: list[dict], rng: random.Random) -> None:
    ridge = RidgeAxisAdapter(alpha=1.0).fit(_load_jsonl_axis_dataset(TRAIN_SPLIT, allow_partial=True))
    rule = RuleBasedAxisAnalyzer()
    for i, row in enumerate(pool):
        rp = ridge.predict_partial(row["utterance"])
        ru = rule.analyze(row["utterance"])
        row["_ridge"] = {a: rp[a] for a in AXES}
        row["_rule"] = {a: getattr(ru, a) for a in AXES}
        row["_laugh"] = bool(set(row.get("annotation_events") or []) & LAUGH_EVENTS)
        row["_question"] = question_cue(row)
        row["_open_q"] = row["_question"] and (
            str(row.get("dialogue_act") or "").split("^")[0] in {"qw", "qo"}
            or bool(OPEN_QUESTION_RE.search(row["utterance"])))
        row["_rand"] = rng.random()
        if (i + 1) % 10000 == 0:
            print(f"  signals {i + 1}/{len(pool)}", file=sys.stderr)


def select(pool: list[dict]) -> tuple[list[dict], Counter]:
    refs = [word_set(t) for t in reserved_texts()]
    selected: list[dict] = []
    group_counts: Counter = Counter()
    near_dup_skips: Counter = Counter()
    used: set[int] = set()

    def take(ranked, reason, n):
        got = 0
        for row in ranked:
            if got >= n:
                break
            if id(row) in used or group_counts[row["source_group"]] >= MAX_PER_GROUP:
                continue
            ws = word_set(row["utterance"])
            if is_near_dup(ws, refs):
                near_dup_skips[reason] += 1
                continue
            row["_reason"] = reason
            selected.append(row)
            used.add(id(row))
            refs.append(ws)
            group_counts[row["source_group"]] += 1
            got += 1
        if got < n:
            raise ValueError(f"quota {reason}: only {got}/{n} rows available")

    hi = lambda r, a: max(r["_ridge"][a], r["_rule"][a])
    lo = lambda r, a: min(r["_ridge"][a], r["_rule"][a])
    dis = lambda r, a: abs(r["_ridge"][a] - r["_rule"][a])
    take(sorted(pool, key=lambda r: r["_rand"]), "random_reference", QUOTAS["random_reference"])
    take(sorted((r for r in pool if r["_laugh"]), key=lambda r: (-hi(r, "Humor"), r["_rand"])),
         "humor_high_enrich", QUOTAS["humor_high_enrich"])
    take(sorted((r for r in pool if r["_question"]), key=lambda r: (-r["_open_q"], -hi(r, "Curiosity"), r["_rand"])),
         "curiosity_high_enrich", QUOTAS["curiosity_high_enrich"])
    take(sorted(pool, key=lambda r: (lo(r, "Formality"), r["_rand"])),
         "formality_low_extreme", QUOTAS["formality_low_extreme"])
    take(sorted(pool, key=lambda r: (-hi(r, "Formality"), r["_rand"])),
         "formality_high_extreme", QUOTAS["formality_high_extreme"])
    for axis in AXES:
        take(sorted(pool, key=lambda r: (-dis(r, axis), r["_rand"])),
             f"{axis.lower()}_disagreement", QUOTAS[f"{axis.lower()}_disagreement"])
    return selected, near_dup_skips


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print stats and a preview, write nothing")
    args = parser.parse_args()
    rng = random.Random(SEED)

    pool, stats = eligible_pool()
    print(f"protected meetings: {len(protected_meetings())}")
    print(f"eligible pool: {len(pool)} rows / {len({r['source_group'] for r in pool})} meetings")
    print(f"filter breakdown: {dict(stats.most_common())}")
    attach_signals(pool, rng)
    print(f"cues in pool: laugh={sum(r['_laugh'] for r in pool)} question={sum(r['_question'] for r in pool)} "
          f"open_question={sum(r['_open_q'] for r in pool)}")
    selected, near_dup_skips = select(pool)

    by = Counter((r["_reason"], r["source"]) for r in selected)
    print(f"selected {len(selected)} from {len({r['source_group'] for r in selected})} meetings; "
          f"near-duplicate rejections by quota {dict(near_dup_skips)}")
    for reason in QUOTAS:
        print(f"  {reason:24s} " + " ".join(f"{s}={by[(reason, s)]}" for s in ("ami_real", "icsi_real", SB_SOURCE)))
    if args.dry_run:
        for r in selected[::10]:
            text = "[SB text withheld: CC BY-ND]" if r["source"] == SB_SOURCE else r["utterance"][:90]
            print(f"  [{r['_reason']}] ridge={r['_ridge']} rule={r['_rule']} | {text}")
        return

    out = []
    for r in selected:
        out.append({
            "item_id": r["source_record_id"],
            "source": r["source"],
            "source_group": r["source_group"],
            "source_record_id": r["source_record_id"],
            "utterance": None if r["source"] == SB_SOURCE else r["utterance"],
            "selection_reason": r["_reason"],
            "sel_ridge": r["_ridge"],
            "sel_rule": r["_rule"],
            "sel_laugh_cue": r["_laugh"],
            "sel_question_cue": r["_question"],
            "sel_open_question_cue": r["_open_q"],
            "protocol_version": "v3.1",
            "acquisition_round": "2026-10-active-r2-gemini",
        })
    write_jsonl(out, OUT)
    print(f"wrote {len(out)} candidates -> {OUT}")


if __name__ == "__main__":
    main()
