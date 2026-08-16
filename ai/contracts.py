# -*- coding: utf-8 -*-
"""
Shared AI-side contracts for analyzer and Reddit vocabulary work.

These models are internal to the AI layer. They mirror the frontend/backend
wire contracts without forcing the rest of the app to know whether the
implementation is rule-based, ML-based, or hybrid.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AXIS_KEYS = ("Formality", "Energy", "Intimacy", "Humor", "Curiosity")
CHARACTER_KEYS = ("tone_casual", "energy_level", "humor_level")


class AxisResult(BaseModel):
    Formality: int = Field(ge=0, le=100)
    Energy: int = Field(ge=0, le=100)
    Intimacy: int = Field(ge=0, le=100)
    Humor: int = Field(ge=0, le=100)
    Curiosity: int = Field(ge=0, le=100)

    def to_axes_dict(self) -> dict[str, int]:
        return self.model_dump()


class RedditSourceItem(BaseModel):
    """AI-side input shape for backend-provided Reddit collector results.

    Week 3 accepts the backend/DB-friendly snake_case fields while preserving
    the Week 1 camelCase names used by existing AI tests and fixtures.
    """

    model_config = ConfigDict(populate_by_name=True)

    sourceId: str = Field(alias="source_id")
    subreddit: str
    text: str = Field(alias="body")
    observedAt: str = Field(alias="observed_at")
    sourceUrl: str = Field(alias="permalink")
    title: str | None = None
    score: int | None = None
    kind: Literal["post", "comment"] = "post"

    @field_validator("subreddit")
    @classmethod
    def normalize_subreddit(cls, value: str) -> str:
        normalized = value.strip()
        if normalized.lower().startswith("r/"):
            normalized = normalized[2:]
        if not normalized:
            raise ValueError("subreddit is required")
        return normalized

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("body/text is required")
        return value


class MemeTermCandidate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    term: str
    normalizedTerm: str = Field(alias="normalized_term")
    meaningKo: str = Field(alias="meaning_ko")
    usageContext: str = Field(alias="usage_context")
    subreddit: str
    sourceId: str = Field(alias="source_id")
    sourceUrl: str = Field(alias="source_url")
    observedAt: str = Field(alias="observed_at")
    confidence: float = Field(ge=0.0, le=1.0)
    safety: Literal["safe", "review", "blocked"]


class MemeTerm(MemeTermCandidate):
    id: str
    status: Literal["approved", "rejected", "expired"]
    approvedAt: str | None = Field(default=None, alias="approved_at")


class FeedbackItem(BaseModel):
    """Wire shape returned by `ai.generate_feedback.generate_feedback`.

    Backend assigns `id` when persisting to `messages.feedback`; this model
    only covers the AI-generated fields.
    """

    original: str
    corrected: str
    explanation_ko: str