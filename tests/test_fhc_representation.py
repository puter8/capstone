"""Feature isolation and scale invariants for the FHC representation experiment."""
import numpy as np
import pytest
from scipy.sparse import csr_matrix

from scripts.compare_fhc_representation import (
    fit_vocabulary, lexical_features, representation_features, predict_bundle,
)


def test_heldout_text_cannot_create_training_vocabulary():
    vocabulary = fit_vocabulary(['we discuss the project', 'the project needs work'])
    original = {kind: dict(v.vocabulary_) for kind, v in vocabulary.items()}
    heldout = lexical_features(vocabulary, ['zzzzzz'])
    assert heldout.nnz == 0
    assert all(v.vocabulary_ == original[kind] for kind, v in vocabulary.items())
    assert 'zzzzzz' not in vocabulary['word'].vocabulary_


def test_combined_modalities_have_equal_norm_despite_arbitrary_input_scale():
    lexical = csr_matrix([[30., 40.], [0., 7.]])
    embedding = np.array([[.6, .8], [9., 0.]])
    before_lexical, before_embedding = lexical.copy(), embedding.copy()
    joined = representation_features('combined', lexical, embedding).toarray()
    assert np.allclose(np.sum(joined[:, :2] ** 2, axis=1), .5)
    assert np.allclose(np.sum(joined[:, 2:] ** 2, axis=1), .5)
    assert np.allclose(np.sum(joined ** 2, axis=1), 1)
    assert np.array_equal(lexical.toarray(), before_lexical.toarray())
    assert np.array_equal(embedding, before_embedding)
    rescaled = representation_features('combined', lexical * 100, embedding * .01).toarray()
    assert np.allclose(joined, rescaled)


def test_oov_zero_lexical_block_does_not_create_nan_or_borrow_signal():
    joined = representation_features('combined', csr_matrix((1, 3)), np.array([[3., 4.]])).toarray()
    assert np.isfinite(joined).all()
    assert np.array_equal(joined[:, :3], np.zeros((1, 3)))
    assert np.sum(joined ** 2) == pytest.approx(.5)


def test_tfidf_bundle_does_not_require_or_call_semantic_encoder():
    from sklearn.linear_model import Ridge

    texts = ['please explain the project', 'stop doing that now']
    vocabulary = fit_vocabulary(texts)
    x = lexical_features(vocabulary, texts)
    targets = {'Formality': [80, 10], 'Humor': [0, 5], 'Curiosity': [70, 0]}
    heads = {axis: Ridge(alpha=.1).fit(x, values) for axis, values in targets.items()}
    bundle = {'vocabulary': vocabulary,
              'config': {axis: {'family': 'tfidf', 'alpha': .1} for axis in targets},
              'heads': heads, 'encoder_path': 'must-not-be-opened'}

    class ForbiddenEncoder:
        def _encode(self, sentences):
            raise AssertionError('Lexical-only bundle attempted a semantic model call')

    result = predict_bundle(bundle, texts, encoder=ForbiddenEncoder())
    assert len(result) == 2 and all(set(row) == set(targets) for row in result)
    assert result[0]['Formality'] > result[1]['Formality']
    assert result[0]['Curiosity'] > result[1]['Curiosity']
    assert all(0 <= v <= 100 and v % 5 == 0 for row in result for v in row.values())
