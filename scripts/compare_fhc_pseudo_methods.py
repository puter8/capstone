"""Fold-regenerated pseudo targets; joint and human residual correction ablation."""
import json
import joblib
import numpy as np
from scipy.sparse import vstack
from sklearn.linear_model import Ridge
from ai.embedding_axis_adapter import EmbeddingAxisAdapter
from scripts.compare_fhc_representation import fit_vocabulary, lexical_features, representation_features, sha
from scripts.compare_fhc_improvements import DEST, stratified, quantize
from scripts.compare_full_corpus_labelers import AXES, OUT
from scripts.train_transfer_axis_models import TRAIN, DEV, FINAL, ENCODER_DIR, read_rows

TARGET = DEST / 'representation_pseudo'
ARMS = ('human_only', 'joint', 'residual')


def stack(x, y):
    return np.vstack([x, y]) if isinstance(x, np.ndarray) else vstack([x, y], format='csr')


def fit_head(arm, hx, hy, px, py, alpha):
    if arm == 'human_only':
        return {'base': Ridge(alpha=alpha).fit(hx, hy), 'residual': None}
    if arm == 'joint':
        weights = np.r_[np.ones(len(hy)), np.full(len(py), .25 * len(hy) / len(py))]
        return {'base': Ridge(alpha=alpha).fit(stack(hx, px), np.r_[hy, py], sample_weight=weights), 'residual': None}
    base = Ridge(alpha=alpha).fit(px, py, sample_weight=np.full(len(py), len(hy) / len(py)))
    residual = Ridge(alpha=alpha).fit(hx, hy - base.predict(hx))
    return {'base': base, 'residual': residual}


def raw_prediction(head, features):
    values = head['base'].predict(features)
    if head['residual'] is not None:
        values = values + head['residual'].predict(features)
    return values


def predict_bundle(bundle, texts, embeddings):
    lex = lexical_features(bundle['vocabulary'], texts)
    values = {a: quantize(raw_prediction(bundle['heads'][a], representation_features(c['family'], lex, embeddings))) for a, c in bundle['config'].items()}
    return [{a: int(values[a][i]) for a in AXES} for i in range(len(texts))]


def write(name, obj):
    (TARGET / name).write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')


def main():
    import torch
    torch.set_num_threads(2)
    rep = DEST / 'representation_round'
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    pool_path = TARGET / 'unlabeled_pool.jsonl'
    assert sha(pool_path) == json.loads((TARGET / 'pool_lock.json').read_text(encoding='utf-8'))['sha256']
    for p in (TRAIN, DEV, FINAL):
        assert sha(p) == manifest['input_sha256'][p.name]
    prior = json.loads((rep / 'protocol.json').read_text(encoding='utf-8'))
    config = json.loads((rep / 'selection_lock.json').read_text(encoding='utf-8'))['config']
    protocol = {'arms': ARMS, 'config': config, 'teacher': 'foldhuman TFIDFalpha.1 and MiniLMalpha.1 raw arithmeticmean then clipround5',
                'joint_pseudo_mass_ratio': .25, 'residual_pseudo_mass_ratio': 1., 'residual_target': 'human minus pseudo_only base RAWprediction',
                'folds': prior['folds'], 'selection': 'axiswise minimum pooled OOF MAE; ties human_only then joint then residual',
                'input_sha256': {str(p): sha(p) for p in (TRAIN, DEV, FINAL, pool_path, rep / 'human_embeddings.npy', rep / 'selection_lock.json')},
                'limitations': ['Small repeatedly explored training CV; arm selection optimistic, not confirmatory.',
                               'Pseudo targets contain no independent human truth; same representation may simply reproduce teacher errors.',
                               'Dev historically reused; all arms reported, no dev selection.',
                               'Pool excludes all118 human groups and near texts globally, including mapping aliases; global filtering is predeclared.'],
                'no_paid_api': True, 'final': 'hash only', 'dev': 'parse after all final fits and arm selection locked'}
    with (TARGET / 'experiment_protocol.json').open('x', encoding='utf-8') as f:
        json.dump(protocol, f, indent=2)
    by_id = {r['item_id']: r for r in read_rows(TRAIN)}
    human = [by_id[i] for i in manifest['train_ids']]
    pool = read_rows(pool_path)
    assert pool and len({r['item_id'] for r in pool}) == len(pool)
    hx = np.load(rep / 'human_embeddings.npy')
    assert hx.shape[0] == len(human) and np.isfinite(hx).all()
    encoder = EmbeddingAxisAdapter(model_name=str(ENCODER_DIR), local_files_only=True)
    px = encoder._encode([r['utterance'] for r in pool])
    np.save(TARGET / 'pool_embeddings.npy', px)
    write('embedding_lock.json', {'human': sha(rep / 'human_embeddings.npy'), 'pool': sha(TARGET / 'pool_embeddings.npy')})
    positions = {r['item_id']: i for i, r in enumerate(human)}
    folds = [(np.array([positions[i] for i in f['train_ids']]), np.array([positions[i] for i in f['validation_ids']])) for f in prior['folds']]
    oofs = {arm: [{} for r in human] for arm in ARMS}
    final_bundles = {}
    for stage, (tr, va) in enumerate(folds + [(np.arange(len(human)), np.array([], dtype=int))]):
        final = stage == len(folds)
        vocab = fit_vocabulary([human[i]['utterance'] for i in tr])
        lex = lexical_features(vocab, [human[i]['utterance'] for i in tr])
        poollex = lexical_features(vocab, [r['utterance'] for r in pool])
        validlex = lexical_features(vocab, [human[i]['utterance'] for i in va]) if not final else None
        pseudo = {}
        bundles = {arm: {'vocabulary': vocab, 'encoder_path': str(ENCODER_DIR), 'config': config, 'heads': {}, 'pool_ids': [r['item_id'] for r in pool], 'human_ids': [human[i]['item_id'] for i in tr]} for arm in ARMS}
        for a, c in config.items():
            ids = [j for j, i in enumerate(tr) if a in human[i]['axes']]
            y = np.array([human[tr[j]]['axes'][a] for j in ids])
            lteacher = Ridge(alpha=.1).fit(lex[ids], y)
            etteacher = Ridge(alpha=.1).fit(hx[tr][ids], y)
            py = quantize((lteacher.predict(poollex) + etteacher.predict(px)) / 2)
            pseudo[a] = py
            features = representation_features(c['family'], lex, hx[tr])
            poolfeatures = representation_features(c['family'], poollex, px)
            validfeatures = representation_features(c['family'], validlex, hx[va]) if not final else None
            for arm in ARMS:
                head = fit_head(arm, features[ids], y, poolfeatures, py, c['alpha'])
                bundles[arm]['heads'][a] = head
                if not final:
                    for i, v in zip(va, quantize(raw_prediction(head, validfeatures))):
                        oofs[arm][i][a] = int(v)
        np.savez_compressed(TARGET / ('pseudo_final.npz' if final else f'pseudo_fold{stage}.npz'), **pseudo)
        if final:
            final_bundles = bundles
        print('STAGE', stage, 'COMPLETE', flush=True)
    results = {arm: stratified(human, p) for arm, p in oofs.items()}
    original_oof = read_rows(rep / 'oof_predictions.jsonl')
    for i, r in enumerate(original_oof):
        for a, c in config.items():
            assert oofs['human_only'][i][a] == r['predictions'][f'{c["family"]}_{c["alpha"]}'][a]
    chosen = {a: min(ARMS, key=lambda arm: results[arm]['overall'][a]['mae']) for a in AXES}
    write('selection_lock.json', {'chosen': chosen, 'criterion': protocol['selection'], 'dev_used': False})
    selected = dict(final_bundles['human_only'])
    selected['heads'] = {a: final_bundles[chosen[a]]['heads'][a] for a in AXES}
    final_bundles['selected'] = selected
    for arm, bundle in final_bundles.items():
        joblib.dump(bundle, TARGET / (arm + '.joblib'))
    write('fit_lock.json', {arm: sha(TARGET / (arm + '.joblib')) for arm in final_bundles})
    write('cv_results.json', results)
    write('oof_predictions.json', {'ids': manifest['train_ids'], 'predictions': oofs})
    print('LOCKED', chosen, flush=True)
    dev = read_rows(DEV)
    texts = [r['utterance'] for r in dev]
    dx = encoder._encode(texts)
    predictions = {arm: predict_bundle(bundle, texts, dx) for arm, bundle in final_bundles.items()}
    for arm in final_bundles:
        assert predictions[arm] == predict_bundle(joblib.load(TARGET / (arm + '.joblib')), texts, dx)
    oldrep = json.loads((rep / 'dev_predictions.json').read_text(encoding='utf-8'))
    assert predictions['human_only'] == oldrep['predictions']
    oldemp = json.loads((DEST / 'empirical_fhc/dev_predictions.json').read_text(encoding='utf-8'))
    predictions['prior_empirical163'] = oldemp['human_plus_empirical50']
    predictions['prior_tfidf_human'] = oldemp['human_only']
    report = {'human_rows': len(human), 'pool_rows': len(pool), 'unique_training_rows': len(human) + len(pool),
              'human_valid_axis_counts': {a: sum(a in r['axes'] for r in human) for a in AXES},
              'chosen': chosen, 'cv': results, 'dev': {arm: stratified(dev, pred) for arm, pred in predictions.items()},
              'baseline_oof_and_dev_exact_reproduction': True, 'all_roundtrips_verified': True,
              'input_hashes_unchanged': all(sha(p) == h for p, h in protocol['input_sha256'].items()),
              'final_test_parsed': False, 'deployed': False, 'limitations': protocol['limitations']}
    assert report['input_hashes_unchanged']
    write('report.json', report)
    write('dev_predictions.json', {'ids': [r['item_id'] for r in dev], 'predictions': predictions})
    print('RESULT ' + json.dumps({arm: {a: vals['overall'][a]['mae'] for a in AXES} for arm, vals in report['dev'].items()}), flush=True)


if __name__ == '__main__':
    main()
