# -*- coding: utf-8 -*-
"""
Reddit meme/slang vocabulary candidate extraction.

This module intentionally does not fetch Reddit. The backend owns collection
and passes approved `RedditSourceItem` batches into this AI-side extractor.
"""

import re

from ai.contracts import MemeTermCandidate, RedditSourceItem


TERM_CATALOG: dict[str, dict[str, str]] = {
    "lowkey": {
        "meaningKo": "은근히, 살짝",
        "usageContext": "Casual emphasis for a mild opinion or feeling.",
    },
    "highkey": {
        "meaningKo": "대놓고, 진심으로",
        "usageContext": "Casual emphasis for a strong opinion or feeling.",
    },
    "no cap": {
        "meaningKo": "진짜로, 거짓말 없이",
        "usageContext": "Casual assurance that the speaker is being honest.",
    },
    "rizz": {
        "meaningKo": "플러팅 매력, 사람을 끄는 말솜씨",
        "usageContext": "Casual internet slang for charm in flirting.",
    },
    "sus": {
        "meaningKo": "수상한, 의심스러운",
        "usageContext": "Casual reaction to something suspicious.",
    },
    "slay": {
        "meaningKo": "멋지게 해내다",
        "usageContext": "Playful praise for doing something well.",
    },
    "based": {
        "meaningKo": "소신 있거나 멋지다는 반응",
        "usageContext": "Internet praise for a confident opinion.",
    },
    "cringe": {
        "meaningKo": "민망하고 오글거리는",
        "usageContext": "Casual judgment that something feels embarrassing.",
    },
    "it's giving": {
        "meaningKo": "어떤 느낌이 난다",
        "usageContext": "Playful description of a vibe or impression.",
    },
    "main character energy": {
        "meaningKo": "주인공 같은 분위기",
        "usageContext": "Playful praise for confident or dramatic behavior.",
    },
}

BLOCKED_TERMS = {
    "kill yourself",
    "kys",
}


def normalize_term(term: str) -> str:
    normalized = term.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _contains_term(text: str, term: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _safety_for_term(normalized_term: str) -> str:
    if normalized_term in BLOCKED_TERMS:
        return "blocked"
    if normalized_term in {"rizz", "sus", "cringe"}:
        return "review"
    return "safe"


def extract_meme_candidates(sources: list[RedditSourceItem]) -> list[MemeTermCandidate]:
    candidates: list[MemeTermCandidate] = []
    seen: set[tuple[str, str]] = set()

    for source in sources:
        combined_text = f"{source.title or ''}\n{source.text}"
        for term, meta in TERM_CATALOG.items():
            if not _contains_term(combined_text, term):
                continue
            normalized = normalize_term(term)
            dedupe_key = (source.sourceId, normalized)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            safety = _safety_for_term(normalized)
            confidence = 0.85 if safety == "safe" else 0.65
            candidates.append(
                MemeTermCandidate(
                    term=term,
                    normalizedTerm=normalized,
                    meaningKo=meta["meaningKo"],
                    usageContext=meta["usageContext"],
                    subreddit=source.subreddit,
                    sourceId=source.sourceId,
                    sourceUrl=source.sourceUrl,
                    observedAt=source.observedAt,
                    confidence=confidence,
                    safety=safety,
                )
            )
    return candidates


def build_prompt_vocabulary(candidates: list[MemeTermCandidate], limit: int = 5) -> list[dict[str, str]]:
    safe_terms = [candidate for candidate in candidates if candidate.safety == "safe"]
    safe_terms.sort(key=lambda item: item.confidence, reverse=True)
    return [
        {
            "term": item.normalizedTerm,
            "meaningKo": item.meaningKo,
            "usageContext": item.usageContext,
        }
        for item in safe_terms[:limit]
    ]

