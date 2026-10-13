"""Offline research comparison; CV selection never consumes dev or final labels."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter

import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

from ai.embedding_axis_adapter import EmbeddingAxisAdapter
from ai.ridge_axis_adapter import RidgeAxisAdapter
from scripts.compare_full_corpus_labelers import AXES, OUT, metrics
from scripts.fhc_round2_select import ami_series, word_set, is_near_dup
from scripts.train_full_corpus_fhc import examples, vector_predictions
from scripts.train_transfer_axis_models import TRAIN, DEV, ENCODER_DIR, read_rows

DEST = OUT / 'improvement'


def write(name, obj):
    (DEST / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def quantize(values):
    return np.round(np.clip(values, 0, 100) / 5) * 5


def score(rows, predictions):
    result = metrics(rows, predictions)
    for axis, m in result.items():
        errors = np.array([pred[axis] - row['axes'][axis] for row, pred in zip(rows, predictions)
                           if axis in row['axes'] and pred.get(axis) is not None])
        m['rmse'] = float(np.sqrt(np.mean(errors ** 2))) if len(errors) else None
        m['within_10'] = float(np.mean(abs(errors) <= 10)) if len(errors) else None
        m['bias_prediction_minus_human'] = float(np.mean(errors)) if len(errors) else None
    return result


def stratified(rows, predictions):
    out = {'overall': score(rows, predictions)}
    for field in ('source', 'source_group'):
        out[field] = {}
        for value in sorted({r[field] for r in rows}):
            ids = [i for i, r in enumerate(rows) if r[field] == value]
            out[field][value] = score([rows[i] for i in ids], [predictions[i] for i in ids])
    out['label_source'] = {}
    for axis in AXES:
        out['label_source'][axis] = {}
        for value in sorted({r['label_source'][axis] for r in rows if axis in r['axes']}):
            ids = [i for i, r in enumerate(rows) if r['label_source'].get(axis) == value]
            out['label_source'][axis][value] = score([rows[i] for i in ids], [predictions[i] for i in ids])[axis]
    return out


def load_inputs():
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    for path in (TRAIN, DEV):
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['input_sha256'][path.name]:
            raise ValueError('Frozen human data changed: ' + path.name)
    by_id = {r['item_id']: r for r in read_rows(TRAIN)}
    human = [by_id[i] for i in manifest['train_ids']]
    assert len(human) == 118 and len(set(manifest['train_ids'])) == 118
    return human, read_rows(DEV), manifest


def components(rows):
    """Union meeting/AMI series and lexical near duplicates before group splitting."""
    parent = list(range(len(rows)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    words = [word_set(r['utterance']) for r in rows]
    for i, row in enumerate(rows):
        for j in range(i):
            if ami_series(row['source_group']) == ami_series(rows[j]['source_group']) or is_near_dup(words[i], [words[j]]):
                parent[root(i)] = root(j)
    return [root(i) for i in range(len(rows))]


def main():
    import torch
    torch.set_num_threads(2)
    DEST.mkdir(exist_ok=True)
    human, dev, manifest = load_inputs()
    encoder = EmbeddingAxisAdapter(model_name=str(ENCODER_DIR), local_files_only=True)
    dx = encoder._encode([r['utterance'] for r in dev])
    bundle = joblib.load(OUT / 'codex/teachers.joblib')
    models = {'human_tfidf': bundle['human'], 'augmented_tfidf': bundle['augmented'],
              'full_corpus_student': joblib.load(OUT / 'codex/student.joblib')}
    predictions = {name: vector_predictions(model, [r['utterance'] for r in dev]) for name, model in models.items()}
    for name, key in [('human_embedding', 'embedding_heads'), ('augmented_embedding', 'embedding_augmented_heads')]:
        vals = {a: quantize(model.predict(dx)) for a, model in bundle[key].items()}
        predictions[name] = [{a: int(vals[a][i]) for a in AXES} for i in range(len(dev))]
    medians = {a: int(quantize(np.median([r['axes'][a] for r in human if a in r['axes']]))) for a in AXES}
    predictions['training_median'] = [dict(medians) for r in dev]
    reproduced = {name: stratified(dev, preds) for name, preds in predictions.items()}
    old = json.loads((OUT / 'codex/training_report.json').read_text(encoding='utf-8'))
    for name in predictions:
        if name == 'training_median':
            continue
        expected = old['student_dev'] if name == 'full_corpus_student' else old['all_teacher_dev'][name]
        for a in AXES:
            assert np.isclose(expected[a]['mae'], reproduced[name]['overall'][a]['mae'])
            assert expected[a]['confusion'] == reproduced[name]['overall'][a]['confusion']
    write('reproduction.json', reproduced)
    print('REPRODUCTION ' + json.dumps({n: {a: m['mae'] for a, m in v['overall'].items()} for n, v in reproduced.items()}), flush=True)
    groups = components(human)
    folds = list(GroupKFold(n_splits=5).split(human, groups=groups))
    grid = [{'family': f, 'alpha': a} for f in ('tfidf', 'embedding') for a in (.1, 1., 10., 100.)]
    grid.append({'family': 'median', 'alpha': None})
    protocol = {'human_ids': manifest['train_ids'], 'input_sha256': manifest['input_sha256'],
                'grid': grid, 'selection': 'minimum pooled rounded OOF MAE; ties first fixed grid order',
                'primary_metric': 'MAE on 0-100 rounded scores', 'group_count': len(set(groups)),
                'folds': [{'train_ids': [human[i]['item_id'] for i in tr], 'validation_ids': [human[i]['item_id'] for i in va]} for tr, va in folds],
                'augmentation_excluded': '70 Codex examples acquired/calibrated using all118; not independent of CV holdouts',
                'final_test': 'never opened, parsed, scored, or used for selection',
                'dev': 'historically reused; existing artifact reproduction before CV; new candidate evaluated only after CV choice lock; exploratory only'}
    protocol_path = DEST / 'protocol.json'
    with protocol_path.open('x', encoding='utf-8') as f:
        json.dump(protocol, f, indent=2)
    hx = encoder._encode([r['utterance'] for r in human])
    results, oofs = {}, {}
    for cfg in grid:
        name = cfg['family'] + '_' + str(cfg['alpha'])
        pred = [{} for _ in human]
        for tr, va in folds:
            training = [human[i] for i in tr]
            if cfg['family'] == 'tfidf':
                model = RidgeAxisAdapter(alpha=cfg['alpha']).fit(examples(training))
                fold_preds = vector_predictions(model, [human[i]['utterance'] for i in va])
            else:
                vals = {}
                for a in AXES:
                    indices = [i for i in tr if a in human[i]['axes']]
                    y = [human[i]['axes'][a] for i in indices]
                    vals[a] = quantize(np.full(len(va), np.median(y)) if cfg['family'] == 'median'
                                       else Ridge(alpha=cfg['alpha']).fit(hx[indices], y).predict(hx[va]))
                fold_preds = [{a: int(vals[a][i]) for a in AXES} for i in range(len(va))]
            for i, p in zip(va, fold_preds):
                pred[i] = p
        results[name], oofs[name] = stratified(human, pred), pred
        print('CV ' + name + ' ' + json.dumps({a: results[name]['overall'][a]['mae'] for a in AXES}), flush=True)
    chosen = {a: min(results, key=lambda n: results[n]['overall'][a]['mae']) for a in AXES}
    write('cv_results.json', results)
    write('selection_lock.json', {'chosen': chosen, 'criterion': protocol['selection'], 'dev_used_for_selection': False})
    with (DEST / 'oof_predictions.jsonl').open('w', encoding='utf-8') as f:
        for i, row in enumerate(human):
            f.write(json.dumps(dict(row, cv_group=groups[i], predictions={n: p[i] for n, p in oofs.items()},
                                   selected_prediction={a: oofs[chosen[a]][i][a] for a in AXES}), ensure_ascii=False) + '\n')
    heads, tfidf_models, selected_preds = {}, {}, [{} for r in dev]
    for a, name in chosen.items():
        family, alpha = name.split('_')
        if family == 'tfidf':
            model = RidgeAxisAdapter(alpha=float(alpha)).fit(examples(human))
            tfidf_models[a] = model
            values = [p[a] for p in vector_predictions(model, [r['utterance'] for r in dev])]
        elif family == 'embedding':
            ids = [i for i, r in enumerate(human) if a in r['axes']]
            heads[a] = Ridge(alpha=float(alpha)).fit(hx[ids], [human[i]['axes'][a] for i in ids])
            values = quantize(heads[a].predict(dx))
        else:
            heads[a] = medians[a]
            values = [medians[a]] * len(dev)
        for i, value in enumerate(values):
            selected_preds[i][a] = int(value)
    joblib.dump({'chosen': chosen, 'tfidf_models': tfidf_models, 'heads': heads,
                 'encoder_path': str(ENCODER_DIR), 'train_ids': manifest['train_ids']}, DEST / 'candidate.joblib')
    write('candidate_dev.json', stratified(dev, selected_preds))
    write('dev_predictions.json', {'ids': [r['item_id'] for r in dev], 'existing': predictions, 'candidate': selected_preds})
    print('CHOSEN ' + json.dumps(chosen), flush=True)
    print('DEV ' + json.dumps({a: score(dev, selected_preds)[a]['mae'] for a in AXES}), flush=True)


def verify_outputs():
    """Audit serialized candidate and annotate diagnostic cohorts after model lock."""
    import torch
    torch.set_num_threads(2)
    human, dev, manifest = load_inputs()
    protocol = json.loads((DEST / 'protocol.json').read_text(encoding='utf-8'))
    by_id = {r['item_id']: r for r in human}
    fold_by_id = {}
    for k, fold in enumerate(protocol['folds']):
        tr, va = [by_id[i] for i in fold['train_ids']], [by_id[i] for i in fold['validation_ids']]
        assert not ({ami_series(r['source_group']) for r in tr} & {ami_series(r['source_group']) for r in va})
        assert all(not is_near_dup(word_set(r['utterance']), [word_set(v['utterance']) for v in va]) for r in tr)
        for r in va:
            assert r['item_id'] not in fold_by_id
            fold_by_id[r['item_id']] = k
    assert len(fold_by_id) == len(human)
    candidate_order = read_rows(TRAIN.parent / 'pally_purpose_v3_active_train_candidates.jsonl')
    numbers = {r['source_record_id']: i + 1 for i, r in enumerate(candidate_order)}
    def cohort(row):
        if any(v.startswith('human_consensus') for v in row['label_source'].values()):
            return 'human_consensus'
        return 'solo_initial40' if numbers[row['item_id']] <= 40 else 'solo41plus'
    oof = read_rows(DEST / 'oof_predictions.jsonl')
    with (DEST / 'oof_predictions.jsonl').open('w', encoding='utf-8') as f:
        for r in oof:
            r['fold'] = fold_by_id[r['item_id']]
            r['cohort'] = cohort(r)
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    predictions = json.loads((DEST / 'dev_predictions.json').read_text(encoding='utf-8'))
    cohort_metrics = {'train_counts': dict(Counter(cohort(r) for r in human)), 'dev_counts': dict(Counter(cohort(r) for r in dev)), 'dev': {}, 'oof': {}}
    all_dev = dict(predictions['existing'], candidate=predictions['candidate'])
    if (DEST / 'nonconstant_predictions.json').exists():
        all_dev['nonconstant'] = json.loads((DEST / 'nonconstant_predictions.json').read_text(encoding='utf-8'))
    for name, preds in all_dev.items():
        cohort_metrics['dev'][name] = {}
        for c in sorted({cohort(r) for r in dev}):
            ids = [i for i, r in enumerate(dev) if cohort(r) == c]
            cohort_metrics['dev'][name][c] = score([dev[i] for i in ids], [preds[i] for i in ids])
    for name in oof[0]['predictions']:
        cohort_metrics['oof'][name] = {}
        for c in sorted({r['cohort'] for r in oof}):
            rows = [r for r in oof if r['cohort'] == c]
            cohort_metrics['oof'][name][c] = score(rows, [r['predictions'][name] for r in rows])
    write('cohort_metrics.json', cohort_metrics)
    model = joblib.load(DEST / 'candidate.joblib')
    encoder = EmbeddingAxisAdapter(model_name=model['encoder_path'], local_files_only=True)
    actual = [{} for r in dev]
    for a, name in model['chosen'].items():
        if name.startswith('tfidf'):
            values = [p[a] for p in vector_predictions(model['tfidf_models'][a], [r['utterance'] for r in dev])]
        elif name.startswith('median'):
            values = [model['heads'][a]] * len(dev)
        else:
            values = quantize(model['heads'][a].predict(encoder._encode([r['utterance'] for r in dev])))
        for i, value in enumerate(values):
            actual[i][a] = int(value)
    assert actual == predictions['candidate']
    write('verification.json', {'group_and_near_duplicate_fold_isolation': True, 'each_human_row_oof_once': True,
                               'candidate_roundtrip_predictions_equal': True, 'human_input_hashes_unchanged': True,
                               'final_test_not_opened': True, 'performance_pass': False,
                               'candidate_sha256': hashlib.sha256((DEST / 'candidate.joblib').read_bytes()).hexdigest()})
    print('VERIFIED ' + json.dumps(cohort_metrics['train_counts']))


def nonconstant_diagnostic():
    import torch
    torch.set_num_threads(2)
    human, dev, manifest = load_inputs()
    results = json.loads((DEST / 'cv_results.json').read_text(encoding='utf-8'))
    chosen = {a: min((n for n in results if not n.startswith('median')), key=lambda n: results[n]['overall'][a]['mae']) for a in AXES}
    with (DEST / 'nonconstant_lock.json').open('x', encoding='utf-8') as f:
        json.dump({'chosen': chosen, 'criterion': 'minimum human-only grouped OOF MAE among predeclared nonconstant grid',
                   'posthoc_family_restriction': True, 'no_dev_based_selection': True}, f, indent=2)
    print('NONCONSTANT_LOCK ' + json.dumps(chosen), flush=True)
    heads, tfidf_models, preds = {}, {}, [{} for r in dev]
    encoder = EmbeddingAxisAdapter(model_name=str(ENCODER_DIR), local_files_only=True)
    for a, name in chosen.items():
        family, alpha = name.split('_')
        if family == 'tfidf':
            model = RidgeAxisAdapter(alpha=float(alpha)).fit(examples(human))
            tfidf_models[a] = model
            values = [p[a] for p in vector_predictions(model, [r['utterance'] for r in dev])]
        else:
            rows = [r for r in human if a in r['axes']]
            heads[a] = Ridge(alpha=float(alpha)).fit(encoder._encode([r['utterance'] for r in rows]), [r['axes'][a] for r in rows])
            values = quantize(heads[a].predict(encoder._encode([r['utterance'] for r in dev])))
        for i, value in enumerate(values):
            preds[i][a] = int(value)
    artifact = {'chosen': chosen, 'tfidf_models': tfidf_models, 'heads': heads, 'encoder_path': str(ENCODER_DIR), 'train_ids': manifest['train_ids']}
    joblib.dump(artifact, DEST / 'nonconstant_candidate.joblib')
    restored = joblib.load(DEST / 'nonconstant_candidate.joblib')
    for a in AXES:
        if a in restored['tfidf_models']:
            assert [p[a] for p in vector_predictions(restored['tfidf_models'][a], [r['utterance'] for r in dev])] == [p[a] for p in preds]
    write('nonconstant_dev.json', stratified(dev, preds))
    write('nonconstant_predictions.json', preds)
    old = json.loads((DEST / 'dev_predictions.json').read_text(encoding='utf-8'))
    rng = np.random.default_rng(20261013)
    groups = sorted({ami_series(r['source_group']) for r in dev})
    intervals = {}
    for name, pp in [('candidate', old['candidate']), ('nonconstant', preds)]:
        intervals[name] = {}
        for ref in ('human_tfidf', 'full_corpus_student'):
            intervals[name][ref] = {}
            for a in AXES:
                deltas = []
                by_group = {g: [abs(p[a] - r['axes'][a]) - abs(q[a] - r['axes'][a]) for r, p, q in zip(dev, pp, old['existing'][ref]) if a in r['axes'] and ami_series(r['source_group']) == g] for g in groups}
                for _ in range(2000):
                    errors = [v for g in rng.choice(groups, len(groups), replace=True) for v in by_group[g]]
                    if errors:
                        deltas.append(np.mean(errors))
                intervals[name][ref][a] = {'delta_mae': score(dev, pp)[a]['mae'] - score(dev, old['existing'][ref])[a]['mae'], 'descriptive_group_bootstrap_95pct': np.percentile(deltas, [2.5, 97.5]).tolist()}
    write('paired_group_bootstrap.json', {'resamples': 2000, 'seed': 20261013, 'negative_delta_favors_candidate': True,
                                         'limitations': 'historically reused dev; descriptive interval, not independent confirmatory evidence', 'results': intervals})
    final_name = next(n for n in manifest['input_sha256'] if n not in (TRAIN.name, DEV.name))
    final_unchanged = hashlib.sha256((TRAIN.parent / final_name).read_bytes()).hexdigest() == manifest['input_sha256'][final_name]
    assert final_unchanged
    write('nonconstant_verification.json', {'roundtrip_predictions_equal': True, 'final_byte_hash_unchanged': True, 'final_labels_never_parsed': True})
    print('NONCONSTANT_DEV ' + json.dumps({a: score(dev, preds)[a]['mae'] for a in AXES}), flush=True)


if __name__ == '__main__':
    if '--verify' in sys.argv:
        verify_outputs()
    elif '--nonconstant' in sys.argv:
        nonconstant_diagnostic()
    else:
        main()
