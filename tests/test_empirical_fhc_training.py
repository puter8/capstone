"""Strict boundaries for independent per-axis empirical training annotations."""
import pytest

from scripts.train_empirical_fhc import validate_annotations


def final(item_id='one', score=0):
    return {'item_id': item_id, 'score_status': 'final', 'score': score,
            'confidence': 3, 'evidence': 'A literal statement supports this assessment.'}


@pytest.mark.parametrize('value', [True, False, 5.0, -5, 105, 7, None])
def test_final_score_requires_integer_five_point_scale(value):
    with pytest.raises(ValueError, match='Final score'):
        validate_annotations([final(score=value)], ['one'])


def test_axis_abstention_stays_missing_and_zero_remains_a_real_label():
    incomplete = {'item_id': 'two', 'score_status': 'context_insufficient',
                  'confidence': 0, 'evidence': 'The incomplete clause lacks an interpretable target.'}
    assert validate_annotations([final(), incomplete], ['one', 'two']) == {'one': 0, 'two': None}
    incomplete['score'] = None
    assert validate_annotations([incomplete], ['two']) == {'two': None}
    incomplete['score'] = 0
    with pytest.raises(ValueError, match='cannot carry a training score'):
        validate_annotations([incomplete], ['two'])


@pytest.mark.parametrize('records', [[final('one'), final('one')], [final('one')],
                                     [final('one'), final('foreign')]])
def test_exact_annotation_identity_coverage_required(records):
    with pytest.raises(ValueError, match='Missing, duplicate, or foreign'):
        validate_annotations(records, ['one', 'two'])


def test_confidence_boolean_is_not_a_numeric_confidence():
    row = final()
    row['confidence'] = True
    with pytest.raises(ValueError, match='Invalid confidence'):
        validate_annotations([row], ['one'])


def test_other_axis_payload_cannot_be_silently_accepted():
    row = final()
    row['axes'] = {'Formality': 50, 'Humor': 0, 'Curiosity': 0}
    with pytest.raises(ValueError, match='Unexpected annotation schema'):
        validate_annotations([row], ['one'])


def test_empty_evidence_rejected():
    row = final()
    row['evidence'] = '  '
    with pytest.raises(ValueError, match='Missing annotation evidence'):
        validate_annotations([row], ['one'])
