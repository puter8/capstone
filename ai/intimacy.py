# -*- coding: utf-8 -*-
"""
Intimacy axis — provisional non-ML signal.

Formality/Humor/Curiosity stay text-derived; Intimacy instead reflects how
many times the user has opened the app (lifetime session count), not the
wording of any single utterance. A brand-new user starts low and the curve
has diminishing returns (it does reach exactly 100 once count >= 390 under
5-point rounding, but getting there takes a lot of sessions).

Reference: docs/AI_TACTIC/Pally_RUBRIC_v3.0_md §2 (provisional, non-ML).
"""

# ponytail: single global half-saturation constant, not configurable per
# cohort/experiment; revisit if product wants to A/B the curve shape.
HALF_SATURATION = 10  # session count at which the raw (pre-rounding) score hits 50


def compute_intimacy_from_session_count(session_count: int) -> int:
    """Map lifetime app-open (session) count to an Intimacy score, 0-100, 5-point rounded.

    ``session_count`` must be the number of sessions the user has ever
    started (including the current one) — a cumulative lifetime count, not a
    windowed/weekly one.
    """
    if session_count < 0:
        raise ValueError(f"session_count must be >= 0, got {session_count}")
    raw = 100 * session_count / (session_count + HALF_SATURATION)
    return min(100, max(0, round(raw / 5) * 5))


def _demo() -> None:
    cases = [(0, 0), (1, 10), (10, 50), (20, 65), (50, 85), (200, 95)]
    for count, expected in cases:
        got = compute_intimacy_from_session_count(count)
        assert got == expected, f"session_count={count}: expected {expected}, got {got}"
    try:
        compute_intimacy_from_session_count(-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative session_count should raise")
    print("ai/intimacy.py self-check passed")


if __name__ == "__main__":
    _demo()
