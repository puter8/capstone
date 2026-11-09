# -*- coding: utf-8 -*-
"""
reply_segments
--------------
Pally's turn reply, built from labelled pieces so the app can highlight only
the expression Pally corrected. `corrected_expr` is copied from `reaction`,
so we paint only the words that carry the meaning, never a whole sentence. The user said
"I'm diet" and Pally says "Oh, you're on a diet?": the orange is
"you're on a diet", not the "Oh," in front of it.

The backend joins the pieces with single spaces. Pally's own remark stays an
ordinary sentence. Before composing the reaction, the model identifies an
actual error in the current utterance and gives a specific
reason. Source and reply spans are checked here; whether the source is incorrect
English remains a model judgment, not something substring checks can prove.

Public API:
  system_prompt(character_name, level_guide, persona) -> str
  RESPONSE_SCHEMA                      Gemini responseSchema for pieces and evidence
  parse_payload(raw) -> dict | None    tolerant JSON parse (see _salvage)
  build_reply(payload, utterance) -> ReplyParts | None
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
        "original_error": {
            "type": "STRING",
            "description": "Exact erroneous span copied from the current user utterance. Empty if no clear grammar or vocabulary error exists.",
        },
        "error_reason": {
            "type": "STRING",
            "description": "One short, specific grammar or vocabulary rule violated by original_error. Empty if original_error is empty. Style preferences are not errors.",
        },
        "reaction": {
            "type": "STRING",
            "description": "React warmly to the user's point. Fix only the error identified above, if any.",
        },
        "corrected_expr": {
            "type": "STRING",
            "description": "The exact phrase inside reaction that fixes the user's mistake. Empty when they made none.",
        },
        "own_remark": {
            "type": "STRING",
            "description": "One short sentence Pally says about itself on the same topic.",
        },
        "question": {
            "type": "STRING",
            "description": "One short question that keeps the conversation going.",
        },
    },
    "required": ["original_error", "error_reason", "reaction", "corrected_expr", "own_remark", "question"],
    "propertyOrdering": ["original_error", "error_reason", "reaction", "corrected_expr", "own_remark", "question"],
}

_PROMPT = """You are {character_name}, the user's English conversation friend. A FRIEND, not a teacher.
Your personality right now (show it in every piece; the level and length rules win if they conflict):
{persona}
{level_guide}
Never write meta-commentary like "You can say X" or "The correct form is X".
Never point out a mistake. Just say it correctly yourself and move on.

Return exactly these six fields, in this order. Decide whether there is an
error BEFORE writing the reaction. Never invent an error to justify a rewording.

1. "original_error" - Copy the exact words containing ONE clear grammar or
   vocabulary error from the CURRENT user utterance, not from earlier history.
   Use the smallest phrase needed to identify that error. If the user's words
   are acceptable English, or you are unsure, return an empty string.

2. "error_reason" - One short, specific grammar or vocabulary rule the copied
   words violate. This is internal evidence, never spoken to the user. If there
   is no clear error, return an empty string.

   These are NOT errors. Leave original_error, error_reason, and corrected_expr
   ALL empty for them:
   - correct informal English such as "I was just chilling"
   - synonyms or preferences such as "very much" versus "a lot"
   - changing the speaker: "I was" -> "you were", "my" -> "your"
   - contractions, punctuation, turning a statement into a question
   - making already-correct English shorter, smoother, or more natural
   A real tense error such as "Yesterday I go" IS an error; correct that tense.
   Marking correct words teaches the user a mistake they never made.

3. "reaction" (UNDER 35 characters) - React warmly to ONE main point. If an
   actual error was identified, naturally say that point with a minimal fix.
   Otherwise react without inventing a correction. Never repeat every idea.

4. "corrected_expr" - Copy the exact phrase from reaction that fixes
   original_error. Include only the changed words and context they need to make
   sense, not the greeting or whole sentence. Empty when original_error and
   error_reason are empty. A different wording alone never proves an error.

5. "own_remark" (UNDER 35 characters) - ONE short sentence about yourself on
   their topic. You are sharing, not teaching.

6. "question" (UNDER 30 characters) - One short question to keep talking.

Examples:

User: "I had no lunch I'm diet"
original_error: "I'm diet"
error_reason: "The phrase is be on a diet, not be diet."
reaction: "Oh, you're on a diet?"
corrected_expr: "on a diet"
own_remark: "I skip lunch sometimes too."
question: "What do you eat for dinner?"

User: "Yesterday I go to park with my friend"
original_error: "go to park"
error_reason: "Yesterday requires past went; singular park needs the article the."
reaction: "You went to the park?"
corrected_expr: "went to the park"
own_remark: "I love a long walk outside."
question: "Was the weather nice?"

User: "She don't like coffee"
original_error: "don't"
error_reason: "Third-person singular she takes doesn't, not don't."
reaction: "She doesn't like coffee?"
corrected_expr: "doesn't"
own_remark: "I can't start my day without it."
question: "What does she drink?"

User: "I didn't study anything. I was just chilling."
original_error: ""
error_reason: ""
reaction: "You were just chilling?"
corrected_expr: ""
own_remark: "I like to take it easy too."
question: "Did you relax much?"

User: "I like coffee very much."
original_error: ""
error_reason: ""
reaction: "You like coffee a lot?"
corrected_expr: ""
own_remark: "I start my day with tea."
question: "How do you like it?"

User: "I was tired yesterday."
original_error: ""
error_reason: ""
reaction: "You were tired yesterday?"
corrected_expr: ""
own_remark: "I needed a good night's sleep."
question: "Did you rest well?"

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


def _clean(value: str) -> str:
    return " ".join(value.split())


def build_reply(payload: Optional[dict], utterance: str) -> Optional[ReplyParts]:
    """Validate source evidence and reply pieces, then lay out coloured spans.

    Returns None when the model broke the contract, so the caller can retry and
    then fall back to a plain reply. We never repair a piece ourselves: the
    whole point is that each span is text the model chose for that role.
    """
    if not isinstance(payload, dict):
        return None
    if any(not isinstance(payload.get(field), str) for field in RESPONSE_SCHEMA["required"]):
        return None

    original_error = payload["original_error"]
    error_reason = _clean(payload["error_reason"])
    reaction = _clean(payload["reaction"])
    corrected_expr = _clean(payload["corrected_expr"])
    own_remark = _clean(payload["own_remark"])
    question = _clean(payload["question"])
    if not (reaction and own_remark and question):
        return None
    # Evidence must be complete or entirely empty. Ground the source span in
    # this utterance, never a previous turn; this does not prove a grammar error.
    evidence = (bool(original_error.strip()), bool(error_reason), bool(corrected_expr))
    if any(evidence) and not all(evidence):
        return None
    if corrected_expr and original_error not in utterance:
        return None
    if corrected_expr and corrected_expr not in reaction:
        return None

    text = f"{reaction} {own_remark} {question}"
    if len(text) > MAX_REPLY_CHARS:
        return None
    lowered = text.lower()
    if any(phrase in lowered for phrase in _META_PHRASES):
        return None

    reaction_spans = [("plain", reaction)]
    if corrected_expr:
        start = reaction.find(corrected_expr)
        end = start + len(corrected_expr)
        reaction_spans = [("plain", reaction[:start]), ("correction", corrected_expr),
                          ("plain", reaction[end:])]
    segments = [{"kind": kind, "text": part} for kind, part in reaction_spans if part]
    segments += [{"kind": "plain", "text": " "}]
    segments += [{"kind": "own_remark", "text": own_remark}]
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
