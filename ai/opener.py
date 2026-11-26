# -*- coding: utf-8 -*-
"""
opener
------
Pally speaks first when a new conversation session starts. This module
writes that opener line (English, 1-2 sentences, ending with one question)
from the user's 5-axis personality and English level, while steering away
from topics of the user's recent sessions.

Public API:
  generate_opener(axes, level, recent_texts) -> str
      Raises OpenerRejected (log-safe `reason` code) when Gemini fails or the
      output breaks the opener rules, httpx errors on transport failure, and
      pydantic.ValidationError on invalid `axes`. No fallback text here: the
      caller decides what to do on failure. The caller owns retries.

`recent_texts`: texts from the user's recent sessions (openers + user
turns), NEWEST FIRST. Only used locally for keyword topic detection; it is
never sent to Gemini.
"""
from __future__ import annotations

import os
import random
import re
import threading

import httpx

from ai.contracts import AxisResult
from ai.conversation_rules import PALLY_IDENTITY, SAFETY_SETTINGS
from ai.tracing import gemini_generation, record_gemini_call
from ai.user_name import user_name_rule

# topic -> keywords that mark the topic as recently used (word-boundary match)
TOPICS: dict[str, tuple[str, ...]] = {
    "weekend plans": ("weekend", "weekends", "saturday", "sunday"),
    "food you ate recently": ("food", "eat", "ate", "eating", "lunch", "dinner", "breakfast", "snack"),
    "a show or movie": ("movie", "movies", "film", "show", "drama", "netflix", "series"),
    "music": ("music", "song", "songs", "playlist", "concert", "singer"),
    "friends": ("friend", "friends", "bestie"),
    "school or work": ("school", "class", "work", "job", "office", "exam", "homework"),
    "hobbies": ("hobby", "hobbies"),
    "travel": ("travel", "trip", "vacation", "flight"),
    "the weather today": ("weather", "rain", "raining", "sunny", "cold", "hot", "snow"),
    "a small happy moment": ("happy", "smile", "smiled"),
    "sleep and energy": ("sleep", "slept", "tired", "nap"),
    "shopping": ("shopping", "shop", "bought", "buy"),
    "pets or animals": ("pet", "pets", "dog", "dogs", "cat", "cats", "animal", "animals"),
    "sports or exercise": ("sport", "sports", "exercise", "gym", "soccer", "running", "workout"),
}

# level -> (guide, max_words). max_words is the hard validation cap; the prompt
# asks for PROMPT_WORD_MARGIN fewer because the model tends to overshoot.
# Unknown level falls back to B1 like _LEVEL_GUIDE in BE.
LEVEL_RULES: dict[str, tuple[str, int]] = {
    "A2": ("Use only very common, simple words (A2 beginner).", 12),
    "B1": ("Use everyday words (B1 intermediate).", 18),
    "B2": ("Use natural, varied phrasing (B2 upper-intermediate).", 22),
    "C1": ("Use rich, idiomatic phrasing (C1 advanced).", 26),
}
PROMPT_WORD_MARGIN = 4

MODEL = "gemini-2.5-flash-lite"
DEFAULT_TIMEOUT_S = 2.5  # per httpx phase; caller enforces any overall deadline
_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

# One client per process. A fresh client per call rebuilt its SSL context
# (~370ms locally) and redid the TLS handshake; reuse cut p50 from ~1.4s to
# ~0.9s, still true with 30s gaps between calls (after idle connections
# expire). httpx.Client is safe to share across the worker threads BE runs us
# in. It is never reset: closing it could break another thread's request.
_client: httpx.Client | None = None
_client_lock = threading.Lock()


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = httpx.Client(timeout=DEFAULT_TIMEOUT_S)
    return _client


_SYSTEM_PROMPT = """\
You are Pally, the user's English speaking buddy (a friend, NOT an assistant or teacher).
""" + PALLY_IDENTITY + """\
You speak first to open a new voice chat.

Your personality right now:
{persona}

Topic to open with: {topic}

Rules (the level rules win over the personality if they conflict):
- 1 or 2 short sentences, at most {max_words} words in total: at most one
  statement, then one question.
- {level_guide}
- End with a question the user can answer about their own life.
- English only. No emoji, no quotation marks.
- You know nothing about the user yet except their name: never refer to past chats or things they told you.
- Do not start with "Hello there". Never offer help ("How can I help/assist").
{name_rule}{expression_rule}Output only the opener. Nothing comes after its question: the last character is "?"."""

_WORD = re.compile(r"[A-Za-z0-9']+")
_SENTENCE = re.compile(r"[^.!?]+[.!?]+")
_HANGUL = re.compile(r"[가-힣ㄱ-ㆎ]")


class OpenerRejected(ValueError):
    """Gemini output violated the opener rules; `reason` is a log-safe code."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _band(value: int, low: str, mid: str, high: str) -> str:
    """Same cuts as the renderer's PallyCanvas `tier` (<=33 / <=66 / rest) and
    the My-page trait tags, so every surface bands an axis identically."""
    return low if value < 34 else mid if value < 67 else high


# Spoken sample words per band, appended to the band label as "(e.g. ...)".
# With labels alone, flash-lite gave the most formal and the most casual
# persona nearly the same reply, differing only in exclamation marks
# (2026-11-24 probe). persona_prompt shows a random few per call because the
# model copies whatever words it is shown: a fixed short list made every
# excited opener start with the same word. Rules for the pools:
# - spoken words only, since TTS reads the reply aloud;
# - no slang, for the same reason the low Formality band says "no slang";
# - no standalone sentences ("I would love to hear more", "That's amazing"):
#   the model used them as an extra sentence and broke the opener's sentence
#   and closing-question checks.
CUE_WORDS: dict[str, tuple[str, ...]] = {
    "relaxed": ("cool", "pretty good", "nice", "sounds fun", "not bad",
                "oh yeah", "fair enough", "got it", "makes sense"),
    "polite": ("That sounds lovely", "I see", "How nice", "How wonderful",
               "What a lovely idea", "How delightful", "I am glad to hear",
               "That must be nice"),
    "excited": ("Whoa", "Oh my gosh", "awesome", "Wow", "so cool", "amazing",
                "fantastic", "great"),
}
CUES_PER_PROMPT = 3


def _cues(band: str, rng: random.Random) -> str:
    words = ", ".join(f"'{w}'" for w in rng.sample(CUE_WORDS[band], CUES_PER_PROMPT))
    return f" (e.g. {words})"


def persona_prompt(axes: dict, rng: random.Random | None = None) -> str:
    """5 axes -> trait lines shared by the opener and the per-turn chat prompt.

    Banded on the raw axes, which is what the renderer and the trait tags band,
    so Pally's look and Pally's voice always come from the same number.

    Tone, Energy and Humor used to be banded on compute_character's weighted
    sums instead. Those pull hard toward the middle - two thirds of the axis
    space lands in the mid band - so the voice disagreed with the tag and the
    shape over a third of Humor's and Energy's range and two thirds of
    Formality's, whose derived `tone_casual` runs opposite to it. In practice a
    user tagged "ridiculous" kept hearing "lightly playful" until Humor hit
    100, and two learners with clearly different styles got four of five
    identical trait lines. compute_character still drives nothing here; it
    remains the renderer's and the analyzer's own mapping.
    """
    rng = rng or random.Random()
    return "\n".join([
        # Formality runs the other way from the rest: 0 is informal, 100 formal.
        # The low band says blunt, not slangy, to match the trait tag
        # ("blunt", "casual", "formal") and the renderer's plain dot eyes.
        # "very casual, slangy" belonged to the derived tone_casual's HIGH end;
        # carried onto raw Formality's low end it asked for American slang, and
        # a learner at Formality 30 got openers like "Yo dude! What's up with
        # your pals?" where they used to get "Hey! What music are you digging?".
        # Pally's line is the model the learner copies, so it stays teachable.
        # The blunt band gets a style, not sample words: a bare "Okay." or
        # "Sure." opening counts as an extra sentence in validate_opener.
        "- Tone: " + _band(
            axes["Formality"],
            "blunt and direct, no slang (short plain sentences, straight to the point)",
            "relaxed" + _cues("relaxed", rng),
            "polite and proper" + _cues("polite", rng),
        ),
        # "no exclamation marks" alone made the model drop the '?' too.
        "- Energy: " + _band(
            axes["Energy"],
            "calm and gentle (soft, even sentences, no exclamation marks; questions still end with '?')",
            "upbeat (positive, at most one exclamation mark)",
            "super excited" + _cues("excited", rng),
        ),
        "- Humor: " + _band(axes["Humor"], "sincere", "lightly playful", "goofy and teasing"),
        "- Closeness: " + _band(axes["Intimacy"], "friendly but a little reserved", "warm", "like a best friend"),
        "- Curiosity: " + _band(axes["Curiosity"], "simple, direct question", "interested question", "eager, specific question"),
        ("- Sample words: the quoted words show the style, they are not a script. Use at most"
         " one per reply, and never repeat a word or phrase you already said in this chat."),
    ])


def word_count(text: str) -> int:
    return len(_WORD.findall(text))


def _recent_topics(texts: list[str]) -> set[str]:
    blob = " ".join(texts).casefold()
    return {
        topic for topic, keywords in TOPICS.items()
        if any(re.search(rf"\b{re.escape(k)}\b", blob) for k in keywords)
    }


def _allowed(candidates: list[str], recent_texts: list[str]) -> list[str]:
    """Candidates not used in recent history; if all are used, forget the
    oldest history first until something becomes available."""
    for n in range(len(recent_texts), -1, -1):
        used = _recent_topics(recent_texts[:n])
        free = [c for c in candidates if c not in used]
        if free:
            return free
    return candidates


def pick_topic(recent_texts: list[str], rng: random.Random) -> str:
    return rng.choice(_allowed(list(TOPICS), recent_texts))


def validate_opener(text: str, max_words: int) -> str:
    text = text.strip().strip('"“”').strip()
    if word_count(text) < 3:
        raise OpenerRejected("too_short")
    if word_count(text) > max_words:
        raise OpenerRejected("too_long")
    if _HANGUL.search(text):
        raise OpenerRejected("non_english")
    # A tilde is never spoken English. It leaks in when a prompt rule shows an
    # expression with a "~" slot ("I'm into ~"): the model copied the marker
    # into the opener ("that makes sense~ What tunes..."), which TTS then reads
    # as a stumble. Reject so the caller's retry produces a clean line.
    if "~" in text:
        raise OpenerRejected("slot_marker")
    if not text.endswith("?"):
        raise OpenerRejected("no_closing_question")
    sentences = _SENTENCE.findall(text)
    # A leading interjection ("Hey!", "Yo, dude!") is not counted as a sentence.
    if len(sentences) > 1 and word_count(sentences[0]) <= 2 and sentences[0].endswith("!"):
        sentences = sentences[1:]
    if len(sentences) > 2:
        raise OpenerRejected("too_many_sentences")
    return text


def _extract_text(resp_json: dict) -> str:
    candidates = resp_json.get("candidates")
    if not candidates:
        raise OpenerRejected("no_candidates")
    candidate = candidates[0]
    if candidate.get("finishReason") not in (None, "STOP"):
        raise OpenerRejected("finish_" + str(candidate.get("finishReason")).lower())
    parts = candidate.get("content", {}).get("parts") or []
    text = " ".join(p.get("text", "") for p in parts if not p.get("thought", False)).strip()
    if not text:
        raise OpenerRejected("empty_text")
    return text


def _call_gemini(system_prompt: str, timeout: float) -> str:
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        raise OpenerRejected("missing_api_key")
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": "Open the chat now."}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 80,
            "thinkingConfig": {"thinkingBudget": 0},
        },
        "safetySettings": SAFETY_SETTINGS,
    }
    # Key in a header, not the URL, so httpx error text never carries it.
    record_gemini_call(payload, None, None)
    resp = _get_client().post(_URL, headers={"x-goog-api-key": api_key}, json=payload, timeout=timeout)
    if resp.status_code != 200:
        raise OpenerRejected(f"http_{resp.status_code}")
    body = resp.json()
    record_gemini_call(payload, body, None)  # keeps usage if _extract_text rejects
    text = _extract_text(body)
    record_gemini_call(payload, body, text)
    return text


def generate_opener(
    axes: dict,
    level: str,
    recent_texts: list[str],
    timeout: float = DEFAULT_TIMEOUT_S,
    rng: random.Random | None = None,
    expression_rule: str | None = None,
    user_name: str | None = None,
) -> str:
    """`user_name`: profiles.display_name; empty or None means Pally does not
    know it (see ai.user_name).

    `expression_rule`: one extra prompt rule, e.g. the day's expression for
    Pally to model (see ai.daily_expression.opener_rule). It is appended after
    the fixed rules so the sentence and word limits still bind."""
    rng = rng or random.Random()
    axes = AxisResult(**axes).to_axes_dict()
    guide, max_words = LEVEL_RULES.get(level, LEVEL_RULES["B1"])
    prompt = _SYSTEM_PROMPT.format(
        persona=persona_prompt(axes, rng),
        topic=pick_topic(recent_texts, rng),
        max_words=max_words - PROMPT_WORD_MARGIN,
        level_guide=guide,
        expression_rule=f"{expression_rule}\n" if expression_rule else "",
        name_rule=f"- {rule}\n" if (rule := user_name_rule(user_name)) else "",
    )
    with gemini_generation("opener", MODEL):
        return validate_opener(_call_gemini(prompt, timeout), max_words)


__all__ = ["generate_opener", "persona_prompt", "validate_opener", "word_count", "OpenerRejected", "LEVEL_RULES", "TOPICS"]
