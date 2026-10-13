"""Inventory all seven canonical corpora and prepare private, deduplicated tasks.

No API calls. Existing human labels are never overwritten. Held-out groups,
the original hash-based eval branch, and exact/near reserved texts are excluded.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.compare_full_corpus_labelers import OUT, ROOT, prepare
from scripts.fhc_round2_select import ami_series, protected_meetings, word_set
from scripts.select_purpose_v3_active_candidates import eval_or_train, group_key, normalize_text, load_exclusions
from scripts.train_transfer_axis_models import TRAIN, DEV, FINAL, read_rows


class ReservedIndex:
    def __init__(self, texts):
        self.words = [word_set(t) for t in texts]
        self.index = defaultdict(set)
        for i, words in enumerate(self.words):
            for word in words:
                self.index[word].add(i)

    def matches(self, text):
        words = word_set(text)
        candidates = set()
        for word in words:
            candidates.update(self.index.get(word, ()))
        return any(len(words & self.words[i]) / len(words | self.words[i]) >= 0.8
                   for i in candidates
                   if min(len(words), len(self.words[i])) >= 0.8 * max(len(words), len(self.words[i])))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / 'corpus_tasks.jsonl'
    if target.exists():
        raise FileExistsError('prepared tasks already exist; do not overwrite frozen inputs')
    reserved_rows = read_rows(DEV) + read_rows(FINAL)
    seed = read_rows(ROOT / 'data/fixtures/pally_purpose_v1_items_100.jsonl')
    reserved_texts = [r['utterance'] for r in reserved_rows]
    reserved_texts += [r['target_turn'] for r in seed if r['split'] == 'final_test']
    for name in ('ml_transition_gold_human_200.jsonl', 'ml_transition_reserved_final_test_pool.jsonl'):
        reserved_texts += [r['utterance'] for r in read_rows(ROOT / 'data/fixtures' / name)]
    near = ReservedIndex(reserved_texts)
    protected = {ami_series(g) for g in protected_meetings()}
    _, old_groups = load_exclusions()
    human_texts = {normalize_text(r['utterance']) for r in read_rows(TRAIN)}
    seen = set()
    stats, hashes = {}, {}
    tasks_tmp = OUT / 'corpus_tasks.preparing.jsonl'
    map_tmp = OUT / 'corpus_mapping.preparing.jsonl'
    with tasks_tmp.open('w', encoding='utf-8') as tasks, map_tmp.open('w', encoding='utf-8') as mapping:
        for path in sorted((ROOT / 'data/fixtures').glob('*utterances.jsonl')):
            counts = Counter()
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            with path.open(encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    counts['raw'] += 1
                    text = normalize_text(r['utterance'])
                    if not r.get('source_group') or not r.get('source_record_id'):
                        raise ValueError(f'missing provenance in {path.name}')
                    if not text:
                        reason = 'empty'
                    elif ami_series(r['source_group']) in protected or group_key(r) in old_groups:
                        reason = 'protected_group'
                    elif eval_or_train(r) == 'eval':
                        reason = 'reserved_hash_branch'
                    elif text in human_texts:
                        reason = 'human_label_preserved'
                    elif near.matches(text):
                        reason = 'reserved_exact_or_near_text'
                    else:
                        reason = 'eligible'
                    counts[reason] += 1
                    if reason != 'eligible':
                        continue
                    key = hashlib.sha256(text.encode()).hexdigest()
                    mapping.write(json.dumps({'key': key, 'source': r['source'],
                                              'source_group': r['source_group'],
                                              'source_record_id': r['source_record_id']}) + '\n')
                    if key in seen:
                        counts['duplicate_reuse'] += 1
                        continue
                    seen.add(key)
                    counts['unique_tasks'] += 1
                    task = {k: r[k] for k in ('utterance', 'source', 'source_group', 'source_record_id')}
                    task.update(item_id=key, label_source='unlabeled')
                    tasks.write(json.dumps(task, ensure_ascii=False) + '\n')
            stats[path.name] = dict(counts)
            print(path.name, dict(counts), flush=True)
    tasks_tmp.rename(target)
    map_tmp.rename(OUT / 'corpus_mapping.jsonl')
    report = {'corpora': stats, 'unique_label_tasks': len(seen), 'source_sha256': hashes,
              'scope': 'all canonical utterance corpora; derived copies are not extra independent data',
              'tasks_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'restrictions': 'Research artifacts only; corpus-specific deployment restrictions remain.'}
    (OUT / 'corpus_inventory.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('unique labeling tasks:', len(seen), flush=True)


if __name__ == '__main__':
    main()
