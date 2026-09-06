# -*- coding: utf-8 -*-

import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.extract_chime6 import clean_words
from scripts.extract_ami import extract_dialogue_act_rows
from scripts.extract_hcrc_maptask import clean_text as clean_hcrc_text
from scripts.extract_taskmaster1_woz import extract_dialogues
from scripts.sample_real_speech_label_candidates import candidate_rejection_reason, classify_bucket, sample_candidates


def test_chime_cleaner_removes_event_marker_but_keeps_words() -> None:
    text, events = clean_words("[laughs] It's the blue, I think.")

    assert text == "It's the blue, I think."
    assert events == ["laughs"]


def test_hcrc_cleaner_removes_only_truncated_token_not_completed_words() -> None:
    assert clean_hcrc_text('s-- slightly "u" shape') == "slightly u shape"


def test_taskmaster_extractor_keeps_only_user_turns() -> None:
    rows = extract_dialogues(
        [
            {
                "conversation_id": "dialogue-1",
                "instruction_id": "restaurant-1",
                "utterances": [
                    {"index": 0, "speaker": "ASSISTANT", "text": "How can I help?"},
                    {"index": 1, "speaker": "USER", "text": "  Could you find dinner nearby?  "},
                ],
            }
        ]
    )

    assert len(rows) == 1
    assert rows[0]["utterance"] == "Could you find dinner nearby?"
    assert rows[0]["source_record_id"] == "dialogue-1:1"
    assert rows[0]["previous_turn"] == "How can I help?"
    assert rows[0]["previous_turn_speaker"] == "ASSISTANT"
    assert rows[0]["next_turn"] is None


def test_external_sampler_keeps_complete_conjunction_answer() -> None:
    rows = [
        {"utterance": "Because I work from home every weekday", "source": "chime6_real", "source_group": "P01"},
        {"utterance": "Could you please repeat that last part", "source": "chime6_real", "source_group": "P02"},
        {"utterance": "I really enjoy cooking dinner with my family", "source": "chime6_real", "source_group": "P03"},
    ]

    assert candidate_rejection_reason(rows[0]) is None
    sampled, _ = sample_candidates(rows, size=3, seed=7)
    assert {row["utterance"] for row in sampled} == {row["utterance"] for row in rows}


def test_ami_extractor_uses_dialogue_act_word_ranges_and_preserves_events() -> None:
    dialogue_root = ET.fromstring(
        """<root xmlns:nite=\"http://nite.sourceforge.net/\"><dact nite:id=\"act-1\">
        <nite:pointer role=\"da-aspect\" href=\"da-types.xml#id(ami_da_5)\"/>
        <nite:child href=\"ES2002a.A.words.xml#id(w0)..id(w6)\"/>
        </dact></root>""",
    )
    entries = [
        {"id": "w0", "text": "Could", "punctuation": False, "event": "", "start_time": "1", "end_time": "1"},
        {"id": "w1", "text": "you", "punctuation": False, "event": "", "start_time": "1", "end_time": "1"},
        {"id": "w2", "text": "send", "punctuation": False, "event": "", "start_time": "1", "end_time": "1"},
        {"id": "w3", "text": "the", "punctuation": False, "event": "", "start_time": "1", "end_time": "1"},
        {"id": "w4", "text": "notes", "punctuation": False, "event": "", "start_time": "1", "end_time": "1"},
        {"id": "w5", "text": "?", "punctuation": True, "event": "", "start_time": "1", "end_time": "1"},
        {"id": "w6", "text": "", "punctuation": False, "event": "laugh", "start_time": "1", "end_time": "1"},
    ]
    rows = extract_dialogue_act_rows(
        dialogue_root,
        entries,
        {entry["id"]: index for index, entry in enumerate(entries)},
        "ES2002a",
        "A",
        {"ami_da_5": {"name": "el.inf", "gloss": "Elicit-Inform"}},
        {"speaker_id": "FEE005", "speaker_native_language": "English", "speaker_role": "ME"},
    )

    assert len(rows) == 1
    assert rows[0]["utterance"] == "Could you send the notes?"
    assert rows[0]["dialogue_act"] == "el.inf"
    assert rows[0]["annotation_events"] == ["laugh"]
    assert rows[0]["speaker_native_language"] == "English"


def test_sampler_does_not_treat_ami_dialogue_act_as_a_question_without_text_signal() -> None:
    row = {"utterance": "Could be really light or something special.", "dialogue_act": "el.sug"}

    assert classify_bucket(row) != "question"
