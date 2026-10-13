"""Report reference agreement and input variation without using final labels."""
from __future__ import annotations

import json
import argparse

import numpy as np
from scipy.stats import spearmanr

from scripts.compare_full_corpus_labelers import AXES, OUT
from scripts.train_transfer_axis_models import read_rows

TARGET = OUT / 'improvement' / 'representation_round'


def axis_diagnostics(reference, predictions, groups):
    y, p = np.asarray(reference, dtype=float), np.asarray(predictions, dtype=float)
    if y.ndim != 1 or y.shape != p.shape or len(y) != len(groups) or not len(y):
        raise ValueError('Aligned nonempty one-dimensional arrays required')
    if not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError('Finite scores required')
    within = []
    for fold in sorted(set(groups)):
        values = p[np.asarray(groups) == fold]
        within.append({'fold': int(fold), 'n': len(values), 'unique_predictions': len(np.unique(values)),
                       'prediction_std': float(np.std(values))})
    rank = None if len(np.unique(y)) < 2 or len(np.unique(p)) < 2 else float(spearmanr(y, p).statistic)
    return {'n': len(y), 'mae': float(np.mean(abs(p - y))), 'spearman': rank,
            'prediction_std': float(np.std(p)), 'reference_std': float(np.std(y)),
            'unique_predictions': len(np.unique(p)), 'within_fold_variation': within}


def main(pseudo=False):
    protocol = json.loads((TARGET / 'protocol.json').read_text(encoding='utf-8'))
    folds = {key: fold for fold, spec in enumerate(protocol['folds']) for key in spec['validation_ids']}
    rows = read_rows(TARGET / 'oof_predictions.jsonl')
    chosen = json.loads((TARGET / 'selection_lock.json').read_text(encoding='utf-8'))['chosen']
    destination = TARGET
    names = ['median_None', 'tfidf_0.1', 'selected_representation']
    if pseudo:
        destination = OUT / 'improvement' / 'representation_pseudo'
        candidate = json.loads((destination / 'oof_predictions.json').read_text(encoding='utf-8'))
        arms = json.loads((destination / 'selection_lock.json').read_text(encoding='utf-8'))['chosen']
        if candidate['ids'] != [r['item_id'] for r in rows]:
            raise ValueError('Pseudo and representation OOF rows are not aligned')
        for i, row in enumerate(rows):
            for arm, predictions in candidate['predictions'].items():
                row['predictions']['pseudo_' + arm] = predictions[i]
            row['predictions']['pseudo_selected'] = {a: candidate['predictions'][arms[a]][i][a] for a in AXES}
        names += ['pseudo_' + arm for arm in candidate['predictions']] + ['pseudo_selected']
    result = {}
    for name in names:
        result[name] = {}
        for axis in AXES:
            selected = [r for r in rows if axis in r['human_reference']]
            key = chosen[axis] if name == 'selected_representation' else name
            result[name][axis] = axis_diagnostics([r['human_reference'][axis] for r in selected],
                                                  [r['predictions'][key][axis] for r in selected],
                                                  [folds[r['item_id']] for r in selected])
    for name, scores in result.items():
        for axis, metrics in scores.items():
            baseline = result['median_None'][axis]['mae']
            metrics['MAE_skill_over_fold_training_median'] = 1 - metrics['mae'] / baseline if baseline else None
    report = {'scope': 'exploratory model-selection OOF diagnostics; no final or dev labels parsed',
              'metrics': result,
              'limitations': ['Variation alone is not quality; inspect rank/reference agreement jointly.',
                              'A pooled fold-median can vary between folds but is constant within each fold.',
                              'Selected representation scores are optimistic selection CV, not independent tests.',
                              'No claim about visible app response; production mappings and rendering need separate validation.']}
    (destination / 'responsiveness.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({name: {a: {'mae': m['mae'], 'spearman': m['spearman'], 'unique': m['unique_predictions']} for a, m in scores.items()} for name, scores in result.items()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pseudo', action='store_true')
    main(pseudo=parser.parse_args().pseudo)
