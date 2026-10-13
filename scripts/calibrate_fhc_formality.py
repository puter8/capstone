"""Tiny train-only, group-held-out calibration of AI Formality to human scores."""
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import Ridge

from scripts.compare_fhc_improvements import DEST, components, quantize
from scripts.compare_full_corpus_labelers import OUT
from scripts.train_transfer_axis_models import TRAIN, read_rows
from scripts.train_fhc_reviewed_augmentation import validated_annotations

TARGET = DEST / 'alignment'
FIELDS = ('respect_face', 'mitigation', 'spoken_register')
GRID = ('identity', 'median_offset', 'affine_ridge', 'component_ridge', 'human_median')


def fit(name, x, y):
    if name == 'identity':
        return {'kind': name}
    if name == 'median_offset':
        return {'kind': name, 'offset': float(np.median(y - x[:, 0]))}
    if name == 'human_median':
        return {'kind': name, 'median': float(np.median(y))}
    features = x[:, :1] if name == 'affine_ridge' else x[:, 1:]
    return {'kind': name, 'model': Ridge(alpha=1.0).fit(features, y)}


def predict(calibrator, x):
    name = calibrator['kind']
    if name == 'identity':
        values = x[:, 0]
    elif name == 'median_offset':
        values = x[:, 0] + calibrator['offset']
    elif name == 'human_median':
        values = np.full(len(x), calibrator['median'])
    else:
        values = calibrator['model'].predict(x[:, :1] if name == 'affine_ridge' else x[:, 1:])
    return quantize(values)


def metrics(y, pred):
    error = pred - y
    return {'n': len(y), 'coverage': 1.0, 'mae': float(np.mean(abs(error))),
            'rmse': float(np.sqrt(np.mean(error ** 2))), 'within10': float(np.mean(abs(error) <= 10)),
            'bias': float(np.mean(error))}


def main():
    TARGET.mkdir(exist_ok=True)
    source = DEST / 'human_calibration'
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256(TRAIN.read_bytes()).hexdigest() != manifest['input_sha256'][TRAIN.name]:
        raise ValueError('Human training file changed')
    selection = json.loads((source / 'protocol.json').read_text(encoding='utf-8'))
    ids = selection['IDs']
    raw = json.loads((source / 'reviewer.json').read_text(encoding='utf-8'))
    validated = validated_annotations(raw, ids)
    raw_by_id = {r['item_id']: r for r in raw}
    human_by_id = {r['item_id']: r for r in read_rows(TRAIN)}
    assert len(ids) == 18 and set(ids) <= set(manifest['train_ids'])
    assert all(validated[i]['score_status']['Formality'] == 'final' for i in ids)
    rows = [human_by_id[i] for i in ids]
    # Groups computed on the entire existing clean training pool preserve transitive links.
    all_rows = [human_by_id[i] for i in manifest['train_ids']]
    all_groups = dict(zip(manifest['train_ids'], components(all_rows)))
    groups = np.array([all_groups[i] for i in ids])
    x = np.array([[validated[i]['axes']['Formality']] + [raw_by_id[i]['formality'][f] for f in FIELDS] for i in ids], dtype=float)
    y = np.array([r['axes']['Formality'] for r in rows], dtype=float)
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (TRAIN, source / 'protocol.json', source / 'reviewer.json')}
    protocol = {'n': 18, 'ids': ids, 'groups': groups.tolist(), 'grid': GRID,
                'features': ['AI Formality score', *FIELDS], 'forbidden_features': ['cohort', 'source', 'human score at prediction time'],
                'selection': 'minimum pooled leave-one-group-out rounded OOF MAE; ties fixed grid order',
                'fit': 'calibration training groups only; Ridge alpha1 with intercept; no feature scaling',
                'baseline_eligible': True, 'dev_final_read': False, 'input_sha256': hashes,
                'limitations': ['Same 18 rows select and estimate calibration; selection optimism.',
                               '18 deliberately balanced human-training rows are not representative application evaluation.',
                               'Human/AI context conditions can differ; affine mapping cannot establish contextual validity.']}
    with (TARGET / 'protocol.json').open('x', encoding='utf-8') as f:
        json.dump(protocol, f, indent=2)
    oof, summary = {}, {}
    cohorts = {r['item_id']: r['cohort'] for r in read_rows(DEST / 'oof_predictions.jsonl')}
    for name in GRID:
        pred = np.full(18, np.nan)
        for group in sorted(set(groups)):
            tr, va = groups != group, groups == group
            pred[va] = predict(fit(name, x[tr], y[tr]), x[va])
        assert np.isfinite(pred).all()
        oof[name] = pred.tolist()
        summary[name] = {'overall': metrics(y, pred), 'cohort': {}, 'source': {}}
        for field in ('cohort', 'source'):
            labels = [cohorts[i] for i in ids] if field == 'cohort' else [r['source'] for r in rows]
            for label in sorted(set(labels)):
                idx = np.array([v == label for v in labels])
                summary[name][field][label] = metrics(y[idx], pred[idx])
    chosen = min(GRID, key=lambda name: summary[name]['overall']['mae'])
    with (TARGET / 'selection_lock.json').open('x', encoding='utf-8') as f:
        json.dump({'chosen': chosen, 'rule': protocol['selection'], 'all18_coverage': True}, f, indent=2)
    calibrator = fit(chosen, x, y)
    bundle = {'calibrator': calibrator, 'feature_order': ['ai_formality', *FIELDS],
              'output': 'clip0to100_then_nearest5_numpy_round', 'fit_ids': ids, 'research_only': True}
    joblib.dump(bundle, TARGET / 'calibrator.joblib')
    restored = joblib.load(TARGET / 'calibrator.joblib')
    assert np.array_equal(predict(calibrator, x), predict(restored['calibrator'], x))
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p, digest in hashes.items())
    report = {'n': 18, 'group_count': len(set(groups)), 'chosen': chosen, 'candidates': summary,
              'oof': [{'item_id': i, 'group': int(groups[j]), 'human': float(y[j]), 'ai': float(x[j, 0]),
                       'predictions': {n: oof[n][j] for n in GRID}} for j, i in enumerate(ids)],
              'saved_roundtrip_verified': True, 'input_hashes_unchanged': True, 'status': 'INSUFFICIENT_GENERALIZATION_EVIDENCE',
              'limitations': protocol['limitations']}
    (TARGET / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'chosen': chosen, 'groups': len(set(groups)), 'metrics': {n: s['overall'] for n, s in summary.items()}}, indent=2))


if __name__ == '__main__':
    main()
