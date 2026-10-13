"""Controlled, offline source ablation. Frozen human vocabulary, no dev selection."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import vstack
from sklearn.linear_model import Ridge

from ai.ridge_axis_adapter import RidgeAxisAdapter
from scripts.compare_full_corpus_labelers import AXES, OUT, metrics
from scripts.train_full_corpus_fhc import examples, vector_predictions
from scripts.train_transfer_axis_models import TRAIN, DEV, FINAL, read_rows

DEST = OUT / 'improvement' / 'controlled_ablation'


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    for path in (TRAIN, DEV, FINAL):
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['input_sha256'][path.name]:
            raise ValueError('Frozen human input changed')
    ids = set(manifest['train_ids'])
    human = [r for r in read_rows(TRAIN) if r['item_id'] in ids]
    if len(human) != len(ids):
        raise ValueError('Missing or duplicate frozen human IDs')
    candidates = {r['item_id']: r for r in json.loads((OUT / 'enrichment_candidates.json').read_text(encoding='utf-8'))}
    direct = read_rows(OUT / 'enrichment_codex.jsonl')
    ai = [dict(candidates[r['item_id']], axes=r['axes'], label_source=r['label_source']) for r in direct if r['axes']]
    direct_ids = {r['item_id'] for r in direct}
    protocol = {
        'primary_metric': 'MAE', 'selection': 'none; explanatory ablation only',
        'feature_space': 'word/char TFIDF fitted only on frozen human118; identical across arms',
        'regressor': 'Ridge(alpha=1,solver=lsqr); same rounding across arms',
        'human_weight': 1, 'direct_ai_weight': 0.5,
        'arms': {'human': 0, 'human_ai': 0, 'human_ai_pseudo025': .25, 'human_ai_pseudo100': 1.0},
        'pseudo_weight': 'total per-axis pseudo weight = ratio * human axis label count',
        'pseudo_exclusion': 'all directly reviewed70 removed to prevent double counting or filling omissions',
        'final_test': 'hash only; never parsed, scored, or used for selection',
        'limitations': ['Historical teachers were selected using dev, so pseudo arms are exploratory.',
                        'Original student uses augmented vocabulary and duplicates usable direct annotations as pseudo anchors; this experiment controls these differences.',
                        'MAE uncertainty on reused dev is descriptive, not an independent final test.'],
        'input_sha256': manifest['input_sha256'],
    }
    protocol_path = DEST / 'protocol.json'
    if protocol_path.exists():
        raise FileExistsError('Use a new directory for another experiment')
    protocol_path.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    feature_model = RidgeAxisAdapter().fit(examples(human))
    chunks, labels, batch, n = [], {a: [] for a in AXES}, [], 0
    def flush():
        if not batch:
            return
        chunks.append(feature_model._vectorize([r['utterance'] for r in batch]).tocsr())
        for r in batch:
            for axis in AXES:
                labels[axis].append(r['axes'].get(axis, np.nan))
        batch.clear()
    with (OUT / 'codex' / 'corpus_labeled.jsonl').open(encoding='utf-8') as source:
        for line in source:
            row = json.loads(line)
            if row['item_id'] in direct_ids:
                continue
            if any(not s.startswith('local_') for s in row['label_source'].values()):
                raise ValueError('Unexpected pseudo provenance')
            batch.append(row)
            n += 1
            if len(batch) == 4000:
                flush()
        flush()
    x = vstack(chunks, format='csr')
    del chunks
    print(f'Frozen features for {n} local pseudo rows', flush=True)
    dev = read_rows(DEV)
    results, predictions = {}, {}
    for name, ratio in protocol['arms'].items():
        model = RidgeAxisAdapter()
        model.word_vec, model.char_vec = feature_model.word_vec, feature_model.char_vec
        for axis in AXES:
            anchors = [r for r in human if axis in r['axes']]
            nhuman = len(anchors)
            weights = [1.] * nhuman
            if name != 'human':
                additional = [r for r in ai if axis in r['axes']]
                anchors += additional
                weights += [.5] * len(additional)
            xx = feature_model._vectorize([r['utterance'] for r in anchors]).tocsr()
            yy = np.array([r['axes'][axis] for r in anchors], dtype=float)
            ww = np.array(weights)
            if ratio:
                pseudo_y = np.asarray(labels[axis])
                keep = np.isfinite(pseudo_y)
                xx = vstack([xx, x[keep]], format='csr')
                yy = np.r_[yy, pseudo_y[keep]]
                ww = np.r_[ww, np.full(keep.sum(), ratio * nhuman / keep.sum())]
            model.axis_models[axis] = Ridge(alpha=1., solver='lsqr').fit(xx, yy, sample_weight=ww)
        pred = vector_predictions(model, [r['utterance'] for r in dev])
        predictions[name] = pred
        results[name] = metrics(dev, pred)
        print(name, {a: round(results[name][a]['mae'], 3) for a in AXES}, flush=True)
    (DEST / 'report.json').write_text(json.dumps({'protocol': protocol, 'local_pseudo_rows': n,
        'dev_metrics': results}, indent=2, allow_nan=False), encoding='utf-8')
    (DEST / 'predictions.json').write_text(json.dumps({'dev_ids': [r['item_id'] for r in dev],
        'predictions': predictions}, indent=2, allow_nan=False), encoding='utf-8')


if __name__ == '__main__':
    main()
