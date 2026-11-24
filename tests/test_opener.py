# -*- coding: utf-8 -*-
import random
import time
from concurrent.futures import ThreadPoolExecutor
from typing import ClassVar

import httpx
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


class _FakeResponse:
    def __init__(self, status_code, text="Hey! What did you eat today?"):
        self.status_code = status_code
        self._text = text

    def json(self):
        return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": self._text}]}}]}


class _FakeClient:
    instances: ClassVar[list["_FakeClient"]] = []

    def __init__(self, **kwargs):
        time.sleep(0.01)  # widen the init race for the concurrency test
        self.posts = []
        self.fail_next = None
        self.status_code = 200
        _FakeClient.instances.append(self)

    def post(self, url, headers, json, timeout):
        self.posts.append({"url": url, "headers": headers, "timeout": timeout})
        if self.fail_next:
            exc, self.fail_next = self.fail_next, None
            raise exc
        return _FakeResponse(self.status_code)


@pytest.fixture
def fake_client(monkeypatch):
    _FakeClient.instances = []
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(opener, "_client", None)
    monkeypatch.setattr(opener.httpx, "Client", _FakeClient)
    return _FakeClient


def test_client_is_built_once_and_reused(fake_client):
    opener._call_gemini("p", 1.0)
    opener._call_gemini("p", 2.0)
    assert len(fake_client.instances) == 1
    posts = fake_client.instances[0].posts
    assert [p["timeout"] for p in posts] == [1.0, 2.0]  # timeout stays per request


def test_concurrent_first_calls_build_one_client(fake_client):
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: opener._call_gemini("p", 1.0), range(8)))
    assert len(fake_client.instances) == 1
    assert len(fake_client.instances[0].posts) == 8


def test_api_key_goes_in_header_not_url(fake_client):
    opener._call_gemini("p", 1.0)
    post = fake_client.instances[0].posts[0]
    assert post["headers"] == {"x-goog-api-key": "test-key"}
    assert "test-key" not in post["url"] and "key=" not in post["url"]


def test_transport_error_propagates_without_retry_and_client_stays_usable(fake_client):
    opener._call_gemini("p", 1.0)
    client = fake_client.instances[0]
    client.fail_next = httpx.ConnectError("boom")
    with pytest.raises(httpx.ConnectError):
        opener._call_gemini("p", 1.0)
    assert len(client.posts) == 2  # exactly one POST for the failed call
    assert opener._call_gemini("p", 1.0) == "Hey! What did you eat today?"
    assert len(fake_client.instances) == 1


def test_http_error_status_is_rejected(fake_client):
    opener._call_gemini("p", 1.0)
    fake_client.instances[0].status_code = 503
    with pytest.raises(OpenerRejected) as e:
        opener._call_gemini("p", 1.0)
    assert e.value.reason == "http_503"


# ---------------------------------------------------------------------------
# persona_prompt bands the RAW axes at the same cuts as the renderer
# (frontend/components/pally/PallyCanvas.tsx tier) and the My-page trait tags
# (backend/main.py _TRAIT_TIERS). It used to band compute_character's weighted
# sums for Tone, Energy and Humor, which pull toward the middle, so what Pally
# looked like and how it talked came from different numbers.
# ---------------------------------------------------------------------------

# Axis -> the trait line it owns, and that line's label per renderer tier.
_PERSONA_BANDS = {
    "Formality": ("Tone", ("blunt and direct, no slang", "relaxed", "polite and proper")),
    "Energy": ("Energy", ("calm and gentle", "upbeat", "super excited")),
    "Humor": ("Humor", ("sincere", "lightly playful", "goofy and teasing")),
    "Intimacy": ("Closeness", ("friendly but a little reserved", "warm", "like a best friend")),
    "Curiosity": ("Curiosity", ("simple, direct question", "interested question",
                                "eager, specific question")),
}


def _renderer_tier(value: int) -> int:
    """frontend/components/pally/PallyCanvas.tsx tier()."""
    return 0 if value <= 33 else 1 if value <= 66 else 2


def _trait_lines(axes: dict) -> dict:
    return dict(
        line.removeprefix("- ").split(": ", 1)
        for line in opener.persona_prompt(axes).splitlines()
    )


@pytest.mark.parametrize("axis", sorted(_PERSONA_BANDS))
def test_every_trait_line_bands_its_own_axis_like_the_renderer(axis):
    line_name, labels = _PERSONA_BANDS[axis]
    for value in range(101):
        axes = dict(AXES, **{axis: value})
        assert _trait_lines(axes)[line_name] == labels[_renderer_tier(value)], (
            f"{axis}={value} must put {line_name} in the same band as Pally's shape"
        )


@pytest.mark.parametrize("axis", sorted(_PERSONA_BANDS))
def test_a_trait_line_moves_only_with_its_own_axis(axis):
    """compute_character mixed all five axes into each tone line, so a user
    could change one axis and watch a different trait flip."""
    line_name, _ = _PERSONA_BANDS[axis]
    baseline = _trait_lines(AXES)[line_name]
    for other in _PERSONA_BANDS:
        if other == axis:
            continue
        for value in (0, 100):
            axes = dict(AXES, **{other: value})
            assert _trait_lines(axes)[line_name] == baseline, (
                f"{other}={value} must not move the {line_name} line"
            )


def test_the_low_formality_band_does_not_ask_for_slang():
    """Pally's line is what the learner imitates. Asking the low Formality band
    for slang produced "Yo dude! What's up with your pals?" openers for a B1
    learner, in 7 of 9 samples, where "blunt" produced none."""
    blunt = _trait_lines(dict(AXES, Formality=10))["Tone"]
    assert "slang" in blunt and "no slang" in blunt
    assert "casual" not in blunt


def test_all_five_axes_reach_the_prompt():
    lines = _trait_lines(AXES)
    assert set(lines) == {"Tone", "Energy", "Humor", "Closeness", "Curiosity"}
