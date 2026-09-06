# -*- coding: utf-8 -*-

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.build_combined_axis_dataset import normalize_row


def test_normalize_row_preserves_label_metadata() -> None:
    row = normalize_row(
        {
            "utterance": "Do you like living alone",
            "axes": {"Formality": 36, "Energy": 27, "Intimacy": 22, "Humor": 6, "Curiosity": 84},
            "style": "learner_question",
            "split": "train",
            "label_status": "ai_draft_needs_human_review",
            "sample_bucket": "question",
            "source_line": 10,
        },
        "nict_jle_real",
    )

    assert row["source"] == "nict_jle_real"
    assert row["label_status"] == "ai_draft_needs_human_review"
    assert row["sample_bucket"] == "question"
