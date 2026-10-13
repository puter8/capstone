"""Provisional within-speaker pitch-range signal, not emotion recognition.

The one-octave fold is a heuristic; large pitch deviations are not confirmed
tracking errors. A baseline needs three valid clips and a session at least five,
matching the conservative 3+5 recording simulation. No text fallback is allowed.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math
from numbers import Real
from statistics import median
from typing import Sequence
import wave

ALGORITHM_VERSION = "pitch-range-fold-v1"
SAMPLE_RATE = 16000
FRAME_LENGTH = 1024
HOP_LENGTH = 160
MIN_VOICED_FRAMES = 50
BASELINE_CLIPS = 3
MIN_SESSION_CLIPS = 5
MAX_SECONDS = 30
MAX_WAV_BYTES = SAMPLE_RATE * 2 * MAX_SECONDS + 4096


def _finite(value: float, name: str, minimum: float | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


def _count(value: int, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


@dataclass(frozen=True)
class ClipMeasurement:
    range_st: float | None
    voiced_frames: int
    total_frames: int
    duration_seconds: float
    median_f0_hz: float | None
    folded_fraction: float
    missing_reason: str | None = None

    def __post_init__(self) -> None:
        _count(self.voiced_frames, "voiced_frames")
        _count(self.total_frames, "total_frames")
        _finite(self.duration_seconds, "duration_seconds", 0)
        _finite(self.folded_fraction, "folded_fraction", 0)
        if (self.voiced_frames > self.total_frames or self.folded_fraction > 1
                or self.duration_seconds > MAX_SECONDS):
            raise ValueError("invalid frame counts or folded fraction")
        if self.range_st is None:
            if not isinstance(self.missing_reason, str) or not self.missing_reason:
                raise ValueError("missing measurement requires a reason")
            if self.median_f0_hz is not None or self.folded_fraction != 0:
                raise ValueError("missing measurement cannot have median f0")
        else:
            _finite(self.range_st, "range_st", 0)
            _finite(self.median_f0_hz, "median_f0_hz", 60)
            if (self.median_f0_hz > 600 or self.missing_reason is not None
                    or self.voiced_frames < MIN_VOICED_FRAMES):
                raise ValueError("invalid valid measurement")


@dataclass(frozen=True)
class EnergyBaseline:
    range_st: float
    valid_clips: int = BASELINE_CLIPS

    def __post_init__(self) -> None:
        _finite(self.range_st, "range_st", 0)
        if type(self.valid_clips) is not int or self.valid_clips != BASELINE_CLIPS:
            raise ValueError("baseline requires exactly three valid clips")


@dataclass(frozen=True)
class SessionEnergy:
    score: int | None
    range_st: float | None
    delta_st: float | None
    valid_clips: int
    missing_reason: str | None = None

    def __post_init__(self) -> None:
        _count(self.valid_clips, "valid_clips")
        if self.range_st is not None:
            _finite(self.range_st, "range_st", 0)
        if self.score is None:
            if not isinstance(self.missing_reason, str) or not self.missing_reason or self.delta_st is not None:
                raise ValueError("missing session requires a reason and no delta")
        else:
            if type(self.score) is not int or not 0 <= self.score <= 100 or self.score % 5:
                raise ValueError("score must be an integer 0..100 in steps of five")
            _finite(self.delta_st, "delta_st")
            if self.range_st is None or self.valid_clips < MIN_SESSION_CLIPS or self.missing_reason is not None:
                raise ValueError("invalid scored session")


def missing_clip(reason: str, *, duration_seconds: float = 0,
                 voiced_frames: int = 0, total_frames: int = 0) -> ClipMeasurement:
    return ClipMeasurement(None, voiced_frames, total_frames, duration_seconds, None, 0, reason)


def measure_wav(wav_bytes: bytes) -> ClipMeasurement:
    """Measure bounded mono PCM16 16 kHz WAV bytes; reject other formats explicitly.

    Dependencies load only after cheap input validation. Unexpected computation
    failures propagate to the worker rather than becoming fabricated scores.
    """
    if not isinstance(wav_bytes, bytes):
        raise TypeError("wav_bytes must be bytes")
    if len(wav_bytes) > MAX_WAV_BYTES:
        return missing_clip("wav_too_large")
    try:
        with wave.open(BytesIO(wav_bytes), "rb") as source:
            if (source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getcomptype()) != (1, 2, SAMPLE_RATE, "NONE"):
                return missing_clip("unsupported_wav_format")
            frames = source.getnframes()
            if frames > SAMPLE_RATE * MAX_SECONDS:
                return missing_clip("audio_too_long")
            raw = source.readframes(frames)
            if len(raw) != frames * 2:
                return missing_clip("truncated_wav")
    except (wave.Error, EOFError):
        return missing_clip("invalid_wav")
    if not frames:
        return missing_clip("empty_audio")
    duration = frames / SAMPLE_RATE
    if frames < FRAME_LENGTH:
        return missing_clip("insufficient_voiced_frames", duration_seconds=duration)
    import numpy as np
    import librosa

    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    f0, voiced, _ = librosa.pyin(samples, fmin=60, fmax=600, sr=SAMPLE_RATE,
                                frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)
    mask = voiced & np.isfinite(f0) & (f0 > 0)
    count = int(np.sum(mask))
    if count < MIN_VOICED_FRAMES:
        return missing_clip("insufficient_voiced_frames", duration_seconds=duration,
                            voiced_frames=count, total_frames=len(f0))
    pitches = f0[mask]
    center = float(np.median(pitches))
    semitones = 12 * np.log2(pitches / center)
    # Single fold relative to the original deviations, not repeated modulo.
    above, below = semitones > 7, semitones < -7
    folded_fraction = float(np.mean(above | below))
    semitones = semitones.copy()
    semitones[above] -= 12
    semitones[below] += 12
    spread = float(np.percentile(semitones, 80) - np.percentile(semitones, 20))
    return ClipMeasurement(spread, count, len(f0), duration, center, folded_fraction)


def _valid_ranges(clips: Sequence[ClipMeasurement]) -> list[float]:
    if any(not isinstance(clip, ClipMeasurement) for clip in clips):
        raise TypeError("clips must contain ClipMeasurement values")
    return [clip.range_st for clip in clips if clip.range_st is not None]


def make_baseline(clips: Sequence[ClipMeasurement]) -> EnergyBaseline:
    values = _valid_ranges(clips)
    if len(values) != BASELINE_CLIPS:
        raise ValueError("baseline requires exactly three valid clips")
    return EnergyBaseline(float(median(values)))


def score_delta(delta_st: float) -> int:
    """Python ties-to-even round, matching the supplied simulation exactly."""
    _finite(delta_st, "delta_st")
    return int(round(min(100.0, max(0.0, 50 + 10 * delta_st)) / 5) * 5)


def aggregate_session(clips: Sequence[ClipMeasurement], baseline: EnergyBaseline | None) -> SessionEnergy:
    if baseline is not None and not isinstance(baseline, EnergyBaseline):
        raise TypeError("baseline must be EnergyBaseline or None")
    values = _valid_ranges(clips)
    spread = float(median(values)) if values else None
    if baseline is None:
        return SessionEnergy(None, spread, None, len(values), "baseline_missing")
    if len(values) < MIN_SESSION_CLIPS:
        return SessionEnergy(None, spread, None, len(values), "insufficient_valid_clips")
    delta = spread - baseline.range_st
    return SessionEnergy(score_delta(delta), spread, delta, len(values))
