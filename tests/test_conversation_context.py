# -*- coding: utf-8 -*-

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.conversation_context import add_adjacent_turn_context


def test_context_is_ordered_within_each_conversation() -> None:
    rows = [
        {"utterance": "Second", "conversation": "a", "speaker": "B", "start": "2", "source_record_id": "a2"},
        {"utterance": "First", "conversation": "a", "speaker": "A", "start": "1", "source_record_id": "a1"},
        {"utterance": "Other", "conversation": "b", "speaker": "C", "start": "1", "source_record_id": "b1"},
    ]

    enriched = add_adjacent_turn_context(rows, "conversation", "start")

    assert [row["utterance"] for row in enriched] == ["First", "Second", "Other"]
    assert enriched[0]["turn_index"] == 0
    assert enriched[0]["next_turn"] == "Second"
    assert enriched[1]["previous_turn"] == "First"
    assert enriched[1]["previous_turn_speaker"] == "A"
    assert enriched[2]["previous_turn"] is None
