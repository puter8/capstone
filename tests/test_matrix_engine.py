# -*- coding: utf-8 -*-
from ai.matrix_engine import compute_character
from ai.opener import persona_prompt

AXES = ["Formality", "Energy", "Intimacy", "Humor", "Curiosity"]
OTHER_VALUES = (0, 50, 100)


def _canvas_tier(v):
    """Mirrors frontend/components/pally/PallyCanvas.tsx::tier()."""
    if v <= 33:
        return 0
    if v <= 66:
        return 1
    return 2


def _other_combos(fixed_axis):
    others = [a for a in AXES if a != fixed_axis]
    for o0 in OTHER_VALUES:
        for o1 in OTHER_VALUES:
            for o2 in OTHER_VALUES:
                for o3 in OTHER_VALUES:
                    yield dict(zip(others, (o0, o1, o2, o3)))


def test_tone_casual_is_exact_formality_complement():
    for f in range(0, 101):
        for base in _other_combos("Formality"):
            axes = {**base, "Formality": f}
            assert compute_character(axes)["tone_casual"] == 100 - f


def test_energy_level_equals_raw_energy():
    for e in range(0, 101):
        for base in _other_combos("Energy"):
            axes = {**base, "Energy": e}
            assert compute_character(axes)["energy_level"] == e


def test_humor_level_equals_raw_humor():
    for h in range(0, 101):
        for base in _other_combos("Humor"):
            axes = {**base, "Humor": h}
            assert compute_character(axes)["humor_level"] == h


def test_canvas_and_prompt_agree_on_energy_and_humor_tier():
    """energy_level/humor_level pass raw axis values straight through, so the
    prompt's <34/<67 bands and canvas's <=33/<=66 tiers see identical integers
    and can never disagree."""
    for axis_name in ("Energy", "Humor"):
        for v in range(0, 101):
            for base in _other_combos(axis_name):
                axes = {**base, axis_name: v}
                char = compute_character(axes)
                level = char["energy_level"] if axis_name == "Energy" else char["humor_level"]
                lo = level < 34
                hi = level >= 67
                tier = _canvas_tier(v)
                assert (tier == 0) == lo
                assert (tier == 2) == hi


def test_canvas_and_prompt_agree_on_formality_tier_by_meaning():
    """Formality is inverted (tone_casual = 100 - Formality): canvas tier 0
    (low Formality, round/casual-looking corners) must mean the same thing as
    the prompt's "very casual, slangy" label (tone_casual >= 67), and canvas
    tier 2 (high Formality, angular/formal-looking) must match "polite and
    proper" (tone_casual < 34)."""
    for f in range(0, 101):
        for base in _other_combos("Formality"):
            axes = {**base, "Formality": f}
            tone_casual = compute_character(axes)["tone_casual"]
            tier = _canvas_tier(f)
            assert (tier == 0) == (tone_casual >= 67)  # casual-looking <-> "very casual, slangy"
            assert (tier == 2) == (tone_casual < 34)   # formal-looking <-> "polite and proper"


def test_persona_prompt_tone_label_matches_formality_direction():
    casual_axes = {"Formality": 0, "Energy": 50, "Intimacy": 50, "Humor": 50, "Curiosity": 50}
    formal_axes = {"Formality": 100, "Energy": 50, "Intimacy": 50, "Humor": 50, "Curiosity": 50}
    assert "very casual" in persona_prompt(casual_axes)
    assert "polite and proper" in persona_prompt(formal_axes)
