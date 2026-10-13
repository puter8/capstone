"""Offline, predeclared dual-review AI augmentation; human labels stay untouched."""
from __future__ import annotations

import hashlib
import json

import joblib
import numpy as np
from sklearn.linear_model import Ridge

from ai.ridge_axis_adapter import RidgeAxisAdapter
from scripts.compare_fhc_improvements import DEST, load_inputs, stratified
from scripts.compare_full_corpus_labelers import AXES
from scripts.fhc_round2_label import compute_labels
from scripts.fhc_round2_select import ami_series
from scripts.train_full_corpus_fhc import vector_predictions


def validated_annotations(records, expected_ids):
    if len(records) != len(expected_ids) or {r['item_id'] for r in records} != set(expected_ids):
        raise ValueError('Reviewer coverage/duplicate IDs mismatch')
    return {r['item_id']: compute_labels({k: v for k, v in r.items() if k != 'item_id'}) for r in records}


def accepted_axes(a, b):
    return {axis: a['axes'][axis] for axis in AXES
            if a['score_status'][axis] == b['score_status'][axis] == 'final'
            and abs(a['axes'][axis] - b['axes'][axis]) <= 10}


def main():
    dest = DEST / 'reviewed_augmentation'
    dest.mkdir(exist_ok=True)
    if (dest / 'report.json').exists():
        raise FileExistsError('Refusing to overwrite completed experiment')
    protocol_path = DEST / 'augmentation_protocol.json'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    human, dev, manifest = load_inputs()
    acquisition = DEST / 'acquisition'
    batch = [json.loads(line) for line in (acquisition / 'blind_batch24.jsonl').read_text(encoding='utf-8').splitlines()]
    ids = [r['item_id'] for r in batch]
    a = validated_annotations(json.loads((acquisition / 'reviewer_a.json').read_text(encoding='utf-8')), ids)
    b = validated_annotations(json.loads((acquisition / 'reviewer_b.json').read_text(encoding='utf-8')), ids)
    decisions = [{'item_id': r['item_id'], 'utterance': r['utterance'],
                  'raw_axes': {axis: a[r['item_id']]['axes'][axis] for axis in AXES
                               if a[r['item_id']]['score_status'][axis] == 'final'},
                  'accepted_axes': accepted_axes(a[r['item_id']], b[r['item_id']]),
                  'provenance': 'dual_codex_review_pseudo_not_human'} for r in batch]
    (dest / 'gate_decisions.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in decisions), encoding='utf-8')
    base = joblib.load(DEST / 'nonconstant_candidate.joblib')
    if any(not name.startswith('tfidf_') for name in base['chosen'].values()):
        raise ValueError('This controlled augmentation supports the locked TFIDF candidates only')
    predictions, results = {}, {}
    for arm, axis_key in [('human_nonconstant', None), ('human_plus_reviewer_a', 'raw_axes'),
                          ('human_plus_agreement_gated', 'accepted_axes')]:
        model = RidgeAxisAdapter()
        # All arms use exactly the same human-only vocabulary and CV-selected alpha.
        reference = base['tfidf_models'][AXES[0]]
        model.word_vec, model.char_vec = reference.word_vec, reference.char_vec
        for axis in AXES:
            anchors = [r for r in human if axis in r['axes']]
            texts = [r['utterance'] for r in anchors]
            yy = [r['axes'][axis] for r in anchors]
            weights = [protocol['human_weight']] * len(anchors)
            if axis_key:
                additions = [r for r in decisions if axis in r[axis_key]]
                texts += [r['utterance'] for r in additions]
                yy += [r[axis_key][axis] for r in additions]
                weights += [protocol['ai_weight']] * len(additions)
            alpha = float(base['chosen'][axis].split('_')[1])
            model.axis_models[axis] = Ridge(alpha=alpha, solver='lsqr').fit(model._vectorize(texts), yy, sample_weight=weights)
        pred = vector_predictions(model, [r['utterance'] for r in dev])
        path = dest / (arm + '.joblib')
        joblib.dump(model, path)
        assert pred == vector_predictions(joblib.load(path), [r['utterance'] for r in dev])
        predictions[arm], results[arm] = pred, stratified(dev, pred)
        print(arm, {axis: results[arm]['overall'][axis]['mae'] for axis in AXES}, flush=True)
    original = json.loads((DEST / 'nonconstant_predictions.json').read_text(encoding='utf-8'))
    if original != predictions['human_nonconstant']:
        raise ValueError('Human baseline does not reproduce locked candidate')
    groups = sorted({ami_series(r['source_group']) for r in dev})
    rng = np.random.default_rng(20261013)
    uncertainty = {}
    for arm in ('human_plus_reviewer_a', 'human_plus_agreement_gated'):
        uncertainty[arm] = {}
        for axis in AXES:
            by_group = {group: [abs(p[axis] - r['axes'][axis]) - abs(q[axis] - r['axes'][axis])
                        for r, p, q in zip(dev, predictions[arm], original)
                        if axis in r['axes'] and ami_series(r['source_group']) == group] for group in groups}
            deltas = []
            for _ in range(2000):
                errors = [value for group in rng.choice(groups, len(groups), replace=True) for value in by_group[group]]
                if errors:
                    deltas.append(float(np.mean(errors)))
            uncertainty[arm][axis] = {'delta_mae_vs_human': results[arm]['overall'][axis]['mae'] - results['human_nonconstant']['overall'][axis]['mae'],
                                     'descriptive_group_bootstrap_95pct': np.percentile(deltas, [2.5, 97.5]).tolist()}
    paths = [protocol_path, DEST / 'nonconstant_lock.json', acquisition / 'blind_batch24.jsonl',
             acquisition / 'reviewer_a.json', acquisition / 'reviewer_b.json']
    report = {'protocol': protocol, 'label_counts': {key: {axis: sum(axis in r[key] for r in decisions) for axis in AXES}
                                                    for key in ('raw_axes', 'accepted_axes')},
              'dual_reviewed_rows': len(batch), 'gated_usable_rows': sum(bool(r['accepted_axes']) for r in decisions),
              'metrics': results, 'descriptive_uncertainty': uncertainty,
              'inputs_sha256': {str(p.relative_to(DEST)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'human_inputs_sha256': manifest['input_sha256'],
              'baseline_reproduced': True, 'roundtrip_verified': True, 'model_selected_from_these_dev_results': False,
              'final_test_used': False, 'production_changed': False,
              'interpretation': 'AI agreement is not accuracy against independent human labels. No performance PASS claimed.'}
    (dest / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    (dest / 'dev_predictions.json').write_text(json.dumps(predictions, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
