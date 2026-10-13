"""Leakage and eligibility checks for the bounded nested selection procedure."""
import copy

import numpy as np

from scripts import search_fhc_models as search


def test_own_heldout_labels_cannot_change_own_fold_predictions(monkeypatch):
    texts = ['please explain apples', 'discuss ripe bananas', 'quiet library meeting',
             'interesting river question', 'casual morning greeting', 'technical network review']
    rows = [{'utterance': t, 'axes': {a: i * 15 for a in search.AXES}} for i, t in enumerate(texts)]
    splits = [(np.array([2, 3, 4, 5]), np.array([0, 1])),
              (np.array([0, 1, 4, 5]), np.array([2, 3])),
              (np.array([0, 1, 2, 3]), np.array([4, 5]))]
    embeddings = np.arange(18, dtype=float).reshape(6, 3)
    candidates = [{'family': 'tfidf', 'model': 'ridge', 'params': {'alpha': 1.}}]
    observed = []
    original = search.fit_vocabulary

    def record_fit(train_texts):
        observed.append(list(train_texts))
        return original(train_texts)

    monkeypatch.setattr(search, 'fit_vocabulary', record_fit)
    before = search.evaluate_grid(rows, embeddings, splits, candidates)[1]
    altered = copy.deepcopy(rows)
    altered[0]['axes'] = {a: 100 for a in search.AXES}
    altered[1]['axes'] = {a: 100 for a in search.AXES}
    after = search.evaluate_grid(altered, embeddings, splits, candidates)[1]
    for a in search.AXES:
        assert np.array_equal(before[0][a][:2], after[0][a][:2])
    expected_texts = [[texts[i] for i in tr] for tr, _ in splits]
    assert observed == expected_texts + expected_texts


def test_lower_mae_ineligible_model_is_not_silently_selected():
    bad = {a: {'eligible': False, 'mae': 0.} for a in search.AXES}
    allowed = {a: {'eligible': True, 'mae': 15.} for a in search.AXES}
    assert search.choose([bad, allowed, allowed]) == {a: 1 for a in search.AXES}
    assert search.choose([bad]) == {a: None for a in search.AXES}


def test_response_guard_rejects_variation_confined_to_one_fold():
    folds = np.array([0, 0, 1, 1, 2, 2])
    pred = np.array([0, 100, 50, 50, 50, 50])
    summary = search.summarize(np.array([0, 90, 40, 50, 60, 70]), pred, folds)
    assert summary['std'] >= 2.5 and summary['distinct'] == 3
    assert summary['eligible'] is False


def test_embedding_rules_runtime_matches_training_features_exactly():
    from ai.researched_axis_model import ResearchedAxisModel

    texts = ['Could you explain why this happened?', 'yo that was funny lol']
    embeddings = np.array([[.6, .8], [0., 1.]])
    expected = search.features_for('embedding_rules', None, embeddings, texts)

    class Encoder:
        def _encode(self, supplied):
            assert supplied == texts
            return embeddings.copy()

    class CaptureHead:
        def predict(self, features):
            assert features.shape == (2, 5)
            assert np.array_equal(features, expected)
            # The semantic block is unchanged, with three distinct rule features.
            assert np.array_equal(features[:, :2], embeddings)
            return np.array([25., 50.])

    bundle = {'schema_version': 1, 'encoder_path': 'unused-local-encoder',
              'configs': {a: {'family': 'embedding_rules'} for a in search.AXES},
              'heads': {a: CaptureHead() for a in search.AXES}}
    result = ResearchedAxisModel(bundle, encoder=Encoder()).predict_many(texts)
    assert result == [{a: 25 for a in search.AXES}, {a: 50 for a in search.AXES}]
