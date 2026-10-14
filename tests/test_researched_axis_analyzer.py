"""Opt-in runtime contract and fail-closed behavior for the researched scorer."""
from pathlib import Path
import ast
import logging
import os
import subprocess
import sys
from types import ModuleType

import pytest

from ai import analyzers
from ai.analyzers import ResearchedAxisAnalyzer, RuleBasedAxisAnalyzer, get_axis_analyzer


def test_portable_schema_dispatch_preserves_configuration_and_errors(monkeypatch):
    from ai.researched_axis_model import ResearchedAxisModel
    import joblib
    bundle = {'schema_version': 2}
    encoder = object()
    seen = []
    class Selected:
        def __init__(self, data, **options):
            seen.append((data, options))
            raise ValueError('Incomplete portable heads')
    module = ModuleType('ai.selected_fhc_model')
    module.SelectedFHCModel = Selected
    monkeypatch.setitem(sys.modules, 'ai.selected_fhc_model', module)
    monkeypatch.setattr(joblib, 'load', lambda _: bundle)
    with pytest.raises(ValueError, match='Incomplete portable heads'):
        ResearchedAxisModel.from_artifact('trusted-model', encoder_path='local-encoder', encoder=encoder)
    assert seen == [(bundle, {'encoder_path': 'local-encoder', 'encoder': encoder})]


class Predictor:
    def __init__(self, prediction=None):
        self.prediction = prediction if prediction is not None else {
            'Formality': 75, 'Humor': 10, 'Curiosity': 85}

    def predict_partial(self, text):
        return self.prediction


def install_loader(monkeypatch, loader):
    module = ModuleType('ai.researched_axis_model')
    module.ResearchedAxisModel = type('Loader', (), {'from_artifact': staticmethod(loader)})
    monkeypatch.setitem(sys.modules, 'ai.researched_axis_model', module)


def test_researched_replaces_all_three_axes_and_preserves_other_pipeline_axes():
    text = 'Could you explain why this result changes?'
    result = ResearchedAxisAnalyzer(Predictor()).analyze(text)
    rule = RuleBasedAxisAnalyzer().analyze(text)
    assert (result.Formality, result.Humor, result.Curiosity) == (75, 10, 85)
    assert (result.Energy, result.Intimacy) == (rule.Energy, rule.Intimacy)
    assert set(result.model_dump()) == {'Formality', 'Humor', 'Curiosity', 'Energy', 'Intimacy'}


def test_prediction_failure_propagates_without_rule_fallback():
    class Broken:
        def predict_partial(self, text):
            raise RuntimeError('Model inference failed')

    analyzer = ResearchedAxisAnalyzer(Broken())

    class ForbiddenRule:
        def analyze(self, *args):
            raise AssertionError('Failure must not invoke rule fallback')

    analyzer._rule = ForbiddenRule()
    with pytest.raises(RuntimeError, match='Model inference failed'):
        analyzer.analyze('Please explain the result.')


@pytest.mark.parametrize('bad', [True, 75.0, 101, -5, 73, None])
def test_invalid_learned_scores_are_not_coerced(bad):
    prediction = {'Formality': bad, 'Humor': 0, 'Curiosity': 5}
    with pytest.raises(ValueError, match='Invalid researched Formality'):
        ResearchedAxisAnalyzer(Predictor(prediction)).analyze('A complete statement.')


@pytest.mark.parametrize('prediction', [
    {'Formality': 50, 'Humor': 0},
    {'Formality': 50, 'Humor': 0, 'Curiosity': 5, 'Energy': 100},
])
def test_missing_head_or_other_axis_override_rejected(prediction):
    with pytest.raises(ValueError, match='exactly Formality, Humor and Curiosity'):
        ResearchedAxisAnalyzer(Predictor(prediction)).analyze('A complete statement.')


def test_blank_input_does_not_score():
    with pytest.raises(ValueError, match='nonblank'):
        ResearchedAxisAnalyzer(Predictor()).analyze('  ')


def test_missing_artifact_fails_explicitly(monkeypatch):
    def loader(*args, **kwargs):
        raise AssertionError('Missing file must not be loaded')

    install_loader(monkeypatch, loader)
    monkeypatch.setattr(Path, 'is_file', lambda self: False)
    with pytest.raises(FileNotFoundError, match='artifact not found'):
        ResearchedAxisAnalyzer(artifact_path='missing.joblib')


def test_corrupt_artifact_failure_is_not_hidden(monkeypatch):
    def loader(*args, **kwargs):
        raise ValueError('corrupt artifact')

    install_loader(monkeypatch, loader)
    monkeypatch.setattr(Path, 'is_file', lambda self: True)
    with pytest.raises(ValueError, match='corrupt artifact'):
        ResearchedAxisAnalyzer(artifact_path='corrupt.joblib')


def test_relative_config_paths_resolve_against_repository(monkeypatch):
    seen = {}

    def loader(path, *, encoder_path):
        seen.update(path=path, encoder_path=encoder_path)
        return Predictor()

    install_loader(monkeypatch, loader)
    monkeypatch.setattr(Path, 'is_file', lambda self: True)
    monkeypatch.setenv('PALLY_AXIS_ANALYZER', 'researched')
    monkeypatch.setenv('PALLY_RESEARCHED_MODEL_PATH', 'private/candidate.joblib')
    monkeypatch.setenv('PALLY_RESEARCHED_ENCODER_PATH', 'private/encoder')
    assert isinstance(get_axis_analyzer(), ResearchedAxisAnalyzer)
    assert seen['path'] == (ResearchedAxisAnalyzer._ROOT / 'private/candidate.joblib').resolve()
    assert seen['encoder_path'] == (ResearchedAxisAnalyzer._ROOT / 'private/encoder').resolve()


def test_default_analyzer_remains_rule(monkeypatch):
    monkeypatch.delenv('PALLY_AXIS_ANALYZER', raising=False)
    assert isinstance(get_axis_analyzer(), RuleBasedAxisAnalyzer)


def test_importing_analyzers_does_not_import_optional_ml_dependencies():
    subprocess.run([sys.executable, '-c',
                    "import sys; import ai.analyzers; assert not {'torch', 'sklearn', 'scipy', 'sentence_transformers'} & set(sys.modules)"],
                   cwd=Path(analyzers.__file__).resolve().parents[1], check=True,
                   capture_output=True, text=True)


def backend_boundary_nodes():
    path = Path(analyzers.__file__).resolve().parents[1] / 'backend/main.py'
    return ast.parse(path.read_text(encoding='utf-8')).body


def test_backend_researched_prediction_failure_never_uses_rule():
    node = next(n for n in backend_boundary_nodes() if isinstance(n, ast.FunctionDef) and n.name == '_analyze_axes')

    class Broken:
        def analyze(self, text):
            raise RuntimeError('scoring unavailable')

    def forbidden_rule(text):
        raise AssertionError('Backend silently substituted rule scores')

    namespace = {'Dict': dict, '_axis_analyzer': Broken(), '_AXIS_ANALYZER_KIND': 'researched',
                 'analyze_utterance': forbidden_rule, 'logging': logging}
    # Execute the real boundary function without importing unrelated DB/API startup.
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'backend/main.py', 'exec'), namespace)
    with pytest.raises(RuntimeError, match='scoring unavailable'):
        namespace['_analyze_axes']('Please explain.')
    namespace['_axis_analyzer'] = None
    with pytest.raises(RuntimeError, match='unavailable'):
        namespace['_analyze_axes']('Please explain.')


@pytest.mark.parametrize('kind', ['researched', 'rule'])
def test_backend_startup_fail_closed_only_for_explicit_researched(monkeypatch, kind):
    nodes = backend_boundary_nodes()
    position = next(i for i, n in enumerate(nodes) if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == '_AXIS_ANALYZER_KIND' for t in n.targets))
    startup = ast.Module(body=nodes[position:position + 2], type_ignores=[])
    assert isinstance(startup.body[1], ast.Try)

    def broken_factory():
        raise FileNotFoundError('local artifact missing')

    monkeypatch.setenv('PALLY_AXIS_ANALYZER', kind)
    monkeypatch.setattr(analyzers, 'get_axis_analyzer', broken_factory)
    namespace = {'os': os, 'logging': logging}
    code = compile(startup, 'backend/main.py', 'exec')
    if kind == 'researched':
        with pytest.raises(FileNotFoundError, match='local artifact missing'):
            exec(code, namespace)
    else:
        exec(code, namespace)
        assert namespace['_axis_analyzer'] is None
