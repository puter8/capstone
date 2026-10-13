"""Exploratory matched-cohort, train-only Formality context ablation."""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

from scripts.calibrate_fhc_formality import metrics
from scripts.compare_fhc_improvements import DEST, components, quantize
from scripts.compare_full_corpus_labelers import OUT
from scripts.train_transfer_axis_models import TRAIN, read_rows
from scripts.fhc_round2_select import word_set, is_near_dup

TARGET = DEST / 'alignment/context'


def matched_records(path, id_field, ids):
    # Mixed source files contain held-out items: inspect only identifier first,
    # never parse scores/text of non-training records.
    pattern = re.compile(r'"' + id_field + r'"\s*:\s*"([^"]+)"')
    result = {}
    with path.open(encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line)
            if match and match.group(1) in ids:
                row = json.loads(line)
                if row[id_field] in result:
                    raise ValueError('duplicate source ID')
                result[row[id_field]] = row
    return result


def features(train, valid):
    pairs = []
    for analyzer, ngrams in [('word', (1, 2)), ('char', (3, 5))]:
        v = TfidfVectorizer(analyzer=analyzer, ngram_range=ngrams)
        pairs.append((v.fit_transform(train), v.transform(valid)))
    return hstack([p[0] for p in pairs]).tocsr(), hstack([p[1] for p in pairs]).tocsr()


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((OUT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(TRAIN.read_bytes()).hexdigest() == manifest['input_sha256'][TRAIN.name]
    all_by_id = {r['item_id']: r for r in read_rows(TRAIN)}
    human = [all_by_id[i] for i in manifest['train_ids']]
    ids = set(manifest['train_ids'])
    cohorts = {r['item_id']: r['cohort'] for r in read_rows(DEST / 'oof_predictions.jsonl')}
    seed_path = TRAIN.parent / 'pally_purpose_v1_items_100.jsonl'
    active_path = TRAIN.parent / 'pally_purpose_v3_active_train_candidates.jsonl'
    seed = matched_records(seed_path, 'item_id', ids)
    active = matched_records(active_path, 'source_record_id', ids)
    rows, excluded = [], Counter()
    group_by_id = dict(zip(manifest['train_ids'], components(human)))
    for row in human:
        i = row['item_id']
        if cohorts[i] not in ('human_consensus', 'solo_initial40'):
            excluded['human_not_shown_context'] += 1
            continue
        if 'Formality' not in row['axes']:
            excluded['missing_Formality'] += 1
            continue
        source = seed[i] if i in seed else active[i]
        if i in seed:
            context, target, meeting = source.get('context_before'), source['target_turn'], source['source_id'].split('.')[0]
            assert source['split'] == 'train'
        else:
            context, target, meeting = source.get('previous_turn'), source['utterance'], source['source_group']
            assert source['source_record_id'].split('.')[0] == meeting
        assert target == row['utterance'] and meeting == row['source_group']
        if not isinstance(context, str) or not context.strip():
            excluded['empty_context'] += 1
            continue
        rows.append(dict(row, context=context, cohort=cohorts[i], group=group_by_id[i]))
    strict = '--strict' in sys.argv
    if strict:
        parent = {r['group']: r['group'] for r in rows}
        def root(g):
            while parent[g] != g:
                parent[g] = parent[parent[g]]
                g = parent[g]
            return g
        words = [[word_set(r['utterance']), word_set(r['context'])] for r in rows]
        for i, row in enumerate(rows):
            for j in range(i):
                if any(left and right and is_near_dup(left, [right]) for left in words[i] for right in words[j]):
                    parent[root(row['group'])] = root(rows[j]['group'])
        for row in rows:
            row['group'] = root(row['group'])
    groups = np.array([r['group'] for r in rows])
    folds = list(GroupKFold(n_splits=5).split(rows, groups=groups))
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (TRAIN, seed_path, active_path)}
    protocol = {'n': len(rows), 'groups': len(set(groups)), 'cohort_counts': dict(Counter(r['cohort'] for r in rows)),
                'excluded': dict(excluded), 'alpha': .1, 'arms': ['target_only', 'target_plus_context', 'training_median'],
                'features': 'independent target word1-2/char3-5 TFIDF; same separate context blocks; fold-local fit',
                'grouping': 'meeting/AMIseries/near-duplicate connected components over all118 training rows',
                'strict_full_input_group_merge': strict,
                'strict_rule': 'add all eligible52 target/context pairs with nonempty word-set Jaccard>=.8 before splitting' if strict else None,
                'folds': [{'train_ids': [rows[i]['item_id'] for i in tr], 'validation_ids': [rows[i]['item_id'] for i in va]} for tr, va in folds],
                'input_sha256': hashes, 'primary_metric': 'rounded 0-100 Formality MAE', 'selection': 'no model selection or deployable artifact',
                'limitations': ['Alpha .1 chosen in prior overlapping training CV; exploratory not independent confirmation.',
                               'Canonical context associated with exact matched target and meeting; separate context utterance IDs absent, adjacency not independently verified.',
                               'Only context-exposed cohorts with nonempty recorded context; cannot infer context causality or generalize to all app conversations.',
                               'No dev/final labels parsed; nontraining source records skipped before JSON parsing.']}
    with (TARGET / 'protocol.json').open('x', encoding='utf-8') as f:
        json.dump(protocol, f, indent=2)
    y = np.array([r['axes']['Formality'] for r in rows])
    preds = {arm: np.full(len(rows), np.nan) for arm in protocol['arms']}
    for tr, va in folds:
        tx, vx = features([rows[i]['utterance'] for i in tr], [rows[i]['utterance'] for i in va])
        cx, cv = features([rows[i]['context'] for i in tr], [rows[i]['context'] for i in va])
        preds['target_only'][va] = quantize(Ridge(alpha=.1).fit(tx, y[tr]).predict(vx))
        preds['target_plus_context'][va] = quantize(Ridge(alpha=.1).fit(hstack([tx, cx]).tocsr(), y[tr]).predict(hstack([vx, cv]).tocsr()))
        preds['training_median'][va] = quantize(np.full(len(va), np.median(y[tr])))
    scores = {}
    for arm, pred in preds.items():
        assert np.isfinite(pred).all()
        scores[arm] = {'overall': metrics(y, pred), 'cohort': {}}
        for c in sorted({r['cohort'] for r in rows}):
            idx = np.array([r['cohort'] == c for r in rows])
            scores[arm]['cohort'][c] = metrics(y[idx], pred[idx])
    rng = np.random.default_rng(20261016)
    bootstrap = {}
    for cohort in ['all'] + sorted({r['cohort'] for r in rows}):
        eligible = np.array([cohort == 'all' or r['cohort'] == cohort for r in rows])
        gs = sorted(set(groups[eligible]))
        errors = abs(preds['target_plus_context'] - y) - abs(preds['target_only'] - y)
        samples = []
        for _ in range(2000):
            values = np.concatenate([errors[(groups == g) & eligible] for g in rng.choice(gs, len(gs), replace=True)])
            samples.append(float(np.mean(values)))
        bootstrap[cohort] = {'delta_MAE_context_minus_target': float(np.mean(errors[eligible])),
                             'descriptive_group_bootstrap95': np.percentile(samples, [2.5, 97.5]).tolist()}
    report = {'protocol': protocol, 'scores': scores, 'paired_bootstrap': bootstrap, 'deployable_model_saved': False,
              'rows': [{'item_id': r['item_id'], 'group': r['group'], 'cohort': r['cohort'], 'human_F': float(y[i]),
                        'predictions': {a: float(p[i]) for a, p in preds.items()}} for i, r in enumerate(rows)]}
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in hashes.items())
    (TARGET / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'n': len(rows), 'groups': len(set(groups)), 'scores': scores, 'bootstrap': bootstrap}, indent=2))


def audit_context_overlap():
    protocol = json.loads((TARGET / 'protocol.json').read_text(encoding='utf-8'))
    ids = set(protocol['folds'][0]['train_ids'] + protocol['folds'][0]['validation_ids'])
    seed = matched_records(TRAIN.parent / 'pally_purpose_v1_items_100.jsonl', 'item_id', ids)
    active = matched_records(TRAIN.parent / 'pally_purpose_v3_active_train_candidates.jsonl', 'source_record_id', ids)
    texts = {i: {'target': r['target_turn'], 'context': r.get('context_before') or ''} for i, r in seed.items()}
    texts.update({i: {'target': r['utterance'], 'context': r.get('previous_turn') or ''} for i, r in active.items()})
    words = {i: {k: word_set(t) for k, t in v.items()} for i, v in texts.items()}
    matches = []
    for fold, split in enumerate(protocol['folds']):
        for tr in split['train_ids']:
            for va in split['validation_ids']:
                for trkind in ('target', 'context'):
                    for vakind in ('target', 'context'):
                        left, right = words[tr][trkind], words[va][vakind]
                        if left and right and is_near_dup(left, [right]):
                            matches.append({'fold': fold, 'train_id': tr, 'validation_id': va,
                                            'train_field': trkind, 'validation_field': vakind,
                                            'jaccard': len(left & right) / len(left | right),
                                            'exact_text': texts[tr][trkind].strip() == texts[va][vakind].strip()})
    result = {'matching_directed_fold_pairs': len(matches),
              'field_pair_counts': dict(Counter(m['train_field'] + '-' + m['validation_field'] for m in matches)),
              'matches': matches, 'scope': '52 selected train rows; four target/context combinations; nonempty word-set Jaccard>=.8',
              'dev_final_used': False}
    (TARGET / 'context_overlap_audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'matches'}))


if __name__ == '__main__':
    if '--strict' in sys.argv:
        TARGET = DEST / 'alignment/context_strict'
    audit_context_overlap() if '--audit-overlap' in sys.argv else main()
