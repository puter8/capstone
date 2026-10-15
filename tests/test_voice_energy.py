from dataclasses import FrozenInstanceError
from io import BytesIO
import wave

import numpy as np
import pytest

from ai.voice_energy import (ClipMeasurement, EnergyBaseline, SessionEnergy, MAX_WAV_BYTES,
                             aggregate_session, make_baseline, measure_wav, missing_clip, score_delta)


def wav(samples=None, sr=16000, channels=1, width=2):
    stream = BytesIO()
    with wave.open(stream, "wb") as target:
        target.setnchannels(channels)
        target.setsampwidth(width)
        target.setframerate(sr)
        target.writeframes(np.asarray(samples if samples is not None else np.zeros(16000), dtype="<i2").tobytes())
    return stream.getvalue()


def clip(value):
    return ClipMeasurement(value, 100, 200, 2, 200, 0)


@pytest.mark.parametrize("payload,reason", [(b"broken", "invalid_wav"),
    (b"x" * (MAX_WAV_BYTES + 1), "wav_too_large"), (wav(sr=8000), "unsupported_wav_format"),
    (wav(channels=2), "unsupported_wav_format"), (wav(width=1), "unsupported_wav_format"),
    (wav([]), "empty_audio"), (wav(np.zeros(480001)), "audio_too_long"),
    (wav()[:-10], "truncated_wav")], ids=["invalid", "large", "rate", "stereo", "width", "empty", "duration", "truncated"])
def test_bad_audio_has_explicit_missing_reason(payload, reason):
    result = measure_wav(payload)
    assert result.range_st is None and result.missing_reason == reason


def test_silence_does_not_become_neutral_score():
    result = measure_wav(wav())
    assert result.range_st is None
    assert result.missing_reason == "insufficient_voiced_frames"


def test_real_pitch_extractor_on_stationary_tone():
    t = np.arange(16000) / 16000
    result = measure_wav(wav(12000 * np.sin(2 * np.pi * 200 * t)))
    assert result.missing_reason is None
    assert result.range_st < 0.5
    assert abs(result.median_f0_hz - 200) < 3


def test_fold_is_single_heuristic_and_50_voiced_frames_required(monkeypatch):
    import librosa
    pitches = np.array([100.] * 20 + [200.] * 60 + [400.] * 20)
    monkeypatch.setattr(librosa, "pyin", lambda *a, **k: (pitches, np.ones(100, dtype=bool), None))
    result = measure_wav(wav())
    assert result.range_st == pytest.approx(0)
    assert result.folded_fraction == .4
    monkeypatch.setattr(librosa, "pyin", lambda *a, **k: (pitches, np.arange(100) < 49, None))
    assert measure_wav(wav()).missing_reason == "insufficient_voiced_frames"
    monkeypatch.setattr(librosa, "pyin", lambda *a, **k: (pitches, np.arange(100) < 50, None))
    assert measure_wav(wav()).range_st is not None


def test_unexpected_extractor_failure_propagates(monkeypatch):
    import librosa
    def fail(*args, **kwargs):
        raise RuntimeError("extractor failed")
    monkeypatch.setattr(librosa, "pyin", fail)
    with pytest.raises(RuntimeError, match="extractor failed"):
        measure_wav(wav())


def test_baseline_and_session_use_valid_medians():
    baseline = make_baseline([clip(2), missing_clip("silence"), clip(4), clip(100)])
    assert baseline.range_st == 4
    result = aggregate_session([clip(v) for v in (2, 4, 6, 7, 100)] + [missing_clip("silence")], baseline)
    assert (result.score, result.delta_st, result.valid_clips) == (70, 2, 5)
    assert aggregate_session([clip(4)] * 4, baseline).score is None
    assert aggregate_session([clip(4)] * 5, None).missing_reason == "baseline_missing"
    with pytest.raises(ValueError):
        make_baseline([clip(4)] * 4)


@pytest.mark.parametrize("delta,score", [(-100, 0), (100, 100), (0, 50), (-1.75, 30),
    (-1.749, 35), (1.749, 65), (1.75, 70), (.25, 50), (.75, 60)])
def test_score_boundaries_and_rounding(delta, score):
    assert score_delta(delta) == score


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "4"])
def test_reject_nonfinite_or_coerced_numbers(value):
    with pytest.raises(ValueError):
        EnergyBaseline(value)
    with pytest.raises(ValueError):
        score_delta(value)


def test_immutable_and_consistent_results():
    with pytest.raises(FrozenInstanceError):
        clip(4).range_st = 7
    with pytest.raises(ValueError):
        ClipMeasurement(4, 49, 100, 1, 200, 0)
    with pytest.raises(ValueError):
        SessionEnergy(50, 3, 0, 4)
    with pytest.raises(ValueError):
        SessionEnergy(None, None, None, 0)
    with pytest.raises(TypeError):
        aggregate_session([4], None)
