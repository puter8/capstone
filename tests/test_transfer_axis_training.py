import pytest

from scripts.train_transfer_axis_models import assert_human_labels, eligible_training_indices, metrics


def test_excludes_meeting_series_and_duplicate_text():
    train = [
        {"source_group": "ES2008a", "utterance": "different"},
        {"source_group": "Bmr001", "utterance": " SAME   TEXT "},
        {"source_group": "Bmr002", "utterance": "unseen"},
    ]
    reserved = [{"source_group": "ES2008d", "utterance": "same text"}]
    assert eligible_training_indices(train, reserved) == [2]


def test_ai_labels_cannot_enter_human_training():
    with pytest.raises(ValueError, match="unverified human provenance"):
        assert_human_labels([{"item_id": "a", "axes": {"Humor": 50},
                              "label_source": {"Humor": "gemini_ai_scored"}}])


def test_perfect_low_only_predictions_do_not_pass_validation():
    rows = [{"axes": {"Humor": 0}} for _ in range(30)]
    result = metrics(rows, [{"Humor": 0}] * 30)["Humor"]
    assert result["mae"] == 0
    assert result["tier_support"] == [30, 0, 0]
    assert result["gate"] == "INSUFFICIENT_EVIDENCE"


def test_missing_predictions_cannot_silently_improve_metrics():
    result = metrics([{"axes": {"Humor": 100}}], [{"Humor": None}])["Humor"]
    assert result["missing_predictions"] == 1
    assert result["gate"] == "FAIL_MISSING_PREDICTIONS"
