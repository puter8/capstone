# -*- coding: utf-8 -*-
"""
daily_expression
----------------
One expression per day, per level, that the home screen shows, Pally works into
the conversation once, and the day's Task credits when the user says it back.

Why the list is written here and not generated: the display copy is the easy
half. The hard half is deciding whether the user actually said it, and that
decision gates a Task. Asked to write the match patterns, Gemini produced
regexes that matched 0 of 6 utterances a human reads as correct uses; asked to
judge matches directly, it agreed with a human 79% of the time, and its errors
were false positives - crediting a Task the user had not earned. So the pattern
for every expression is written and pinned by a test here, and Gemini's role is
limited to drafting Korean glosses and examples for a human to check before
they land in this file.

Matching accepts the core structure, not the dictionary form. A learner who
says "I'm not really into horror movies" has practised "I'm into ~" and gets
credit; demanding the bare affirmative would fail the people using the
expression best. Each pattern therefore allows negation and up to two
intervening modifiers where the structure permits it, and nothing more - a
pattern loose enough to fire on unrelated speech would hand out the Task for
free.

Selection is a per-user rotation, not a daily hash. A hash of (user, date)
repeats expressions at random within a week; ordering the level's list once per
user and walking it by date gives every expression one turn before any repeats.

Public API:
  Expression                      one catalog entry
  EXPRESSIONS                     the whole catalog
  LEVELS                          catalog levels, matching profiles.english_level
  for_level(level)                the expressions available at a level
  by_id(expr_id)                  catalog lookup, None when unknown
  pick_for_day(user_id, date, level) -> Expression
  normalize(text)                 the form patterns are written against
  matches(expr, text)             did this utterance use the expression
  opener_rule(expr)               the opener prompt line for this expression
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date as _date
from typing import Optional

LEVELS = ("A2", "B1", "B2", "C1")

# Up to two degree words between the anchor words, so "I'm into" also covers
# "I'm not into" and "I'm really kind of into". The list is a whitelist, not
# `\w+`: any word at all there makes "I'm going into town" look like "I'm into
# ~", which credits a Task the user did not earn.
_DEGREE = (
    r"(?:(?:not|really|so|very|too|totally|super|quite|pretty|also|still|"
    r"definitely|absolutely|mostly|that|all|much|kind\s+of|kinda|sort\s+of|"
    r"sorta|a\s+bit|a\s+little)\s+){0,2}"
)


@dataclass(frozen=True)
class Expression:
    """A catalog entry.

    `text` is the teaching form shown on screen, with `~` for the slot the user
    fills. `patterns` are regexes written against `normalize()` output, not
    against raw transcripts.

    """

    id: str
    level: str
    text: str
    meaning_ko: str
    example_en: str
    example_ko: str
    patterns: tuple

    def compiled(self) -> tuple:
        return tuple(re.compile(p) for p in self.patterns)


# Every entry has to work as an opener, because the opener is where Pally
# models it. That rules out response forms - expressions that only mean
# something as a reply to what someone just said ("That makes sense", "come to
# think of it", "on purpose", "I'll give you that"). Pally speaks the opener
# first and is told it knows nothing about the user yet, so there is nothing
# for those to answer, and the model produced sentences that parse but mean
# nothing: asked to open with "on purpose" it said "I saw a cute dog today on
# purpose!". Ten such expressions were dropped from this catalog for that
# reason; apply the same test before adding one.
EXPRESSIONS = (
    # --- A2 -----------------------------------------------------------------
    Expression(
        "a2-would-like", "A2", "I'd like to ~", "~하고 싶어요",
        "I'd like to try that someday.", "언젠가 그거 해보고 싶어요.",
        (r"\b(?:i'd|i\s+would)\s+like\s+to\s+\w",),
    ),
    Expression(
        "a2-how-about", "A2", "How about ~?", "~는 어때요?",
        "How about Saturday morning?", "토요일 아침은 어때요?",
        (r"\bhow\s+about\s+\w",),
    ),
    Expression(
        "a2-good-at", "A2", "I'm good at ~", "~를 잘해요",
        "I'm good at remembering names.", "저는 이름 기억하는 걸 잘해요.",
        (r"\b(?:i'm|i\s+am|im)\s+" + _DEGREE + r"good\s+at\b",),
    ),
    Expression(
        "a2-a-lot-of", "A2", "There's a lot of ~", "~가 많아요",
        "There's a lot of homework this week.", "이번 주에 숙제가 많아요.",
        (r"\bthere(?:'s|\s+is|\s+are|'re)\s+(?:a\s+lot|lots)\s+of\b",),
    ),
    Expression(
        "a2-lets", "A2", "Let's ~", "~하자",
        "Let's talk about something fun.", "재미있는 얘기 하자.",
        # Bare "lets" is a different verb ("she lets me drive"), so accept it
        # only where a sentence starts.
        (r"\blet's\s+\w", r"(?:^|[.?!,]\s*)lets\s+\w"),
    ),
    Expression(
        "a2-want-to-try", "A2", "I want to try ~", "~해보고 싶어요",
        "I want to try cooking Italian food.", "이탈리아 음식 만들어보고 싶어요.",
        (r"\bi\s+want\s+to\s+try\b",),
    ),
    Expression(
        "a2-kind-of", "A2", "It's kind of ~", "좀 ~해요",
        "It's kind of cold today.", "오늘 좀 추워요.",
        (r"\b(?:it'?s|it\s+is|that'?s|that\s+is)\s+kind\s+of\b",),
    ),
    Expression(
        "a2-usually", "A2", "I usually ~", "보통 ~해요",
        "I usually wake up at seven.", "저는 보통 일곱 시에 일어나요.",
        (r"\bi\s+usually\s+\w",),
    ),
    Expression(
        "a2-maybe-should", "A2", "Maybe I should ~", "~해야 할지도요",
        "Maybe I should go to bed earlier.", "더 일찍 자야 할지도요.",
        (r"\bmaybe\s+i\s+should\b",),
    ),
    Expression(
        "a2-not-sure", "A2", "I'm not sure", "잘 모르겠어요",
        "I'm not sure about that.", "그건 잘 모르겠어요.",
        (r"\b(?:i'm|i\s+am|im)\s+not\s+(?:really\s+|so\s+)?sure\b",),
    ),
    Expression(
        "a2-favorite", "A2", "my favorite ~", "제가 제일 좋아하는 ~",
        "Pizza is my favorite food.", "피자가 제가 제일 좋아하는 음식이에요.",
        (r"\bmy\s+favorite\b",),
    ),
    Expression(
        "a2-little-bit", "A2", "a little bit", "조금",
        "I'm a little bit tired.", "저는 조금 피곤해요.",
        (r"\ba\s+little\s+bit\b",),
    ),

    # --- B1 -----------------------------------------------------------------
    Expression(
        "b1-into", "B1", "I'm into ~", "~에 푹 빠져 있어요",
        "I'm really into indie music lately.", "요즘 인디 음악에 푹 빠져 있어요.",
        (r"\b(?:i'm|i\s+am|im)\s+" + _DEGREE + r"into\s+\w",),
    ),
    Expression(
        "b1-not-my-thing", "B1", "It's not my thing", "제 취향은 아니에요",
        "Horror movies aren't really my thing.", "공포 영화는 제 취향이 아니에요.",
        (r"\b(?:not|isn'?t|aren'?t|wasn'?t)\s+(?:really\s+|quite\s+|exactly\s+)?my\s+thing\b",),
    ),
    Expression(
        "b1-rather", "B1", "I'd rather ~", "차라리 ~하는 게 좋아요",
        "I'd rather stay home tonight.", "오늘 밤은 차라리 집에 있는 게 좋아요.",
        (r"\b(?:i'd|i\s+would)\s+rather\b",),
    ),
    Expression(
        "b1-end-up", "B1", "end up ~ing", "결국 ~하게 되다",
        "I ended up watching three episodes.", "결국 세 편을 보게 됐어요.",
        (r"\bend(?:s|ed|ing)?\s+up\s+\w",),
    ),
    Expression(
        "b1-looking-forward", "B1", "I'm looking forward to ~", "~가 기대돼요",
        "I'm looking forward to the weekend.", "주말이 기대돼요.",
        (r"\b(?:i'm|i\s+am|im)\s+looking\s+forward\s+to\b",),
    ),
    Expression(
        "b1-thinking-of", "B1", "I'm thinking of ~ing", "~할까 생각 중이에요",
        "I'm thinking of learning the guitar.", "기타를 배울까 생각 중이에요.",
        (r"\b(?:i'm|i\s+am|im)\s+thinking\s+(?:of|about)\s+\w+ing\b",),
    ),
    Expression(
        "b1-to-be-honest", "B1", "to be honest", "솔직히 말하면",
        "To be honest, I forgot about it.", "솔직히 말하면 깜빡했어요.",
        (r"\bto\s+be\s+honest\b",),
    ),
    Expression(
        "b1-big-deal", "B1", "a big deal", "대단한 일",
        "It's not a big deal, really.", "진짜 별일 아니에요.",
        (r"\ba\s+big\s+deal\b",),
    ),
    Expression(
        "b1-get-used-to", "B1", "get used to ~", "~에 익숙해지다",
        "I'm getting used to the new schedule.", "새 일정에 익숙해지고 있어요.",
        (r"\b(?:get|gets|got|getting|gotten)\s+used\s+to\b",),
    ),
    Expression(
        "b1-feel-like", "B1", "I feel like ~", "~인 것 같아요",
        "I feel like I need a break.", "쉬어야 할 것 같아요.",
        (r"\bi\s+feel\s+like\b",),
    ),
    Expression(
        "b1-used-to", "B1", "I used to ~", "전에는 ~했어요",
        "I used to play the piano.", "전에는 피아노를 쳤어요.",
        # "get used to"(b1-get-used-to)와 섞이지 않게 주어를 고정한다.
        (r"\bi\s+used\s+to\s+\w",),
    ),
    Expression(
        "b1-trying-to", "B1", "I'm trying to ~", "~하려고 노력 중이에요",
        "I'm trying to read more books.", "책을 더 읽으려고 노력 중이에요.",
        (r"\b(?:i'm|i\s+am|im)\s+trying\s+to\b",),
    ),

    # --- B2 -----------------------------------------------------------------
    Expression(
        "b2-torn-between", "B2", "I'm torn between ~", "~사이에서 고민 중이에요",
        "I'm torn between the two offers.", "두 제안 사이에서 고민 중이에요.",
        (r"\b(?:i'm|i\s+am|im)\s+torn\s+between\b",),
    ),
    Expression(
        "b2-grew-on-me", "B2", "It grew on me", "점점 좋아졌어요",
        "I hated the song, but it grew on me.", "그 노래 싫었는데 점점 좋아졌어요.",
        (r"\bgr(?:ew|own|ows|owing)\s+on\s+me\b",),
    ),
    Expression(
        "b2-cant-help", "B2", "I can't help ~ing", "~하지 않을 수 없어요",
        "I can't help laughing at that.", "그건 웃지 않을 수 없어요.",
        (r"\b(?:can'?t|cannot|couldn'?t)\s+help\s+\w+ing\b",),
    ),
    Expression(
        "b2-big-fan", "B2", "I'm a big fan of ~", "~를 엄청 좋아해요",
        "I'm a big fan of rainy mornings.", "비 오는 아침을 엄청 좋아해요.",
        (r"\ba\s+big\s+fan\s+of\b",),
    ),
    Expression(
        "b2-worth", "B2", "It's worth ~ing", "~할 만해요",
        "The trip is worth taking.", "그 여행은 가볼 만해요.",
        (r"\bworth\s+\w+ing\b",),
    ),
    Expression(
        "b2-id-say", "B2", "I'd say ~", "~라고 보는 편이에요",
        "I'd say it's about an hour away.", "한 시간쯤 걸린다고 보면 돼요.",
        (r"\b(?:i'd|i\s+would)\s+say\b",),
    ),
    Expression(
        "b2-more-often-than-not", "B2", "more often than not", "대개",
        "More often than not, I skip breakfast.", "대개 아침을 건너뛰어요.",
        (r"\bmore\s+often\s+than\s+not\b",),
    ),
    Expression(
        "b2-for-granted", "B2", "take ~ for granted", "~를 당연하게 여기다",
        "I took my free time for granted.", "여유 시간을 당연하게 여겼어요.",
        (r"\bfor\s+granted\b",),
    ),
    Expression(
        "b2-not-big-on", "B2", "I'm not big on ~", "~를 별로 안 좋아해요",
        "I'm not big on spicy food.", "매운 음식은 별로 안 좋아해요.",
        (r"\b(?:i'm|i\s+am|im)\s+not\s+" + _DEGREE + r"big\s+on\b",),
    ),
    Expression(
        "b2-hard-time", "B2", "have a hard time ~ing", "~하는 데 애를 먹다",
        "I had a hard time falling asleep.", "잠드는 데 애를 먹었어요.",
        (r"\b(?:have|has|had|having)\s+a\s+(?:hard|tough)\s+time\b",),
    ),
    Expression(
        "b2-tend-to", "B2", "I tend to ~", "~하는 편이에요",
        "I tend to stay up too late.", "너무 늦게까지 안 자는 편이에요.",
        (r"\bi\s+tend\s+to\b",),
    ),
    Expression(
        "b2-makes-my-day", "B2", "It makes my day", "그거면 하루가 좋아져요",
        "A good coffee makes my day.", "좋은 커피 한 잔이면 하루가 좋아져요.",
        (r"\bma(?:ke|kes|de)\s+my\s+day\b",),
    ),

    # --- C1 -----------------------------------------------------------------
    Expression(
        "c1-inclined", "C1", "I'm inclined to ~", "~하는 쪽으로 기울어요",
        "I'm inclined to agree with you.", "당신 말에 동의하는 쪽으로 기울어요.",
        (r"\b(?:i'm|i\s+am|im)\s+inclined\s+to\b",),
    ),
    Expression(
        "c1-hindsight", "C1", "in hindsight", "지나고 보니",
        "In hindsight, I should have asked.", "지나고 보니 물어봤어야 했어요.",
        (r"\b(?:in|with)\s+hindsight\b",),
    ),
    Expression(
        "c1-boils-down", "C1", "It boils down to ~", "결국 ~로 귀결돼요",
        "It all boils down to practice.", "결국 다 연습으로 귀결돼요.",
        (r"\bboils?\s+down\s+to\b",),
    ),
    Expression(
        "c1-soft-spot", "C1", "I have a soft spot for ~", "~에는 좀 약해요",
        "I have a soft spot for old bookshops.", "오래된 서점에는 좀 약해요.",
        (r"\ba\s+soft\s+spot\s+for\b",),
    ),
    Expression(
        "c1-by-and-large", "C1", "by and large", "대체로",
        "By and large, the plan worked.", "대체로 그 계획은 잘 됐어요.",
        (r"\bby\s+and\s+large\b",),
    ),
    Expression(
        "c1-fine-line", "C1", "a fine line between ~", "~사이의 경계가 미묘해요",
        "There's a fine line between confident and rude.", "자신감과 무례함 사이의 경계는 미묘해요.",
        (r"\ba\s+(?:fine|thin)\s+line\s+between\b",),
    ),
    Expression(
        "c1-second-nature", "C1", "It's second nature to me", "이젠 몸에 익었어요",
        "Early mornings are second nature to me now.", "이른 아침은 이젠 몸에 익었어요.",
        (r"\bsecond\s+nature\b",),
    ),
    Expression(
        "c1-at-the-expense", "C1", "at the expense of ~", "~를 희생해서",
        "I finished it at the expense of sleep.", "잠을 희생해서 끝냈어요.",
        (r"\bat\s+the\s+expense\s+of\b",),
    ),
    Expression(
        "c1-mixed-bag", "C1", "It's a mixed bag", "좋은 점도 나쁜 점도 있어요",
        "The reviews were a mixed bag.", "리뷰는 좋은 것도 나쁜 것도 있었어요.",
        (r"\ba\s+mixed\s+bag\b",),
    ),
    Expression(
        "c1-put-my-finger", "C1", "I can't put my finger on it", "뭔지 딱 집어 말하기 어려워요",
        "Something felt off, but I can't put my finger on it.", "뭔가 이상했는데 딱 집어 말하기 어려워요.",
        (r"\bput\s+my\s+finger\s+on\s+it\b",),
    ),
    Expression(
        "c1-partial-to", "C1", "I'm partial to ~", "~쪽을 더 좋아해요",
        "I'm partial to quiet weekends.", "조용한 주말 쪽을 더 좋아해요.",
        (r"\b(?:i'm|i\s+am|im)\s+partial\s+to\b",),
    ),
    Expression(
        "c1-on-the-fence", "C1", "I'm on the fence about ~", "~에 대해 아직 결정을 못 했어요",
        "I'm still on the fence about moving.", "이사 문제는 아직 결정을 못 했어요.",
        (r"\bon\s+the\s+fence\b",),
    ),
)

_BY_ID = {expr.id: expr for expr in EXPRESSIONS}
_BY_LEVEL = {
    level: tuple(e for e in EXPRESSIONS if e.level == level) for level in LEVELS
}
# Compiled once at import; the matcher runs on every user turn.
_COMPILED = {expr.id: expr.compiled() for expr in EXPRESSIONS}

# Straight-quote the apostrophes STT and keyboards produce, so one pattern per
# expression covers every spelling of "I'm".
_APOSTROPHES = str.maketrans({"’": "'", "ʼ": "'", "`": "'", "´": "'"})


def for_level(level: str) -> tuple:
    """Expressions available at `level`, falling back to B1 for unknown input."""
    return _BY_LEVEL.get(level) or _BY_LEVEL["B1"]


def by_id(expr_id: str) -> Optional[Expression]:
    return _BY_ID.get(expr_id)


def pick_for_day(user_id: str, date_kst: str, level: str) -> Expression:
    """The expression for one user on one day.

    The level's list is ordered once per user, then walked by date, so each
    expression gets its turn before any repeats and two users on the same day
    are usually on different ones.
    """
    pool = for_level(level)
    ordered = sorted(
        pool,
        key=lambda e: hashlib.sha256(f"{user_id}:{e.id}".encode()).hexdigest(),
    )
    day = _date.fromisoformat(date_kst).toordinal()
    return ordered[day % len(ordered)]


def normalize(text: str) -> str:
    """The form `patterns` are written against: lowercase, plain apostrophes,
    single spaces. Punctuation stays, because the patterns rely on word
    boundaries rather than on stripping it."""
    return " ".join((text or "").translate(_APOSTROPHES).lower().split())


def matches(expr: Expression, text: str) -> bool:
    """Did this utterance use the expression's core structure."""
    haystack = normalize(text)
    if not haystack:
        return False
    return any(p.search(haystack) for p in _COMPILED[expr.id])


def opener_rule(expr: Expression) -> str:
    """The opener prompt line that makes Pally model the day's expression.

    The expression goes in the opener, not in mid-conversation turns. Injected
    into a turn it did reach the reply (7 of 8 live calls against 1 of 8
    without), but it arrived off-topic: the user said they listen to music
    every day and Pally answered "It depends on my mood." The opener has no
    topic to contradict yet - it is the turn that chooses the topic - so the
    expression can lead instead of being squeezed in.

    The rule also asks for a question the same expression answers, so the user
    hears the structure and is immediately invited to use it.
    """
    return (
        f'- Use the expression "{expr.text}" in your opener, as something true '
        f'about yourself, with "~" filled in to fit the topic. Then ask your '
        f'question so the user could answer with that same expression. Never '
        f'explain or quote it as a phrase to learn - just say it, and never '
        f'write the "~" character itself. The sentence and word limits above '
        f'win over this rule.'
    )
