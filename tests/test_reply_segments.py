# -*- coding: utf-8 -*-
"""reply_segments — 색칠용 조각 조립·검증 (네트워크 없이 도는 순수 로직)."""
import itertools

import pytest

from ai.reply_segments import MAX_REPLY_CHARS, RESPONSE_SCHEMA, build_reply, parse_payload, system_prompt

UTTERANCE = "I'm diet"

GOOD = {
    "original_error": "I'm diet",
    "error_reason": "The phrase is be on a diet, not be diet.",
    "reaction": "Oh, you're on a diet?",
    "corrected_expr": "you're on a diet",
    "own_remark": "I skip lunch sometimes too.",
    "question": "What do you eat for dinner?",
}


def test_pieces_become_spans_that_cover_the_whole_reply():
    """조각을 이어붙이면 TTS 가 읽는 문장과 글자 하나까지 같아야 한다.

    다르면 화면과 음성이 어긋난다.
    """
    built = build_reply(GOOD, UTTERANCE)

    assert built.text == "Oh, you're on a diet? I skip lunch sometimes too. What do you eat for dinner?"
    assert "".join(segment["text"] for segment in built.segments) == built.text
    assert [segment["kind"] for segment in built.segments] == [
        "plain", "correction", "plain", "plain", "own_remark",
        "plain", "question",
    ]


def test_only_the_corrected_words_are_marked_not_the_whole_sentence():
    """주황은 고쳐준 표현만 덮는다. 문장 전체를 칠하면 사용자가 어디를 틀렸는지
    알 수 없고, 인사말("Oh,")까지 교정으로 보이게 된다."""
    built = build_reply(GOOD, UTTERANCE)
    marked = [s["text"] for s in built.segments if s["kind"] == "correction"]

    assert marked == ["you're on a diet"]
    assert "Oh, " not in marked[0]
    # reaction 의 나머지는 평범한 말이다
    plain_before = built.segments[0]
    assert plain_before["kind"] == "plain" and plain_before["text"] == "Oh, "


@pytest.mark.parametrize("utterance,reaction", [
    ("I didn't study anything. I was just chilling.", "You were just chilling?"),
    ("I like coffee very much.", "You like coffee a lot?"),
    ("I was tired yesterday.", "You were tired yesterday?"),
    ("My cat sleeps all day.", "Your cat sleeps all day?"),
])
def test_a_correct_sentence_gets_no_orange_at_all(utterance, reaction):
    """사용자가 틀리지 않았으면 교정 구간이 없다 — 칠하면 하지도 않은 교정을 배운다."""
    built = build_reply({
        **GOOD, "reaction": reaction, "original_error": "", "error_reason": "",
        "corrected_expr": "",
    }, utterance)

    assert built is not None
    assert not [s for s in built.segments if s["kind"] == "correction"]
    assert "".join(s["text"] for s in built.segments) == built.text


def test_a_correction_the_model_did_not_actually_say_is_rejected():
    """corrected_expr 는 reaction 안의 구간이어야 한다. 아니면 Pally 가 말하지
    않은 표현에 색이 칠해진다."""
    assert build_reply({**GOOD, "corrected_expr": "you are on a diet"}, UTTERANCE) is None


@pytest.mark.parametrize("utterance,original_error,reaction,corrected_expr,error_reason", [
    ("Yesterday I go to park", "go to park", "You went to the park?", "went to the park",
     "Yesterday requires past went; singular park needs an article."),
    ("She don't like coffee", "don't", "She doesn't like coffee?", "doesn't",
     "Third-person singular she requires doesn't."),
])
def test_grounded_corrections_keep_only_the_changed_span(
    utterance, original_error, reaction, corrected_expr, error_reason,
):
    built = build_reply({
        **GOOD, "original_error": original_error, "error_reason": error_reason,
        "reaction": reaction, "corrected_expr": corrected_expr,
    }, utterance)

    assert built is not None
    assert [s["text"] for s in built.segments if s["kind"] == "correction"] == [corrected_expr]
    assert "".join(s["text"] for s in built.segments) == built.text


def test_error_from_a_previous_turn_cannot_be_used_for_the_current_utterance():
    assert build_reply(GOOD, "I was just chilling.") is None
    assert build_reply(GOOD, "I'm on a diet.") is None


def test_original_error_must_be_copied_exactly_without_rewriting_source_spacing():
    assert build_reply({**GOOD, "original_error": "I'm  diet"}, UTTERANCE) is None
    assert build_reply({**GOOD, "original_error": "I'm  diet"}, "I'm  diet") is not None


@pytest.mark.parametrize("present", [
    flags for flags in itertools.product((False, True), repeat=3)
    if any(flags) and not all(flags)
])
def test_partial_error_evidence_is_rejected(present):
    fields = ("original_error", "error_reason", "corrected_expr")
    payload = {**GOOD, **{field: GOOD[field] if has_value else "" for field, has_value in zip(fields, present)}}
    assert build_reply(payload, UTTERANCE) is None


@pytest.mark.parametrize("field", tuple(GOOD))
def test_missing_fields_are_rejected(field):
    payload = {key: value for key, value in GOOD.items() if key != field}
    assert build_reply(payload, UTTERANCE) is None


@pytest.mark.parametrize("field", tuple(GOOD))
@pytest.mark.parametrize("value", (None, 123, False, [], {}))
def test_fields_are_not_coerced_from_non_string_values(field, value):
    assert build_reply({**GOOD, field: value}, UTTERANCE) is None


def test_own_remark_stays_one_ordinary_sentence():
    built = build_reply(GOOD, UTTERANCE)
    assert [s["text"] for s in built.segments if s["kind"] == "own_remark"] == [GOOD["own_remark"]]
    assert not [s for s in built.segments if s["kind"] == "new_expr"]


def test_own_remark_needs_no_learning_phrase():
    for own in ("Me too.", "I love coffee.", "I often skip lunch."):
        built = build_reply({**GOOD, "own_remark": own}, UTTERANCE)
        assert built is not None
        assert all(segment["text"] for segment in built.segments)
        assert [s["text"] for s in built.segments if s["kind"] == "own_remark"] == [own]


def test_model_contract_does_not_request_expression_generation_or_classification():
    assert "new_expr" not in RESPONSE_SCHEMA["properties"]
    assert "new_expr" not in RESPONSE_SCHEMA["required"]
    assert "new_expr" not in RESPONSE_SCHEMA["propertyOrdering"]
    assert "new_expr" not in system_prompt("Pally", "Use simple English.", "Warm.")


def test_obsolete_model_fields_do_not_split_or_drop_the_reply():
    built = build_reply({**GOOD, "new_expr": "a phrase not in the reply"}, UTTERANCE)
    assert built is not None
    assert [s["text"] for s in built.segments if s["kind"] == "own_remark"] == [GOOD["own_remark"]]
    assert not [s for s in built.segments if s["kind"] == "new_expr"]


def test_a_broken_contract_is_rejected_instead_of_guessed():
    """조각을 추측해 채우지 않는다 — 틀린 구간에 색을 칠하면 Pally 가 하지도
    않은 교정을 사용자가 배운다. None 이면 호출부가 평문으로 내려간다."""
    too_long = {**GOOD, "reaction": "Oh, you did not eat lunch because you are on a diet today?"}

    assert build_reply({**GOOD, "question": ""}, UTTERANCE) is None          # 조각 누락
    assert build_reply(too_long, UTTERANCE) is None                           # 90자 초과
    assert len(f"{too_long['reaction']} {too_long['own_remark']} {too_long['question']}") > MAX_REPLY_CHARS
    assert build_reply({**GOOD, "own_remark": "You can say I skip lunch."}, UTTERANCE) is None  # 선생님 말투
    assert build_reply(None, UTTERANCE) is None
    assert build_reply("not a dict", UTTERANCE) is None


def test_missing_braces_are_recovered_but_nameless_values_are_not():
    """Gemini 가 가끔 중괄호를 빼고 필드만 뱉는다(실측 40회 중 2회). 내용은
    멀쩡하니 괄호만 돌려준다. 다만 필드 이름까지 없으면 순서로 끼워맞추지
    않는다 — 조용히 엉뚱한 구간에 색이 칠해진다.
    """
    recovered = parse_payload(
        '"original_error": "",\n"error_reason": "",\n'
        '"reaction": "You are tired?",\n"corrected_expr": "",\n'
        '"own_remark": "I feel tired today too.",\n'
        '"question": "Did you sleep well?"'
    )

    assert recovered["own_remark"] == "I feel tired today too."
    assert build_reply(recovered, "I am tired.") is not None
    assert parse_payload('"Pizza is great!"\n"I love pizza too."\n"love pizza"\n"What topping?"') is None
    assert parse_payload("") is None
