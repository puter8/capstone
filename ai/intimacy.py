# -*- coding: utf-8 -*-
"""Intimacy axis — how often the user comes back, not how any utterance reads.

Input is the number of distinct KST calendar days on which the user opened the
app (2026-10-15 decision: one access = one day, so reloading the page does not
inflate it). The curve has diminishing returns: 5th access-day reaches the mid
tier (35), 21st the high tier (70).
"""

HALF_SATURATION = 10  # access-day count at which the raw (pre-rounding) score hits 50


def compute_intimacy_from_access_days(access_days: int) -> int:
    """Map lifetime access-day count to an Intimacy score, 0-100, 5-point rounded."""
    if access_days < 0:
        raise ValueError(f"access_days must be >= 0, got {access_days}")
    raw = 100 * access_days / (access_days + HALF_SATURATION)
    return min(100, max(0, round(raw / 5) * 5))
