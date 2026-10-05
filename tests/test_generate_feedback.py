# -*- coding: utf-8 -*-
from ai.generate_feedback import generate_feedback
import ai.generate_feedback as feedback_module
import pytest


@pytest.fixture(autouse=True)
def isolated_feedback_http_pool():
    feedback_module._reset_client()
    yield
    feedback_module._reset_client()


def _item(original, corrected):
    return {"original": original, "corrected": corrected, "explanation_ko": "주어에 맞춰 동사를 바꿔요."}


def test_review_records_correction_actually_spoken(monkeypatch):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    item = _item("she want", "she wants")
    monkeypatch.setattr(feedback_module, "_call_gemini_feedback", lambda *args: [item])
    assert generate_feedback("she want cookies", "Oh, she wants cookies? What kind?", "B1") == ([item], False)


@pytest.mark.parametrize("original, corrected, reply", [
    ("she want", "she wants", "What kind of cookies?"),
    ("he want", "she wants", "Oh, she wants cookies?"),
    ("she want", "he wants", "Oh, she wants cookies?"),
])
def test_ungrounded_correction_is_not_saved(monkeypatch, original, corrected, reply):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(feedback_module, "_call_gemini_feedback", lambda *args: [_item(original, corrected)])
    items, failed = generate_feedback("she want cookies", reply, "B1")
    assert items == []
    assert failed is False


def test_one_ungrounded_item_does_not_discard_a_grounded_one(monkeypatch):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    good = _item("she want", "she wants")
    bad = _item("he want", "she wants")
    monkeypatch.setattr(feedback_module, "_call_gemini_feedback", lambda *args: [bad, good])
    items, failed = generate_feedback("she want cookies", "Oh, she wants cookies? What kind?", "B1")
    assert items == [good]
    assert failed is False


def test_punctuation_only_change_is_not_a_review_item(monkeypatch):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(feedback_module, "_call_gemini_feedback", lambda *args: [_item("she wants cookies", "She wants cookies!")])
    assert generate_feedback("she wants cookies", "She wants cookies!", "B1") == ([], False)


def test_failed_provider_cannot_introduce_unspoken_fallback(monkeypatch):
    monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
    assert generate_feedback("I had no lunch.", "What would you like to eat?", "B1") == ([], True)


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


@pytest.mark.parametrize("original, corrected", [
    ("Fally", "Pally"),
    ("Bally", "Pally"),
    ("Hi fally", "Hi Pally"),
    ("I'm happy", "you are happy"),
    ("I have been learning", "you've been learning"),
    ("I'm not going to be able to go", "you won't be able to go"),
    ("I do not like coffee", "I don't like coffee"),
])
def test_names_and_correct_restatements_are_not_grammar_feedback(monkeypatch, original, corrected):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(feedback_module, "_call_gemini_feedback", lambda *args: [_item(original, corrected)])
    assert generate_feedback(original, corrected, "B1") == ([], False)


@pytest.mark.parametrize("original, corrected", [
    ("Fally want cookies", "Fally wants cookies"),
    ("Pally cookies", "Pally's cookies"),
    ("I are happy", "you are happy"),
    ("Me went to school", "I went to school"),
    ("She invited I to dinner", "she invited you to dinner"),
    ("He gave I a book", "he gave you a book"),
    ("she have cookies", "she has cookies"),
    ("he don't like it", "he doesn't like it"),
    ("I go yesterday", "you went yesterday"),
    ("I am happy", "you were happy"),
    ("I can go", "you can't go"),
])
def test_filter_keeps_grammar_tense_and_negation_changes(monkeypatch, original, corrected):
    # This checks the conservative filter, not whether the model SHOULD emit
    # every pair. Semantic correctness is also covered by live model checks.
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    item = _item(original, corrected)
    monkeypatch.setattr(feedback_module, "_call_gemini_feedback", lambda *args: [item])
    assert generate_feedback(original, corrected, "B1") == ([item], False)


def test_duplicate_items_are_removed_within_a_turn(monkeypatch):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    item = _item("she want", "she wants")
    monkeypatch.setattr(feedback_module, "_call_gemini_feedback", lambda *args: [item, item])
    assert generate_feedback("she want cookies", "she wants cookies", "B1") == ([item], False)


def test_provider_failure_does_not_replace_a_correct_sentence_with_fallback(monkeypatch):
    monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
    assert generate_feedback("I had no lunch.", "I didn't have lunch.", "B1") == ([], True)


@pytest.mark.parametrize("provider_json", [
    {},
    {"candidates": []},
    {"candidates": [{"finishReason": "SAFETY"}]},
    {"candidates": [{"finishReason": "STOP", "content": {"parts": []}}]},
    {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "[]"}]}}]},
    {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '[{"original":"she want"}]'}]}}]},
    {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "not json"}]}}]},
])
def test_bad_provider_response_is_failure_not_no_corrections(monkeypatch, provider_json):
    import httpx

    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    client_type = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=provider_json))
    monkeypatch.setattr(feedback_module.httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    assert generate_feedback("she want cookies", "she wants cookies", "B1") == ([], True)


def test_successful_empty_provider_array_is_no_corrections(monkeypatch):
    import json
    import httpx

    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"candidates": [{
            "finishReason": "STOP", "content": {"parts": [{"text": "[]"}]},
        }]})

    client_type = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(feedback_module.httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    assert generate_feedback('Hey "Fally"!', "How are you?", "B1") == ([], False)
    assert len(requests) == 1
    assert "key=" not in str(requests[0].url)
    assert requests[0].headers["x-goog-api-key"] == "test-key"
    payload = json.loads(requests[0].content)
    user_data = json.loads(payload["contents"][0]["parts"][0]["text"])
    assert user_data["user_transcript"] == 'Hey "Fally"!'


def test_feedback_calls_reuse_client_with_per_request_timeouts(monkeypatch):
    import httpx

    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    clients, requests = [], []
    client_type = httpx.Client

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"candidates": [{
            "finishReason": "STOP", "content": {"parts": [{"text": "[]"}]},
        }]})

    def factory(**kwargs):
        client = client_type(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(feedback_module.httpx, "Client", factory)
    feedback_module._call_gemini_feedback("Hello", "Hi")
    feedback_module._call_gemini_session_feedback([], "B1")
    assert len(clients) == 1
    assert [request.extensions["timeout"]["read"] for request in requests] == [10.0, 30.0]


def test_transport_failure_reconnects_once(monkeypatch):
    import httpx

    monkeypatch.setenv("GOOGLE_AI_API_KEY", "test-key")
    clients = []
    client_type = httpx.Client

    def failing(request):
        raise httpx.ConnectError("Test stale connection", request=request)

    def success(request):
        return httpx.Response(200, json={"candidates": [{
            "finishReason": "STOP", "content": {"parts": [{"text": "[]"}]},
        }]})

    def factory(**kwargs):
        client = client_type(transport=httpx.MockTransport(failing if not clients else success), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(feedback_module.httpx, "Client", factory)
    assert generate_feedback("Hi", "Hello", "B1") == ([], False)
    assert len(clients) == 2
    assert clients[0].is_closed
