"""Offline safeguards for training-only FHC improvement experiments."""
import json
from pathlib import Path

import pytest
import numpy as np
from sklearn.model_selection import GroupKFold

from scripts.compare_fhc_improvements import components, score
from scripts.fhc_round2_select import ami_series, is_near_dup, word_set
from scripts import select_fhc_improvement_candidates as acquisition
from scripts.train_fhc_reviewed_augmentation import accepted_axes, validated_annotations
from scripts.verify_fhc_calibration import fresh_sample, formality, direct_formality
from scripts.calibrate_fhc_formality import fit, predict


def test_group_folds_protect_series_and_transitive_text_connections():
    rows = [
        {'source_group': 'ES2001a', 'utterance': 'project scheduling is discussed today'},
        {'source_group': 'ES2001d', 'utterance': 'one two three four five six seven eight'},
        {'source_group': 'Bmr010', 'utterance': 'one two three four five six seven eight nine ten'},
        {'source_group': 'Bmr011', 'utterance': 'three four five six seven eight nine ten'},
        {'source_group': 'Bmr012', 'utterance': 'apples oranges bananas'},
        {'source_group': 'Bmr013', 'utterance': 'rivers lakes oceans'},
    ]
    # Endpoints are not near duplicates, but a middle utterance connects them.
    assert not is_near_dup(word_set(rows[1]['utterance']), [word_set(rows[3]['utterance'])])
    groups = components(rows)
    assert len(set(groups[:4])) == 1
    assert len(set(groups)) == 3
    for train, validation in GroupKFold(n_splits=3).split(rows, groups=groups):
        assert not set(groups[i] for i in train) & set(groups[i] for i in validation)
        for i in train:
            for j in validation:
                assert ami_series(rows[i]['source_group']) != ami_series(rows[j]['source_group'])
                assert not is_near_dup(word_set(rows[i]['utterance']), [word_set(rows[j]['utterance'])])


def test_partial_predictions_report_missing_support_without_inventing_errors():
    rows = [{'axes': {'Formality': 0}}, {'axes': {'Formality': 50}},
            {'axes': {'Formality': 100}}, {'axes': {'Humor': 5}}]
    predictions = [{'Formality': 10}, {}, {'Formality': 90}, {'Humor': 5}]
    result = score(rows, predictions)
    assert result['Formality']['n'] == 3
    assert result['Formality']['coverage'] == pytest.approx(2 / 3)
    assert result['Formality']['mae'] == 10
    assert result['Formality']['rmse'] == 10
    assert result['Formality']['bias_prediction_minus_human'] == 0
    assert result['Formality']['gate'] == 'FAIL_MISSING_PREDICTIONS'
    assert result['Curiosity']['mae'] is None
    assert result['Curiosity']['rmse'] is None


def test_acquisition_rejects_in_sample_predictions_before_opening_corpus(monkeypatch):
    root = Path('synthetic-fhc-root')
    base = root / 'data/models/full-corpus-fhc'
    train = root / 'data/fixtures/pally_purpose_v3_train_dev_split_train.jsonl'
    manifest = {'train_ids': ['human1'], 'input_sha256': {
        train.name: 'synthetic-hash'}}
    oof = base / 'oof_predictions.jsonl'
    files = {
        train: json.dumps({'item_id': 'human1', 'axes': {'Formality': 50}}),
        base / 'pilot_manifest.json': json.dumps(manifest),
        oof: json.dumps({'item_id': 'human1', 'predictions': {'tfidf_1.0': {'Formality': 50}}}),
        base / 'protocol.json': json.dumps({'folds': [
            {'train_ids': ['human1'], 'validation_ids': ['human1']}]}),
    }
    monkeypatch.setattr(Path, 'read_text', lambda path, **kwargs: files[path])
    monkeypatch.setattr(acquisition, 'sha', lambda path: 'synthetic-hash')
    monkeypatch.setattr(acquisition, 'ROOT', root)
    monkeypatch.setattr(acquisition, 'BASE', base)
    # No corpus file exists: the invalid OOF partition must fail before acquisition.
    with pytest.raises(ValueError, match='invalid OOF train/validation partition'):
        acquisition.select(oof, base / 'acquisition')


@pytest.mark.parametrize('provisional_reviewer', ['a', 'b'])
def test_agreement_gate_requires_final_labels_and_keeps_original_target(provisional_reviewer):
    a = {'axes': {'Formality': 40, 'Humor': 20, 'Curiosity': 50},
         'score_status': {'Formality': 'final', 'Humor': 'final', 'Curiosity': 'final'}}
    b = {'axes': {'Formality': 50, 'Humor': 20, 'Curiosity': 65},
         'score_status': {'Formality': 'final', 'Humor': 'final', 'Curiosity': 'final'}}
    (a if provisional_reviewer == 'a' else b)['score_status']['Humor'] = 'provisional'
    # F differs by the accepted boundary10: preserve A40, never average to45.
    # H agrees numerically but is provisional. C differs by15 and is rejected.
    assert accepted_axes(a, b) == {'Formality': 40}
    assert a['axes']['Formality'] == 40 and b['axes']['Formality'] == 50


@pytest.mark.parametrize('records', [
    [{'item_id': 'a'}, {'item_id': 'a'}],
    [{'item_id': 'a'}],
    [{'item_id': 'a'}, {'item_id': 'foreign'}],
])
def test_annotation_coverage_rejected_before_scoring(records):
    # Invalid coverage must fail before score parsing, even if bodies are malformed.
    with pytest.raises(ValueError, match='Reviewer coverage/duplicate IDs mismatch'):
        validated_annotations(records, ['a', 'b'])


def test_fresh_selection_blocks_related_groups_and_ignores_score_values():
    rows = [
        {'item_id': 'prompt', 'source_group': 'ES2001a', 'utterance': 'original prompt text'},
        {'item_id': 'sibling', 'source_group': 'ES2001d', 'utterance': 'one two three four five six seven eight'},
        {'item_id': 'bridge', 'source_group': 'other', 'utterance': 'one two three four five six seven eight nine ten'},
        {'item_id': 'safe1', 'source_group': 'safe1', 'utterance': 'independent apples oranges'},
        {'item_id': 'safe2', 'source_group': 'safe2', 'utterance': 'river lake ocean'},
    ]
    for row in rows:
        row['axes'] = {'Formality': 5}
    selected, eligible, ngroups = fresh_sample(rows, {'prompt'}, count=2)
    assert {r['item_id'] for r, _ in selected} == {'safe1', 'safe2'}
    assert eligible == ngroups == 2
    first_order = [r['item_id'] for r, _ in selected]
    for i, row in enumerate(rows):
        row['axes']['Formality'] = i * 25
    assert [r['item_id'] for r, _ in fresh_sample(rows, {'prompt'}, count=2)[0]] == first_order


def test_formality_only_schema_preserves_half_up_and_abstention():
    record = {'item_id': 'opaque', 'formality': {'respect_face': 1, 'mitigation': 0,
        'spoken_register': 2, 'case_type': 'context_insufficient', 'confidence': 2,
        'evidence': 'The intended relationship requires missing context.'}}
    # 25 * (.4 + .5) =22.5, rounded half-up to25, but never a final target.
    features, final = formality(record)
    assert features == [25, 1, 0, 2]
    assert final is False
    record['formality']['respect_face'] = True
    with pytest.raises(ValueError, match='integer'):
        formality(record)


def test_calibration_offset_is_fit_from_training_residuals_only():
    x_train = np.array([[10., 0, 0, 0], [20., 1, 1, 1]])
    y_train = np.array([20., 30.])
    fitted = fit('median_offset', x_train, y_train)
    held_out = np.array([[95., 4, 4, 4], [15., 0, 1, 0]])
    assert predict(fitted, held_out).tolist() == [100., 25.]
    assert fitted['offset'] == 10.


def test_empirical_teacher_abstains_without_a_numeric_target():
    row = {'item_id': 'opaque', 'score_status': 'context_insufficient', 'evidence': 'Missing relationship context.'}
    assert direct_formality(row) == (None, False)
    row['formality_score'] = 50
    with pytest.raises(ValueError, match='omit a numeric score'):
        direct_formality(row)


@pytest.mark.parametrize('invalid', [True, 101, -5, 23])
def test_empirical_teacher_rejects_invalid_score(invalid):
    row = {'item_id': 'opaque', 'score_status': 'final', 'formality_score': invalid,
           'evidence': 'A complete style judgment.'}
    with pytest.raises(ValueError):
        direct_formality(row)
