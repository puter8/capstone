# -*- coding: utf-8 -*-

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.build_real_speech_axis_dataset import normalize_row


def test_normalize_row_keeps_external_provenance() -> None:
    row = normalize_row(
        {
            "utterance": "Could you repeat that?",
            "axes": {"Formality": 55, "Energy": 25, "Intimacy": 25, "Humor": 5, "Curiosity": 82},
            "source": "taskmaster1_woz_user_real",
            "conversation_id": "dialogue-1",
            "source_record_id": "dialogue-1:2",
            "label_status": "ai_draft_needs_human_review",
        },
        "ai_generated",
    )

    assert row["source"] == "taskmaster1_woz_user_real"
    assert row["conversation_id"] == "dialogue-1"
    assert row["source_record_id"] == "dialogue-1:2"
