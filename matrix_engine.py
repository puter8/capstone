# -*- coding: utf-8 -*-
"""
Matrix Engine — CHARACTER MATRIX Core
=====================================
Weighted-sum matrix operation: 5-axis scores → character parameters.
Also handles EMA smoothing for temporal updates.
"""

# ---------------------------------------------------------------------------
# Weight matrix W  (3 outputs × 5 inputs)
# Row: [tone_casual, energy_level, humor_level]
# Col: [Formality, Energy, Intimacy, Humor, Curiosity]
#
# Design rationale:
#   tone_casual  : driven by low formality; intimacy & humor add casual feel
#   energy_level : driven by Energy axis; other axes contribute moderately
#   humor_level  : driven primarily by Humor; Energy and Intimacy support it
#
# Weights are kept small (<= 0.5 per cell) so the full range (0-100 inputs)
# does not saturate the output. bias centers each parameter at a neutral baseline.
# ---------------------------------------------------------------------------

W = [
    [-0.45,  0.10,  0.15,  0.15,  0.00],  # tone_casual
    [ 0.05,  0.40,  0.15,  0.10,  0.10],  # energy_level
    [ 0.00,  0.05,  0.10,  0.50,  0.05],  # humor_level
]

BIAS = [50, 20, 10]

# EMA smoothing factor (0 < alpha <= 1)
# alpha=0.3 means 30% new value, 70% history → gradual personality drift
DEFAULT_ALPHA = 0.3


def compute_character(axes: dict) -> dict:
    """
    Weighted-sum matrix operation: 5-axis scores → character parameters.

    Args:
        axes: dict with keys Formality, Energy, Intimacy, Humor, Curiosity (0-100)

    Returns:
        dict with keys tone_casual, energy_level, humor_level (0-100, clipped)
    """
    v = [
        axes["Formality"],
        axes["Energy"],
        axes["Intimacy"],
        axes["Humor"],
        axes["Curiosity"],
    ]
    params = []
    for i, row in enumerate(W):
        val = sum(row[j] * v[j] for j in range(5)) + BIAS[i]
        params.append(max(0.0, min(100.0, val)))
    return {
        "tone_casual":  round(params[0]),
        "energy_level": round(params[1]),
        "humor_level":  round(params[2]),
    }


def apply_ema(prev: dict, new_axes: dict, alpha: float = DEFAULT_ALPHA) -> dict:
    """
    Exponential Moving Average update for axis scores.

    Smooths abrupt personality shifts:
        updated = alpha * new + (1 - alpha) * previous

    Args:
        prev:     previous axis scores (dict)
        new_axes: newly measured axis scores from current utterance (dict)
        alpha:    smoothing factor (0–1). Higher = reacts faster.

    Returns:
        Updated axis scores after EMA blending.
    """
    keys = ["Formality", "Energy", "Intimacy", "Humor", "Curiosity"]
    return {
        k: round(alpha * new_axes[k] + (1 - alpha) * prev[k])
        for k in keys
    }


def describe_character(char: dict) -> tuple:
    """Convert character parameters to human-readable labels."""
    tone = (
        "Very casual (slang freely used)" if char["tone_casual"] > 60
        else "Formal (polite and respectful)" if char["tone_casual"] < 30
        else "Neutral"
    )
    energy = (
        "Very active (enthusiastic)" if char["energy_level"] > 60
        else "Calm (quiet and measured)" if char["energy_level"] < 30
        else "Moderate"
    )
    humor = (
        "Humor/meme mode" if char["humor_level"] > 60
        else "Serious and direct" if char["humor_level"] < 30
        else "Occasional wit"
    )
    return tone, energy, humor
