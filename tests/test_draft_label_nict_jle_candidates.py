# -*- coding: utf-8 -*-

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.draft_label_nict_jle_candidates import draft_axes, has_repair, label_rows, validate_rows


def test_draft_axes_follow_core_signals() -> None:
    question = draft_axes({"utterance": "Could you please tell me why this happened", "sample_bucket": "question"})
    statement = draft_axes({"utterance": "I went to Ueno Zoo with my family", "sample_bucket": "personal_statement"})
    repair = draft_axes({"utterance": "I I have seen this movie recently", "sample_bucket": "repair_disfluency"})

    assert question["Curiosity"] > statement["Curiosity"]
    assert question["Formality"] > statement["Formality"]
    assert statement["Intimacy"] > question["Intimacy"]
    assert repair["Formality"] < statement["Formality"]


def test_label_rows_preserve_schema_and_need_review() -> None:
    rows = [
        {
            "utterance": "Do you like living alone",
            "source": "nict_jle_real",
            "axes": None,
            "sample_bucket": "question",
            "source_line": 10,
        }
    ]
    labeled = label_rows(rows)
    validate_rows(labeled)

    assert labeled[0]["utterance"] == rows[0]["utterance"]
    assert labeled[0]["source"] == "nict_jle_real"
    assert labeled[0]["label_status"] == "ai_draft_needs_human_review"
    assert labeled[0]["style"] == "learner_question"


def test_normal_short_words_do_not_create_a_false_repair_signal() -> None:
    assert not has_repair("The air conditioning is working")
    assert has_repair("I I need a moment")
