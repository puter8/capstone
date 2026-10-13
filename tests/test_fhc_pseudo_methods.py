"""Behavioral checks for fold-local pseudo fitting and human residual correction."""
import numpy as np
import pytest
from scipy.sparse import csr_matrix
from sklearn.linear_model import Ridge

from scripts.compare_fhc_pseudo_methods import fit_head, raw_prediction


@pytest.mark.parametrize('sparse', [False, True])
def test_joint_duplicate_pool_cannot_increase_total_pseudo_influence(sparse):
    human_x = np.array([[0.], [1.], [2.]])
    pseudo_x = np.array([[.5], [1.5]])
    human_y, pseudo_y = np.array([0., 20., 40.]), np.array([80., 90.])
    repeated_x = np.tile(pseudo_x, (7, 1))
    if sparse:
        human_x, pseudo_x, repeated_x = map(csr_matrix, (human_x, pseudo_x, repeated_x))
    small = fit_head('joint', human_x, human_y, pseudo_x, pseudo_y, 1.)
    repeated = fit_head('joint', human_x, human_y, repeated_x, np.tile(pseudo_y, 7), 1.)
    assert np.allclose(raw_prediction(small, human_x), raw_prediction(repeated, human_x))


def test_human_only_head_is_independent_of_all_pseudo_targets():
    x = np.array([[0.], [1.], [2.]])
    y = np.array([0., 20., 40.])
    low = fit_head('human_only', x, y, x, np.zeros(3), .1)
    high = fit_head('human_only', x, y, x, np.full(3, 100.), .1)
    assert np.array_equal(raw_prediction(low, x), raw_prediction(high, x))
    assert low['residual'] is None and high['residual'] is None


def test_residual_corrects_raw_base_before_any_clipping_or_rounding():
    pseudo_x = np.array([[0.], [1.]])
    pseudo_y = np.array([0., 100.])
    human_x = np.array([[2.], [3.], [4.]])
    # Construct an exact constant discrepancy from the actual pseudo-only Ridge.
    reference = Ridge(alpha=.1).fit(pseudo_x, pseudo_y, sample_weight=np.full(2, 3 / 2))
    human_y = reference.predict(human_x) - 150.
    head = fit_head('residual', human_x, human_y, pseudo_x, pseudo_y, .1)
    assert np.any(head['base'].predict(human_x) > 100)
    assert np.allclose(head['residual'].predict(human_x), -150.)
    assert np.allclose(raw_prediction(head, human_x), human_y)
