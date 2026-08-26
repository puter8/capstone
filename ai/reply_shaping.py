# -*- coding: utf-8 -*-
"""
reply_shaping
-------------
Keep Pally's chat replies short enough to fit the compact ShortBubble UI
(~2 lines per message, ~290px message area) and to be spoken naturally by
TTS, without ever cutting a sentence mid-word.

Why this exists: the system prompt already asks Gemini for "1-3 sentences"
/ "usually 1-2 short sentences", but that's a soft instruction the model
doesn't always follow. When it runs long, Gemini's own maxOutputTokens cap
(512) cuts the response off mid-sentence (backend/main.py already detects
`finishReason == "MAX_TOKENS"` and logs it, but still returns the broken
text as-is). shape_reply() is a safety net: apply it to every reply before
it's shown, spoken, or stored, so a broken mid-sentence cutoff never
reaches the user even if Gemini ignores the length guidance.
"""
from __future__ import annotations

import re

MAX_REPLY_CHARS = 90

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def shape_reply(text: str, max_chars: int = MAX_REPLY_CHARS) -> str:
    """Truncate `text` at the last complete sentence boundary that still
    fits within `max_chars`. Never cuts mid-word.

    If even the first sentence alone exceeds max_chars, fall back to
    cutting at the last word boundary within max_chars (still not
    mid-word) rather than returning an overlong sentence unshaped.
    """
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text

    sentences = [s for s in _SENTENCE_BOUNDARY.split(text) if s]
    if not sentences:
        sentences = [text]

    kept = ""
    for sentence in sentences:
        candidate = f"{kept} {sentence}".strip() if kept else sentence
        if len(candidate) > max_chars:
            if kept:
                break
            return _cut_at_word_boundary(sentence, max_chars)
        kept = candidate
    return kept


def _cut_at_word_boundary(text: str, max_chars: int) -> str:
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.rstrip(",;: ")


__all__ = ["shape_reply", "MAX_REPLY_CHARS"]
