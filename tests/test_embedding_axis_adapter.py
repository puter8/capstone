import numpy as np
import pytest

from ai.embedding_axis_adapter import EmbeddingAxisAdapter
from ai.ml_baseline import AxisTrainingExample


class FixedEncoder:
    def encode(self, sentences, **kwargs):
        return np.array([[float(text), 1.0] for text in sentences])


def example(text, **labels):
    return AxisTrainingExample(text, labels, "conversation")


def test_partial_labels_are_not_zero_targets_and_refit_clears_old_axes():
    model = EmbeddingAxisAdapter(encoder=FixedEncoder()).fit([
        example("0", Humor=80, Formality=20), example("1", Formality=50),
        example("2", Formality=80),
    ])
    prediction = model.predict_partial("1")
    assert prediction == {"Formality": 50, "Humor": 80, "Curiosity": None}
    model.fit([example("0", Curiosity=75)])
    assert model.predict_partial("1") == {"Formality": None, "Humor": None, "Curiosity": 75}


def test_predictions_learn_targets_and_are_bounded():
    model = EmbeddingAxisAdapter(alpha=0.01, encoder=FixedEncoder()).fit([
        example("0", Formality=0), example("1", Formality=100),
    ])
    predictions = model.predict_many(["-100", "0.5", "100"])
    assert [p["Formality"] for p in predictions] == [0, 50, 100]


def test_rejects_nonfinite_targets_and_encoder_outputs():
    model = EmbeddingAxisAdapter(encoder=FixedEncoder())
    with pytest.raises(ValueError, match="invalid Humor"):
        model.fit([example("1", Humor=float("nan"))])
    with pytest.raises(ValueError, match="non-finite features"):
        model.fit([example("nan", Humor=50)])


def test_unfitted_prediction_is_explicit_error():
    with pytest.raises(RuntimeError, match="not fitted"):
        EmbeddingAxisAdapter(encoder=FixedEncoder()).predict_partial("1")
