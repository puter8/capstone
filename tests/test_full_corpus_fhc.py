"""Offline checks for held-out protection and honest missing-prediction metrics."""
from scripts.compare_full_corpus_labelers import metrics
from scripts.prepare_full_corpus_fhc import ReservedIndex
from scripts.fhc_round2_select import is_near_dup, word_set
from scripts.train_full_corpus_fhc import MAX_USD, PRIOR_RESERVE_USD


def test_near_duplicate_index_preserves_reference_rule():
    refs = ['one two three four five', 'can you explain this result', 'hello']
    index = ReservedIndex(refs)
    for text in ['one two three four', 'one two three', 'HELLO', '', 'different sentence',
                 'can you explain this result again']:
        assert index.matches(text) == is_near_dup(word_set(text), [word_set(r) for r in refs])


def test_missing_model_output_stays_in_recall_denominator():
    rows = [{'axes': {'Formality': 0}}, {'axes': {'Formality': 0}},
            {'axes': {'Formality': 50}}, {'axes': {'Formality': 100}}]
    scores = [{'Formality': 0}, {}, {'Formality': 50}, {'Formality': 100}]
    result = metrics(rows, scores)['Formality']
    assert result['n'] == 4 and result['valid_predictions'] == 3
    assert result['coverage'] == 0.75
    assert result['tier_support'] == [2, 1, 1]
    assert result['tier_recall'] == [0.5, 1.0, 1.0]
    assert result['gate'] == 'FAIL_MISSING_PREDICTIONS'


def test_budget_leaves_margin_under_owner_cap():
    assert 0 < PRIOR_RESERVE_USD < MAX_USD
    assert MAX_USD * 3000 < 1000
