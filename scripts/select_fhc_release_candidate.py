"""Explicit development-set model selection across reproducible saved artifacts."""
import json
import sys
import joblib
import numpy as np
from ai.selected_fhc_model import SelectedFHCModel
from ai.embedding_axis_adapter import EmbeddingAxisAdapter
from scripts.compare_fhc_representation import sha
from scripts.compare_fhc_improvements import DEST, stratified
from scripts.compare_full_corpus_labelers import AXES
from scripts.train_transfer_axis_models import DEV, ENCODER_DIR, read_rows

TARGET = DEST / 'release_candidate'


def paths():
    specs = [('empirical_fhc', ('human_only', 'human_plus_empirical50')),
             ('empirical_full_corpus', ('anchor_only', 'uniform_025', 'uniform_100', 'agreement_025')),
             ('representation_round', ('human_selected',)),
             ('representation_pseudo', ('human_only', 'joint', 'residual', 'selected')),
             ('research_round', ('model',)), ('research_extended', ('model',)),
             ('reviewed_augmentation', ('human_nonconstant', 'human_plus_reviewer_a', 'human_plus_agreement_gated'))]
    return {folder + '/' + name: DEST / folder / (name + '.joblib') for folder, names in specs for name in names}


def convert(model, axis):
    if hasattr(model, 'axis_models'):
        return {'family': 'tfidf', 'vocabulary': {'word': model.word_vec, 'char': model.char_vec}, 'base': model.axis_models[axis], 'residual': None}
    if model.get('schema_version') == 1:
        return {'family': model['configs'][axis]['family'], 'vocabulary': model['vocabulary'], 'base': model['heads'][axis], 'residual': None}
    config = model['config'][axis]
    head = model['heads'][axis]
    return {'family': config['family'], 'vocabulary': model['vocabulary'],
            'base': head['base'] if isinstance(head, dict) else head,
            'residual': head.get('residual') if isinstance(head, dict) else None}


def unified(model):
    return {'schema_version': 2, 'axis_routing': {a: a for a in AXES},
            'components': {a: convert(model, a) for a in AXES}, 'encoder_path': 'data/models/minilm-base'}


def inspect():
    import torch
    torch.set_num_threads(1)
    TARGET.mkdir(exist_ok=True)
    candidates = paths()
    protocol = {'candidate_sha256': {n: sha(p) for n, p in candidates.items()}, 'dev_sha256': sha(DEV),
                'selection': 'axiswise lowest rounded DEV MAE among eligible complete3axis saved artifacts; ties frozen path insertion order',
                'eligibility': 'same development axis rows std>=2.5 and>=3 distinct rounded outputs',
                'development_role': 'explicit model-selection data, NOT independent model evaluation',
                'final': 'not read; protected31 currently unlabeled, no invented ground truth',
                'limitation': 'Unserialized ablation scores cannot enter reproducible candidate selection; repeated dev selection is optimistic.',
                'rule_code_sha256': sha('ai/analyzer.py')}
    with (TARGET / 'protocol.json').open('x', encoding='utf-8') as f:
        json.dump(protocol, f, indent=2)
    dev = read_rows(DEV)
    encoder = EmbeddingAxisAdapter(model_name=str(ENCODER_DIR), local_files_only=True)
    dx = encoder._encode([r['utterance'] for r in dev])
    np.save(TARGET / 'dev_embeddings.npy', dx)
    class Cache:
        def _encode(self, texts):
            assert len(texts) == len(dx)
            return dx
    predictions, scores = {}, {}
    for name, path in candidates.items():
        bundle = unified(joblib.load(path))
        pred = SelectedFHCModel(bundle, encoder=Cache()).predict_many([r['utterance'] for r in dev])
        predictions[name] = pred
        scores[name] = stratified(dev, pred)
        for a in AXES:
            vals = [p[a] for r, p in zip(dev, pred) if a in r['axes']]
            scores[name]['overall'][a].update({'prediction_std': float(np.std(vals)), 'distinct': len(set(vals)), 'eligible': np.std(vals) >= 2.5 and len(set(vals)) >= 3})
    eligible = {a: [n for n in candidates if scores[n]['overall'][a]['eligible']] for a in AXES}
    proposed = {a: min(names, key=lambda n: scores[n]['overall'][a]['mae']) if names else None for a, names in eligible.items()}
    result = {'scores': scores, 'eligible': eligible, 'proposed': proposed, 'selection_not_locked': True}
    (TARGET / 'eligibility.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (TARGET / 'all_dev_predictions.json').write_text(json.dumps(predictions, indent=2), encoding='utf-8')
    assert all(sha(candidates[n]) == h for n, h in protocol['candidate_sha256'].items())
    print(json.dumps({'eligible_counts': {a: len(v) for a, v in eligible.items()}, 'proposed': proposed,
                      'metrics': {a: scores[n]['overall'][a] if n else None for a, n in proposed.items()}}, indent=2))


def package():
    protocol = json.loads((TARGET / 'protocol.json').read_text(encoding='utf-8'))
    eligibility = json.loads((TARGET / 'eligibility.json').read_text(encoding='utf-8'))
    chosen = eligibility['proposed']
    if any(n is None for n in chosen.values()):
        raise ValueError('An axis has no eligible candidate; discuss before packaging')
    candidate_paths = paths()
    assert all(sha(candidate_paths[n]) == h for n, h in protocol['candidate_sha256'].items())
    assert sha(DEV) == protocol['dev_sha256']
    bundle = {'schema_version': 2, 'axis_routing': {a: a for a in AXES}, 'components': {},
              'encoder_path': 'data/models/minilm-base', 'selection_sources': chosen,
              'rule_code_sha256': protocol['rule_code_sha256'], 'evaluation_status': 'DEV_SELECTED_NOT_INDEPENDENTLY_VALIDATED'}
    for a, name in chosen.items():
        bundle['components'][a] = convert(joblib.load(candidate_paths[name]), a)
    with (TARGET / 'selection_lock.json').open('x', encoding='utf-8') as f:
        json.dump({'chosen': chosen, 'criterion': protocol['selection'], 'selection_data': 'DEV35'}, f, indent=2)
    joblib.dump(bundle, TARGET / 'model.joblib')
    dev = read_rows(DEV)
    dx = np.load(TARGET / 'dev_embeddings.npy')
    class Cache:
        def _encode(self, texts):
            assert len(texts) == len(dx)
            return dx
    model = SelectedFHCModel.from_artifact(TARGET / 'model.joblib', encoder=Cache())
    pred = model.predict_many([r['utterance'] for r in dev])
    allpred = json.loads((TARGET / 'all_dev_predictions.json').read_text(encoding='utf-8'))
    expected = [{a: allpred[n][i][a] for a, n in chosen.items()} for i in range(len(dev))]
    assert pred == expected
    report = {'chosen': chosen, 'dev_selection_metrics': stratified(dev, pred), 'model_sha256': sha(TARGET / 'model.joblib'),
              'roundtrip_and_source_head_equivalence': True, 'final_test_used': False,
              'independent_generalization_validated': False, 'saved_candidate_count': len(candidate_paths),
              'limitations': [protocol['development_role'], protocol['limitation'],
                              'Protected31 has no human reference labels; no independent final performance claim is available.',
                              'Best means minimum within these16 reproducible saved candidates on reused development selection data.']}
    (TARGET / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (TARGET / 'dev_predictions.json').write_text(json.dumps({'ids': [r['item_id'] for r in dev], 'predictions': pred}, indent=2), encoding='utf-8')
    print('PACKAGED', json.dumps(chosen))


if __name__ == '__main__':
    package() if '--package' in sys.argv else inspect()
