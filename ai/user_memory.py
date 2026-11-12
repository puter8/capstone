"""Extract durable facts about the user from one finished conversation.

Model output is never trusted as-is. Two guards run on every fact:

1. `key` is constrained to ALLOWED_KEYS by the response schema AND re-checked
   here. Real calls showed a prompt alone does not hold: with the categories
   open, gemini-2.5-flash-lite stored `health_condition: depression` on 5 of 5
   runs despite the prompt forbidding health information. A closed key list
   leaves no category for it.
2. `quote` must appear word for word in the user's own turns. This is what
   catches a fabricated fact and, just as important, a fact taken from Pally's
   side of the conversation ("I have a cat named Mochi" is Pally's cat).
   Same idea as ai.generate_feedback._ground_feedback.

Facts are extracted after a conversation ends, so nothing here runs inside a
turn. gemini-2.5-flash-lite is used rather than -flash: measured over 5 runs
per case, -flash stored a city the user had only visited (5/5) and attributed a
sister's job to the user, while -flash-lite was stable and did neither.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading

import httpx

MODEL = "gemini-2.5-flash-lite"
DEFAULT_TIMEOUT_S = 20.0
_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

# A closed set. Nothing here can hold a health condition, religion, political
# view or income, so the extractor has nowhere to put one.
ALLOWED_KEYS = (
    "name", "age", "city", "occupation", "workplace", "field_of_study", "school",
    "school_year", "family", "pet", "hobby", "skill", "language", "plan",
)

# Keys where a newer fact replaces the older one instead of adding to it: a
# person has one city, but can have several hobbies.
SINGLE_VALUED = frozenset({
    "name", "age", "city", "occupation", "workplace", "field_of_study", "school",
    "school_year",
})

MAX_VALUE_CHARS = 200
# How many facts Pally is told about. The reply is capped at 90 characters, so a
# long list only dilutes the prompt; the newest facts are the ones that matter.
MAX_PROMPT_FACTS = 8

_SYSTEM_PROMPT = """\
You extract durable facts about the USER from one finished English-practice conversation.

Record ONLY facts the user stated about themselves or their life. A fact is durable:
it would still be true weeks from now.

Do NOT record:
- anything Pally said. Pally's hobbies, pets and opinions are not the user's.
- opinions or judgements ("winter is the worst season"), and feelings.
- today's mood or one-off events ("I'm tired", "I slept four hours", "I went to Busan last weekend").
- anything the user denied. "I don't have a cat" and "I don't play any instrument"
  are not facts; skip them entirely rather than recording the absence.
- wishes and hypotheticals ("if I lived alone", "I want to get a cat").
- health, medication, medical visits, religion, politics, sexual orientation, income.

Write "value" as a short noun phrase, not a sentence: "two dogs, Kongi and Bori",
never "I have two dogs." Do not start a value with "I".

Keep the specifics. Names of pets, family members, schools, companies and places
belong in the value: "two dogs, Kongi and Bori", not "dogs". A fact without its
name is not worth remembering.

Only record where the user LIVES, never a place they visited or travelled to.
Do not infer one fact from another; if the user never said it, it is not a fact.

The user is a learner, so their English has mistakes. Extract the meaning, and write
the value in correct, short English.

For every fact, "quote" must be copied WORD FOR WORD from one of the user's turns.
Never quote Pally. Never reword the quote. If you cannot quote the user verbatim,
do not output that fact.

Output nothing when the conversation holds no durable fact about the user.
"""

_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "enum": list(ALLOWED_KEYS),
                            "description": "which kind of fact this is"},
                    "value": {"type": "string", "description": "short correct English"},
                    "quote": {"type": "string", "description": "verbatim from a user turn"},
                },
                "required": ["key", "value", "quote"],
            },
        }
    },
    "required": ["facts"],
}

# One client per process, for the same reason as ai.opener: a fresh client per
# call rebuilds the SSL context and redoes the TLS handshake.
_client: httpx.Client | None = None
_client_lock = threading.Lock()

_WORD = re.compile(r"[a-z0-9']+")


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = httpx.Client(timeout=DEFAULT_TIMEOUT_S)
    return _client


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _contains_span(haystack: list[str], needle: list[str]) -> bool:
    if not needle:
        return False
    return any(haystack[i:i + len(needle)] == needle
               for i in range(len(haystack) - len(needle) + 1))


def _call_gemini(conversation: str, timeout: float) -> list:
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_AI_API_KEY not configured")
    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": conversation}]}],
        "generationConfig": {
            # Deterministic: the same conversation must not yield a different
            # set of facts on a retry.
            "temperature": 0.0,
            "maxOutputTokens": 1024,
            "thinkingConfig": {"thinkingBudget": 0},
            "responseMimeType": "application/json",
            "responseSchema": _SCHEMA,
        },
    }
    # Key in a header, not the URL, so httpx error text never carries it.
    resp = _get_client().post(_URL, headers={"x-goog-api-key": api_key},
                              json=payload, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini memory extraction error {resp.status_code}")
    candidate = resp.json()["candidates"][0]
    reason = candidate.get("finishReason")
    if reason not in (None, "STOP"):
        raise RuntimeError(f"Gemini memory extraction stopped: {reason}")
    text = "".join(part["text"] for part in candidate["content"]["parts"]
                   if not part.get("thought", False))
    facts = json.loads(text)["facts"]
    if not isinstance(facts, list):
        raise RuntimeError("Gemini memory extraction returned a non-list")
    return facts


def ground_facts(facts: list, turns: list) -> list:
    """Keep the facts the user actually said, in the order the model gave them.

    A bad item is dropped, not raised on: one unusable fact in an otherwise good
    answer should not throw the conversation's whole memory away. Every drop is
    logged with its reason so the rate stays visible.
    """
    user_words = _words(" ".join(text for role, text in turns if role == "user"))
    kept: list = []
    seen: set = set()
    for fact in facts:
        if not isinstance(fact, dict):
            logging.warning("Memory fact skipped: not an object")
            continue
        key, value, quote = fact.get("key"), fact.get("value"), fact.get("quote")
        if key not in ALLOWED_KEYS:
            logging.warning("Memory fact skipped: key outside the allowed list")
            continue
        if not isinstance(value, str) or not value.strip():
            logging.warning("Memory fact skipped (%s): empty value", key)
            continue
        value = value.strip()[:MAX_VALUE_CHARS]
        if not isinstance(quote, str) or not _contains_span(user_words, _words(quote)):
            # Either invented, or taken from Pally's side of the conversation.
            logging.warning("Memory fact skipped (%s): quote not in the user's turns", key)
            continue
        identity = (key, value.lower())
        if identity in seen:
            continue
        seen.add(identity)
        kept.append({"key": key, "value": value})
    return kept


def extract_user_facts(turns: list, timeout: float = DEFAULT_TIMEOUT_S) -> list:
    """Facts the user stated about themselves, as [{"key", "value"}, ...].

    `turns` is [(role, transcript)] in conversation order, roles "user"/"pally".
    Returns [] when the conversation holds nothing durable. Raises on provider
    failure so the caller can retry; it never substitutes invented facts.
    """
    if not any(role == "user" and text and text.strip() for role, text in turns):
        return []
    conversation = "\n".join(
        f"{'User' if role == 'user' else 'Pally'}: {text}" for role, text in turns if text)
    return ground_facts(_call_gemini(conversation, timeout), turns)


def memory_prompt(facts: list, limit: int = MAX_PROMPT_FACTS):
    """The block injected into the chat system prompt, or None when empty.

    `facts` is newest first; single-valued keys keep only their newest value so
    a changed major or city does not appear twice with conflicting answers.
    """
    lines: list = []
    used: set = set()
    for fact in facts:
        key, value = fact["key"], fact["value"]
        if key in SINGLE_VALUED:
            if key in used:
                continue
            used.add(key)
        lines.append(f"- {key.replace('_', ' ')}: {value}")
        if len(lines) >= limit:
            break
    if not lines:
        return None
    # The "these are theirs, not yours" rule is not decoration. Without it,
    # measured live, Pally spoke of the user's dogs as its own ("Kongi and Bori
    # love morning walks!", "I love taking my dogs out!") because the reply
    # contract has a field for Pally's own remark and the facts leaked into it.
    # The positive rule goes last, nearest the reply. With the "say you do not
    # remember" clause last instead, Pally answered "I don't remember where you
    # live!" on 2 of 3 live runs while the city was sitting in the list above it.
    return ("## What you already know about the user, told to you in earlier chats\n"
            + "\n".join(lines)
            + "\n\nThese facts are the USER's, never yours: never speak of them as your own,\n"
            "and do not bring them up unprompted. Never read the list out. If they ask about\n"
            "something that is NOT listed above, say you do not remember instead of guessing.\n"
            "But everything listed above you DO remember: when they ask about their age, where\n"
            "they live, their pet's name or anything else on that list, answer it directly.\n"
            "Never ask them for something the list already tells you.")


__all__ = ["extract_user_facts", "ground_facts", "memory_prompt", "ALLOWED_KEYS",
           "SINGLE_VALUED", "MAX_VALUE_CHARS", "MAX_PROMPT_FACTS", "MODEL"]
