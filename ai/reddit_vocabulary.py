# -*- coding: utf-8 -*-
"""
Reddit meme/slang vocabulary candidate extraction.

This module intentionally does not fetch Reddit. The backend owns OAuth,
collection, dedupe, retention, and storage. The AI layer only receives approved
or fixture `RedditSourceItem` batches and returns normalized candidates.
"""

import re
from dataclasses import dataclass

from ai.contracts import MemeTerm, MemeTermCandidate, RedditSourceItem


ALLOWED_SUBREDDITS = frozenset({"EnglishLearning", "languagelearning", "OutOfTheLoop"})
EXCLUDED_SUBREDDITS = frozenset({"teenagers", "GenZ"})


@dataclass(frozen=True)
class TermMeta:
    meaningKo: str
    usageContext: str
    baseSafety: str = "safe"
    confidence: float = 0.86


TERM_CATALOG: dict[str, TermMeta] = {
    "lowkey": TermMeta(
        meaningKo="은근히, 살짝",
        usageContext="Casual spoken emphasis for a mild opinion or hidden feeling.",
    ),
    "highkey": TermMeta(
        meaningKo="대놓고, 진심으로",
        usageContext="Casual spoken emphasis for a strong opinion or feeling.",
    ),
    "no cap": TermMeta(
        meaningKo="진짜로, 거짓말 없이",
        usageContext="Casual way to stress that the speaker is being honest.",
    ),
    "bet": TermMeta(
        meaningKo="좋아, 알겠어, 그렇게 하자",
        usageContext="Very casual agreement, similar to 'okay' or 'sounds good'.",
    ),
    "delulu": TermMeta(
        meaningKo="비현실적으로 기대하는, 망상에 가까운",
        usageContext="Joking casual word for unrealistic hopes or beliefs.",
        baseSafety="review",
        confidence=0.72,
    ),
    "it's giving": TermMeta(
        meaningKo="어떤 느낌이 난다",
        usageContext="Playful way to describe a vibe or impression.",
    ),
    "main character energy": TermMeta(
        meaningKo="주인공 같은 분위기",
        usageContext="Playful praise for confident or dramatic behavior.",
    ),
    "mid": TermMeta(
        meaningKo="평범한, 별로 인상적이지 않은",
        usageContext="Casual negative judgment meaning mediocre or average.",
    ),
    "slay": TermMeta(
        meaningKo="멋지게 해내다",
        usageContext="Playful praise for doing something well.",
    ),
    "ate": TermMeta(
        meaningKo="아주 잘했다, 멋지게 해냈다",
        usageContext="Casual praise, often about performance, style, or delivery.",
    ),
    "sus": TermMeta(
        meaningKo="수상한, 의심스러운",
        usageContext="Casual reaction to something suspicious.",
        baseSafety="review",
        confidence=0.68,
    ),
    "the ick": TermMeta(
        meaningKo="갑자기 정떨어지는 느낌",
        usageContext="Casual dating-related expression for sudden turn-off.",
        baseSafety="review",
        confidence=0.7,
    ),
    "bussin": TermMeta(
        meaningKo="정말 맛있는, 아주 좋은",
        usageContext="Very casual praise, especially for food.",
    ),
    "fr": TermMeta(
        meaningKo="진짜로, 정말",
        usageContext="Casual abbreviation of 'for real'. Better for comprehension than Pally output.",
        baseSafety="review",
        confidence=0.66,
    ),
    "fr fr": TermMeta(
        meaningKo="진짜 진심으로",
        usageContext="Repeated 'for real' for emphasis in casual speech/text.",
        baseSafety="review",
        confidence=0.66,
    ),
    "rizz": TermMeta(
        meaningKo="플러팅 매력, 사람을 끄는 말솜씨",
        usageContext="Casual internet slang for charm in flirting.",
        baseSafety="review",
        confidence=0.65,
    ),
    "cringe": TermMeta(
        meaningKo="민망한, 오글거리는",
        usageContext="Casual judgment that something feels embarrassing.",
        baseSafety="review",
        confidence=0.68,
    ),
}

BLOCKED_TERMS = frozenset({"kill yourself", "kys"})

MINOR_OR_PII_PATTERNS = [
    re.compile(r"\b(?:i'?m|i am)\s+(?:1[0-7])\b", re.IGNORECASE),
    re.compile(r"\b(?:middle school|high school|my school|my teacher|my class)\b", re.IGNORECASE),
    re.compile(r"\b(?:i live in|my address|my phone|my discord)\b", re.IGNORECASE),
]


REDDIT_COLLECTION_POLICY = {
    "api_access": "Backend applies for official Reddit Data API OAuth access; AI uses fixture until approval.",
    "allowed_subreddits": sorted(ALLOWED_SUBREDDITS),
    "excluded_subreddits": sorted(EXCLUDED_SUBREDDITS),
    "daily_limit": "30 post/comment items per subreddit, 90 total per day.",
    "retention": "Do not use Reddit source text for ML training. Store only what the approved use case requires and delete source text aggressively when no longer needed.",
    "prompt_rule": "Only safe/approved vocabulary may enter Pally prompt context.",
}


def normalize_term(term: str) -> str:
    normalized = term.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def normalize_subreddit(subreddit: str) -> str:
    normalized = subreddit.strip()
    if normalized.lower().startswith("r/"):
        normalized = normalized[2:]
    return normalized


def is_allowed_source(source: RedditSourceItem) -> bool:
    subreddit = normalize_subreddit(source.subreddit)
    if subreddit in EXCLUDED_SUBREDDITS:
        return False
    if subreddit not in ALLOWED_SUBREDDITS:
        return False
    combined_text = f"{source.title or ''}\n{source.text}"
    return not _contains_minor_or_pii_signal(combined_text)


def filter_allowed_sources(sources: list[RedditSourceItem]) -> list[RedditSourceItem]:
    return [source for source in sources if is_allowed_source(source)]


def _contains_minor_or_pii_signal(text: str) -> bool:
    return any(pattern.search(text) is not None for pattern in MINOR_OR_PII_PATTERNS)


def _contains_term(text: str, term: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _safety_for_term(normalized_term: str, meta: TermMeta) -> str:
    if normalized_term in BLOCKED_TERMS:
        return "blocked"
    return meta.baseSafety


def extract_meme_candidates(sources: list[RedditSourceItem]) -> list[MemeTermCandidate]:
    candidates: list[MemeTermCandidate] = []
    seen: set[tuple[str, str]] = set()

    for source in filter_allowed_sources(sources):
        combined_text = f"{source.title or ''}\n{source.text}"
        for term, meta in TERM_CATALOG.items():
            if not _contains_term(combined_text, term):
                continue
            normalized = normalize_term(term)
            dedupe_key = (source.sourceId, normalized)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            safety = _safety_for_term(normalized, meta)
            candidates.append(
                MemeTermCandidate(
                    term=term,
                    normalizedTerm=normalized,
                    meaningKo=meta.meaningKo,
                    usageContext=meta.usageContext,
                    subreddit=source.subreddit,
                    sourceId=source.sourceId,
                    sourceUrl=source.sourceUrl,
                    observedAt=source.observedAt,
                    confidence=meta.confidence,
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


def build_prompt_vocabulary_from_terms(terms: list[MemeTerm], limit: int = 5) -> list[dict[str, str]]:
    """Convert backend-persisted, human/policy-approved `MemeTerm` rows into
    Pally prompt vocabulary entries.

    Unlike `build_prompt_vocabulary` (which runs on freshly extracted
    `MemeTermCandidate`s, before any approval step), this requires
    `status == "approved"`. `safety` is re-checked here too — approval
    should never override a `review`/`blocked` safety verdict, in case a
    term's safety classification changed after it was approved.
    """
    approved_safe = [term for term in terms if term.status == "approved" and term.safety == "safe"]
    approved_safe.sort(key=lambda item: item.confidence, reverse=True)
    return [
        {
            "term": item.normalizedTerm,
            "meaningKo": item.meaningKo,
            "usageContext": item.usageContext,
        }
        for item in approved_safe[:limit]
    ]