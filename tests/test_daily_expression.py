# -*- coding: utf-8 -*-
"""daily_expression — 48개 표현의 매칭 패턴을 케이스로 고정 (네트워크 없이 도는 순수 로직).

패턴이 Task 달성을 좌우하므로, 표현마다 "이건 인정" / "이건 불인정" 문장을 함께 둔다.
HITS 는 학습자가 그 표현을 실제로 쓴 발화, MISSES 는 비슷하지만 쓰지 않은 발화.
"""
import re

import pytest

from ai.daily_expression import (
    EXPRESSIONS,
    LEVELS,
    Expression,
    by_id,
    for_level,
    matches,
    normalize,
    opener_rule,
    pick_for_day,
)

# expr_id -> (인정해야 하는 발화들, 불인정해야 하는 발화들)
CASES = {
    "a2-would-like": (
        ["I'd like to try it.", "I would like to go there someday."],
        ["I like to read.", "I'd love that."],
    ),
    "a2-how-about": (
        ["How about Saturday?", "how about we meet later"],
        ["What about it?", "I was thinking about how it works."],
    ),
    "a2-good-at": (
        ["I'm good at cooking.", "I am not good at math.", "Im pretty good at it."],
        ["It's a good idea.", "I'm good, thanks."],
    ),
    "a2-a-lot-of": (
        ["There's a lot of work today.", "There are lots of people here."],
        ["I have a lot of work.", "That's a lot."],
    ),
    "a2-lets": (
        ["Let's talk about movies.", "lets go"],
        ["She lets me drive.", "Let me think."],
    ),
    "a2-want-to-try": (
        ["I want to try surfing.", "i want to try that food"],
        ["I want to go.", "She wants to try it."],
    ),
    "a2-kind-of": (
        ["It's kind of cold.", "That's kind of funny."],
        ["What kind of music?", "I'm kind of busy."],
    ),
    "a2-usually": (
        ["I usually wake up early.", "i usually walk to work"],
        ["Usually it rains.", "I don't usually."],
    ),
    "a2-maybe-should": (
        ["Maybe I should sleep now.", "maybe i should ask her"],
        ["I should sleep.", "Maybe you should go."],
    ),
    "a2-not-sure": (
        ["I'm not sure about that.", "I am not really sure.", "im not so sure"],
        ["I'm sure about it.", "She's not sure."],
    ),
    "a2-little-bit": (
        ["I'm a little bit tired.", "just a little bit more"],
        ["A little tired.", "Wait a bit."],
    ),
    "a2-favorite": (
        ["Pizza is my favorite food.", "my favorite color is blue"],
        ["I like it the most.", "Your favorite song?"],
    ),
    "b1-looking-forward": (
        ["I'm looking forward to the trip.", "I am looking forward to seeing you."],
        ["I look forward to it.", "She's looking forward to it."],
    ),
    "b1-used-to": (
        ["I used to play the piano.", "i used to live in busan"],
        # "get used to"(b1-get-used-to) 와 겹치지 않아야 한다.
        ["I'm getting used to it.", "She used to sing.", "I used my phone."],
    ),
    "b1-trying-to": (
        ["I'm trying to read more.", "I am trying to sleep earlier."],
        ["I tried to call you.", "She's trying to help."],
    ),
    "b2-big-fan": (
        ["I'm a big fan of rainy days.", "not a big fan of mondays"],
        ["I'm a fan.", "It's a big deal."],
    ),
    "b2-tend-to": (
        ["I tend to stay up late.", "i tend to forget names"],
        ["She tends to worry.", "I tended the garden."],
    ),
    "b2-makes-my-day": (
        ["A good coffee makes my day.", "that made my day", "it makes my day honestly"],
        ["It makes sense.", "My day was long."],
    ),
    "c1-soft-spot": (
        ["I have a soft spot for old bookshops.", "a soft spot for stray cats"],
        ["It's a soft chair.", "A spot on the wall."],
    ),
    "c1-second-nature": (
        ["Early mornings are second nature to me.", "it's second nature now"],
        ["The second one.", "Human nature is odd."],
    ),
    "c1-partial-to": (
        ["I'm partial to quiet weekends.", "I am partial to strong coffee."],
        ["A partial refund.", "She's partial to it."],
    ),
    "b1-into": (
        ["I'm into indie music.", "I'm really into cooking lately.",
         "I'm not into horror movies.", "I am kind of into it."],
        ["I walked into the room.", "I'm going into town."],
    ),
    "b1-not-my-thing": (
        ["It's not my thing.", "Horror isn't really my thing.",
         "Those aren't my thing."],
        ["It's my thing.", "My thing is cooking."],
    ),
    "b1-rather": (
        ["I'd rather stay home.", "I would rather not."],
        ["Rather cold today.", "She'd rather go."],
    ),
    "b1-end-up": (
        ["I ended up watching three episodes.", "We end up arguing every time.",
         "I ended up with two tickets."],
        ["At the end of the day.", "The end is near."],
    ),
    "b1-thinking-of": (
        ["I'm thinking of learning guitar.", "I am thinking about moving."],
        ["I'm thinking of a number.", "I was thinking."],
    ),
    "b1-to-be-honest": (
        ["To be honest, I forgot.", "it was boring to be honest"],
        ["He's an honest person.", "Honestly, I forgot."],
    ),
    "b1-big-deal": (
        ["It's not a big deal.", "That was a big deal for me."],
        ["It's a big problem.", "A great deal of money."],
    ),
    "b1-get-used-to": (
        ["I'm getting used to the schedule.", "I got used to it.",
         "You'll get used to it."],
        ["I used to live there.", "She used my phone."],
    ),
    "b1-feel-like": (
        ["I feel like I need a break.", "i feel like pizza tonight"],
        ["It feels like summer.", "I feel tired."],
    ),
    "b2-torn-between": (
        ["I'm torn between the two.", "I am torn between staying and leaving."],
        ["The paper is torn.", "Between us, it's fine."],
    ),
    "b2-grew-on-me": (
        ["It grew on me.", "The song has grown on me.", "it's growing on me"],
        ["I grew up here.", "She grew taller."],
    ),
    "b2-cant-help": (
        ["I can't help laughing.", "I couldn't help wondering about it.",
         "cannot help thinking that"],
        ["I can't help you.", "I can't stop laughing."],
    ),
    "b2-worth": (
        ["It's worth trying.", "The trip is worth taking.", "worth reading twice"],
        ["It's worth ten dollars.", "What's it worth?"],
    ),
    "b2-id-say": (
        ["I'd say about an hour.", "I would say it's fine."],
        ["I said that.", "She'd say no."],
    ),
    "b2-more-often-than-not": (
        ["More often than not, I skip breakfast.", "more often than not it works"],
        ["More often now.", "Often than not."],
    ),
    "b2-for-granted": (
        ["I took it for granted.", "we take our free time for granted"],
        ["She was granted access.", "For good."],
    ),
    "b2-not-big-on": (
        ["I'm not big on spicy food.", "I am not really big on parties.",
         "im not that big on it"],
        ["I'm big on fitness.", "It's not big."],
    ),
    "b2-hard-time": (
        ["I had a hard time sleeping.", "I'm having a tough time with it.",
         "she has a hard time focusing"],
        ["It was hard.", "Time is hard to find."],
    ),
    "c1-inclined": (
        ["I'm inclined to agree.", "I am inclined to think so."],
        ["The roof is inclined.", "She's inclined that way."],
    ),
    "c1-hindsight": (
        ["In hindsight, I should have asked.", "with hindsight it was obvious"],
        ["Looking back, I was wrong.", "Hindsight is twenty twenty."],
    ),
    "c1-boils-down": (
        ["It boils down to practice.", "it all boil down to money"],
        ["The water boils fast.", "It comes down to this."],
    ),
    "c1-by-and-large": (
        ["By and large, it worked.", "by and large people agree"],
        ["A large group.", "By the way."],
    ),
    "c1-fine-line": (
        ["There's a fine line between the two.", "a thin line between love and hate"],
        ["A fine day.", "The line between them."],
    ),
    "c1-at-the-expense": (
        ["I finished it at the expense of sleep.", "at the expense of quality"],
        ["It was expensive.", "On my own expense."],
    ),
    "c1-mixed-bag": (
        ["The reviews were a mixed bag.", "it was a mixed bag honestly"],
        ["Mixed feelings.", "A paper bag."],
    ),
    "c1-put-my-finger": (
        ["I can't put my finger on it.", "cant quite put my finger on it"],
        ["I pointed my finger.", "Put your hand on it."],
    ),
    "c1-on-the-fence": (
        ["I'm on the fence about moving.", "still on the fence"],
        ["The cat is on the wall.", "A wooden fence."],
    ),
}


def test_every_expression_has_cases():
    """새 표현을 추가하면 케이스도 같이 추가하도록 강제."""
    assert {e.id for e in EXPRESSIONS} == set(CASES)


@pytest.mark.parametrize("expr", EXPRESSIONS, ids=lambda e: e.id)
def test_hits(expr: Expression):
    for text in CASES[expr.id][0]:
        assert matches(expr, text), f"{expr.id} should match: {text!r}"


@pytest.mark.parametrize("expr", EXPRESSIONS, ids=lambda e: e.id)
def test_misses(expr: Expression):
    for text in CASES[expr.id][1]:
        assert not matches(expr, text), f"{expr.id} should NOT match: {text!r}"


@pytest.mark.parametrize("expr", EXPRESSIONS, ids=lambda e: e.id)
def test_own_example_matches(expr: Expression):
    """화면에 띄우는 예문 자체가 패턴을 통과해야 한다. 통과 못 하면 사용자가
    예문을 그대로 따라 말해도 Task 가 달성되지 않는다."""
    assert matches(expr, expr.example_en)


def test_empty_and_korean_never_match():
    for expr in EXPRESSIONS:
        assert not matches(expr, "")
        assert not matches(expr, None)
        assert not matches(expr, "저는 오늘 피곤해요")


def test_curly_apostrophe_is_accepted():
    expr = by_id("b1-into")
    assert matches(expr, "I’m into jazz.")


def test_catalog_shape():
    assert len(EXPRESSIONS) == 48
    for level in LEVELS:
        assert len(for_level(level)) == 12
    assert by_id("nope") is None
    # 모든 패턴이 컴파일되고, 레벨 값은 profiles.english_level 과 같은 집합.
    for expr in EXPRESSIONS:
        assert expr.level in LEVELS
        assert expr.patterns
        for pattern in expr.patterns:
            re.compile(pattern)


def test_unknown_level_falls_back_to_b1():
    assert for_level("Z9") == for_level("B1")


def test_pick_is_stable_within_a_day_and_moves_between_days():
    user = "11111111-1111-1111-1111-111111111111"
    a = pick_for_day(user, "2026-10-29", "B1")
    assert a is pick_for_day(user, "2026-10-29", "B1")
    assert pick_for_day(user, "2026-10-30", "B1").id != a.id
    assert a.level == "B1"


def test_pick_cycles_through_the_whole_level_before_repeating():
    user = "22222222-2222-2222-2222-222222222222"
    seen = {
        pick_for_day(user, f"2026-11-{day:02d}", "B2").id for day in range(1, 13)
    }
    assert seen == {e.id for e in for_level("B2")}


def test_different_users_get_different_orders():
    dates = [f"2026-10-{day:02d}" for day in range(1, 13)]
    a = [pick_for_day("aaaa", d, "B1").id for d in dates]
    b = [pick_for_day("bbbb", d, "B1").id for d in dates]
    assert a != b


def test_normalize_collapses_whitespace_and_case():
    assert normalize("  I'M   Into\nJazz ") == "i'm into jazz"


def test_opener_rule_names_the_expression_and_bans_the_slot_marker():
    expr = by_id("b1-into")
    rule = opener_rule(expr)
    assert expr.text in rule
    # 모델이 "~" 를 그대로 출력해 TTS 가 더듬은 일이 있다 (오프너 실측).
    assert 'never write the "~" character' in rule
    # 한 줄 규칙이라 오프너 프롬프트에 그대로 붙는다.
    assert rule.startswith("- ") and "\n" not in rule
