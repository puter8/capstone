# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.extract_nict_jle import (
    FILLER_TOKEN_RE,
    collapse_filler_runs,
    extract_records_from_file,
    extract_utterances_from_file,
    filler_ratio,
    is_continuation_fragment,
)


def test_continuation_fragments_are_short_dependent_clauses() -> None:
    assert is_continuation_fragment("at a computer school")
    assert is_continuation_fragment("and then")
    assert not is_continuation_fragment("And I usually go there with my friend after work")
    assert not is_continuation_fragment("Maybe he is explaining something")


def test_filler_regex_catches_common_variants_but_not_hmm() -> None:
    fillers = [
        "mm",
        "mmm",
        "mhmm",
        "um",
        "umm",
        "uum",
        "uh",
        "uhm",
        "ur",
        "urr",
        "urm",
        "uunto",
        "mmto",
        "er",
        "err",
        "erm",
        "eeto",
        "eh",
        "em",
        "ee",
        "ah",
    ]
    for token in fillers:
        assert FILLER_TOKEN_RE.fullmatch(token)
    assert not FILLER_TOKEN_RE.fullmatch("hmm")
    assert not FILLER_TOKEN_RE.fullmatch("well")
    assert not FILLER_TOKEN_RE.fullmatch("like")


def test_collapse_filler_runs_only_collapses_three_or_more() -> None:
    assert collapse_filler_runs("mm mmm mm since I was small") == "mm since I was small"
    assert collapse_filler_runs("uh, uhm, erm, I think so") == "uh I think so"
    assert collapse_filler_runs("um er I think so") == "um er I think so"


def test_filler_ratio_counts_tokens_after_cleanup() -> None:
    assert filler_ratio("mm since I was small") == 0.2
    assert filler_ratio("hmm I think so") == 0.0


def test_extracts_learner_turns_and_filters_dense_fillers() -> None:
    source = Path("tests/.tmp_nict_jle_sample.txt")
    try:
        source.write_text(
            """
            <A>What do you do?</A>
            <B>I study English. at a computer school. <F>mm</F> <F>mmm</F> <F>mm</F> yes.</B>
            <B><F>um</F> <F>uh</F> <F>er</F> ok.</B>
            """,
            encoding="utf-8",
        )

        assert extract_utterances_from_file(source) == ["I study English at a computer school"]
        records = extract_records_from_file(source)
        assert records[0]["conversation_id"] == source.stem
        assert records[0]["speaker"] == "B"
        assert records[0]["previous_turn"] == "What do you do?"
        assert records[0]["next_turn_speaker"] == "B"
    finally:
        source.unlink(missing_ok=True)
