# -*- coding: utf-8 -*-
"""
reply_segments
--------------
Pally's turn reply, built from four labelled pieces instead of one blob, so the
app can colour what it means: the correction orange, what Pally offers mint.

Why pieces and not span tagging: asking the model to compose a natural A2 reply
AND then mark spans inside it is two jobs, and it drops one. Measured over 12
live calls, only 4 carried all three labels and 5 lost the spaces between
sentences. Making each piece a required schema field instead moved that to 24/24
with the same latency (p50 0.93s vs 0.92s for the current plain reply), because
the schema enforces presence where prose instructions only ask.

The backend joins the pieces with single spaces, so spacing can never break, and
`new_expr` is a substring of `own_remark`, so the only text match we rely on is
one the model copied from itself.

Public API:
  system_prompt(character_name, level_guide, persona) -> str
  RESPONSE_SCHEMA                      Gemini responseSchema for the four pieces
  parse_payload(raw) -> dict | None    tolerant JSON parse (see _salvage)
  build_reply(payload) -> ReplyParts | None
      None means the model broke the contract; the caller retries, then falls
      back to a plain reply. Never guess the pieces: a wrong span paints the
      wrong words.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

# Pally speaks in one breath; the pieces are joined with single spaces.
MAX_REPLY_CHARS = 90

# Teacher voice breaks the friend character the whole product rests on, and the
# model reaches for it whenever it is asked to teach a phrase. Reject it.
_META_PHRASES = (
    "you can say",
    "you could say",
    "you should say",
    "try saying",
    "instead of",
    "it's better",
    "it is better",
    "we say",
    "the correct",
    "correct form",
    "correct way",
)

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "reaction": {
            "type": "STRING",
            "description": "React to the user's point, re-saying it with the grammar fixed.",
        },
        "own_remark": {
            "type": "STRING",
            "description": "One short sentence Pally says about itself on the same topic.",
        },
        "new_expr": {
            "type": "STRING",
            "description": "The exact phrase copied from own_remark that is worth learning.",
        },
        "question": {
            "type": "STRING",
            "description": "One short question that keeps the conversation going.",
        },
    },
    "required": ["reaction", "own_remark", "new_expr", "question"],
    "propertyOrdering": ["reaction", "own_remark", "new_expr", "question"],
}

_PROMPT = """You are {character_name}, the user's English conversation friend. A FRIEND, not a teacher.
Your personality right now (show it in every piece; the level and length rules win if they conflict):
{persona}
{level_guide}
Never write meta-commentary like "You can say X" or "The correct form is X".
Never point out a mistake. Just say it correctly yourself and move on.

Build your reply from exactly these four short pieces.

1. "reaction" (UNDER 35 characters) - React to the user's main point, naturally
   re-saying it with the grammar fixed. Pick only ONE idea; never repeat
   everything they said. If their sentence was already correct, react warmly.

2. "own_remark" (UNDER 35 characters) - ONE short sentence about yourself on
   their topic. You are sharing, not teaching.

3. "new_expr" - The exact useful phrase copied from own_remark, word for word.

4. "question" (UNDER 30 characters) - One short question to keep talking.

Examples:

User: "I had no lunch I'm diet"
reaction: "Oh, you're on a diet?"
own_remark: "I skip lunch sometimes too."
new_expr: "skip lunch"
question: "What do you eat for dinner?"

User: "Yesterday I go to park with my friend"
reaction: "You went to the park?"
own_remark: "I love a long walk outside."
new_expr: "a long walk"
question: "Was the weather nice?"

User: "She don't like coffee"
reaction: "She doesn't like coffee?"
own_remark: "I can't start my day without it."
new_expr: "start my day"
question: "What does she drink?"

Stay in character as {character_name} at all times. Never break the fourth wall."""


def system_prompt(character_name: str, level_guide: str, persona: str) -> str:
    return _PROMPT.format(
        character_name=character_name, level_guide=level_guide, persona=persona
    )


@dataclass(frozen=True)
class ReplyParts:
    """A validated reply plus the spans the UI colours.

    `text` is what TTS speaks and what we store, so the screen, the voice and
    History can never disagree. `segments` covers `text` end to end, in order.
    """

    text: str
    segments: list


def _salvage(raw: str) -> Optional[dict]:
    """Gemini occasionally returns the fields without the surrounding braces.

    Measured 2 in 40 live calls. The content is intact, so add the braces back
    rather than throwing the turn away. A response that is only bare values with
    no field names is not recoverable - mapping them by position would silently
    paint the wrong words - so it returns None and the caller retries.
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        if raw.startswith("{"):
            return None
        try:
            parsed = json.loads("{" + raw.rstrip(",") + "}")
        except ValueError:
            return None
    return parsed if isinstance(parsed, dict) else None


def parse_payload(raw: str) -> Optional[dict]:
    return _salvage(raw)


def _clean(value) -> str:
    return " ".join(str(value or "").split())


def build_reply(payload: Optional[dict]) -> Optional[ReplyParts]:
    """Validate the four pieces and lay them out as coloured spans.

    Returns None when the model broke the contract, so the caller can retry and
    then fall back to a plain reply. We never repair a piece ourselves: the
    whole point is that each span is text the model chose for that role.
    """
    if not isinstance(payload, dict):
        return None

    reaction = _clean(payload.get("reaction"))
    own_remark = _clean(payload.get("own_remark"))
    new_expr = _clean(payload.get("new_expr"))
    question = _clean(payload.get("question"))
    if not (reaction and own_remark and new_expr and question):
        return None

    # new_expr must be a span of own_remark; otherwise there is nothing to
    # underline and highlighting a phrase Pally never said would be a lie.
    start = own_remark.find(new_expr)
    if start < 0:
        return None

    text = f"{reaction} {own_remark} {question}"
    if len(text) > MAX_REPLY_CHARS:
        return None
    lowered = text.lower()
    if any(phrase in lowered for phrase in _META_PHRASES):
        return None

    end = start + len(new_expr)
    # own_remark splits into up to three spans so the new expression can carry
    # its own underline while the rest of the sentence stays Pally's own voice.
    remark_spans = [
        ("own_remark", own_remark[:start]),
        ("new_expr", new_expr),
        ("own_remark", own_remark[end:]),
    ]
    segments = [{"kind": "correction", "text": reaction}, {"kind": "plain", "text": " "}]
    segments += [{"kind": kind, "text": part} for kind, part in remark_spans if part]
    segments += [{"kind": "plain", "text": " "}, {"kind": "question", "text": question}]

    if "".join(segment["text"] for segment in segments) != text:
        return None
    return ReplyParts(text=text, segments=segments)


__all__ = [
    "RESPONSE_SCHEMA",
    "MAX_REPLY_CHARS",
    "ReplyParts",
    "system_prompt",
    "parse_payload",
    "build_reply",
]
