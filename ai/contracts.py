# -*- coding: utf-8 -*-
"""
Shared AI-side contracts for analyzer and Reddit vocabulary work.

These models are internal to the AI layer. They mirror the frontend/backend
wire contracts without forcing the rest of the app to know whether the
implementation is rule-based, ML-based, or hybrid.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
    sourceId: str
    sourceUrl: str
    subreddit: str
    text: str
    observedAt: str
    title: str | None = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text is required")
        return value


class MemeTermCandidate(BaseModel):
    term: str
    normalizedTerm: str
    meaningKo: str
    usageContext: str
    subreddit: str
    sourceId: str
    sourceUrl: str
    observedAt: str
    confidence: float = Field(ge=0.0, le=1.0)
    safety: Literal["safe", "review", "blocked"]


class MemeTerm(MemeTermCandidate):
    id: str
    status: Literal["approved", "rejected", "expired"]
    approvedAt: str | None = None

