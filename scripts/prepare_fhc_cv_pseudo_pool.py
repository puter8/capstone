"""Freeze an unlabeled pool disjoint from all human CV meetings and near texts."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.compare_full_corpus_labelers import OUT
from scripts.fhc_round2_select import ami_series
from scripts.prepare_full_corpus_fhc import ReservedIndex
from scripts.train_transfer_axis_models import TRAIN, DEV, FINAL, read_rows
from scripts.train_empirical_full_corpus_fhc import sha

TARGET = OUT / 'improvement' / 'representation_pseudo'


def freeze_pool(per_source=700):
    TARGET.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    for path in (TRAIN, DEV, FINAL):
        if sha(path) != manifest['input_sha256'][path.name]:
            raise ValueError('Frozen human file changed')
    inventory = json.loads((OUT / 'corpus_inventory.json').read_text(encoding='utf-8'))
    tasks_path, mapping_path = OUT / 'corpus_tasks.jsonl', OUT / 'corpus_mapping.jsonl'
    if sha(tasks_path) != inventory['tasks_sha256']:
        raise ValueError('Frozen corpus changed')
    initial_hashes = {str(p): sha(p) for p in (TRAIN, DEV, FINAL, tasks_path, mapping_path)}
    by_id = {r['item_id']: r for r in read_rows(TRAIN)}
    human = [by_id[i] for i in manifest['train_ids']]
    protected = {ami_series(r['source_group']) for r in human}
    near = ReservedIndex([r['utterance'] for r in human])
    alias_blocked, mapped_records = set(), set()
    with mapping_path.open(encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            mapped_records.add((r['key'], r['source'], r['source_group'], r['source_record_id']))
            if ami_series(r['source_group']) in protected:
                alias_blocked.add(r['key'])
    reviewed = {r['item_id'] for p in (OUT / 'enrichment_codex.jsonl', OUT / 'improvement/empirical_fhc/merged_labels.jsonl') for r in read_rows(p)}
    buckets, reasons = defaultdict(list), Counter()
    seen = set()
    with tasks_path.open(encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            key = row['item_id']
            if key in seen:
                raise ValueError('Duplicate corpus ID')
            seen.add(key)
            if (key, row['source'], row['source_group'], row['source_record_id']) not in mapped_records:
                raise ValueError('Task representative missing from corpus mapping')
            if key in reviewed:
                reasons['previously_direct_reviewed'] += 1
            elif key in alias_blocked or ami_series(row['source_group']) in protected:
                reasons['any_alias_human_group'] += 1
            elif near.matches(row['utterance']):
                reasons['human_near_text'] += 1
            else:
                # Text hash gives a reproducible order without using any scores.
                buckets[row['source']].append(row)
                reasons['eligible'] += 1
    rows = [r for source in sorted(buckets) for r in sorted(buckets[source], key=lambda r: r['item_id'])[:per_source]]
    protocol = {
        'maximum_per_source': per_source, 'selection': 'first SHA256 text IDs per canonical source; no scores',
        'protection': 'all118 human groups/AMI series including every mapping alias plus lexical Jaccard >=.8',
        'counts': dict(reasons), 'eligible_by_source': {s: len(rs) for s, rs in buckets.items()},
        'selected_by_source': dict(Counter(r['source'] for r in rows)), 'selected_count': len(rows),
        'input_hashes': initial_hashes,
        'human_ids': manifest['train_ids'], 'dev_final': 'byte hashes only; not parsed',
        'excluded_reviewed_ids_count': len(reviewed),
        'scope': 'bounded offline method comparison; earlier full238355 experiment preserved'
    }
    if any(sha(Path(p)) != h for p, h in initial_hashes.items()):
        raise ValueError('Pool inputs changed during preparation')
    with (TARGET / 'pool_protocol.json').open('x', encoding='utf-8') as f:
        json.dump(protocol, f, indent=2)
    with (TARGET / 'unlabeled_pool.jsonl').open('x', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    (TARGET / 'pool_lock.json').write_text(json.dumps({'sha256': sha(TARGET / 'unlabeled_pool.jsonl')}, indent=2), encoding='utf-8')
    print(json.dumps({'selected_count': len(rows), 'selected_by_source': protocol['selected_by_source'], 'filter_counts': dict(reasons)}), flush=True)


if __name__ == '__main__':
    freeze_pool()
