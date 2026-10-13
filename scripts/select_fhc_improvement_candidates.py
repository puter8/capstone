"""Acquire unlabeled train-only neighbors of human out-of-fold errors.

Never opens dev/final data or calls an API. Acquisition diagnostics are private;
the separate annotation queue exposes only a target utterance and opaque ID.
Similarity is a selection heuristic, never a source of copied labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/models/full-corpus-fhc'
AXES = ('Formality', 'Humor', 'Curiosity')


def read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(oof_path: Path, output: Path, per_axis: int = 12):
    manifest = json.loads((BASE / 'pilot_manifest.json').read_text(encoding='utf-8'))
    train_path = ROOT / 'data/fixtures/pally_purpose_v3_train_dev_split_train.jsonl'
    if sha(train_path) != manifest['input_sha256'][train_path.name]:
        raise ValueError('human train changed since frozen manifest')
    human = {r['item_id']: r for r in read(train_path) if r['item_id'] in manifest['train_ids']}
    # Input contract: one row per human train item with a fold and a prediction dict.
    oof = read(oof_path)
    if {r['item_id'] for r in oof} != set(human) or len(oof) != len(human):
        raise ValueError('OOF must cover exactly frozen clean human training IDs')
    protocol_path = oof_path.with_name('protocol.json')
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    folds = {}
    for fold_no, fold in enumerate(protocol['folds']):
        training, validation = set(fold['train_ids']), set(fold['validation_ids'])
        if training & validation or training | validation != set(human):
            raise ValueError('invalid OOF train/validation partition')
        for item_id in validation:
            if item_id in folds:
                raise ValueError('multiple validation folds for same item')
            folds[item_id] = fold_no
    if set(folds) != set(human):
        raise ValueError('OOF folds do not cover all human IDs')
    for r in oof:
        r['fold'] = folds[r['item_id']]
        # Fixed pre-existing alpha=1 baseline; no best-OOF-model selection here.
        r['prediction'] = r['predictions']['tfidf_1.0']
        if 'fold' not in r or not all(a in r['prediction'] for a in human[r['item_id']]['axes']):
            raise ValueError('missing fold or per-axis OOF prediction')
        if not all(np.isfinite(v) and 0 <= v <= 100 for v in r['prediction'].values()):
            raise ValueError('invalid OOF prediction')
    tasks_path = BASE / 'corpus_tasks.jsonl'
    inventory = json.loads((BASE / 'corpus_inventory.json').read_text(encoding='utf-8'))
    # Support the original inventory field without accessing reserved texts.
    task_hash = sha(tasks_path)
    expected_hash = inventory['tasks_sha256']
    if task_hash != expected_hash:
        raise ValueError('frozen corpus task checksum changed')
    excluded = {r['item_id'] for r in read(BASE / 'enrichment_codex.jsonl')}
    rng, pools, counts = random.Random(20261014), defaultdict(list), Counter()
    with tasks_path.open(encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            if row['item_id'] in excluded or len(row['utterance'].split()) < 4:
                continue
            source = row['source']
            counts[source] += 1
            if len(pools[source]) < 1000:
                pools[source].append(row)
            else:
                j = rng.randrange(counts[source])
                if j < 1000:
                    pools[source][j] = row
    pool = [r for source in sorted(pools) for r in pools[source]]
    vec = TfidfVectorizer(analyzer='char', ngram_range=(3, 5), max_features=30000)
    vec.fit([r['utterance'] for r in human.values()])
    x = vec.transform([r['utterance'] for r in pool])
    selected, groups = {}, Counter()
    def take(index, reason):
        row = pool[index]
        group = row['source_group']
        # AMI scenario variants share a group cap.
        if len(group) == 7 and group[:2] in ('ES', 'IS', 'TS') and group[2:6].isdigit():
            group = group[:6]
        group = (row['source'], group)
        if row['item_id'] in selected or groups[group] >= 2:
            return False
        selected[row['item_id']] = dict(row, acquisition=reason)
        groups[group] += 1
        return True
    for axis in AXES:
        difficult = sorted((r for r in oof if axis in human[r['item_id']]['axes']),
                           key=lambda r: (-abs(r['prediction'][axis] - human[r['item_id']]['axes'][axis]), r['item_id']))
        taken = 0
        for anchor in difficult:
            if taken >= per_axis:
                break
            similarities = (x @ vec.transform([human[anchor['item_id']]['utterance']]).T).toarray().ravel()
            for i in np.argsort(-similarities, kind='stable')[:100]:
                if similarities[i] <= 0:
                    break
                if take(int(i), {'axis': axis, 'strategy': 'human_oof_error_neighbor',
                                 'anchor_id': anchor['item_id'], 'anchor_fold': anchor['fold'],
                                 'anchor_absolute_error': abs(anchor['prediction'][axis] - human[anchor['item_id']]['axes'][axis]),
                                 'lexical_similarity': float(similarities[i])}):
                    taken += 1
                    break
    # Preserve random coverage; do not claim this selected mixture is prevalence data.
    for source in sorted(pools):
        order = [i for i, r in enumerate(pool) if r['source'] == source]
        rng.shuffle(order)
        taken = 0
        for i in order:
            if take(i, {'strategy': 'random_reference'}):
                taken += 1
            if taken >= 2:
                break
    if not output.resolve().is_relative_to(BASE.resolve()):
        raise ValueError('text-bearing outputs must remain in private full-corpus directory')
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'annotation_queue.jsonl').exists():
        raise ValueError('refusing to overwrite frozen acquisition')
    diagnostics = list(selected.values())
    queue = [{'item_id': r['item_id'], 'utterance': r['utterance']} for r in diagnostics]
    for name, rows in (('acquisition_diagnostics.jsonl', diagnostics), ('annotation_queue.jsonl', queue)):
        (output / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    report = {'rows': len(queue), 'source_counts': dict(Counter(r['source'] for r in diagnostics)),
              'acquisition_model': 'tfidf_1.0 fixed human-only OOF baseline',
              'oof_sha256': sha(oof_path), 'train_sha256': sha(train_path), 'tasks_sha256': task_hash,
              'oof_protocol_sha256': sha(protocol_path),
              'annotation_queue_sha256': sha(output / 'annotation_queue.jsonl'),
              'human_labels_copied': 0, 'dev_or_final_opened': False,
              'status': 'UNLABELED_ACQUISITION_QUEUE',
              'limitations': ['Training-only errors guide selection, not scores.',
                              'An upstream OOF audit must verify fold training exclusion.',
                              'Human cohort inconsistencies can produce hard examples.',
                              'Existing AI labels are excluded; no new labels have been assigned.']}
    (output / 'acquisition_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--oof', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=BASE / 'improvement/acquisition')
    parser.add_argument('--per-axis', type=int, default=12)
    args = parser.parse_args()
    select(args.oof, args.output, args.per_axis)
