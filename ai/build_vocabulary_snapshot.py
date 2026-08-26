# -*- coding: utf-8 -*-
"""
Build a fixture-based Reddit vocabulary snapshot.

Real Reddit collection + human/policy approval is backend/PM-owned and not
built yet (no OAuth access, no MemeTerm storage — see Week 3/4 handoff
notes). Until that exists, this script demonstrates the full pipeline
(extract -> safety filter -> simulated approval -> prompt vocabulary) on a
fixture batch, so the contract is exercised end-to-end and the output is
reproducible without live Reddit access.

Run from the repository root:
  python ai/build_vocabulary_snapshot.py
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.contracts import MemeTerm, RedditSourceItem
from ai.reddit_vocabulary import build_prompt_vocabulary_from_terms, extract_meme_candidates

FIXTURE_PATH = os.path.join(ROOT, "data", "fixtures", "reddit_sources_week5.json")
SNAPSHOT_PATH = os.path.join(ROOT, "data", "fixtures", "pally_vocabulary_snapshot_week5.json")


def _load_sources() -> list[RedditSourceItem]:
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [RedditSourceItem.model_validate(item) for item in raw]


def _simulate_approval(candidates: list) -> list[MemeTerm]:
    """Simulate a human/policy approval pass: only safety=="safe" candidates
    are approved, one per normalized term (first occurrence), highest
    confidence first. `review`/`blocked` candidates are never auto-approved.
    """
    safe = [c for c in candidates if c.safety == "safe"]
    safe.sort(key=lambda c: c.confidence, reverse=True)
    seen_terms: set[str] = set()
    approved: list[MemeTerm] = []
    for candidate in safe:
        if candidate.normalizedTerm in seen_terms:
            continue
        seen_terms.add(candidate.normalizedTerm)
        approved.append(
            MemeTerm(
                **candidate.model_dump(),
                id=f"term-{candidate.normalizedTerm.replace(' ', '-')}",
                status="approved",
            )
        )
    return approved


def build_snapshot() -> dict:
    sources = _load_sources()
    candidates = extract_meme_candidates(sources)
    approved_terms = _simulate_approval(candidates)
    prompt_vocabulary = build_prompt_vocabulary_from_terms(approved_terms)

    return {
        "note": "Fixture-based snapshot. Not real Reddit data -- backend Reddit OAuth/collection and human approval are not built yet (see docs/plan Week 3/4 handoff).",
        "source_count": len(sources),
        "candidates": [
            {
                "term": c.term,
                "normalizedTerm": c.normalizedTerm,
                "subreddit": c.subreddit,
                "safety": c.safety,
                "confidence": c.confidence,
            }
            for c in candidates
        ],
        "approved_terms": [
            {"id": t.id, "term": t.normalizedTerm, "safety": t.safety, "confidence": t.confidence}
            for t in approved_terms
        ],
        "prompt_vocabulary": prompt_vocabulary,
    }


def main() -> None:
    snapshot = build_snapshot()
    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"source_count: {snapshot['source_count']}")
    print(f"candidates found: {len(snapshot['candidates'])}")
    for c in snapshot["candidates"]:
        print(f"  [{c['safety']:<7}] {c['term']!r} ({c['subreddit']}) confidence={c['confidence']}")
    print(f"approved terms: {len(snapshot['approved_terms'])}")
    print(f"prompt vocabulary (final, safe+approved only): {len(snapshot['prompt_vocabulary'])}")
    for v in snapshot["prompt_vocabulary"]:
        print(f"  - {v['term']}: {v['meaningKo']}")
    print(f"\nwritten to {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
