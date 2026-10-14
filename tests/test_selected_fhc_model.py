"""Portable composition preserves each estimator's raw output semantics."""
import numpy as np
import pytest
from ai.selected_fhc_model import SelectedFHCModel


class Encoder:
    def _encode(self, texts):
        return np.ones((len(texts), 2))


class Head:
    def __init__(self, value):
        self.value = value

    def predict(self, x):
        return np.full(len(x), self.value)


def bundle():
    return {'schema_version': 2, 'encoder_path': 'unused',
            'axis_routing': {'Formality': 'f', 'Humor': 'h', 'Curiosity': 'c'},
            'components': {
                'f': {'family': 'embedding', 'base': Head(102), 'residual': Head(-49)},
                'h': {'family': 'embedding', 'base': Head(1)},
                'c': {'family': 'embedding', 'base': Head(52), 'residual': Head(1)}}}


def test_components_add_raw_residual_before_clipping_or_quantization():
    model = SelectedFHCModel(bundle(), encoder=Encoder())
    # Rounding each component first or clipping the base first changes F/C.
    expected = {'Formality': 55, 'Humor': 0, 'Curiosity': 55}
    assert model.predict_many(['one', 'two']) == [expected, expected]
    assert model.predict_partial('one') == expected


def test_nonfinite_selected_head_cannot_silently_use_other_component():
    data = bundle()
    data['components']['h']['base'] = Head(float('nan'))
    with pytest.raises(ValueError, match='Invalid head predictions'):
        SelectedFHCModel(data, encoder=Encoder()).predict_many(['text'])


def test_missing_axis_is_rejected_before_inference():
    data = bundle()
    del data['axis_routing']['Humor']
    with pytest.raises(ValueError, match='schema'):
        SelectedFHCModel(data, encoder=Encoder())
