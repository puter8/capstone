# -*- coding: utf-8 -*-
"""
Week 1 AI contract checks.

Run from the repository root:
  python tests/test_ai_week1_contracts.py
"""

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.analyzer import analyze_utterance
from ai.analyzers import RuleBasedAxisAnalyzer
from ai.contracts import AXIS_KEYS, MemeTermCandidate, RedditSourceItem
from ai.matrix_engine import compute_character
from ai.reddit_vocabulary import build_prompt_vocabulary, extract_meme_candidates


def _load_sources() -> list[RedditSourceItem]:
    path = os.path.join(ROOT, "data", "fixtures", "reddit_sources_week1.json")
    with open(path, "r", encoding="utf-8") as handle:
        return [RedditSourceItem.model_validate(item) for item in json.load(handle)]


def test_rule_based_wrapper_matches_legacy_analyzer() -> None:
    utterance = "yo what's up, this movie was lowkey amazing!"
    legacy_axes = analyze_utterance(utterance)
    wrapped_axes = RuleBasedAxisAnalyzer().analyze(utterance).to_axes_dict()
    assert wrapped_axes == legacy_axes
    assert tuple(wrapped_axes.keys()) == AXIS_KEYS
    assert all(0 <= value <= 100 for value in wrapped_axes.values())

    character = compute_character(wrapped_axes)
    assert set(character) == {"tone_casual", "energy_level", "humor_level"}
    assert all(0 <= value <= 100 for value in character.values())


def test_reddit_fixture_extracts_candidates_without_prompting_review_terms() -> None:
    candidates = extract_meme_candidates(_load_sources())
    normalized_terms = {candidate.normalizedTerm for candidate in candidates}
    assert {"lowkey", "main character energy", "no cap", "sus"}.issubset(normalized_terms)
    assert all(isinstance(candidate, MemeTermCandidate) for candidate in candidates)
    assert all(candidate.sourceId for candidate in candidates)
    assert all(0.0 <= candidate.confidence <= 1.0 for candidate in candidates)

    prompt_terms = build_prompt_vocabulary(candidates)
    prompt_term_names = {item["term"] for item in prompt_terms}
    assert "lowkey" in prompt_term_names
    assert "no cap" in prompt_term_names
    assert "sus" not in prompt_term_names


def run() -> None:
    test_rule_based_wrapper_matches_legacy_analyzer()
    test_reddit_fixture_extracts_candidates_without_prompting_review_terms()
    print("Week 1 AI contract checks passed.")


if __name__ == "__main__":
    run()

