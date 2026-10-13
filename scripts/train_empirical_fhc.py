"""Train all three heads with frozen human-example AI labels, offline research only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import Ridge

from ai.ridge_axis_adapter import RidgeAxisAdapter
from scripts.compare_fhc_improvements import DEST, stratified
from scripts.compare_full_corpus_labelers import AXES, OUT
from scripts.fhc_round2_select import ami_series
from scripts.train_full_corpus_fhc import examples, vector_predictions
from scripts.train_transfer_axis_models import TRAIN, DEV, FINAL, read_rows

TARGET = DEST / 'empirical_fhc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_annotations(records, ids):
    if len(records) != len(ids) or {r.get('item_id') for r in records} != set(ids):
        raise ValueError('Missing, duplicate, or foreign annotation IDs')
    result = {}
    for r in records:
        required = {'item_id', 'score_status', 'confidence', 'evidence'}
        if not required <= set(r) or set(r) - required - {'score'}:
            raise ValueError('Unexpected annotation schema')
        if type(r['confidence']) is not int or not 0 <= r['confidence'] <= 4:
            raise ValueError('Invalid confidence')
        if not isinstance(r['evidence'], str) or not r['evidence'].strip():
            raise ValueError('Missing annotation evidence')
        status, value = r['score_status'], r.get('score')
        if status == 'final':
            if type(value) is not int or not 0 <= value <= 100 or value % 5:
                raise ValueError('Final score must be integer0..100 multiple5')
        elif status == 'context_insufficient':
            if value is not None:
                raise ValueError('Insufficient context cannot carry a training score')
        else:
            raise ValueError('Unknown annotation status')
        result[r['item_id']] = value
    return result


def main():
    if (TARGET / 'report.json').exists():
        raise FileExistsError('Completed experiment is immutable; use another output directory')
    protocol_path = TARGET / 'protocol.json'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    for path in (TRAIN, DEV, FINAL):
        if sha(path) != manifest['input_sha256'][path.name]:
            raise ValueError('Original human file changed')
    queue_path = TARGET / 'blind_batch50.jsonl'
    if sha(queue_path) != protocol['queue_sha256']:
        raise ValueError('Frozen50 queue changed')
    if sha(TARGET / 'human_examples35.json') != protocol['examples_sha256']:
        raise ValueError('Human examples changed')
    queue = read_rows(queue_path)
    ids = [r['item_id'] for r in queue]
    if len(ids) != 50 or len(set(ids)) != 50:
        raise ValueError('Expected50 unique frozen candidates')
    annotations = {}
    annotation_paths = []
    for axis in AXES:
        path = TARGET / (axis.lower() + '.json')
        annotations[axis] = validate_annotations(json.loads(path.read_text(encoding='utf-8')), ids)
        annotation_paths.append(path)
    inventory = json.loads((OUT / 'corpus_inventory.json').read_text(encoding='utf-8'))
    corpus_path = OUT / 'corpus_tasks.jsonl'
    if sha(corpus_path) != inventory['tasks_sha256']:
        raise ValueError('Protected corpus tasks changed')
    wanted, found = set(ids), {}
    with corpus_path.open(encoding='utf-8') as source:
        for line in source:
            row = json.loads(line)
            if row['item_id'] in wanted:
                if row['item_id'] in found:
                    raise ValueError('Duplicate frozen corpus ID')
                found[row['item_id']] = row
    if set(found) != wanted:
        raise ValueError('Candidate outside frozen protected corpus')
    ai = []
    for r in queue:
        original = found[r['item_id']]
        if r['utterance'] != original['utterance']:
            raise ValueError('Candidate text changed')
        axes = {a: annotations[a][r['item_id']] for a in AXES if annotations[a][r['item_id']] is not None}
        ai.append(dict(original, axes=axes, label_source={a: 'codex_empirical_pseudo_not_human' for a in axes}))
    by_id = {r['item_id']: r for r in read_rows(TRAIN)}
    human = [by_id[i] for i in manifest['train_ids']]
    # Labels are merged only after validating all three independent annotation files.
    (TARGET / 'merged_labels.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in ai), encoding='utf-8')
    execution = {'input_sha256': {str(p): sha(p) for p in [protocol_path, queue_path, TRAIN, *annotation_paths]},
                 'human_ids': manifest['train_ids'], 'ai_ids': ids,
                 'label_counts': {a: sum(a in r['axes'] for r in ai) for a in AXES},
                 'selection_rule': 'none; fixed parameters, report both models after fitting',
                 'final_test': 'hash only; not parsed or scored'}
    with (TARGET / 'execution_manifest.json').open('x', encoding='utf-8') as f:
        json.dump(execution, f, indent=2)
    feature_model = RidgeAxisAdapter(alpha=.1).fit(examples(human))
    models = {}
    for arm in protocol['arms']:
        model = RidgeAxisAdapter(alpha=.1)
        model.word_vec, model.char_vec = feature_model.word_vec, feature_model.char_vec
        for axis in AXES:
            anchors = [r for r in human if axis in r['axes']]
            weights = [protocol['human_weight']] * len(anchors)
            if arm == 'human_plus_empirical50':
                additions = [r for r in ai if axis in r['axes']]
                anchors += additions
                weights += [protocol['ai_weight']] * len(additions)
            model.axis_models[axis] = Ridge(alpha=protocol['alpha_by_axis'][axis], solver='lsqr').fit(
                model._vectorize([r['utterance'] for r in anchors]), [r['axes'][axis] for r in anchors], sample_weight=weights)
        models[arm] = model
        joblib.dump(model, TARGET / (arm + '.joblib'))
    # Freeze model identities before opening dev for scoring.
    with (TARGET / 'fit_lock.json').open('x', encoding='utf-8') as f:
        json.dump({arm: sha(TARGET / (arm + '.joblib')) for arm in models}, f, indent=2)
    dev = read_rows(DEV)
    texts = [r['utterance'] for r in dev]
    predictions = {arm: vector_predictions(model, texts) for arm, model in models.items()}
    for arm in models:
        if predictions[arm] != vector_predictions(joblib.load(TARGET / (arm + '.joblib')), texts):
            raise ValueError('Saved model predictions changed')
    reference = json.loads((DEST / 'nonconstant_predictions.json').read_text(encoding='utf-8'))
    if predictions['human_only'] != reference:
        raise ValueError('Locked human-only baseline failed reproduction')
    predictions['prior_full_corpus_student'] = vector_predictions(joblib.load(OUT / 'codex/student.joblib'), texts)
    metrics = {arm: stratified(dev, pred) for arm, pred in predictions.items()}
    groups = sorted({ami_series(r['source_group']) for r in dev})
    rng = np.random.default_rng(20261013)
    uncertainty = {}
    for axis in AXES:
        delta = {g: [abs(p[axis] - r['axes'][axis]) - abs(q[axis] - r['axes'][axis])
                     for r, p, q in zip(dev, predictions['human_plus_empirical50'], predictions['human_only'])
                     if axis in r['axes'] and ami_series(r['source_group']) == g] for g in groups}
        samples = []
        for _ in range(2000):
            values = [v for g in rng.choice(groups, len(groups), replace=True) for v in delta[g]]
            if values:
                samples.append(np.mean(values))
        uncertainty[axis] = {'delta_mae_new_minus_human': metrics['human_plus_empirical50']['overall'][axis]['mae'] - metrics['human_only']['overall'][axis]['mae'],
                             'descriptive_95pct': np.percentile(samples, [2.5, 97.5]).tolist()}
    if any(sha(Path(p)) != h for p, h in execution['input_sha256'].items()):
        raise ValueError('Input mutated during training')
    report = {'human_rows': len(human), 'human_axes': {a: sum(a in r['axes'] for r in human) for a in AXES},
              'reviewed_ai_rows': len(ai), 'usable_ai_rows': sum(bool(r['axes']) for r in ai),
              'ai_axes': execution['label_counts'], 'metrics': metrics, 'uncertainty': uncertainty,
              'model_selection_from_dev': False, 'roundtrip_verified': True,
              'baseline_reproduced': True, 'original_human_hashes_unchanged': True,
              'final_test_used': False, 'paid_api_calls': 0, 'production_changed': False,
              'limitations': protocol['limitations'] + ['Dev historically reused; not an independent final model test.',
                                                       'Previous full-corpus student differs in training configuration, so its comparison is descriptive.']}
    (TARGET / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    (TARGET / 'dev_predictions.json').write_text(json.dumps(predictions, indent=2), encoding='utf-8')
    print(json.dumps({'ai_axes': report['ai_axes'], 'mae': {arm: {a: vals['overall'][a]['mae'] for a in AXES} for arm, vals in metrics.items()},
                      'uncertainty': uncertainty}, indent=2))


if __name__ == '__main__':
    main()
