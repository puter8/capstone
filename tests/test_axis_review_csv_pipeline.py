# -*- coding: utf-8 -*-

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.build_human_reviewed_axis_dataset import ReviewError, convert_row
from scripts.export_axis_review_csv import ENERGY_CURIOSITY_FIELDS, REVIEW_FIELDS, review_row


def test_blind_review_row_has_no_draft_axes() -> None:
    row = review_row(
        {
            "utterance": "Could you explain that again?",
            "source": "ami_real",
            "source_group": "meeting-1",
            "source_record_id": "act-1",
        },
        "gold",
        1,
    )

    assert tuple(row) == REVIEW_FIELDS
    assert all(row[f"reviewed_{axis}"] == "" for axis in ("Formality", "Energy", "Intimacy", "Humor", "Curiosity"))
    assert row["review_status"] == "pending"
    assert "axes" not in row
    assert "focus_bucket" not in row
    assert row["previous_turn"] == ""
    assert row["next_turn"] == ""
    assert "source" not in row
    assert "source_group" not in row
    assert "source_record_id" not in row


def test_energy_curiosity_review_row_exposes_only_requested_axes() -> None:
    row = review_row({"utterance": "Could you explain that again?"}, "train", 1, "energy-curiosity")

    assert tuple(row) == ENERGY_CURIOSITY_FIELDS
    assert set(row) >= {"reviewed_Energy", "reviewed_Curiosity"}
    assert "reviewed_Formality" not in row


def test_completed_review_row_becomes_labeled_test_example() -> None:
    row = {
        "review_set": "gold",
        "utterance": "Could you explain that again?",
        "reviewed_Formality": "45",
        "reviewed_Energy": "30",
        "reviewed_Intimacy": "35",
        "reviewed_Humor": "5",
        "reviewed_Curiosity": "85",
        "reviewer_id": "reviewer-a",
        "review_status": "completed",
        "reviewer_notes": "Clear request for explanation.",
    }

    candidate = {
        "utterance": "Could you explain that again?",
        "source": "ami_real",
        "source_group": "meeting-1",
        "source_record_id": "act-1",
        "focus_bucket": "low_energy_high_curiosity",
    }
    converted = convert_row(row, candidate, 1, "human_blind_review")

    assert converted["split"] == "test"
    assert converted["axes"]["Curiosity"] == 85
    assert converted["label_status"] == "human_reviewed_blind"


def test_incomplete_review_is_rejected() -> None:
    row = {"review_set": "train", "review_status": "pending", "utterance": "Hello"}

    try:
        convert_row(row, {"utterance": "Hello"}, 1, "human_blind_review")
    except ReviewError as exc:
        assert "review_status" in str(exc)
    else:
        raise AssertionError("expected ReviewError")
