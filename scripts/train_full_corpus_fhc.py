"""Budgeted Gemini acquisition, full-corpus local labeling, and research student training.

All outputs are private/gitignored. Human labels, Gemini labels and local
teacher predictions retain separate provenance. No production model is replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from collections import Counter, defaultdict

import joblib
import numpy as np
import requests
from scipy.sparse import vstack
from sklearn.linear_model import Ridge

from ai.ml_baseline import AxisTrainingExample, _load_jsonl_axis_dataset
from ai.ridge_axis_adapter import RidgeAxisAdapter
from ai.embedding_axis_adapter import EmbeddingAxisAdapter
from scripts import fhc_round2_label as oracle
from scripts.compare_full_corpus_labelers import AXES, OUT, prepare, digest, metrics
from scripts.train_transfer_axis_models import TRAIN, ENCODER_DIR, read_rows

MAX_USD = 0.25  # <= 750 KRW at conservative budgeting rate 3,000 KRW/USD; margin remains
PRIOR_RESERVE_USD = 0.08  # 35-item pilot + connection probes; overestimated, not actual billing


def vector_predictions(model, texts):
    x = model._vectorize(texts)
    values = {a: np.round(np.clip(m.predict(x), 0, 100) / 5) * 5 for a, m in model.axis_models.items()}
    return [{a: int(values[a][i]) for a in AXES} for i in range(len(texts))]


def examples(rows):
    return [AxisTrainingExample(r['utterance'], r['axes'], 'conversation', r['source'],
                                r['source_group'], r['label_source']) for r in rows if r['axes']]


def base():
    train, _, dev, manifest = prepare()
    return train, dev, manifest, RidgeAxisAdapter().fit(examples(train))


def select():
    path = OUT / 'enrichment_candidates.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    _, _, _, teacher = base()
    # Reservoirs span each whole corpus; expensive model ranking is bounded.
    rng, pools, counts = random.Random(20261013), defaultdict(list), Counter()
    with (OUT / 'corpus_tasks.jsonl').open(encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            s = r['source']
            counts[s] += 1
            if len(pools[s]) < 500:
                pools[s].append(r)
            else:
                j = rng.randrange(counts[s])
                if j < 500:
                    pools[s][j] = r
    selected = {}
    for source, pool in sorted(pools.items()):
        preds = vector_predictions(teacher, [r['utterance'] for r in pool])
        # Extremes from all axes, then independent random coverage. No dev scores used.
        chosen = set()
        for axis in AXES:
            order = sorted(range(len(pool)), key=lambda i: (preds[i][axis], pool[i]['item_id']))
            chosen.update((order[0], order[-1]))
        order = list(range(len(pool)))
        rng.shuffle(order)
        for i in order:
            if len(chosen) >= 10:
                break
            chosen.add(i)
        for i in sorted(chosen):
            selected[pool[i]['item_id']] = pool[i]
    result = list(selected.values())
    with path.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    return result


def enrich():
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    rows = select()
    log = OUT / 'enrichment_gemini.jsonl'
    old = read_rows(log) if log.exists() else []
    run_hash = digest({'pilot': manifest, 'candidates': rows, 'budget_usd': MAX_USD})
    if any(r['run_sha256'] != run_hash for r in old):
        raise ValueError('foreign enrichment run')
    done = {r['item_id'] for r in old}
    ledger = OUT / 'paid_attempts.jsonl'
    attempts = read_rows(ledger) if ledger.exists() else []
    if len(done) != len(old) or len(attempts) != len(old) or {r['item_id'] for r in attempts} != done:
        raise ValueError('ambiguous/duplicate paid attempt; reconcile ledger before resuming, never auto-retry')
    if any(r['run_sha256'] != run_hash for r in attempts):
        raise ValueError('foreign paid attempt ledger')
    spent_bound = PRIOR_RESERVE_USD + sum(r['cost_upper_usd'] for r in old)
    key = oracle.load_api_key()
    for i, row in enumerate(rows):
        if row['item_id'] in done:
            continue
        payload = {'system_instruction': {'parts': [{'text': manifest['system_prompt']}]},
                   'contents': [{'parts': [{'text': oracle.USER_TEMPLATE.format(utterance=row['utterance'])}]}],
                   'generationConfig': oracle.GENERATION_CONFIG}
        # One input token per UTF-8 byte + overhead, maximum output tokens, no retries.
        bound = (len(json.dumps(payload, ensure_ascii=False).encode()) + 512) * 0.10 / 1e6 + 1024 * 0.40 / 1e6
        if spent_bound + bound > MAX_USD:
            print('Budget guard stopped before another paid request', flush=True)
            break
        oracle.throttle()
        record = {'item_id': row['item_id'], 'run_sha256': run_hash, 'cost_upper_usd': bound,
                  'axes': {}, 'label_source': {}, 'error': None}
        # Charge the conservative bound before networking; uncertain calls are never auto-retried.
        with ledger.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'item_id': row['item_id'], 'run_sha256': run_hash, 'cost_upper_usd': bound}) + '\n')
            f.flush()
            os.fsync(f.fileno())
        try:
            resp = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{oracle.MODEL}:generateContent',
                                 headers={'x-goog-api-key': key}, json=payload, timeout=60)
            record['http_status'] = resp.status_code
            record['raw_response'] = resp.text
            if resp.status_code != 200:
                raise ValueError(f'HTTP {resp.status_code}')
            envelope = resp.json()
            record['usage'] = envelope.get('usageMetadata')
            cand = envelope['candidates'][0]
            if cand.get('finishReason') != 'STOP':
                raise ValueError('non-STOP finish')
            text = ''.join(p.get('text', '') for p in cand['content']['parts'] if not p.get('thought'))
            label = oracle.compute_labels(json.loads(text))
            record['label'] = label
            record['axes'] = {a: label['axes'][a] for a in AXES if label['score_status'][a] == 'final'}
            record['label_source'] = {a: 'gemini_human_examples_pseudo' for a in record['axes']}
        except (requests.RequestException, ValueError, KeyError, TypeError, RecursionError) as exc:
            record['error'] = type(exc).__name__ if isinstance(exc, requests.RequestException) else str(exc)
        with log.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
            f.flush()
            os.fsync(f.fileno())
        spent_bound += bound
        print(f'Enrichment {i + 1}/{len(rows)}: {record["error"] or "recorded"}; upper bound ${spent_bound:.4f}', flush=True)
        if record.get('http_status') != 200:
            raise RuntimeError('transport/API failure; recorded and stopped')


def finish(provider='gemini'):
    import torch
    torch.set_num_threads(4)
    human, dev, manifest, baseline = base()
    selected = {r['item_id']: r for r in select()}
    records = read_rows(OUT / f'enrichment_{provider}.jsonl')
    artifact_dir = OUT / provider
    artifact_dir.mkdir(exist_ok=True)
    augmented = [dict(selected[r['item_id']], axes=r['axes'], label_source=r['label_source'])
                 for r in records if r['axes']]
    teacher = RidgeAxisAdapter().fit(examples(human + augmented))
    embedding = EmbeddingAxisAdapter(model_name=str(ENCODER_DIR), local_files_only=True).fit(examples(human))
    embedding_augmented = EmbeddingAxisAdapter(encoder=embedding.encoder).fit(examples(human + augmented))
    dev_texts = [r['utterance'] for r in dev]
    baseline_metrics = metrics(dev, vector_predictions(baseline, dev_texts))
    augmented_metrics = metrics(dev, vector_predictions(teacher, dev_texts))
    teachers = {'human_tfidf': baseline, 'augmented_tfidf': teacher,
                'human_embedding': embedding, 'augmented_embedding': embedding_augmented}
    all_metrics = {'human_tfidf': baseline_metrics, 'augmented_tfidf': augmented_metrics,
                   'human_embedding': metrics(dev, embedding.predict_many(dev_texts)),
                   'augmented_embedding': metrics(dev, embedding_augmented.predict_many(dev_texts))}
    # Relative dev selection is exploratory. It does NOT turn an unsupported tier into PASS.
    chosen = {a: max(all_metrics, key=lambda name: (all_metrics[name][a]['macro_recall_observed_tiers'],
                                                    -all_metrics[name][a]['mae'])) for a in AXES}
    print('Selected local teachers:', chosen, flush=True)
    (artifact_dir / 'teacher_comparison.json').write_text(json.dumps(all_metrics, indent=2), encoding='utf-8')
    joblib.dump({'human': baseline, 'augmented': teacher, 'chosen': chosen,
                 'embedding_heads': embedding.axis_models,
                 'embedding_augmented_heads': embedding_augmented.axis_models,
                 'encoder_path': str(ENCODER_DIR)}, artifact_dir / 'teachers.joblib')
    label_path = artifact_dir / 'corpus_labeled.jsonl'
    if label_path.exists():
        raise FileExistsError('full-corpus labels already exist; refusing overwrite')
    direct = {r['item_id']: r for r in records}
    counts, tiers = Counter(), {a: Counter() for a in AXES}
    chunks, ys = [], {a: [] for a in AXES}
    # Freeze student feature space to the human/AI-supported teacher vocabulary.
    with (OUT / 'corpus_tasks.jsonl').open(encoding='utf-8') as source, label_path.open('x', encoding='utf-8') as out:
        batch = []
        def flush():
            if not batch:
                return
            texts = [r['utterance'] for r in batch]
            predictions = {}
            embedding_features = None
            for name in set(chosen.values()):
                model = teachers[name]
                if 'embedding' in name:
                    if embedding_features is None:
                        embedding_features = embedding._encode(texts)
                    vals = {a: np.round(np.clip(m.predict(embedding_features), 0, 100) / 5) * 5
                            for a, m in model.axis_models.items()}
                    predictions[name] = [{a: int(vals[a][i]) for a in AXES} for i in range(len(texts))]
                else:
                    predictions[name] = vector_predictions(model, texts)
            chunks.append(teacher._vectorize(texts).tocsr())
            for i, r in enumerate(batch):
                values = {a: predictions[chosen[a]][i][a] for a in AXES}
                provenance = {a: 'local_' + chosen[a] + '_pseudo' for a in AXES}
                if r['item_id'] in direct:
                    # A directly reviewed context-insufficient axis must not be silently
                    # replaced by the local model's guess.
                    values = dict(direct[r['item_id']]['axes'])
                    provenance = dict(direct[r['item_id']]['label_source'])
                out.write(json.dumps(dict(r, axes=values, label_source=provenance,
                                          status='pseudo_not_human_ground_truth'), ensure_ascii=False) + '\n')
                for a in AXES:
                    ys[a].append(values.get(a, float('nan')))
                    if a in values:
                        tiers[a][0 if values[a] <= 33 else 1 if values[a] <= 66 else 2] += 1
                        counts[provenance[a]] += 1
            batch.clear()
        for line in source:
            batch.append(json.loads(line))
            if len(batch) == 2000:
                flush()
                print(f'Labeled {len(ys[AXES[0]])}', flush=True)
        flush()
    x = vstack(chunks, format='csr')
    del chunks
    student = RidgeAxisAdapter()
    student.word_vec, student.char_vec = teacher.word_vec, teacher.char_vec
    for a in AXES:
        anchors = [r for r in human + augmented if a in r['axes']]
        anchor_x = teacher._vectorize([r['utterance'] for r in anchors])
        # Total local-pseudo weight equals human weight, rather than drowning 118 humans in 238k predictions.
        labels = np.asarray(ys[a])
        keep = np.isfinite(labels)
        weights = np.full(int(keep.sum()), sum(a in r['axes'] for r in human) / keep.sum())
        anchor_weights = [1.0 if r in human else 0.5 for r in anchors]
        student.axis_models[a] = Ridge(alpha=1.0, solver='lsqr').fit(
            vstack([anchor_x, x[keep]], format='csr'), np.r_[[r['axes'][a] for r in anchors], labels[keep]],
            sample_weight=np.r_[anchor_weights, weights])
    joblib.dump(student, artifact_dir / 'student.joblib')
    restored = joblib.load(artifact_dir / 'student.joblib')
    predictions = vector_predictions(student, dev_texts)
    assert predictions == vector_predictions(restored, dev_texts)
    result = {'human_rows': len(human), 'direct_label_provider': provider, 'ai_rows_with_usable_axes': len(augmented),
              'full_corpus_unique_labeled': x.shape[0], 'provenance_axis_counts': dict(counts),
              'tier_counts': {a: dict(t) for a, t in tiers.items()},
              'baseline_dev': baseline_metrics, 'augmented_teacher_dev': augmented_metrics,
              'all_teacher_dev': all_metrics, 'selected_teacher_by_axis': chosen, 'student_dev': metrics(dev, predictions),
              'artifact_roundtrip_verified': True, 'deployed': False,
              'limitations': ['Automatic labels are not independent human evidence.',
                             'Dev reused for exploratory teacher choice; no unbiased generalization claim.',
                             'Research only; source-specific licensing restrictions remain.',
                             'Full-corpus learning can reproduce teacher errors; it is not proof of improvement.']}
    (artifact_dir / 'training_report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=('select', 'enrich', 'finish'))
    p.add_argument('--provider', choices=('gemini', 'codex'), default='codex')
    args = p.parse_args()
    if args.command == 'finish':
        finish(args.provider)
    elif args.command == 'enrich':
        if args.provider != 'gemini':
            raise ValueError('Codex labels are authored in-chat; no API calls are made for this provider')
        enrich()
    else:
        select()
