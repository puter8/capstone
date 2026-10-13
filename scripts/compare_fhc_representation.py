"""Train-only group CV of lexical, semantic, and equal-norm joint features."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.preprocessing import normalize

from ai.embedding_axis_adapter import EmbeddingAxisAdapter
from scripts.compare_fhc_improvements import DEST, stratified, quantize
from scripts.compare_full_corpus_labelers import AXES, OUT
from scripts.train_transfer_axis_models import TRAIN, DEV, FINAL, ENCODER_DIR, read_rows

TARGET = DEST / 'representation_round'
ALPHAS = (.1, 1., 10., 100.)
FAMILIES = ('tfidf', 'embedding', 'combined')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def fit_vocabulary(texts):
    return {'word': TfidfVectorizer(ngram_range=(1, 2)).fit(texts),
            'char': TfidfVectorizer(analyzer='char', ngram_range=(3, 5)).fit(texts)}


def lexical_features(vocabulary, texts):
    return hstack([vocabulary['word'].transform(texts), vocabulary['char'].transform(texts)]).tocsr()


def representation_features(family, lexical, embeddings):
    """Original standalone scales; combined gives each whole modality equal norm."""
    if family == 'tfidf':
        return lexical
    if family == 'embedding':
        return embeddings
    if family == 'combined':
        return hstack([normalize(lexical, norm='l2', copy=True),
                       csr_matrix(normalize(embeddings, norm='l2', copy=True))]).tocsr() / np.sqrt(2.)
    raise ValueError('Unknown representation')


def predict_bundle(bundle, texts, encoder=None, embeddings=None):
    lexical = lexical_features(bundle['vocabulary'], texts)
    if embeddings is None and any(c['family'] != 'tfidf' for c in bundle['config'].values()):
        if encoder is None:
            encoder = EmbeddingAxisAdapter(model_name=bundle['encoder_path'], local_files_only=True)
        embeddings = encoder._encode(texts)
    features = {c['family']: representation_features(c['family'], lexical, embeddings) for c in bundle['config'].values()}
    values = {a: quantize(bundle['heads'][a].predict(features[c['family']])) for a, c in bundle['config'].items()}
    return [{a: int(values[a][i]) for a in AXES} for i in range(len(texts))]


def write(name, value):
    (TARGET / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def main():
    import torch
    torch.set_num_threads(2)
    TARGET.mkdir(exist_ok=True)
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    for p in (TRAIN, DEV, FINAL):
        assert sha(p) == manifest['input_sha256'][p.name]
    original = json.loads((DEST / 'protocol.json').read_text(encoding='utf-8'))
    assert original['human_ids'] == manifest['train_ids']
    grid = [{'family': family, 'alpha': alpha} for family in FAMILIES for alpha in ALPHAS]
    protocol = {'human_ids': manifest['train_ids'], 'folds': original['folds'], 'grid': grid,
                'selection': 'minimum pooled OOF rounded MAE peraxis; tie first fixed family/alpha order; median ineligible',
                'median': 'diagnostic only; constant outputs unsuitable for responsive character scoring',
                'solver': 'Ridge default auto, matching previous comparison',
                'combined': 'L2 normalize entire TFIDF block and MiniLM block separately; concatenate then divide sqrt2',
                'standalone_scales': 'original raw word+char TFIDF and normalized MiniLM unchanged for reproducibility',
                'vocabulary': 'fit only each human train fold; encoder pretrained and frozen offline',
                'input_sha256': {str(p): sha(p) for p in (TRAIN, DEV, FINAL, DEST / 'protocol.json', DEST / 'cv_results.json')},
                'encoder_files_sha256': {str(p.relative_to(ENCODER_DIR)): sha(p) for p in ENCODER_DIR.rglob('*') if p.is_file()},
                'dev': 'parse only after selected human-only models saved and locked', 'final': 'hash only',
                'limitations': ['Humans are reference annotations, not infallible ground truth.',
                               'Same small training set has informed previous experimentation; selected OOF MAE is optimistic.',
                               'Historically reused dev is exploratory; no independent confirmatory claim.',
                               'No cherry-picking across dev metrics; all selected axes reported together.'], 'paid_api_calls': 0}
    with (TARGET / 'protocol.json').open('x', encoding='utf-8') as f:
        json.dump(protocol, f, indent=2)
    human_by_id = {r['item_id']: r for r in read_rows(TRAIN)}
    human = [human_by_id[i] for i in manifest['train_ids']]
    positions = {r['item_id']: i for i, r in enumerate(human)}
    folds = [(np.array([positions[i] for i in f['train_ids']]), np.array([positions[i] for i in f['validation_ids']])) for f in original['folds']]
    encoder = EmbeddingAxisAdapter(model_name=str(ENCODER_DIR), local_files_only=True)
    hx = encoder._encode([r['utterance'] for r in human])
    np.save(TARGET / 'human_embeddings.npy', hx)
    oofs = {f'{c["family"]}_{c["alpha"]}': [{} for _ in human] for c in grid}
    oofs['median_None'] = [{} for _ in human]
    for fold, (tr, va) in enumerate(folds):
        vocabulary = fit_vocabulary([human[i]['utterance'] for i in tr])
        lx, lv = lexical_features(vocabulary, [human[i]['utterance'] for i in tr]), lexical_features(vocabulary, [human[i]['utterance'] for i in va])
        for family in FAMILIES:
            x, v = representation_features(family, lx, hx[tr]), representation_features(family, lv, hx[va])
            for alpha in ALPHAS:
                name = f'{family}_{alpha}'
                for a in AXES:
                    available = [j for j, i in enumerate(tr) if a in human[i]['axes']]
                    y = [human[tr[j]]['axes'][a] for j in available]
                    head = Ridge(alpha=alpha).fit(x[available], y)
                    pred = quantize(head.predict(v))
                    for i, value in zip(va, pred):
                        oofs[name][i][a] = int(value)
        for a in AXES:
            median = int(quantize(np.median([human[i]['axes'][a] for i in tr if a in human[i]['axes']])))
            for i in va:
                oofs['median_None'][i][a] = median
        print('FOLD', fold + 1, 'COMPLETE', flush=True)
    results = {n: stratified(human, pred) for n, pred in oofs.items()}
    previous = json.loads((DEST / 'cv_results.json').read_text(encoding='utf-8'))
    for name in previous:
        for a in AXES:
            assert results[name]['overall'][a]['mae'] == previous[name]['overall'][a]['mae']
            assert results[name]['overall'][a]['confusion'] == previous[name]['overall'][a]['confusion']
    chosen = {a: min((n for n in oofs if not n.startswith('median')), key=lambda n: results[n]['overall'][a]['mae']) for a in AXES}
    config = {a: {'family': n.rsplit('_', 1)[0], 'alpha': float(n.rsplit('_', 1)[1])} for a, n in chosen.items()}
    write('cv_results.json', results)
    write('selection_lock.json', {'chosen': chosen, 'config': config, 'dev_used': False, 'previous_grid_reproduced': True})
    with (TARGET / 'oof_predictions.jsonl').open('x', encoding='utf-8') as f:
        for i, r in enumerate(human):
            f.write(json.dumps({'item_id': r['item_id'], 'human_reference': r['axes'], 'predictions': {n: p[i] for n, p in oofs.items()}}, ensure_ascii=False) + '\n')
    vocabulary = fit_vocabulary([r['utterance'] for r in human])
    lx = lexical_features(vocabulary, [r['utterance'] for r in human])
    bundle = {'vocabulary': vocabulary, 'encoder_path': str(ENCODER_DIR), 'config': config, 'heads': {}, 'train_ids': manifest['train_ids'], 'research_only': True}
    for a, c in config.items():
        x = representation_features(c['family'], lx, hx)
        ids = [i for i, r in enumerate(human) if a in r['axes']]
        bundle['heads'][a] = Ridge(alpha=c['alpha']).fit(x[ids], [human[i]['axes'][a] for i in ids])
    joblib.dump(bundle, TARGET / 'human_selected.joblib')
    write('fit_lock.json', {'human_selected.joblib': sha(TARGET / 'human_selected.joblib'), 'selected_config': config})
    print('MODELS LOCKED ' + json.dumps(chosen), flush=True)
    dev = read_rows(DEV)
    texts = [r['utterance'] for r in dev]
    dx = encoder._encode(texts)
    predictions = predict_bundle(bundle, texts, embeddings=dx)
    assert predictions == predict_bundle(joblib.load(TARGET / 'human_selected.joblib'), texts, embeddings=dx)
    write('dev_predictions.json', {'ids': [r['item_id'] for r in dev], 'predictions': predictions})
    report = {'chosen': chosen, 'config': config, 'cv_selected': {a: results[chosen[a]]['overall'][a] for a in AXES},
              'dev': stratified(dev, predictions), 'roundtrip_verified': True, 'previous_grid_reproduced': True,
              'all_input_hashes_unchanged': all(sha(p) == h for p, h in protocol['input_sha256'].items()),
              'final_labels_parsed': False, 'deployed': False, 'limitations': protocol['limitations']}
    assert report['all_input_hashes_unchanged']
    write('report.json', report)
    print('DEV ' + json.dumps({a: report['dev']['overall'][a]['mae'] for a in AXES}), flush=True)


if __name__ == '__main__':
    main()
