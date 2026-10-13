"""Seal a fresh train-only labeler check; never load dev or final-test data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np

from scripts.calibrate_fhc_formality import FIELDS, predict
from scripts.compare_fhc_improvements import components, score
from scripts.fhc_round2_label import CASE_TYPES, WEIGHTS, _strict_int, round_to_5_half_up

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/models/full-corpus-fhc'
DEST = BASE / 'improvement/alignment'
TRAIN = ROOT / 'data/fixtures/pally_purpose_v3_train_dev_split_train.jsonl'
SEED = 'fresh-formality-group-check-20261015'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def training():
    manifest = read(BASE / 'pilot_manifest.json')
    if sha(TRAIN) != manifest['input_sha256'][TRAIN.name]:
        raise ValueError('Frozen human training data changed')
    rows = [json.loads(s) for s in TRAIN.read_text(encoding='utf-8').splitlines() if s.strip()]
    by_id = {r['item_id']: r for r in rows}
    if len(by_id) != len(rows) or len(set(manifest['train_ids'])) != len(manifest['train_ids']):
        raise ValueError('Duplicate human IDs')
    return [by_id[i] for i in manifest['train_ids']], manifest


def fresh_sample(rows, blocked_ids, count=18):
    """Select only by a fixed hash, with one row per protected component."""
    groups = components(rows)
    blocked_groups = {g for r, g in zip(rows, groups) if r['item_id'] in blocked_ids}
    eligible = [(r, g) for r, g in zip(rows, groups)
                if g not in blocked_groups and 'Formality' in r['axes']]
    ranked = sorted(eligible, key=lambda rg: hashlib.sha256(
        (SEED + rg[0]['item_id']).encode()).hexdigest())
    selected, seen = [], set()
    for row, group in ranked:
        if group in seen:
            continue
        seen.add(group)
        selected.append((row, group))
        if len(selected) == count:
            break
    if len(selected) != count:
        raise ValueError('Insufficient independent fresh groups')
    return selected, len(eligible), len({g for _, g in eligible})


def write_new(path, obj, *, jsonl=False):
    with path.open('x', encoding='utf-8') as f:
        if jsonl:
            for row in obj:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
        else:
            json.dump(obj, f, ensure_ascii=False, indent=2)


def prepare():
    rows, manifest = training()
    prior_path = BASE / 'improvement/human_calibration/protocol.json'
    prior = read(prior_path)
    blocked = set(manifest['example_ids']) | set(prior['IDs'])
    blocked.add(prior['pre_annotation_replacement']['excluded_id'])
    selected, nrows, ngroups = fresh_sample(rows, blocked)
    DEST.mkdir(parents=True, exist_ok=True)
    queue, mapping = [], []
    for row, group in selected:
        opaque = hashlib.sha256(('blind:' + SEED + row['item_id']).encode()).hexdigest()
        queue.append({'item_id': opaque, 'utterance': row['utterance']})
        mapping.append({'item_id': opaque, 'human_item_id': row['item_id'], 'component': group})
    queue_path = DEST / 'fresh_blind18.jsonl'
    mapping_path = DEST / 'fresh_evaluator_mapping.json'
    protocol_path = DEST / 'fresh_protocol.json'
    if any(p.exists() for p in (queue_path, mapping_path, protocol_path)):
        raise FileExistsError('Fresh check already sealed; never resample after inspection')
    write_new(queue_path, queue, jsonl=True)
    write_new(mapping_path, mapping)
    protocol = {
        'status': 'SEALED_UNLABELED_NOT_EVALUATED', 'n': len(queue), 'seed': SEED,
        'selection': 'hash order only; one row per full118 connected component; no score or cohort ranking',
        'group_guard': 'meeting/AMI series plus transitive lexical near duplicates over all clean118',
        'blocked_ids': sorted(blocked), 'eligible_rows': nrows, 'eligible_groups': ngroups,
        'train_sha256': sha(TRAIN), 'prior_protocol_sha256': sha(prior_path),
        'queue_sha256': sha(queue_path), 'mapping_sha256': sha(mapping_path),
        'dev_final_read': False,
        'evaluation': 'requires a separately locked genuine candidate and annotations; raw/corrected/old18median on identical final-prediction rows; full gold support retained',
        'limitations': ['Previously unused human TRAIN groups; not a production or final-model test.',
                        'Only18 groups; no claim of population representativeness.',
                        'Do not consume this check merely to compare identity with itself.'],
    }
    write_new(protocol_path, protocol)
    print(json.dumps({'status': protocol['status'], 'rows': len(queue), 'eligible_groups': ngroups,
                      'queue_path': str(queue_path)}, indent=2))


def formality(record):
    if not isinstance(record, dict) or set(record) != {'item_id', 'formality'}:
        raise ValueError('Expected item_id and formality only')
    block = record['formality']
    if not isinstance(block, dict) or set(block) != set(FIELDS) | {'case_type', 'confidence', 'evidence'}:
        raise ValueError('Invalid Formality schema')
    levels = [_strict_int(block[f], 0, 4, f) for f in FIELDS]
    _strict_int(block['confidence'], 0, 4, 'confidence')
    if block['case_type'] not in CASE_TYPES or not isinstance(block['evidence'], str) or not block['evidence'].strip():
        raise ValueError('Invalid Formality case or evidence')
    value = round_to_5_half_up(25 * sum(block[f] * WEIGHTS['Formality'][f] for f in FIELDS))
    return [value, *levels], block['case_type'] != 'context_insufficient'


def freeze_teacher_check():
    """Freeze the actual revised teacher before either annotator sees fresh texts."""
    human, manifest = training()
    by_id = {r['item_id']: r for r in human}
    prior = read(BASE / 'improvement/human_calibration/protocol.json')
    ids = list(dict.fromkeys(manifest['example_ids'] + prior['IDs']))
    if len(ids) != 35 or any('Formality' not in by_id[i]['axes'] for i in ids):
        raise ValueError('Expected35 examples with human Formality labels')
    examples_path = DEST / 'fresh_teacher_examples35.json'
    examples = [{'utterance': by_id[i]['utterance'], 'human_formality': by_id[i]['axes']['Formality']} for i in ids]
    write_new(examples_path, examples)
    sealed = read(DEST / 'fresh_protocol.json')
    protocol = {
        'status': 'LOCKED_BEFORE_FRESH_ANNOTATION', 'primary_metric': 'paired MAE against fresh human Formality',
        'same_35_examples_both_reviewers': True, 'examples_sha256': sha(examples_path),
        'example_ids': ids, 'fresh_queue_sha256': sealed['queue_sha256'],
        'fresh_mapping_sha256': sealed['mapping_sha256'], 'train_sha256': sealed['train_sha256'],
        'arms': {
            'fixed_rubric': 'original respect_face40/mitigation35/spoken_register25 components0..4; half-up nearest5; no direct adjustment',
            'direct_empirical': 'direct0..100 multiple5 aligned to the same35 human examples; no forced neutral50 or component arithmetic',
        },
        'direct_schema': {'item_id': 'opaque ID', 'formality_score': 'integer0..100 multiple5',
                          'score_status': 'final or context_insufficient', 'evidence': 'nonempty explanation'},
        'forbidden_inputs': ['fresh human targets', 'source IDs', 'cohort labels', 'other reviewer predictions'],
        'context': 'target utterance only, same condition for both reviewers',
        'abstention': 'Allowed; report each coverage and common-final subset with all18 gold support retained',
        'reference': 'median human Formality of original18 calibration rows, fixed before fresh evaluation',
        'selection': 'none; report both methods without refit, row dropping, or post-result prompt edits',
        'post_evaluation': 'No automatic student retraining; this is a small teacher-validation experiment',
        'independence': 'separate root/subagent annotations; same model family can share biases',
        'dev_final_read': False,
    }
    write_new(DEST / 'fresh_teacher_protocol.json', protocol)
    print('Fresh teacher protocol and35 common examples locked; no fresh targets exposed.')


def direct_formality(record):
    required = {'item_id', 'score_status', 'evidence'}
    if not isinstance(record, dict) or not required <= set(record) or set(record) - required - {'formality_score'}:
        raise ValueError('Invalid direct Formality schema')
    if not isinstance(record['evidence'], str) or not record['evidence'].strip():
        raise ValueError('Direct annotation needs evidence')
    if record['score_status'] == 'context_insufficient':
        if record.get('formality_score') is not None:
            raise ValueError('Context-insufficient direct labels must omit a numeric score')
        return None, False
    if record['score_status'] != 'final' or 'formality_score' not in record:
        raise ValueError('Invalid direct status or missing final score')
    value = _strict_int(record['formality_score'], 0, 100, 'formality_score')
    if value % 5:
        raise ValueError('Direct score must be a multiple of5')
    return value, True


def evaluate_teachers(direct_path, rubric_path):
    protocol_path = DEST / 'fresh_teacher_protocol.json'
    protocol = read(protocol_path)
    clarification_path = DEST / 'fresh_teacher_protocol_clarification.json'
    clarification = read(clarification_path)
    if clarification['original_protocol_sha256'] != sha(protocol_path):
        raise ValueError('Teacher protocol clarification mismatch')
    if clarification['empirical_examples_sha256'] != sha(DEST / 'empirical_examples35.json'):
        raise ValueError('Empirical examples changed after prompt lock')
    for path, key in ((TRAIN, 'train_sha256'), (DEST / 'fresh_blind18.jsonl', 'fresh_queue_sha256'),
                      (DEST / 'fresh_evaluator_mapping.json', 'fresh_mapping_sha256'),
                      (DEST / 'fresh_teacher_examples35.json', 'examples_sha256')):
        if sha(path) != protocol[key]:
            raise ValueError('Locked teacher-check input changed')
    mapping = read(DEST / 'fresh_evaluator_mapping.json')
    ids = {r['item_id'] for r in mapping}
    parsed = {}
    for name, path, parser in (('direct_empirical', direct_path, direct_formality),
                               ('fixed_rubric', rubric_path, formality)):
        records = read(path)
        if len(records) != len(ids) or {r['item_id'] for r in records} != ids:
            raise ValueError('Reviewer coverage/duplicate IDs mismatch')
        parsed[name] = {r['item_id']: parser(r) for r in records}
    human, manifest = training()
    by_id = {r['item_id']: r for r in human}
    prior = read(BASE / 'improvement/human_calibration/protocol.json')
    median = int(np.round(np.median([by_id[i]['axes']['Formality'] for i in prior['IDs']]) / 5) * 5)
    gold, individual, paired = [], {n: [] for n in parsed}, {n: [] for n in parsed}
    paired['old18_median'] = []
    details = []
    for item in mapping:
        opaque = item['item_id']
        gold.append(by_id[item['human_item_id']])
        common = all(values[opaque][1] for values in parsed.values())
        row = {'item_id': opaque, 'human': gold[-1]['axes']['Formality'], 'common_final': common}
        for name, values in parsed.items():
            value, final = values[opaque]
            value = value[0] if name == 'fixed_rubric' else value
            individual[name].append({'Formality': value} if final else {})
            paired[name].append({'Formality': value} if common else {})
            row[name] = value if final else None
        paired['old18_median'].append({'Formality': median} if common else {})
        details.append(row)
    report = {
        'n': len(gold), 'paired_common_final_count': sum(r['common_final'] for r in details),
        'individual': {n: score(gold, p)['Formality'] for n, p in individual.items()},
        'paired_all_gold_denominators': {n: score(gold, p)['Formality'] for n, p in paired.items()},
        'reference_median': median, 'no_refit_or_selection': True, 'dev_final_read': False,
        'annotation_sha256': {'direct': sha(direct_path), 'rubric': sha(rubric_path)},
        'protocol_sha256': sha(protocol_path), 'human_input_sha256': manifest['input_sha256'][TRAIN.name],
        'protocol_clarification_sha256': sha(clarification_path),
        'limitations': ['Small fresh humanTRAIN group check, not independent production-model evaluation.',
                        'Paired MAE is conditional on common final predictions; coverage is reported.',
                        'No source/cohort balancing; same-family reviewer errors may correlate.'],
    }
    write_new(DEST / 'fresh_teacher_predictions.json', details)
    write_new(DEST / 'fresh_teacher_report.json', report)
    print(json.dumps(report, indent=2))


def evaluate(annotations, candidate_lock):
    """Explicit opt-in only, after the labeler and mapping have been locked."""
    protocol = read(DEST / 'fresh_protocol.json')
    for path, key in ((TRAIN, 'train_sha256'), (DEST / 'fresh_blind18.jsonl', 'queue_sha256'),
                      (DEST / 'fresh_evaluator_mapping.json', 'mapping_sha256')):
        if sha(path) != protocol[key]:
            raise ValueError('Sealed fresh inputs changed')
    lock = read(candidate_lock)
    if not lock.get('labeler_description') or lock['calibrator_sha256'] != sha(DEST / 'calibrator.joblib'):
        raise ValueError('Missing labeler identity or changed locked calibrator')
    # A timestamp cannot establish independent ordering; caller must lock before annotating.
    records = read(annotations)
    mapping = read(DEST / 'fresh_evaluator_mapping.json')
    expected = {r['item_id'] for r in mapping}
    if len(records) != len(expected) or {r['item_id'] for r in records} != expected:
        raise ValueError('Fresh annotation coverage/duplicate IDs mismatch')
    by_annotation = {r['item_id']: r for r in records}
    rows, _ = training()
    by_human = {r['item_id']: r for r in rows}
    bundle = joblib.load(DEST / 'calibrator.joblib')
    prior = read(BASE / 'improvement/human_calibration/protocol.json')
    if set(bundle['fit_ids']) != set(prior['IDs']):
        raise ValueError('Calibrator must fit only the original18')
    median = int(np.round(np.median([by_human[i]['axes']['Formality'] for i in prior['IDs']]) / 5) * 5)
    gold, preds = [], {'raw': [], 'corrected': [], 'old18_median_same_coverage': []}
    for item in mapping:
        gold.append(by_human[item['human_item_id']])
        features, final = formality(by_annotation[item['item_id']])
        values = {'raw': features[0], 'corrected': int(predict(bundle['calibrator'], np.array([features]))[0]),
                  'old18_median_same_coverage': median}
        for name, value in values.items():
            preds[name].append({'Formality': value} if final else {})
    report = {'n': len(gold), 'metrics': {name: score(gold, p)['Formality'] for name, p in preds.items()},
              'mapping_kind': bundle['calibrator']['kind'], 'no_refit_or_selection': True,
              'dev_final_read': False, 'annotations_sha256': sha(annotations),
              'candidate_lock_sha256': sha(candidate_lock), 'final_model_test': False,
              'interpretation': 'Fresh labeler check on protected human TRAIN groups; small exploratory sample.'}
    write_new(DEST / 'fresh_report.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'evaluate', 'freeze-teacher-check', 'evaluate-teachers'))
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--candidate-lock', type=Path)
    parser.add_argument('--rubric', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
    elif args.command == 'freeze-teacher-check':
        freeze_teacher_check()
    elif args.command == 'evaluate-teachers':
        if args.annotations is None or args.rubric is None:
            parser.error('evaluate-teachers requires --annotations and --rubric')
        evaluate_teachers(args.annotations, args.rubric)
    elif args.annotations is None or args.candidate_lock is None:
        parser.error('evaluate requires --annotations and --candidate-lock')
    else:
        evaluate(args.annotations, args.candidate_lock)
