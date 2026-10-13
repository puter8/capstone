# -*- coding: utf-8 -*-
"""Codex-recommended Humor rescue, Priority #1 (2026-10-12): the existing
F/H/C dev split has 1 mid and 0 high Humor examples (34/1/0), so no model
comparison can establish tier recall until real mid/high examples exist.
This script does NOT invent labels -- it mines a CANDIDATE shortlist from
AMI's own objective `annotation_events` field (vocalsound type="laugh",
parsed by scripts/extract_ami.py from the official NXT XML).

This is an internal MINING sheet, not a rating sheet: it carries context
turns, meeting IDs, laugh annotations and pool labels, which rubric v2.2
Sec.2 forbids raters from seeing. A blinded rater view (opaque ID + target
utterance only) must be generated separately if human Humor rating happens.

Caveats recorded with the data:
- Co-occurring self-laughter is a sampling cue, not proof of playfulness.
- "no_laugh_random_negative_candidate" rows are random utterances with an
  EMPTY annotation-events list; absence of annotated laughter does not
  establish absence of humor, and designed hard negatives (literal slang,
  quoted jokes, slang questions, sarcastic hostility) do not exist yet.
- AMI here is mostly scenario (role-play) meetings -- a domain mismatch with
  casual ESL chat.
- `fhc_partition` tags rows from the F/H/C protected final-eval meetings and
  the current dev meetings; those rows must never be added to training.
"""
import csv
import json
import random
from collections import Counter
from pathlib import Path

SRC = Path("data/fixtures/ami_utterances.jsonl")
OUT = Path("data/fixtures/pally_humor_rescue_candidates.csv")
EVAL_PARTITION = Path("data/fixtures/pally_purpose_v3_eval_partition.jsonl")
DEV_SPLIT = Path("data/fixtures/pally_purpose_v3_train_dev_split_dev.jsonl")
SEED = 20261012


def load_rows():
    return [json.loads(l) for l in open(SRC, encoding="utf-8")]


def partition_groups(path):
    return {json.loads(l)["source_group"].split(".")[0] for l in open(path, encoding="utf-8")}


def main(n_positive=50, n_negative=20, max_per_meeting=2):
    rows = load_rows()
    rng = random.Random(SEED)

    positive_pool = [
        r for r in rows
        if "laugh" in (r.get("annotation_events") or [])
        and len(r["utterance"].split()) >= 4
    ]
    rng.shuffle(positive_pool)
    per_meeting = Counter()
    positives = []
    for r in positive_pool:
        if per_meeting[r["meeting_id"]] >= max_per_meeting:
            continue
        positives.append(r)
        per_meeting[r["meeting_id"]] += 1
        if len(positives) >= n_positive:
            break

    positive_meetings = {r["meeting_id"] for r in positives}
    negative_pool = [
        r for r in rows
        if not (r.get("annotation_events") or [])
        and len(r["utterance"].split()) >= 6
        and r["meeting_id"] in positive_meetings
    ]
    rng.shuffle(negative_pool)
    per_meeting_neg = Counter()
    negatives = []
    for r in negative_pool:
        if per_meeting_neg[r["meeting_id"]] >= 2:
            continue
        negatives.append(r)
        per_meeting_neg[r["meeting_id"]] += 1
        if len(negatives) >= n_negative:
            break

    combined = [("laugh_cooccur_candidate", r) for r in positives] + \
               [("no_laugh_random_negative_candidate", r) for r in negatives]
    rng.shuffle(combined)

    eval_groups, dev_groups = partition_groups(EVAL_PARTITION), partition_groups(DEV_SPLIT)

    def fhc_partition(meeting):
        if meeting in eval_groups:
            return "protected_final_eval"
        return "fhc_dev" if meeting in dev_groups else ""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "pool", "fhc_partition", "meeting_id", "speaker", "previous_turn",
            "utterance", "next_turn", "annotation_events",
        ])
        for i, (pool, r) in enumerate(combined):
            w.writerow([
                f"humor_rescue_{i:03d}", pool, fhc_partition(r["meeting_id"]), r["meeting_id"],
                r["speaker"], r.get("previous_turn") or "", r["utterance"], r.get("next_turn") or "",
                ",".join(r.get("annotation_events") or []),
            ])
    tags = Counter(fhc_partition(r["meeting_id"]) for _, r in combined)
    print(f"wrote {len(combined)} rows ({len(positives)} laugh-candidates, "
          f"{len(negatives)} random negatives, {len(positive_meetings)} meetings; "
          f"fhc_partition {dict(tags)}) to {OUT}")


if __name__ == "__main__":
    main()
