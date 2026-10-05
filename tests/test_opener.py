# -*- coding: utf-8 -*-
import random

import pydantic
import pytest

import ai.opener as opener
from ai.opener import (LEVEL_RULES, OpenerRejected, generate_opener, pick_topic,
                       validate_opener, word_count)

AXES = {"Formality": 50, "Energy": 50, "Intimacy": 50, "Humor": 50, "Curiosity": 50}


def _stub(monkeypatch, result):
    def fake(prompt, timeout):
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr(opener, "_call_gemini", fake)


def test_valid_output_passes_through(monkeypatch):
    _stub(monkeypatch, '"Yo! What did you eat today?"')
    assert generate_opener(AXES, "A2", []) == "Yo! What did you eat today?"


@pytest.mark.parametrize("bad", [
    "?",
    "Tell me about your day.",                       # no question
    "Nice day. Busy week. What's new?",              # >2 sentences
    "Hey! Nice day. Busy week? What's new?",         # >2 after the interjection
    "안녕! 오늘 뭐 했어?",                             # Korean
    "Hey there buddy, what exciting things did you do today, my good friend?",  # 13 words > A2 cap
])
def test_rule_breaking_output_raises(monkeypatch, bad):
    _stub(monkeypatch, bad)
    with pytest.raises(OpenerRejected):
        generate_opener(AXES, "A2", [])


@pytest.mark.parametrize("good", [
    "Hey! I love dogs. Do you have a pet?",          # interjection + 2 sentences
    "Have you watched any good shows? What was it?",  # follow-up question is fine
])
def test_natural_openers_pass(good):
    assert validate_opener(good, LEVEL_RULES["B1"][1]) == good


def test_provider_errors_propagate(monkeypatch):
    _stub(monkeypatch, TimeoutError())
    with pytest.raises(TimeoutError):
        generate_opener(AXES, "A2", [])


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
    with pytest.raises(OpenerRejected) as e:
        generate_opener(AXES, "B1", [])
    assert e.value.reason == "missing_api_key"


@pytest.mark.parametrize("level", list(LEVEL_RULES))
def test_word_cap_is_exact(level):
    cap = LEVEL_RULES[level][1]
    ok = " ".join(["word"] * (cap - 1)) + " ok?"
    assert word_count(validate_opener(ok, cap)) == cap
    with pytest.raises(OpenerRejected):
        validate_opener("extra " + ok, cap)


@pytest.mark.parametrize("bad_axes", [
    {k: v for k, v in AXES.items() if k != "Humor"},
    {**AXES, "Energy": 101},
    {**AXES, "Energy": None},
])
def test_invalid_axes_raise(bad_axes):
    with pytest.raises(pydantic.ValidationError):
        generate_opener(bad_axes, "B1", [])


def test_recent_topic_is_avoided():
    rng = random.Random(1)
    recent = ["Any plans for this weekend?", "We had pizza for dinner"]
    for _ in range(50):
        assert pick_topic(recent, rng) not in {"weekend plans", "food you ate recently"}


def test_keyword_match_respects_word_boundaries():
    # "eat" must not match inside "great"/"theater".
    assert "food you ate recently" not in opener._recent_topics(["great theater"])


def test_all_topics_used_relaxes_oldest_history_first():
    newest = "We talked about the weekend"
    oldest = " ".join(k for kws in opener.TOPICS.values() for k in kws)
    for seed in range(20):
        assert pick_topic([newest, oldest], random.Random(seed)) != "weekend plans"


@pytest.mark.parametrize("resp, reason", [
    ({}, "no_candidates"),
    ({"candidates": []}, "no_candidates"),
    ({"candidates": [{"finishReason": "SAFETY"}]}, "finish_safety"),
    ({"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "Hey what"}]}}]}, "finish_max_tokens"),
    ({"candidates": [{"content": {"parts": [{"thought": True, "text": "x"}]}}]}, "empty_text"),
])
def test_extract_text_rejects_unusable_responses(resp, reason):
    with pytest.raises(OpenerRejected) as e:
        opener._extract_text(resp)
    assert e.value.reason == reason
