# -*- coding: utf-8 -*-
"""reply_segments — 색칠용 조각 조립·검증 (네트워크 없이 도는 순수 로직)."""
from ai.reply_segments import MAX_REPLY_CHARS, build_reply, parse_payload

GOOD = {
    "reaction": "Oh, you're on a diet?",
    "corrected_expr": "you're on a diet",
    "own_remark": "I skip lunch sometimes too.",
    "new_expr": "skip lunch",
    "question": "What do you eat for dinner?",
}


def test_pieces_become_spans_that_cover_the_whole_reply():
    """조각을 이어붙이면 TTS 가 읽는 문장과 글자 하나까지 같아야 한다.

    다르면 화면과 음성이 어긋난다.
    """
    built = build_reply(GOOD)

    assert built.text == "Oh, you're on a diet? I skip lunch sometimes too. What do you eat for dinner?"
    assert "".join(segment["text"] for segment in built.segments) == built.text
    assert [segment["kind"] for segment in built.segments] == [
        "plain", "correction", "plain", "plain", "own_remark", "new_expr", "own_remark",
        "plain", "question",
    ]


def test_only_the_corrected_words_are_marked_not_the_whole_sentence():
    """주황은 고쳐준 표현만 덮는다. 문장 전체를 칠하면 사용자가 어디를 틀렸는지
    알 수 없고, 인사말("Oh,")까지 교정으로 보이게 된다."""
    built = build_reply(GOOD)
    marked = [s["text"] for s in built.segments if s["kind"] == "correction"]

    assert marked == ["you're on a diet"]
    assert "Oh, " not in marked[0]
    # reaction 의 나머지는 평범한 말이다
    plain_before = built.segments[0]
    assert plain_before["kind"] == "plain" and plain_before["text"] == "Oh, "


def test_a_correct_sentence_gets_no_orange_at_all():
    """사용자가 틀리지 않았으면 교정 구간이 없다 — 칠하면 하지도 않은 교정을 배운다."""
    built = build_reply({**GOOD, "reaction": "You went to the beach?", "corrected_expr": ""})

    assert not [s for s in built.segments if s["kind"] == "correction"]
    assert "".join(s["text"] for s in built.segments) == built.text


def test_a_correction_the_model_did_not_actually_say_is_rejected():
    """corrected_expr 는 reaction 안의 구간이어야 한다. 아니면 Pally 가 말하지
    않은 표현에 색이 칠해진다."""
    assert build_reply({**GOOD, "corrected_expr": "you are on a diet"}) is None


def test_new_expression_is_marked_inside_pallys_own_sentence():
    """새 표현은 Pally 가 실제로 말한 문장 안의 구간이어야 밑줄을 그을 수 있다."""
    built = build_reply(GOOD)
    marked = [s["text"] for s in built.segments if s["kind"] == "new_expr"]

    assert marked == ["skip lunch"]
    assert "".join(s["text"] for s in built.segments if s["kind"] in ("own_remark", "new_expr")) == GOOD["own_remark"]


def test_new_expression_at_the_very_start_or_end_leaves_no_empty_span():
    """빈 구간을 넘기면 프론트가 빈 span 을 그린다."""
    for own, expr in (("Skip lunch is my habit.", "Skip lunch"), ("I often skip lunch", "skip lunch")):
        built = build_reply({**GOOD, "own_remark": own, "new_expr": expr})
        assert built is not None
        assert all(segment["text"] for segment in built.segments)


def test_a_broken_contract_is_rejected_instead_of_guessed():
    """조각을 추측해 채우지 않는다 — 틀린 구간에 색을 칠하면 Pally 가 하지도
    않은 교정을 사용자가 배운다. None 이면 호출부가 평문으로 내려간다."""
    too_long = {**GOOD, "reaction": "Oh, you did not eat lunch because you are on a diet today?"}

    assert build_reply({**GOOD, "question": ""}) is None          # 조각 누락
    assert build_reply({**GOOD, "new_expr": "eat pizza"}) is None  # own_remark 안에 없음
    assert build_reply(too_long) is None                           # 90자 초과
    assert len(f"{too_long['reaction']} {too_long['own_remark']} {too_long['question']}") > MAX_REPLY_CHARS
    assert build_reply({**GOOD, "own_remark": "You can say I skip lunch."}) is None  # 선생님 말투
    assert build_reply(None) is None
    assert build_reply("not a dict") is None


def test_missing_braces_are_recovered_but_nameless_values_are_not():
    """Gemini 가 가끔 중괄호를 빼고 필드만 뱉는다(실측 40회 중 2회). 내용은
    멀쩡하니 괄호만 돌려준다. 다만 필드 이름까지 없으면 순서로 끼워맞추지
    않는다 — 조용히 엉뚱한 구간에 색이 칠해진다.
    """
    recovered = parse_payload(
        '"reaction": "You are tired?",\n"corrected_expr": "You are tired",\n'
        '"own_remark": "I feel tired today too.",\n'
        '"new_expr": "feel tired",\n"question": "Did you sleep well?"'
    )

    assert recovered["new_expr"] == "feel tired"
    assert build_reply(recovered) is not None
    assert parse_payload('"Pizza is great!"\n"I love pizza too."\n"love pizza"\n"What topping?"') is None
    assert parse_payload("") is None
