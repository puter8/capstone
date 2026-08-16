# -*- coding: utf-8 -*-
from ai.generate_feedback import generate_feedback


def test_generate_feedback_no_api_key_returns_failed_true(monkeypatch):
    monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
    utterance = "I had no lunch. I'm on a diet."
    pally = "Oh no, you skipped lunch because you're on a diet? What would you like to eat later?"

    items, failed = generate_feedback(utterance, pally, "B1")

    assert failed is True
    assert isinstance(items, list)
    if items:
        item = items[0]
        assert all(k in item for k in ("original", "corrected", "explanation_ko"))


def test_generate_feedback_empty_utterance_is_not_a_failure():
    items, failed = generate_feedback("", "reply", "B1")

    assert items == []
    assert failed is False
