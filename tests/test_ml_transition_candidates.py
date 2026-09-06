# -*- coding: utf-8 -*-

import hashlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.sample_ml_transition_candidates import focus_bucket, focus_quota, review_partition, sample_transition_sets


def _group_for_partition(source: str, partition: str) -> str:
    for index in range(100):
        group = f"group-{index}"
        digest = hashlib.sha256(f"{source}:{group}".encode("utf-8")).digest()
        if ("gold" if int.from_bytes(digest[:4], "big") % 3 == 0 else "train") == partition:
            return group
    raise AssertionError(f"could not find {partition} group")


def _rows_for_group(source: str, group: str, topic: str) -> list[dict]:
    return [
        {"utterance": f"Why are you really excited about {topic}?", "source": source, "source_group": group},
        {"utterance": f"I am really excited about the {topic} plan.", "source": source, "source_group": group},
        {"utterance": f"Could you explain the {topic} schedule?", "source": source, "source_group": group},
        {"utterance": f"The {topic} schedule is on the table.", "source": source, "source_group": group},
    ]


def test_focus_bucket_targets_energy_and_curiosity_independently() -> None:
    assert focus_bucket({"utterance": "Why are you really excited?"}) == "high_energy_high_curiosity"
    assert focus_bucket({"utterance": "I am really excited about this plan."}) == "high_energy_low_curiosity"
    assert focus_bucket({"utterance": "Could you explain the schedule?"}) == "low_energy_high_curiosity"
    assert focus_bucket({"utterance": "The schedule is on the table."}) == "low_energy_low_curiosity"
    assert focus_bucket({"utterance": "I have a question about the schedule."}) == "low_energy_high_curiosity"
    assert focus_bucket({"utterance": "Could this really be the schedule?"}) == "low_energy_high_curiosity"
    assert focus_bucket({"utterance": "To private rooms?"}) == "low_energy_high_curiosity"
    assert focus_bucket({"utterance": "It is challenging to explain the schedule."}) == "low_energy_low_curiosity"


def test_weighted_focus_quota_keeps_energy_and_curiosity_marginals_balanced() -> None:
    quotas = focus_quota(600)

    assert quotas == {
        "high_energy_high_curiosity": 75,
        "high_energy_low_curiosity": 225,
        "low_energy_high_curiosity": 225,
        "low_energy_low_curiosity": 75,
    }
    assert quotas["high_energy_high_curiosity"] + quotas["high_energy_low_curiosity"] == 300
    assert quotas["high_energy_high_curiosity"] + quotas["low_energy_high_curiosity"] == 300


def test_transition_sampling_keeps_source_groups_out_of_the_other_split() -> None:
    source = "ami_real"
    gold_group = _group_for_partition(source, "gold")
    train_group = _group_for_partition(source, "train")
    rows = _rows_for_group(source, gold_group, "amber") + _rows_for_group(source, train_group, "bravo")

    gold, train, _ = sample_transition_sets(rows, gold_size=4, train_size=4, seed=7)

    assert len(gold) == 4
    assert len(train) == 4
    assert {row["source_group"] for row in gold} == {gold_group}
    assert {row["source_group"] for row in train} == {train_group}
    assert all(review_partition(row) == "gold" for row in gold)
    assert all(review_partition(row) == "train" for row in train)
