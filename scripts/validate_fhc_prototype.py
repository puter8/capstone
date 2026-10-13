"""Validate the frozen release against the user-approved prototype MAE ceiling."""
import hashlib
import importlib
import json
import os
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'data/models/full-corpus-fhc/improvement/release_candidate'
AXES = ('Formality', 'Humor', 'Curiosity')


def main():
    torch.set_num_threads(1)
    from ai.analyzers import ResearchedAxisAnalyzer, RuleBasedAxisAnalyzer
    from ai.researched_axis_model import ResearchedAxisModel
    from scripts.train_transfer_axis_models import DEV, read_rows

    report = json.loads((TARGET / 'report.json').read_text(encoding='utf-8'))
    artifact = TARGET / 'model.joblib'
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert digest == report['model_sha256']
    rows = read_rows(DEV)
    texts = [r['utterance'] for r in rows]
    model = ResearchedAxisModel.from_artifact(artifact)
    batch = model.predict_many(texts)
    expected = json.loads((TARGET / 'dev_predictions.json').read_text(encoding='utf-8'))
    assert expected['ids'] == [r['item_id'] for r in rows]
    assert batch == expected['predictions']
    analyzer, rule = ResearchedAxisAnalyzer(model=model), RuleBasedAxisAnalyzer()
    for text, prediction in zip(texts, batch):
        actual = analyzer.analyze(text).model_dump()
        assert {a: actual[a] for a in AXES} == prediction
        baseline = rule.analyze(text)
        assert actual['Energy'] == baseline.Energy and actual['Intimacy'] == baseline.Intimacy
    maes = {a: sum(abs(p[a] - r['axes'][a]) for r, p in zip(rows, batch) if a in r['axes']) /
            sum(a in r['axes'] for r in rows) for a in AXES}
    assert all(maes[a] == report['dev_selection_metrics']['overall'][a]['mae'] for a in AXES)
    assert all(value <= 13 for value in maes.values()), 'User prototype MAE ceiling failed'
    os.environ['PALLY_AXIS_ANALYZER'] = 'researched'
    os.environ['PALLY_RESEARCHED_MODEL_PATH'] = str(artifact)
    os.environ['PALLY_RESEARCHED_ENCODER_PATH'] = str(ROOT / 'data/models/minilm-base')
    backend = importlib.import_module('backend.main')
    for text, prediction in zip(texts, batch):
        actual = backend._analyze_axes(text)
        assert {a: actual[a] for a in AXES} == prediction
    result = {
        'status': 'PASS_LOCAL_PROTOTYPE_MODEL_AND_BACKEND_INFERENCE',
        'user_criterion': 'each axis development-reference MAE <=13; values below10 also pass',
        'model_sha256': digest, 'sentence_count': len(rows), 'mae': maes,
        'valid_reference_count': {a: sum(a in r['axes'] for r in rows) for a in AXES},
        'real_encoder_batch_single_backend_equal': True, 'other_axes_preserved': True,
        'independent_generalization_test': False, 'visual_or_full_chat_e2e_validated': False,
        'paid_api_calls': 0, 'production_deployed': False,
        'limitation': 'These35 development sentences selected the model; protected31 lacks human scores.'
    }
    (TARGET / 'prototype_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
