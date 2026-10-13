"""Protection and weighting invariants for reuse of historical corpus labels."""
import copy

import numpy as np
import pytest

from scripts.train_empirical_full_corpus_fhc import admit_pseudo, pseudo_weights


def pseudo():
    return {'item_id': 'local', 'status': 'pseudo_not_human_ground_truth',
            'axes': {'Formality': 50, 'Humor': 0, 'Curiosity': 10},
            'label_source': {'Formality': 'local_human_embedding_pseudo',
                             'Humor': 'local_augmented_tfidf_pseudo',
                             'Curiosity': 'local_augmented_tfidf_pseudo'}}


def test_reviewed_item_excluded_before_old_labels_are_interpreted():
    # Old direct judgments can be partial or invalid for the local-pseudo schema.
    # Their ID takes precedence: never fill omitted new axes from these values.
    row = {'item_id': 'reviewed', 'axes': {'Humor': 85},
           'label_source': {'Humor': 'old_reviewer'}}
    before = copy.deepcopy(row)
    assert admit_pseudo(row, {'reviewed'}) is False
    assert row == before
    assert admit_pseudo(pseudo(), {'reviewed'}) is True


def test_pseudo_origin_cannot_be_gemini_or_human_masquerade():
    for origin in ('gemini_human_examples_pseudo', 'human_consensus', 'codex_in_chat_pseudo_not_human'):
        row = pseudo()
        row['label_source']['Humor'] = origin
        with pytest.raises(ValueError, match='provenance'):
            admit_pseudo(row, set())


def test_partial_corpus_labels_are_rejected_instead_of_filled():
    row = pseudo()
    del row['axes']['Curiosity']
    with pytest.raises(ValueError, match='missing pseudo axis'):
        admit_pseudo(row, set())


@pytest.mark.parametrize('value', [True, 7, -5, 105, float('nan')])
def test_invalid_pseudo_targets_rejected(value):
    row = pseudo()
    row['axes']['Humor'] = value
    with pytest.raises(ValueError, match='Invalid pseudo score'):
        admit_pseudo(row, set())


def test_total_pseudo_weight_does_not_grow_with_corpus_size():
    small = pseudo_weights([0, 10], [0, 10], human_count=110, ratio=.25)
    large = pseudo_weights(np.zeros(2000), np.zeros(2000), human_count=110, ratio=.25)
    assert small.sum() == pytest.approx(27.5)
    assert large.sum() == pytest.approx(small.sum())
    assert large.max() < small.min()


def test_agreement_changes_relative_weight_but_not_total_mass():
    weights = pseudo_weights([0, 20, 100], [0, 10, 0], 118, .25, agreement=True)
    assert weights[0] > weights[1] > weights[2] > 0
    assert weights.sum() == pytest.approx(29.5)
    assert weights[0] / weights[1] == pytest.approx(2)
    assert np.array_equal(pseudo_weights([10], [0], 118, 0, agreement=True), [0])


@pytest.mark.parametrize('human_count,ratio', [(float('nan'), .25), (float('inf'), .25),
                                               (118, float('nan')), (118, float('inf'))])
def test_nonfinite_normalization_parameters_rejected(human_count, ratio):
    with pytest.raises(ValueError, match='Invalid weight inputs'):
        pseudo_weights([10], [10], human_count, ratio)
