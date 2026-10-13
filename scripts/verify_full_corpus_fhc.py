"""Verify completed Codex-derived corpus artifacts without making API calls."""
import hashlib
import json
import math
from collections import Counter
from itertools import zip_longest

from scripts.compare_full_corpus_labelers import OUT, AXES
from scripts.train_transfer_axis_models import TRAIN, DEV, FINAL


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = OUT / 'codex'
    report = json.loads((folder / 'training_report.json').read_text(encoding='utf-8'))
    inventory = json.loads((OUT / 'corpus_inventory.json').read_text(encoding='utf-8'))
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    for path in (TRAIN, DEV, FINAL):
        if sha(path) != manifest['input_sha256'][path.name]:
            raise ValueError('original human inputs changed')
    if sha(OUT / 'corpus_tasks.jsonl') != inventory['tasks_sha256']:
        raise ValueError('prepared corpus changed')
    direct = {r['item_id']: r for r in map(json.loads, (OUT / 'enrichment_codex.jsonl').read_text(encoding='utf-8').splitlines())}
    count, empty, ids, sources, provenance, axis_counts = 0, 0, set(), Counter(), Counter(), Counter()
    with (OUT / 'corpus_tasks.jsonl').open(encoding='utf-8') as tasks, (folder / 'corpus_labeled.jsonl').open(encoding='utf-8') as labeled:
        for left, right in zip_longest(tasks, labeled):
            if left is None or right is None:
                raise ValueError('task/output count mismatch')
            task, row = json.loads(left), json.loads(right)
            for key in ('item_id', 'utterance', 'source', 'source_group', 'source_record_id'):
                if row[key] != task[key]:
                    raise ValueError('output lost source identity')
            if row['item_id'] in ids:
                raise ValueError('duplicate output identity')
            ids.add(row['item_id'])
            if row['item_id'] in direct and row['axes'] != direct[row['item_id']]['axes']:
                raise ValueError('direct judgments or context exclusions were overwritten')
            if set(row['axes']) != set(row['label_source']):
                raise ValueError('missing label provenance')
            for axis, score in row['axes'].items():
                if axis not in AXES or isinstance(score, bool) or not math.isfinite(score) or not 0 <= score <= 100 or score % 5:
                    raise ValueError('invalid axis score')
                origin = row['label_source'][axis]
                if origin != 'codex_in_chat_pseudo_not_human' and not (origin.startswith('local_') and origin.endswith('_pseudo')):
                    raise ValueError('unexpected provenance (human/Gemini masquerade)')
                provenance[origin] += 1
                axis_counts[axis] += 1
            count += 1
            empty += not row['axes']
            sources[row['source']] += 1
    if count != inventory['unique_label_tasks'] or count != report['full_corpus_unique_labeled']:
        raise ValueError('reported corpus coverage differs from actual output')
    if dict(provenance) != report['provenance_axis_counts']:
        raise ValueError('reported provenance counts differ')
    result = {'status': 'PASS_ARTIFACT_INTEGRITY_ONLY', 'processed_rows': count,
              'rows_with_at_least_one_axis': count - empty, 'context_insufficient_rows': empty,
              'axis_label_counts': dict(axis_counts), 'source_counts': dict(sources),
              'original_human_files_unchanged': True, 'gemini_labels_in_this_run': 0,
              'student_sha256': sha(folder / 'student.joblib'),
              'corpus_labels_sha256': sha(folder / 'corpus_labeled.jsonl'),
              'warning': 'Artifact integrity is not evidence of label accuracy or performance-gate passage.'}
    (folder / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
