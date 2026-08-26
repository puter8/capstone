# -*- coding: utf-8 -*-
"""
Week 5 checks: the fixture-based Reddit vocabulary snapshot is reproducible,
and the safety/exclusion filters behave as documented.

Run from the repository root:
  python tests/test_ai_week5_vocabulary_snapshot.py
"""

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.build_vocabulary_snapshot import SNAPSHOT_PATH, build_snapshot


def _load_committed_snapshot() -> dict:
    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_snapshot_is_reproducible() -> None:
    rebuilt = build_snapshot()
    committed = _load_committed_snapshot()
    assert rebuilt["candidates"] == committed["candidates"]
    assert rebuilt["approved_terms"] == committed["approved_terms"]
    assert rebuilt["prompt_vocabulary"] == committed["prompt_vocabulary"]


def test_excluded_and_unsafe_sources_produce_no_candidates() -> None:
    snapshot = build_snapshot()
    subreddits_with_candidates = {c["subreddit"] for c in snapshot["candidates"]}
    # teenagers (excluded subreddit) and the PII-signal source never contribute.
    assert "teenagers" not in subreddits_with_candidates
    assert snapshot["source_count"] == 6
    assert len(snapshot["candidates"]) == 6  # only sources 001-003 contribute


def test_review_terms_are_never_approved() -> None:
    snapshot = build_snapshot()
    review_terms = {c["normalizedTerm"] for c in snapshot["candidates"] if c["safety"] == "review"}
    approved_terms = {t["term"] for t in snapshot["approved_terms"]}
    assert review_terms, "fixture should contain at least one review-safety candidate"
    assert not (review_terms & approved_terms)


def test_prompt_vocabulary_only_contains_approved_safe_terms() -> None:
    snapshot = build_snapshot()
    assert len(snapshot["prompt_vocabulary"]) == len(snapshot["approved_terms"])


def _run_all() -> None:
    test_snapshot_is_reproducible()
    test_excluded_and_unsafe_sources_produce_no_candidates()
    test_review_terms_are_never_approved()
    test_prompt_vocabulary_only_contains_approved_safe_terms()
    print("Week 5 vocabulary snapshot checks passed.")


if __name__ == "__main__":
    _run_all()
