"""Measure blinded AI annotations against existing human train labels, not test."""
import hashlib
import json

import numpy as np

from scripts.compare_fhc_improvements import DEST, load_inputs, score
from scripts.compare_full_corpus_labelers import AXES
from scripts.train_fhc_reviewed_augmentation import validated_annotations


def main():
    dest = DEST / 'human_calibration'
    protocol = json.loads((dest / 'protocol.json').read_text(encoding='utf-8'))
    human, _, _ = load_inputs()
    by_id = {r['item_id']: r for r in human}
    ids = protocol['IDs']
    records = json.loads((dest / 'reviewer.json').read_text(encoding='utf-8'))
    annotations = validated_annotations(records, ids)
    rows = [by_id[i] for i in ids]
    pred = [{a: annotations[i]['axes'][a] for a in AXES if annotations[i]['score_status'][a] == 'final'} for i in ids]
    rest = [r for r in human if r['item_id'] not in ids]
    median = {a: int(np.round(np.median([r['axes'][a] for r in rest if a in r['axes']]) / 5) * 5) for a in AXES}
    baseline = [dict(median) for _ in rows]
    paired_baseline = [{a: median[a] for a in p} for p in pred]
    cohorts = {r['item_id']: r['cohort'] for r in [json.loads(s) for s in (DEST / 'oof_predictions.jsonl').read_text(encoding='utf-8').splitlines()]}
    per_cohort = {}
    for cohort in sorted(set(cohorts[i] for i in ids)):
        idx = [j for j, i in enumerate(ids) if cohorts[i] == cohort]
        per_cohort[cohort] = score([rows[j] for j in idx], [pred[j] for j in idx])
    report = {'purpose': protocol['purpose'], 'n': len(rows), 'metrics': score(rows, pred),
              'median_reference_excluding_calibration_rows': median,
              'median_all_rows': score(rows, baseline), 'median_same_predicted_rows': score(rows, paired_baseline),
              'per_cohort': per_cohort, 'provenance': 'existing human TRAIN targets; new Codex predictions',
              'no_independent_model_performance_claim': True,
              'limitations': ['18 rows only; cohorts balanced deliberately, not app prevalence.',
                             'Human context-exposed cohorts and AI single utterance conditions differ.',
                             'No automatic alteration of human labels or fitted models follows this diagnostic.'],
              'input_sha256': {name: hashlib.sha256((dest / name).read_bytes()).hexdigest()
                               for name in ('protocol.json', 'blind_batch18.jsonl', 'reviewer.json')}}
    with (dest / 'report.json').open('x', encoding='utf-8') as out:
        json.dump(report, out, indent=2, allow_nan=False)
    print(json.dumps({a: {'mae': report['metrics'][a]['mae'], 'coverage': report['metrics'][a]['coverage'],
                         'paired_median_mae': report['median_same_predicted_rows'][a]['mae']} for a in AXES}, indent=2))


if __name__ == '__main__':
    main()
