# -*- coding: utf-8 -*-

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.sample_nict_jle_label_candidates import (
    classify_bucket,
    is_candidate,
    is_low_information,
    sample_candidates,
)


def test_low_information_filters_empty_labeling_value() -> None:
    assert is_low_information("O K")
    assert is_low_information("Only once")
    assert is_low_information("Thank you very much")
    assert not is_low_information("I want to practice English conversation")


def test_candidate_filter_keeps_useful_learner_speech() -> None:
    assert not is_candidate("O K")
    assert not is_candidate("I went to")
    assert not is_candidate("for my age")
    assert not is_candidate("I live near XXX03 Station")
    assert not is_candidate("um er ah I think so")
    assert is_candidate("Could you please refund this ticket or exchange the new one")
    assert is_candidate("I like to watch the non-fiction program")


def test_bucket_classification_prefers_labeling_signals() -> None:
    assert classify_bucket("What kind of shop is this") == "question"
    assert classify_bucket("Could you please speak more slowly") == "question"
    assert classify_bucket("may happen to everyone") != "polite_request"
    assert classify_bucket("I want to go, but no chance") == "personal_statement"
    assert classify_bucket("The woman is talking to the teacher") == "narrative_description"


def test_sampling_is_deterministic_and_balanced() -> None:
    rows = [
        {"utterance": "What is this place", "source": "nict_jle_real", "axes": None, "_source_line": 1},
        {"utterance": "Could you please help me", "source": "nict_jle_real", "axes": None, "_source_line": 2},
        {"utterance": "I like playing tennis after school", "source": "nict_jle_real", "axes": None, "_source_line": 3},
        {"utterance": "The woman is reading a book", "source": "nict_jle_real", "axes": None, "_source_line": 4},
        {"utterance": "Yes please", "source": "nict_jle_real", "axes": None, "_source_line": 5},
    ]

    first = sample_candidates(rows, size=3, seed=7)
    second = sample_candidates(rows, size=3, seed=7)
    assert first == second
    assert len(first) == 3
    assert all(row["axes"] is None for row in first)
