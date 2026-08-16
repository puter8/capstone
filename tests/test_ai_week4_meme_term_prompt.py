# -*- coding: utf-8 -*-
"""
Week 4 checks: approved MemeTerm -> Pally prompt vocabulary conversion.

Run from the repository root:
  python tests/test_ai_week4_meme_term_prompt.py
"""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.contracts import MemeTerm
from ai.reddit_vocabulary import build_prompt_vocabulary_from_terms


def _make_term(**overrides) -> MemeTerm:
    base = dict(
        term="lowkey",
        normalizedTerm="lowkey",
        meaningKo="은근히, 살짝",
        usageContext="Casual spoken emphasis for a mild opinion.",
        subreddit="EnglishLearning",
        sourceId="src-1",
        sourceUrl="https://reddit.com/r/EnglishLearning/comments/abc",
        observedAt="2026-08-01T00:00:00Z",
        confidence=0.9,
        safety="safe",
        id="term-1",
        status="approved",
    )
    base.update(overrides)
    return MemeTerm(**base)


def test_only_approved_and_safe_terms_are_included() -> None:
    terms = [
        _make_term(id="t1", status="approved", safety="safe", term="lowkey"),
        _make_term(id="t2", status="rejected", safety="safe", term="highkey"),
        _make_term(id="t3", status="approved", safety="review", term="sus"),
        _make_term(id="t4", status="approved", safety="blocked", term="kys"),
        _make_term(id="t5", status="expired", safety="safe", term="bet"),
    ]

    vocab = build_prompt_vocabulary_from_terms(terms)

    assert len(vocab) == 1
    assert vocab[0]["term"] == "lowkey"


def test_output_shape_and_sorted_by_confidence() -> None:
    terms = [
        _make_term(id="t1", term="mid", normalizedTerm="mid", confidence=0.5),
        _make_term(id="t2", term="slay", normalizedTerm="slay", confidence=0.95),
    ]

    vocab = build_prompt_vocabulary_from_terms(terms)

    assert [item["term"] for item in vocab] == ["slay", "mid"]
    for item in vocab:
        assert set(item.keys()) == {"term", "meaningKo", "usageContext"}


def test_respects_limit() -> None:
    terms = [
        _make_term(id=f"t{i}", term=f"term{i}", normalizedTerm=f"term{i}", confidence=i / 10)
        for i in range(10)
    ]

    vocab = build_prompt_vocabulary_from_terms(terms, limit=3)

    assert len(vocab) == 3


def test_empty_input_returns_empty_list() -> None:
    assert build_prompt_vocabulary_from_terms([]) == []


def _run_all() -> None:
    test_only_approved_and_safe_terms_are_included()
    test_output_shape_and_sorted_by_confidence()
    test_respects_limit()
    test_empty_input_returns_empty_list()
    print("Week 4 MemeTerm prompt checks passed.")


if __name__ == "__main__":
    _run_all()
