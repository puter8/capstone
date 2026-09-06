# -*- coding: utf-8 -*-

import os
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.select_ml_transition_annotation_sets import select_active_training, select_stratified_gold


def _scored_row(index: int) -> dict:
    return {
        "utterance": f"This is candidate utterance number {index}.",
        "source": "ami_real" if index % 2 else "nict_jle_real",
        "source_group": f"group-{index}",
        "source_record_id": f"record-{index}",
        "focus_bucket": "high_energy_low_curiosity" if index % 2 else "low_energy_high_curiosity",
        "word_count": 5 + index % 16,
        "selection_energy_disagreement": index,
        "selection_curiosity_disagreement": 200 - index,
        "selection_energy_extremeness": index % 70,
        "selection_curiosity_extremeness": (index * 3) % 70,
    }


def test_active_training_selection_has_the_planned_reason_quotas() -> None:
    selected = select_active_training([_scored_row(index) for index in range(200)], seed=7)

    assert len(selected) == 120
    assert Counter(row["selection_reason"] for row in selected) == {
        "energy_disagreement": 40,
        "curiosity_disagreement": 40,
        "energy_extreme": 15,
        "curiosity_extreme": 15,
        "random_control": 10,
    }
    assert len({row["source_group"] for row in selected}) == 120


def test_gold_selection_is_stratified_and_has_no_model_selection_metadata() -> None:
    rows = [
        {
            "utterance": f"Candidate {index} has enough words for review.",
            "source": "ami_real" if index % 2 else "nict_jle_real",
            "source_group": f"gold-{index}",
            "focus_bucket": "high_energy_low_curiosity" if index % 3 else "low_energy_high_curiosity",
            "word_count": 5 if index % 3 == 0 else 10 if index % 3 == 1 else 20,
        }
        for index in range(30)
    ]

    selected = select_stratified_gold(rows, size=20, seed=7)

    assert len(selected) == 20
    assert len({row["selection_stratum"] for row in selected}) >= 6
    assert all(row["selection_method"] == "stratified_random" for row in selected)
    assert all("selection_ml_axes" not in row for row in selected)
