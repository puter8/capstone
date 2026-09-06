# -*- coding: utf-8 -*-
"""User-style state and experimental adaptation-policy primitives.

This module deliberately separates measurement from response adaptation.
The analyzer estimates a user's five-axis communication state; an experiment
can later decide whether and how an agent should move toward that state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from ai.contracts import AXIS_KEYS


AxisVector = dict[str, int]
StyleMode = str


def validate_axis_vector(values: Mapping[str, int]) -> AxisVector:
    vector: AxisVector = {}
    for axis in AXIS_KEYS:
        value = int(values[axis])
        if not 0 <= value <= 100:
            raise ValueError(f"{axis} must be between 0 and 100")
        vector[axis] = value
    return vector


def smooth(previous: Mapping[str, int], observed: Mapping[str, int], alpha: float) -> AxisVector:
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be greater than zero and at most one")
    prev = validate_axis_vector(previous)
    current = validate_axis_vector(observed)
    return {axis: round(alpha * current[axis] + (1 - alpha) * prev[axis]) for axis in AXIS_KEYS}


@dataclass(frozen=True)
class UserStyleState:
    """Long-run baseline and recent state for one user session or profile."""

    baseline: AxisVector
    current: AxisVector
    turn_count: int

    @classmethod
    def first_turn(cls, observed: Mapping[str, int]) -> "UserStyleState":
        vector = validate_axis_vector(observed)
        return cls(baseline=vector, current=vector, turn_count=1)

    def observe(
        self,
        observed: Mapping[str, int],
        current_alpha: float = 0.7,
        baseline_alpha: float = 0.15,
    ) -> "UserStyleState":
        return UserStyleState(
            baseline=smooth(self.baseline, observed, baseline_alpha),
            current=smooth(self.current, observed, current_alpha),
            turn_count=self.turn_count + 1,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline": self.baseline,
            "current": self.current,
            "turn_count": self.turn_count,
        }


def style_distance(
    left: Mapping[str, int],
    right: Mapping[str, int],
    weights: Mapping[str, float] | None = None,
) -> float:
    """Return normalized weighted Euclidean distance in the inclusive 0..1 range."""
    first = validate_axis_vector(left)
    second = validate_axis_vector(right)
    axis_weights = {axis: float((weights or {}).get(axis, 1.0)) for axis in AXIS_KEYS}
    if any(weight < 0 for weight in axis_weights.values()) or not any(axis_weights.values()):
        raise ValueError("weights must be non-negative with at least one positive value")
    squared = sum(axis_weights[axis] * ((first[axis] - second[axis]) / 100) ** 2 for axis in AXIS_KEYS)
    return math.sqrt(squared / sum(axis_weights.values()))


def partial_mirror_target(
    agent_anchor: Mapping[str, int],
    user_state: Mapping[str, int],
    strength: float,
    max_axis_shift: int = 20,
) -> AxisVector:
    """Create a bounded experimental target without assuming full matching is best."""
    if not 0 <= strength <= 1:
        raise ValueError("strength must be between 0 and 1")
    if not 0 <= max_axis_shift <= 100:
        raise ValueError("max_axis_shift must be between 0 and 100")
    anchor = validate_axis_vector(agent_anchor)
    user = validate_axis_vector(user_state)
    target: AxisVector = {}
    for axis in AXIS_KEYS:
        requested_shift = round((user[axis] - anchor[axis]) * strength)
        bounded_shift = max(-max_axis_shift, min(max_axis_shift, requested_shift))
        target[axis] = max(0, min(100, anchor[axis] + bounded_shift))
    return target


def style_similarity(left: Mapping[str, int], right: Mapping[str, int]) -> float:
    return 1 - style_distance(left, right)
