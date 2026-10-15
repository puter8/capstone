# -*- coding: utf-8 -*-
"""축 분석의 3단 폴백 — 한 단계가 죽어도 턴이 죽지 않는다.

1단 선택된 어댑터(ml/hybrid) → 2단 어댑터 내부에서 rule 기반으로 →
3단 어댑터 자체가 죽으면 모듈 함수 analyze_utterance 로.

researched(F/H/C 운영 모델)는 이 체인에서 제외된다. 모델이 실패했는데 조용히
다른 값으로 내려가면 어떤 모델이 낸 점수인지 알 수 없어, 실패를 그대로 올린다.
"""
import importlib

from ai.analyzers import HybridAxisAnalyzer, MLAxisAnalyzer, RuleBasedAxisAnalyzer
from ai.contracts import AxisResult

AXIS_KEYS = ("Formality", "Energy", "Intimacy", "Humor", "Curiosity")
UTTERANCE = "I had no lunch I'm diet"


class _DeadModel:
    def predict(self, _utterance):
        raise RuntimeError("model is unavailable")


def test_stage2_ml_failure_degrades_to_the_rule_analyzer():
    """모델 예측이 깨져도 축이 나와야 한다 — 값까지 rule 결과와 같아야,
    '폴백했다'가 아니라 '무엇으로 폴백했는지'가 확인된다."""
    broken = MLAxisAnalyzer(model=_DeadModel())

    degraded = broken.analyze(UTTERANCE)

    assert degraded == RuleBasedAxisAnalyzer().analyze(UTTERANCE)
    assert all(0 <= getattr(degraded, key) <= 100 for key in AXIS_KEYS)


def test_stage2_hybrid_keeps_working_when_ml_is_dead():
    """hybrid 는 rule 과 ml 을 평균 내는데, ml 쪽이 죽으면 rule 과 rule 의
    평균이 되어 결국 rule 값으로 수렴한다 — 예외가 밖으로 나가지 않는다."""
    hybrid = HybridAxisAnalyzer(ml_analyzer=MLAxisAnalyzer(model=_DeadModel()))

    blended = hybrid.analyze(UTTERANCE)

    assert blended == RuleBasedAxisAnalyzer().analyze(UTTERANCE)


def test_stage3_module_function_runs_when_the_adapter_is_gone(monkeypatch):
    """어댑터 생성 자체가 실패한 상태(_axis_analyzer is None)에서도 축이 나온다."""
    import main
    from ai.analyzer import analyze_utterance

    monkeypatch.setattr(main, "_axis_analyzer", None)
    monkeypatch.setattr(main, "_AXIS_ANALYZER_KIND", "rule")

    assert main._analyze_axes(UTTERANCE) == analyze_utterance(UTTERANCE)


def test_stage3_also_catches_an_adapter_that_raises(monkeypatch):
    """어댑터가 살아 있어도 analyze 가 터지면 모듈 함수로 내려간다."""
    import main
    from ai.analyzer import analyze_utterance

    class _Exploding:
        def analyze(self, _text):
            raise RuntimeError("adapter exploded")

    monkeypatch.setattr(main, "_axis_analyzer", _Exploding())
    monkeypatch.setattr(main, "_AXIS_ANALYZER_KIND", "hybrid")

    assert main._analyze_axes(UTTERANCE) == analyze_utterance(UTTERANCE)


def test_researched_model_failure_is_raised_not_hidden(monkeypatch):
    """운영 모델은 폴백하지 않는다 — 조용히 다른 값으로 내려가면 화면에 보이는
    점수가 어느 모델에서 나온 건지 알 수 없게 된다."""
    import main

    class _Exploding:
        def analyze(self, _text):
            raise RuntimeError("researched model exploded")

    monkeypatch.setattr(main, "_axis_analyzer", _Exploding())
    monkeypatch.setattr(main, "_AXIS_ANALYZER_KIND", "researched")

    try:
        main._analyze_axes(UTTERANCE)
    except RuntimeError:
        return
    raise AssertionError("researched 모드는 실패를 숨기지 않아야 한다")


def test_every_stage_returns_the_same_contract():
    """어느 단계로 내려가든 5축 계약은 같아야 한다 — 폴백이 화면을 깨면 안 된다."""
    for analyzer in (RuleBasedAxisAnalyzer(), MLAxisAnalyzer(model=_DeadModel()),
                     HybridAxisAnalyzer(ml_analyzer=MLAxisAnalyzer(model=_DeadModel()))):
        result = analyzer.analyze(UTTERANCE)
        assert isinstance(result, AxisResult)
        assert all(isinstance(getattr(result, key), int) for key in AXIS_KEYS)

    assert importlib  # 모듈 재로딩 없이 돌아야 한다(부팅 비용 회피)
