# -*- coding: utf-8 -*-

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.contracts import AXIS_KEYS
from ai.style_state import UserStyleState, partial_mirror_target, style_distance, style_similarity


def _axes(value: int) -> dict[str, int]:
    return {axis: value for axis in AXIS_KEYS}


def test_user_style_state_keeps_baseline_and_current_separate() -> None:
    state = UserStyleState.first_turn(_axes(40)).observe(_axes(80))

    assert state.turn_count == 2
    assert state.current["Energy"] == 68
    assert state.baseline["Energy"] == 46


def test_distance_and_similarity_are_normalized() -> None:
    assert style_distance(_axes(50), _axes(50)) == 0
    assert style_distance(_axes(0), _axes(100)) == 1
    assert style_similarity(_axes(50), _axes(50)) == 1


def test_partial_mirror_is_bounded() -> None:
    target = partial_mirror_target(_axes(30), _axes(100), strength=1, max_axis_shift=15)

    assert target == _axes(45)
