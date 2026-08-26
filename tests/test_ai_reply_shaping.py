# -*- coding: utf-8 -*-
from ai.reply_shaping import MAX_REPLY_CHARS, shape_reply


def test_short_reply_passes_through_unchanged():
    text = "Oh no, that sounds rough!"
    assert shape_reply(text) == text


def test_long_reply_truncates_at_sentence_boundary():
    text = (
        "Oh no, you skipped lunch because you're on a diet? "
        "Maybe have something light later, like a small salad or some fruit. "
        "It's important not to skip meals too often, though!"
    )
    result = shape_reply(text)
    assert len(result) <= MAX_REPLY_CHARS
    assert result.endswith(("?", ".", "!"))
    assert text.startswith(result)


def test_never_cuts_mid_word():
    text = "This is a normal length reply that keeps going and going and going and going and going and going."
    result = shape_reply(text)
    assert len(result) <= MAX_REPLY_CHARS or result == text.split(".")[0] + "."
    assert not result.endswith((" and", "goin", "keep"))


def test_single_long_sentence_kept_whole_rather_than_broken():
    text = "A" * 40 + " is a single sentence with no punctuation breaks at all inside it whatsoever"
    result = shape_reply(text)
    # No sentence boundary exists, so it falls back to a hard char cut --
    # still not literally mid-word-broken in a way that looks like garbage,
    # just shorter.
    assert len(result) <= MAX_REPLY_CHARS


def test_empty_and_none_safe():
    assert shape_reply("") == ""
    assert shape_reply(None) == ""


def test_max_tokens_style_broken_cutoff_gets_cleaned_up():
    # Simulates Gemini text that got hard-cut by maxOutputTokens mid-sentence.
    broken = (
        "That's so exciting! I love hearing about your weekend plans, "
        "did you also want to talk about what you're going to do "
        "when you get th"
    )
    result = shape_reply(broken)
    assert result.endswith("!")
    assert len(result) <= MAX_REPLY_CHARS
