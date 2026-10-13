"""Nested grouped search of linear, epsilon-insensitive, and nonlinear regressors."""
import json
import sys
import joblib
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge, QuantileRegressor
from sklearn.svm import SVR
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import GroupKFold
from ai.researched_axis_model import ResearchedAxisModel
from scripts.compare_fhc_representation import fit_vocabulary, lexical_features, representation_features, sha
from scripts.compare_fhc_improvements import DEST, components, quantize, stratified
from scripts.compare_full_corpus_labelers import AXES, OUT
from scripts.train_transfer_axis_models import TRAIN, DEV, FINAL, read_rows

TARGET = DEST / 'research_round'
EXTENDED = '--extended' in sys.argv
if EXTENDED:
    TARGET = DEST / 'research_extended'


def features_for(family, lexical, embeddings, texts):
    if family != 'embedding_rules':
        return representation_features(family, lexical, embeddings)
    from ai.analyzer import analyze_utterance
    rules = [analyze_utterance(t) for t in texts]
    return np.hstack([embeddings, np.array([[r[a] for a in AXES] for r in rules], dtype=float) / 100.])


def grid():
    candidates = [{'family': f, 'model': 'ridge', 'params': {'alpha': a}}
                  for f in ('tfidf', 'embedding', 'combined') for a in (.1, 1., 10.)]
    candidates += [{'family': f, 'model': 'svr', 'params': {'kernel': k, 'C': c, 'epsilon': 5., 'gamma': 'scale'}}
                   for f in ('embedding', 'combined') for k in ('linear', 'rbf') for c in (10., 100.)]
    candidates += [{'family': 'embedding', 'model': 'extra_trees', 'params': {'n_estimators': 200, 'min_samples_leaf': leaf, 'random_state': 20261013, 'n_jobs': 2}}
                   for leaf in (3, 8)]
    if EXTENDED:
        candidates += [{'family': 'embedding', 'model': 'quantile', 'params': {'quantile': .5, 'alpha': a, 'solver': 'highs', 'solver_options': {'threads': 1}}} for a in (.001, .01)]
        candidates += [{'family': 'embedding_rules', 'model': 'ridge', 'params': {'alpha': a}} for a in (.1, 1., 10.)]
        candidates += [{'family': 'embedding_rules', 'model': 'svr', 'params': {'kernel': 'linear', 'C': c, 'epsilon': 5., 'gamma': 'scale'}} for c in (10., 100.)]
    return candidates


def estimator(config):
    constructor = {'ridge': Ridge, 'svr': SVR, 'extra_trees': ExtraTreesRegressor, 'quantile': QuantileRegressor}[config['model']]
    params = dict(config['params'])
    if config['model'] == 'extra_trees':
        params['n_jobs'] = 1  # Windows sandbox blocks joblib thread pool named pipes.
    return constructor(**params)


def summarize(y, pred, fold_ids):
    std = float(np.std(pred))
    distinct = len(np.unique(pred))
    fold_distinct = {str(int(f)): len(np.unique(pred[fold_ids == f])) for f in sorted(set(fold_ids))}
    need = 2 if len(fold_distinct) == 3 else 3
    rho = spearmanr(y, pred).statistic if len(np.unique(y)) > 1 and distinct > 1 else None
    return {'n': len(y), 'mae': float(np.mean(abs(pred - y))), 'within10': float(np.mean(abs(pred - y) <= 10)),
            'spearman': float(rho) if rho is not None and np.isfinite(rho) else None,
            'std': std, 'distinct': distinct, 'fold_distinct': fold_distinct,
            'eligible': std >= 2.5 and distinct >= 3 and sum(v >= 2 for v in fold_distinct.values()) >= need}


def choose(metrics):
    return {a: min((i for i, m in enumerate(metrics) if m[a]['eligible']), key=lambda i: metrics[i][a]['mae'], default=None) for a in AXES}


def write(name, obj):
    (TARGET / name).write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')


def evaluate_grid(rows, embeddings, splits, candidates):
    predictions = [{a: np.full(len(rows), np.nan) for a in AXES} for _ in candidates]
    median = {a: np.full(len(rows), np.nan) for a in AXES}
    fold_ids = np.full(len(rows), -1)
    for fold, (tr, va) in enumerate(splits):
        fold_ids[va] = fold
        vocab = fit_vocabulary([rows[i]['utterance'] for i in tr])
        lx, lv = lexical_features(vocab, [rows[i]['utterance'] for i in tr]), lexical_features(vocab, [rows[i]['utterance'] for i in va])
        features = {f: (features_for(f, lx, embeddings[tr], [rows[i]['utterance'] for i in tr]), features_for(f, lv, embeddings[va], [rows[i]['utterance'] for i in va])) for f in {c['family'] for c in candidates}}
        for a in AXES:
            valid = [j for j, i in enumerate(tr) if a in rows[i]['axes']]
            y = np.array([rows[tr[j]]['axes'][a] for j in valid])
            median[a][va] = quantize(np.full(len(va), np.median(y)))
            for n, config in enumerate(candidates):
                x, v = features[config['family']]
                model = estimator(config).fit(x[valid], y)
                predictions[n][a][va] = quantize(model.predict(v))
    assert (fold_ids >= 0).all()
    metrics = []
    for pred in predictions:
        per_axis = {}
        for a in AXES:
            ids = [i for i, r in enumerate(rows) if a in r['axes']]
            assert np.isfinite(pred[a]).all()
            per_axis[a] = summarize(np.array([rows[i]['axes'][a] for i in ids]), pred[a][ids], fold_ids[ids])
        metrics.append(per_axis)
    return metrics, predictions, median, fold_ids


def main():
    from threadpoolctl import threadpool_limits
    threadpool_limits(limits=1)
    TARGET.mkdir(exist_ok=True)
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    for p in (TRAIN, DEV, FINAL):
        assert sha(p) == manifest['input_sha256'][p.name]
    original = json.loads((DEST / 'protocol.json').read_text(encoding='utf-8'))
    candidates = grid()
    hashes = {str(p): sha(p) for p in (TRAIN, DEV, FINAL, DEST / 'protocol.json', DEST / 'representation_round/human_embeddings.npy')}
    if EXTENDED:
        hashes['ai/analyzer.py'] = sha('ai/analyzer.py')
    protocol = {'grid': candidates, 'outer_folds': original['folds'], 'inner': 'GroupKFold3 on outer training groups only',
                'group_definition': 'connected meeting/AMIseries/wordset near duplicates across original118',
                'selection': 'minimum rounded human-reference MAE among eligible candidates; fixed grid ties',
                'response_guard': {'pooled_std_min': 2.5, 'pooled_unique_min': 3, 'inner_folds_with_two_unique_min': 2, 'final5_folds_with_two_unique_min': 3},
                'guard_basis': 'predeclared product responsiveness requirement, arbitrary thresholds not scientific accuracy standard',
                'no_eligible': 'explicit blocked flag; no automatic fallback or best model claim',
                'human_reference': 'human scores are empirical reference, not infallible objective truth',
                'sources': ['https://arxiv.org/abs/1908.10084', 'https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVR.html',
                            'https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html',
                            'https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html'],
                'input_sha256': hashes, 'paid_api': False, 'final': 'hash only', 'dev': 'parse only after full model lock',
                'limitations': ['Nested CV estimates this bounded selection procedure, not the optimistic minimum full-data CV.',
                               'Previous exploration of the same118 means outer scores are not a pristine untouched final test.',
                               'Current synthetic labels excluded from nested CV; fold-regenerated pseudo previous comparison is descriptive only.',
                               'Only train118 references; cohort/context/low-support uncertainty remains.']}
    if EXTENDED:
        protocol['extension'] = {'rules': 'normalized frozen MiniLM concatenate deterministic ai.analyzer F/H/C divided100; no postconcat scaling',
                                 'quantile': 'median quantile regression explicitly targets absolute loss',
                                 'runtime': 'ExtraTrees n_jobs1; BLASthreads1; HiGHSthreads1; repeated original19 plus7'}
        protocol['sources'] += ['https://aclanthology.org/Q16-1005/', 'https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.QuantileRegressor.html']
    if (TARGET / 'protocol.json').exists():
        assert json.loads((TARGET / 'protocol.json').read_text(encoding='utf-8')) == protocol
        if (TARGET / 'nested_progress.json').exists() or (TARGET / 'full_cv.json').exists():
            raise FileExistsError('Refusing to rerun a completed/partially scored search')
        write('runtime_amendment.json', {'reason': 'First ExtraTrees n_jobs2 call failed WinError5 namedpipe creation before fold results',
                                         'change': 'ExtraTrees execution n_jobs1 only; seed200trees/hyperparameters unchanged',
                                         'results_seen_before_change': False})
    else:
        with (TARGET / 'protocol.json').open('x', encoding='utf-8') as f:
            json.dump(protocol, f, indent=2)
    by_id = {r['item_id']: r for r in read_rows(TRAIN)}
    rows = [by_id[i] for i in manifest['train_ids']]
    embeddings = np.load(DEST / 'representation_round/human_embeddings.npy')
    assert len(embeddings) == len(rows) and np.isfinite(embeddings).all()
    positions = {r['item_id']: i for i, r in enumerate(rows)}
    outer = [(np.array([positions[i] for i in f['train_ids']]), np.array([positions[i] for i in f['validation_ids']])) for f in original['folds']]
    groups = np.array(components(rows))
    nested_predictions = [{} for _ in rows]
    nested_log = []
    blocked = []
    for fold, (tr, va) in enumerate(outer):
        train_rows = [rows[i] for i in tr]
        inner = list(GroupKFold(n_splits=3).split(train_rows, groups=groups[tr]))
        scores, _, _, _ = evaluate_grid(train_rows, embeddings[tr], inner, candidates)
        chosen = choose(scores)
        nested_log.append({'fold': fold, 'chosen': chosen, 'candidate_metrics': scores,
                           'inner_splits': [{'train_ids': [train_rows[i]['item_id'] for i in it], 'validation_ids': [train_rows[i]['item_id'] for i in iv]} for it, iv in inner]})
        if any(v is None for v in chosen.values()):
            blocked.append({'fold': fold, 'axes': [a for a, v in chosen.items() if v is None]})
        vocab = fit_vocabulary([r['utterance'] for r in train_rows])
        lx = lexical_features(vocab, [r['utterance'] for r in train_rows])
        lv = lexical_features(vocab, [rows[i]['utterance'] for i in va])
        for a, index in chosen.items():
            if index is None:
                continue
            c = candidates[index]
            ids = [j for j, r in enumerate(train_rows) if a in r['axes']]
            x, v = features_for(c['family'], lx, embeddings[tr], [r['utterance'] for r in train_rows]), features_for(c['family'], lv, embeddings[va], [rows[i]['utterance'] for i in va])
            model = estimator(c).fit(x[ids], [train_rows[j]['axes'][a] for j in ids])
            for i, value in zip(va, quantize(model.predict(v))):
                nested_predictions[i][a] = int(value)
        write('nested_progress.json', {'folds': nested_log, 'blocked': blocked})
        print('NESTED OUTER', fold + 1, chosen, flush=True)
    final_scores, final_oof, medians, fold_ids = evaluate_grid(rows, embeddings, outer, candidates)
    median_diagnostic = {}
    for a in AXES:
        ids = [i for i, r in enumerate(rows) if a in r['axes']]
        median_diagnostic[a] = summarize(np.array([rows[i]['axes'][a] for i in ids]), medians[a][ids], fold_ids[ids])
    write('median_diagnostic.json', {'diagnostic_only_not_candidate': True, 'metrics': median_diagnostic})
    chosen = choose(final_scores)
    write('full_cv.json', {'grid': candidates, 'metrics': final_scores, 'chosen': chosen})
    write('nested_predictions.json', {'ids': manifest['train_ids'], 'predictions': nested_predictions})
    write('full_oof.json', {'ids': manifest['train_ids'], 'predictions': [{a: v.tolist() for a, v in p.items()} for p in final_oof], 'median': {a: v.tolist() for a, v in medians.items()}})
    write('selection_lock.json', {'chosen_indices': chosen, 'configs': {a: candidates[i] if i is not None else None for a, i in chosen.items()}, 'dev_used': False})
    if any(v is None for v in chosen.values()) or blocked:
        write('blocked.json', {'nested': blocked, 'final': chosen, 'reason': 'Responsiveness guard left no eligible candidate; no silent fallback'})
        print('BLOCKED BY RESPONSIVENESS', flush=True)
        return
    vocab = fit_vocabulary([r['utterance'] for r in rows])
    lx = lexical_features(vocab, [r['utterance'] for r in rows])
    bundle = {'schema_version': 1, 'vocabulary': vocab, 'encoder_path': 'data/models/minilm-base', 'heads': {},
              'configs': {a: candidates[i] for a, i in chosen.items()}, 'human_ids': manifest['train_ids']}
    for a, c in bundle['configs'].items():
        ids = [i for i, r in enumerate(rows) if a in r['axes']]
        x = features_for(c['family'], lx, embeddings, [r['utterance'] for r in rows])
        bundle['heads'][a] = estimator(c).fit(x[ids], [rows[i]['axes'][a] for i in ids])
    joblib.dump(bundle, TARGET / 'model.joblib')
    write('fit_lock.json', {'model_sha256': sha(TARGET / 'model.joblib'), 'configs': bundle['configs']})
    print('FINAL MODEL LOCKED', bundle['configs'], flush=True)
    dev = read_rows(DEV)
    class CachedEncoder:
        def __init__(self, values):
            self.values = values
        def _encode(self, texts):
            assert len(texts) == len(self.values)
            return self.values
    from ai.embedding_axis_adapter import EmbeddingAxisAdapter
    from scripts.train_transfer_axis_models import ENCODER_DIR
    import torch
    torch.set_num_threads(1)
    enc = EmbeddingAxisAdapter(model_name=str(ENCODER_DIR), local_files_only=True)
    dx = enc._encode([r['utterance'] for r in dev])
    pred = ResearchedAxisModel(bundle, encoder=CachedEncoder(dx)).predict_many([r['utterance'] for r in dev])
    assert pred == ResearchedAxisModel.from_artifact(TARGET / 'model.joblib', encoder=CachedEncoder(dx)).predict_many([r['utterance'] for r in dev])
    nested_metrics = stratified(rows, nested_predictions)
    responsive = {}
    for a in AXES:
        ids = [i for i, r in enumerate(rows) if a in r['axes']]
        responsive[a] = summarize(np.array([rows[i]['axes'][a] for i in ids]), np.array([nested_predictions[i][a] for i in ids]), fold_ids[ids])
    report = {'nested_metrics': nested_metrics, 'nested_responsiveness': responsive, 'selected_configs': bundle['configs'],
              'final_cv_selected': {a: final_scores[i][a] for a, i in chosen.items()}, 'dev': stratified(dev, pred),
              'roundtrip_verified': True, 'input_hashes_unchanged': all(sha(p) == h for p, h in hashes.items()),
              'final_labels_used': False, 'limitations': protocol['limitations']}
    assert report['input_hashes_unchanged']
    write('report.json', report)
    write('dev_predictions.json', {'ids': [r['item_id'] for r in dev], 'predictions': pred})
    print('COMPLETE', json.dumps({'nested': {a: v['mae'] for a, v in responsive.items()}, 'dev': {a: v['mae'] for a, v in report['dev']['overall'].items()}}), flush=True)


if __name__ == '__main__':
    main()
