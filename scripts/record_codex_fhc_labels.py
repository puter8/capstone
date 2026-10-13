"""Validate and record annotations directly authored by Codex in this chat.

No remote API. The compact private annotation file contains component judgments,
not human labels. Scores are computed with the unchanged v2.2 arithmetic.
"""
import hashlib
import json
from collections import Counter

from scripts.compare_full_corpus_labelers import AXES, OUT, digest
from scripts.fhc_round2_label import WEIGHTS, CURIOSITY_CLAMP, round_to_5_half_up


def main():
    candidates = json.loads((OUT / 'enrichment_candidates.json').read_text(encoding='utf-8'))
    annotation_file = OUT / 'codex_annotations.json'
    authored = json.loads(annotation_file.read_text(encoding='utf-8'))
    assert [r[0] for r in authored] == list(range(1, len(candidates) + 1))
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    run_hash = digest({'candidates': candidates, 'annotations': authored, 'human_inputs': manifest['input_sha256']})
    records = []
    for candidate, entry in zip(candidates, authored):
        index, f, h, c, function, provisional, evidence = entry
        assert function in CURIOSITY_CLAMP and evidence
        record = {'item_id': candidate['item_id'], 'run_sha256': run_hash,
                  'annotator': 'Codex assistant, directly authored in conversation',
                  'rubric_version': 'v2.2', 'human_example_ids': manifest['example_ids'],
                  'axes': {}, 'label_source': {}, 'components': {}, 'score_status': {},
                  'evidence': evidence, 'error': None, 'api_calls': 0}
        for axis, levels, short in zip(AXES, (f, h, c), 'FHC'):
            assert len(levels) == len(WEIGHTS[axis]) and all(v in '01234' for v in levels)
            components = dict(zip(WEIGHTS[axis], map(int, levels)))
            raw100 = 25 * sum(components[k] * weight for k, weight in WEIGHTS[axis].items())
            score = round_to_5_half_up(raw100)
            if axis == 'Curiosity':
                lo, hi = CURIOSITY_CLAMP[function]
                score = max(lo, min(hi, score))
                components['curiosity_function'] = function
            record['components'][axis] = components
            record['score_status'][axis] = 'context_insufficient' if short in provisional else 'final'
            if short not in provisional:
                record['axes'][axis] = score
                record['label_source'][axis] = 'codex_in_chat_pseudo_not_human'
        records.append(record)
    output = OUT / 'enrichment_codex.jsonl'
    content = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records)
    if output.exists():
        assert output.read_text(encoding='utf-8') == content, 'refusing to overwrite frozen annotations'
    else:
        with output.open('x', encoding='utf-8') as f:
            f.write(content)
    audit = {'annotated_rows': len(records), 'usable_rows': sum(bool(r['axes']) for r in records),
             'usable_axes': dict(Counter(a for r in records for a in r['axes'])),
             'annotation_sha256': hashlib.sha256(annotation_file.read_bytes()).hexdigest(),
             'input_sha256': manifest['input_sha256'], 'run_sha256': run_hash,
             'limitations': ['AI judgments, not additional human ground truth.',
                            'Human examples include scale disagreements; no missing context was invented.',
                            'Fragmentary or ambiguous axes were omitted, not labeled zero.']}
    (OUT / 'codex_annotation_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
