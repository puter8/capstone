import pytest

from ai.intimacy import compute_intimacy_from_access_days
from ai.matrix_engine import apply_cumulative, cumulative_alpha

KEYS = ("Formality", "Energy", "Intimacy", "Humor", "Curiosity")


def axes(v):
    return {k: v for k in KEYS}


def test_alpha_starts_fast_then_floors_at_twenty_percent():
    assert [cumulative_alpha(n) for n in range(5)] == [1 / 2, 1 / 3, 1 / 4, 0.2, 0.2]
    with pytest.raises(ValueError):
        cumulative_alpha(-1)


def test_steady_user_converges_and_one_outlier_barely_moves_pally():
    state = axes(50)
    seen = []
    for n in range(10):
        state = apply_cumulative(state, [axes(70)], n)
        seen.append(state["Formality"])
    assert seen[:3] == [60, 63, 65] and seen[-1] in (68, 69)
    outlier = apply_cumulative(axes(60), [axes(90)], 9)
    assert outlier["Formality"] == 66  # one 90 conversation among 60s moves Pally 20%, not to ~90


def test_whole_conversation_is_averaged_not_just_the_last_turn():
    after = apply_cumulative(axes(50), [axes(10), axes(10), axes(100)], 0)
    assert after["Formality"] == 45  # mean 40 -> 50 + 0.5*(40-50)
    with pytest.raises(ValueError):
        apply_cumulative(axes(50), [], 0)


@pytest.mark.parametrize("days, score", [(0, 0), (1, 10), (4, 30), (5, 35), (20, 65), (21, 70), (200, 95)])
def test_intimacy_milestones_on_access_days(days, score):
    assert compute_intimacy_from_access_days(days) == score
