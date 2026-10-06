# -*- coding: utf-8 -*-
"""Session feedback must stay attached to the turn that actually expressed it."""

from copy import deepcopy

import pytest

import ai.generate_feedback as feedback_module
from ai.contracts import FeedbackTurn


def _turn(turn_id="turn-1", *, user="she want cookies", reply="Oh, she wants cookies? What kind?"):
    return {"turn_id": turn_id, "user_transcript": user, "pally_text": reply}


def _item(original="she want", corrected="she wants"):
    return {
        "original": original,
        "corrected": corrected,
        "explanation_ko": "3인칭 단수 현재형에는 동사에 -s를 붙여요.",
    }


def _result(turn_id, items=None, *, failed=False):
    return {"turn_id": turn_id, "items": [] if items is None else items, "failed": failed}


@pytest.fixture(autouse=True)
def configured_provider(monkeypatch):
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "session-feedback-test-key")

    def unexpected_call(turns, level):
        pytest.fail("This test must provide its own Gemini response or avoid calling Gemini.")

    monkeypatch.setattr(feedback_module, "_call_gemini_session_feedback", unexpected_call)


def _provider_returns(monkeypatch, response):
    calls = []

    def provider(turns, level):
        calls.append((turns, level))
        return deepcopy(response)

    monkeypatch.setattr(feedback_module, "_call_gemini_session_feedback", provider)
    return calls


def test_empty_session_does_not_need_key_or_call_provider(monkeypatch):
    monkeypatch.delenv("GOOGLE_AI_API_KEY")
    assert feedback_module.generate_session_feedback([]) == []


def test_dict_input_is_normalized_and_level_is_forwarded(monkeypatch):
    item = _item()
    source = _turn()
    untouched = deepcopy(source)
    calls = _provider_returns(monkeypatch, [{"turn_id": "turn-1", "items": [item]}])

    assert feedback_module.generate_session_feedback([source], level="A2") == [
        _result("turn-1", [item]),
    ]
    assert len(calls) == 1
    normalized, level = calls[0]
    assert level == "A2"
    assert len(normalized) == 1
    assert isinstance(normalized[0], FeedbackTurn)
    assert normalized[0].model_dump() == source
    assert source == untouched


def test_contract_input_and_valid_empty_feedback_are_successful(monkeypatch):
    turn = FeedbackTurn(**_turn())
    calls = _provider_returns(monkeypatch, [{"turn_id": turn.turn_id, "items": []}])

    assert feedback_module.generate_session_feedback([turn]) == [_result(turn.turn_id)]
    assert calls[0][1] == "B1"


def test_shuffled_provider_response_is_restored_to_input_order(monkeypatch):
    turns = [_turn("turn-a"), _turn("turn-b"), _turn("turn-c")]
    item = _item()
    _provider_returns(monkeypatch, [
        {"turn_id": "turn-c", "items": []},
        {"turn_id": "turn-a", "items": [item]},
        {"turn_id": "turn-b", "items": []},
    ])

    assert feedback_module.generate_session_feedback(turns) == [
        _result("turn-a", [item]), _result("turn-b"), _result("turn-c"),
    ]


@pytest.mark.parametrize("response", [
    [{"turn_id": "turn-1", "items": []}, {"turn_id": "unknown", "items": []}],
    [{"turn_id": "turn-1", "items": []}],
    [{"turn_id": "turn-1", "items": []}, {"turn_id": "turn-1", "items": []}],
    [],
], ids=["unknown-id", "missing-id", "duplicate-id", "missing-all-ids"])
def test_unreliable_provider_ids_fail_the_whole_batch(monkeypatch, response):
    _provider_returns(monkeypatch, response)

    assert feedback_module.generate_session_feedback([_turn("turn-1"), _turn("turn-2")]) == [
        _result("turn-1", failed=True), _result("turn-2", failed=True),
    ]


def test_duplicate_input_id_is_rejected_before_any_provider_call():
    with pytest.raises(ValueError):
        feedback_module.generate_session_feedback([
            _turn("same-id"),
            _turn("same-id", user="I feel happy.", reply="What made you happy?"),
        ])


@pytest.mark.parametrize("field", ["turn_id", "user_transcript", "pally_text"])
@pytest.mark.parametrize("invalid", [None, 123, "", "   "])
def test_input_fields_must_be_nonempty_strings(field, invalid):
    turn = _turn()
    turn[field] = invalid

    with pytest.raises(ValueError):
        feedback_module.generate_session_feedback([turn])


def test_correction_from_another_turn_does_not_leak_into_this_turn(monkeypatch):
    item = _item()
    turns = [
        _turn("uncorrected", reply="What kind of cookies?"),
        _turn("corrected"),
    ]
    _provider_returns(monkeypatch, [
        {"turn_id": "uncorrected", "items": [item]},
        {"turn_id": "corrected", "items": [item]},
    ])

    assert feedback_module.generate_session_feedback(turns) == [
        _result("uncorrected", failed=True),
        _result("corrected", [item]),
    ]


def test_original_expression_must_come_from_the_same_user_turn(monkeypatch):
    item = _item()
    turns = [
        _turn("wrong-user", user="my friend likes cookies"),
        _turn("correct-user"),
    ]
    _provider_returns(monkeypatch, [
        {"turn_id": "wrong-user", "items": [item]},
        {"turn_id": "correct-user", "items": [item]},
    ])

    assert feedback_module.generate_session_feedback(turns) == [
        _result("wrong-user", failed=True),
        _result("correct-user", [item]),
    ]


def test_ungrounded_item_fails_its_turn_without_hiding_other_turns(monkeypatch):
    valid = _item()
    _provider_returns(monkeypatch, [
        {"turn_id": "mixed", "items": [valid, _item("he want", "he wants")]},
        {"turn_id": "good", "items": [valid]},
        {"turn_id": "empty", "items": []},
    ])

    assert feedback_module.generate_session_feedback([
        _turn("mixed"), _turn("good"), _turn("empty"),
    ]) == [
        _result("mixed", failed=True), _result("good", [valid]), _result("empty"),
    ]


@pytest.mark.parametrize("field", ["original", "corrected", "explanation_ko"])
@pytest.mark.parametrize("invalid", [None, 123, True, [], {}, "", "   "])
def test_invalid_item_fields_fail_batch_instead_of_coercing_or_dropping(monkeypatch, field, invalid):
    malformed = _item()
    malformed[field] = invalid
    _provider_returns(monkeypatch, [
        {"turn_id": "valid", "items": [_item()]},
        {"turn_id": "malformed", "items": [malformed]},
    ])

    assert feedback_module.generate_session_feedback([_turn("valid"), _turn("malformed")]) == [
        _result("valid", failed=True), _result("malformed", failed=True),
    ]


@pytest.mark.parametrize("malformed", [
    {"turn_id": "bad", "items": None},
    {"turn_id": "bad", "items": "no corrections"},
    {"turn_id": "bad", "items": _item()},
    {"turn_id": "bad", "items": [None]},
    {"turn_id": "bad", "items": [{"original": "she want", "corrected": "she wants"}]},
    {"turn_id": "bad"},
    {"turn_id": 123, "items": []},
    {"items": []},
], ids=["null-items", "string-items", "object-items", "null-item", "missing-explanation",
        "missing-items", "non-string-id", "missing-id"])
def test_malformed_provider_entries_fail_the_whole_batch(monkeypatch, malformed):
    _provider_returns(monkeypatch, [{"turn_id": "good", "items": [_item()]}, malformed])

    assert feedback_module.generate_session_feedback([_turn("good"), _turn("bad")]) == [
        _result("good", failed=True), _result("bad", failed=True),
    ]


@pytest.mark.parametrize("response", [None, "[]", {"turn_id": "turn-1", "items": []}])
def test_provider_must_return_a_list(monkeypatch, response):
    _provider_returns(monkeypatch, response)

    assert feedback_module.generate_session_feedback([_turn()]) == [
        _result("turn-1", failed=True),
    ]


def test_missing_api_key_preserves_every_turn_with_failure_flag(monkeypatch):
    monkeypatch.delenv("GOOGLE_AI_API_KEY")

    assert feedback_module.generate_session_feedback([_turn("one"), _turn("two")]) == [
        _result("one", failed=True), _result("two", failed=True),
    ]


def test_provider_exception_preserves_every_turn_with_failure_flag(monkeypatch):
    def provider(turns, level):
        raise TimeoutError("Test provider timeout")

    monkeypatch.setattr(feedback_module, "_call_gemini_session_feedback", provider)

    assert feedback_module.generate_session_feedback([_turn("one"), _turn("two")]) == [
        _result("one", failed=True), _result("two", failed=True),
    ]


def test_sessions_are_split_into_bounded_batches_and_all_results_are_returned(monkeypatch):
    turns = [_turn(f"turn-{index}") for index in range(18)]
    batches = []

    def provider(batch, level):
        batches.append([turn.turn_id for turn in batch])
        return [{"turn_id": turn.turn_id, "items": []} for turn in reversed(batch)]

    monkeypatch.setattr(feedback_module, "_call_gemini_session_feedback", provider)

    assert feedback_module.generate_session_feedback(turns) == [
        _result(turn["turn_id"]) for turn in turns
    ]
    assert [len(batch) for batch in batches] == [8, 8, 2]
    assert [turn_id for batch in batches for turn_id in batch] == [
        turn["turn_id"] for turn in turns
    ]


def test_one_failed_batch_does_not_discard_or_skip_other_batches(monkeypatch):
    turns = [_turn(f"turn-{index}") for index in range(17)]
    batches = []

    def provider(batch, level):
        batches.append([turn.turn_id for turn in batch])
        if len(batches) == 2:
            raise TimeoutError("Only the middle batch failed")
        return [{"turn_id": turn.turn_id, "items": []} for turn in batch]

    monkeypatch.setattr(feedback_module, "_call_gemini_session_feedback", provider)

    assert feedback_module.generate_session_feedback(turns) == [
        _result(turn["turn_id"], failed=8 <= index < 16)
        for index, turn in enumerate(turns)
    ]
    assert [len(batch) for batch in batches] == [8, 8, 1]


def test_tutor_name_change_is_ignored_while_real_same_turn_grammar_is_kept(monkeypatch):
    grammar = _item()
    name = {
        "original": "Fally",
        "corrected": "Pally",
        "explanation_ko": "이름을 바르게 써요.",
    }
    _provider_returns(monkeypatch, [{"turn_id": "turn-1", "items": [name, grammar]}])

    assert feedback_module.generate_session_feedback([
        _turn(user="Fally, she want cookies.", reply="I'm Pally. Oh, she wants cookies?"),
    ]) == [_result("turn-1", [grammar])]


def test_first_person_to_second_person_reaction_is_not_a_correction(monkeypatch):
    perspective = {
        "original": "I had lunch",
        "corrected": "you had lunch",
        "explanation_ko": "주어를 바꾸어요.",
    }
    _provider_returns(monkeypatch, [{"turn_id": "turn-1", "items": [perspective]}])

    assert feedback_module.generate_session_feedback([
        _turn(user="I had lunch.", reply="Oh, you had lunch? What did you eat?"),
    ]) == [_result("turn-1")]


@pytest.mark.parametrize(("user", "reply", "item", "expected"), [
    # The user's own fix keeps "I" even though Pally said "you".
    ("I is so tired.", "Oh, you're so tired?",
     {"original": "I is", "corrected": "you're", "replacement": "I'm"}, "I'm"),
    ("Yesterday I go to the park.", "You went to the park yesterday?",
     {"original": "go", "corrected": "went", "replacement": "went"}, "went"),
    ("She invited I to dinner.", "Oh, she invited you to dinner?",
     {"original": "invited I", "corrected": "invited you", "replacement": "invited me"}, "invited me"),
    # Pally's perspective must not leak into the user's sentence.
    ("Yesterday I go to the park.", "You went to the park yesterday?",
     {"original": "I go", "corrected": "You went", "replacement": "You went"}, None),
    # A fix Pally never said is not grounded; the card still shows the item.
    ("I have many people.", "Having many people there sounds fun!",
     {"original": "I have", "corrected": "Having", "replacement": "I had"}, None),
])
def test_replacement_is_kept_only_when_grounded_in_the_users_sentence(monkeypatch, user, reply, item, expected):
    _provider_returns(monkeypatch, [{"turn_id": "turn-1", "items": [{**item, "explanation_ko": "설명"}]}])

    [result] = feedback_module.generate_session_feedback([_turn(user=user, reply=reply)])

    assert result["failed"] is False
    assert result["items"][0].get("replacement") == expected


def test_stt_capitalization_and_punctuation_changes_are_not_corrections(monkeypatch):
    _provider_returns(monkeypatch, [{
        "turn_id": "turn-1",
        "items": [_item("she wants cookies", "She wants cookies!")],
    }])

    assert feedback_module.generate_session_feedback([
        _turn(user="she wants cookies", reply="She wants cookies! What kind?"),
    ]) == [_result("turn-1")]
