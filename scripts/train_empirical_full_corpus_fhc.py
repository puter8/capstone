"""Frozen offline ablation adding protected corpus pseudo labels to empirical anchors."""
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import vstack, save_npz
from sklearn.linear_model import Ridge

from ai.ridge_axis_adapter import RidgeAxisAdapter
from scripts.compare_fhc_improvements import DEST, stratified
from scripts.compare_full_corpus_labelers import AXES, OUT
from scripts.fhc_round2_select import ami_series
from scripts.train_full_corpus_fhc import vector_predictions
from scripts.train_transfer_axis_models import TRAIN, DEV, FINAL, read_rows

TARGET = DEST / 'empirical_full_corpus'
EMP = DEST / 'empirical_fhc'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def admit_pseudo(row, excluded_ids):
    """Exclude reviewed records before interpreting their partial/old labels."""
    if row['item_id'] in excluded_ids:
        return False
    if row.get('status') != 'pseudo_not_human_ground_truth':
        raise ValueError('Invalid pseudo status')
    expected = {'Formality': 'local_human_embedding_pseudo', 'Humor': 'local_augmented_tfidf_pseudo', 'Curiosity': 'local_augmented_tfidf_pseudo'}
    if row.get('label_source') != expected or set(row.get('axes', {})) != set(AXES):
        raise ValueError('Unexpected provenance or missing pseudo axis')
    if any(type(v) is not int or not 0 <= v <= 100 or v % 5 for v in row['axes'].values()):
        raise ValueError('Invalid pseudo score')
    return True


def pseudo_weights(old_scores, new_predictions, human_count, ratio, agreement=False):
    old_scores, new_predictions = np.asarray(old_scores, dtype=float), np.asarray(new_predictions, dtype=float)
    if old_scores.shape != new_predictions.shape or old_scores.ndim != 1 or not len(old_scores):
        raise ValueError('Invalid score vectors')
    if not np.isfinite(old_scores).all() or not np.isfinite(new_predictions).all() or not np.isfinite(human_count) or not np.isfinite(ratio) or human_count <= 0 or ratio < 0:
        raise ValueError('Invalid weight inputs')
    w = 1 / (1 + abs(old_scores - new_predictions) / 10) if agreement else np.ones(len(old_scores))
    return normalize_reliability(w, human_count, ratio)


def normalize_reliability(w, human_count, ratio):
    w = np.asarray(w, dtype=float)
    if w.ndim != 1 or not len(w) or not np.isfinite(w).all() or np.any(w <= 0) or not np.isfinite(human_count) or not np.isfinite(ratio) or human_count <= 0 or ratio < 0:
        raise ValueError('Invalid reliability weights')
    return w * (human_count * ratio / w.sum())


def main():
    TARGET.mkdir(exist_ok=True)
    corpus = OUT / 'codex/corpus_labeled.jsonl'
    paths = [TRAIN, DEV, FINAL, corpus, OUT / 'corpus_tasks.jsonl', OUT / 'enrichment_codex.jsonl',
             EMP / 'merged_labels.jsonl', EMP / 'human_plus_empirical50.joblib', EMP / 'fit_lock.json',
             EMP / 'formality.json', EMP / 'humor.json', EMP / 'curiosity.json']
    input_hashes = {str(p): sha(p) for p in paths}
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    for p in (TRAIN, DEV, FINAL):
        assert input_hashes[str(p)] == manifest['input_sha256'][p.name]
    inventory = json.loads((OUT / 'corpus_inventory.json').read_text(encoding='utf-8'))
    assert sha(OUT / 'corpus_tasks.jsonl') == inventory['tasks_sha256']
    oldverify = json.loads((OUT / 'codex/verification.json').read_text(encoding='utf-8'))
    # Corpus hash recorded by the preceding independently verified labeling run.
    expected_corpus = 'e1bab292b04faca1824f07a28d68f0ee3eabab566d4200d7e180e0d9c06b70c7'
    assert input_hashes[str(corpus)] == expected_corpus
    arms = {'anchor_only': (0.0, False), 'uniform_025': (.25, False), 'uniform_100': (1.0, False), 'agreement_025': (.25, True)}
    protocol = {'arms': arms, 'primary': 'uniform_025', 'alpha': .1, 'human_weight': 1., 'latest_AI_weight': .25,
                'pseudo_weight': 'normalize peraxis to ratio times valid human axis count',
                'agreement_formula': '1/(1+abs(old_pseudo-latest_empirical_teacher_prediction)/10)',
                'agreement_warning': 'model agreement heuristic, not calibrated correctness confidence',
                'vocabulary': 'frozen118human word1-2 and char3-5; identical across all arms',
                'exclude': 'all original70 reviewed IDs and all latest50 IDs from corpus pseudo pool',
                'selection': 'none; all models locked before dev; no result-driven tuning',
                'input_sha256': input_hashes,
                'limitations': ['AI labels are not independent human truth.', 'Previously reused dev is exploratory.',
                               'Primary and sensitivity arms predeclared; no winner selection.',
                               'Prior full corpus student is descriptive reference with different settings.'],
                'final': 'byte hash only, never parsed or fit', 'paid_api_calls': 0, 'production_changed': False}
    with (TARGET / 'protocol.json').open('x', encoding='utf-8') as f:
        json.dump(protocol, f, indent=2)
    print('PROTOCOL LOCKED', flush=True)
    human_map = {r['item_id']: r for r in read_rows(TRAIN)}
    human = [human_map[i] for i in manifest['train_ids']]
    ai = read_rows(EMP / 'merged_labels.jsonl')
    old = read_rows(OUT / 'enrichment_codex.jsonl')
    old_ids, new_ids = {r['item_id'] for r in old}, {r['item_id'] for r in ai}
    assert len(old_ids) == 70 and len(new_ids) == 50
    excluded_ids = old_ids | new_ids
    for r in ai:
        assert set(r['axes']) == set(r['label_source'])
        assert all(v == 'codex_empirical_pseudo_not_human' for v in r['label_source'].values())
        assert all(type(v) is int and 0 <= v <= 100 and v % 5 == 0 for v in r['axes'].values())
    teacher = joblib.load(EMP / 'human_plus_empirical50.joblib')
    previous_lock = json.loads((EMP / 'fit_lock.json').read_text(encoding='utf-8'))
    assert sha(EMP / 'human_plus_empirical50.joblib') == previous_lock['human_plus_empirical50']
    chunks, targets, agreement = [], {a: [] for a in AXES}, {a: [] for a in AXES}
    seen, retained, excluded_seen, batch = set(), 0, set(), []
    def flush():
        nonlocal retained
        if not batch:
            return
        x = teacher._vectorize([r['utterance'] for r in batch]).tocsr()
        chunks.append(x)
        for a in AXES:
            labels = np.array([r['axes'][a] for r in batch])
            current = np.round(np.clip(teacher.axis_models[a].predict(x), 0, 100) / 5) * 5
            targets[a].extend(labels.tolist())
            agreement[a].extend((1 / (1 + abs(labels - current) / 10)).tolist())
        retained += len(batch)
        batch.clear()
    with corpus.open(encoding='utf-8') as f, (OUT / 'corpus_tasks.jsonl').open(encoding='utf-8') as tasks:
        for line in f:
            r, task = json.loads(line), json.loads(next(tasks))
            assert r['item_id'] == task['item_id'] and r['utterance'] == task['utterance']
            assert r['item_id'] not in seen
            seen.add(r['item_id'])
            assert r['status'] == 'pseudo_not_human_ground_truth'
            if not admit_pseudo(r, excluded_ids):
                excluded_seen.add(r['item_id'])
                continue
            batch.append(r)
            if len(batch) == 4000:
                flush()
                if retained % 40000 == 0:
                    print('VECTORIZED', retained, flush=True)
        assert next(tasks, None) is None
    flush()
    assert len(seen) == 238475 and excluded_seen == excluded_ids
    assert not ({r['item_id'] for r in human} & seen)
    x = vstack(chunks, format='csr')
    del chunks
    save_npz(TARGET / 'pseudo_features.npz', x)
    np.savez_compressed(TARGET / 'pseudo_targets_agreement.npz', **{a: np.array(targets[a]) for a in AXES},
                        **{a + '_agreement': np.array(agreement[a]) for a in AXES})
    fit_counts, models = {}, {}
    for arm, (ratio, use_agreement) in arms.items():
        model = RidgeAxisAdapter(alpha=.1)
        model.word_vec, model.char_vec = teacher.word_vec, teacher.char_vec
        fit_counts[arm] = {}
        for a in AXES:
            hr, ar = [r for r in human if a in r['axes']], [r for r in ai if a in r['axes']]
            anchors = hr + ar
            ax = teacher._vectorize([r['utterance'] for r in anchors]).tocsr()
            y = np.array([r['axes'][a] for r in anchors])
            weights = np.r_[np.ones(len(hr)), np.full(len(ar), .25)]
            if ratio:
                w = np.array(agreement[a]) if use_agreement else np.ones(retained)
                w = normalize_reliability(w, len(hr), ratio)
                xx, yy, ww = vstack([ax, x], format='csr'), np.r_[y, targets[a]], np.r_[weights, w]
            else:
                xx, yy, ww = ax, y, weights
            model.axis_models[a] = Ridge(alpha=.1, solver='lsqr').fit(xx, yy, sample_weight=ww)
            fit_counts[arm][a] = {'human': len(hr), 'latest_AI': len(ar), 'corpus_pseudo': retained if ratio else 0,
                                'unique_total': len(hr) + len(ar) + (retained if ratio else 0),
                                'pseudo_weight_total': len(hr) * ratio}
            print('FIT', arm, a, flush=True)
        models[arm] = model
        joblib.dump(model, TARGET / (arm + '.joblib'))
    with (TARGET / 'fit_lock.json').open('x', encoding='utf-8') as f:
        json.dump({arm: sha(TARGET / (arm + '.joblib')) for arm in models}, f, indent=2)
    dev = read_rows(DEV)
    texts = [r['utterance'] for r in dev]
    predictions = {arm: vector_predictions(m, texts) for arm, m in models.items()}
    for arm in models:
        assert predictions[arm] == vector_predictions(joblib.load(TARGET / (arm + '.joblib')), texts)
    prior_predictions = json.loads((EMP / 'dev_predictions.json').read_text(encoding='utf-8'))
    assert predictions['anchor_only'] == prior_predictions['human_plus_empirical50']
    predictions['prior_full_corpus_student'] = vector_predictions(joblib.load(OUT / 'codex/student.joblib'), texts)
    scores = {arm: stratified(dev, pred) for arm, pred in predictions.items()}
    groups = sorted({ami_series(r['source_group']) for r in dev})
    rng, uncertainty = np.random.default_rng(20261017), {}
    for arm in arms:
        if arm == 'anchor_only':
            continue
        uncertainty[arm] = {}
        for a in AXES:
            errors = {g: [abs(p[a] - r['axes'][a]) - abs(q[a] - r['axes'][a]) for r, p, q in zip(dev, predictions[arm], predictions['anchor_only']) if a in r['axes'] and ami_series(r['source_group']) == g] for g in groups}
            draws = []
            for _ in range(2000):
                values = [v for g in rng.choice(groups, len(groups), replace=True) for v in errors[g]]
                if values:
                    draws.append(float(np.mean(values)))
            uncertainty[arm][a] = {'delta_mae': scores[arm]['overall'][a]['mae'] - scores['anchor_only']['overall'][a]['mae'], 'descriptive95': np.percentile(draws, [2.5, 97.5]).tolist()}
    assert all(sha(Path(p)) == h for p, h in input_hashes.items())
    report = {'raw_corpus': len(seen), 'excluded_old70': len(old_ids), 'excluded_latest50': len(new_ids),
              'excluded_union': len(excluded_seen), 'retained_corpus_pseudo': retained,
              'latest_AI_usable_rows': sum(bool(r['axes']) for r in ai),
              'overall_unique_training_rows': {arm: len(human) + sum(bool(r['axes']) for r in ai) + (retained if ratio else 0) for arm, (ratio, _) in arms.items()},
              'fit_counts': fit_counts, 'metrics': scores, 'uncertainty': uncertainty,
              'all_roundtrips_verified': True, 'anchor_baseline_exact_reproduction': True, 'input_hashes_unchanged': True,
              'final_test_parsed': False, 'all_models_locked_before_dev': True, 'deployed': False,
              'limitations': protocol['limitations']}
    (TARGET / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (TARGET / 'dev_predictions.json').write_text(json.dumps(predictions, indent=2), encoding='utf-8')
    print('RESULT ' + json.dumps({arm: {a: s['overall'][a]['mae'] for a in AXES} for arm, s in scores.items()}), flush=True)


if __name__ == '__main__':
    main()
