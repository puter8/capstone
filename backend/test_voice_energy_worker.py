"""Durable queue safety, audio identity, redaction, and baseline contracts."""
from io import BytesIO
import wave
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from lib import voice_energy as worker
from ai.voice_energy import ClipMeasurement, missing_clip


def wav_audio():
    stream = BytesIO()
    with wave.open(stream, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16000)
        target.writeframes(b"\x00\x00" * 1600)
    return stream.getvalue()


def valid(value=2.0):
    return ClipMeasurement(value, 100, 120, 1.2, 150, 0)


def database(payload):
    sb = Mock()
    sb.rpc.return_value.execute.side_effect = [
        SimpleNamespace(data=[{"id": "turn-1", "voice_energy": {**payload, "claim_token": "token-1"}}]),
        SimpleNamespace(data=True),
    ]
    return sb


@pytest.mark.parametrize("measurement,status", [(valid(), "ready"), (missing_clip("invalid_wav"), "missing")])
def test_terminal_job_removes_audio_and_uses_claim_token(monkeypatch, measurement, status):
    sb = database(worker.pending_audio(wav_audio()))
    measure = Mock(return_value=measurement)
    monkeypatch.setattr(worker, "measure_wav", measure)
    result = worker.process_pending(lambda: sb)
    assert result == {"processed": 1, "failed": 0, "skipped": 0}
    measure.assert_called_once_with(wav_audio())
    name, args = sb.rpc.call_args.args
    assert name == "finish_voice_energy_job"
    assert args["p_token"] == "token-1"
    assert args["p_result"]["status"] == status
    assert "audio_base64" not in args["p_result"]
    assert args["p_result"]["range_st"] == measurement.range_st


def test_audio_hash_mismatch_never_reaches_measurement(monkeypatch, caplog):
    payload = worker.pending_audio(wav_audio())
    payload["audio_sha256"] = "tampered"
    sb = database(payload)
    measure = Mock()
    monkeypatch.setattr(worker, "measure_wav", measure)
    result = worker.process_pending(lambda: sb)
    measure.assert_not_called()
    assert result["failed"] == 1
    terminal = sb.rpc.call_args.args[1]["p_result"]
    assert terminal["status"] == "error"
    assert "audio_base64" not in terminal
    assert "measurement failed" in caplog.text


def test_exception_is_recorded_and_audio_removed(monkeypatch):
    sb = database(worker.pending_audio(wav_audio()))
    monkeypatch.setattr(worker, "measure_wav", Mock(side_effect=RuntimeError("bad DSP")))
    assert worker.process_pending(lambda: sb)["failed"] == 1
    result = sb.rpc.call_args.args[1]["p_result"]
    assert result["error_type"] == "RuntimeError"
    assert result["missing_reason"] == "measurement_failed"
    assert "audio_base64" not in result


def test_storage_error_leaves_lease_recoverable(monkeypatch):
    sb = database(worker.pending_audio(wav_audio()))
    sb.rpc.return_value.execute.side_effect = [
        SimpleNamespace(data=[{"id": "turn-1", "voice_energy": {**worker.pending_audio(wav_audio()), "claim_token": "t"}}]),
        RuntimeError("database unavailable"),
    ]
    monkeypatch.setattr(worker, "measure_wav", Mock(return_value=valid()))
    assert worker.process_pending(lambda: sb)["failed"] == 1
    assert not worker._guard.locked()


def test_worker_does_not_touch_snapshots_or_axes(monkeypatch):
    sb = database(worker.pending_audio(wav_audio()))
    monkeypatch.setattr(worker, "measure_wav", Mock(return_value=valid()))
    worker.process_pending(lambda: sb)
    sb.table.assert_not_called()
    assert [call.args[0] for call in sb.rpc.call_args_list] == ["claim_voice_energy_job", "finish_voice_energy_job"]


def test_oversized_audio_never_enters_queue():
    with pytest.raises(ValueError):
        worker.pending_audio(b"x" * (worker.MAX_WAV_BYTES + 1))


def test_baseline_preserves_existing_race_winner():
    sb = Mock()
    stored = {"user_id": "owner", "range_st": 9.0}
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data=stored)
    assert worker.save_baseline(sb, "owner", [valid(1), valid(2), valid(3)]) == stored
    assert sb.rpc.call_args.args[1]["p_range_st"] == 2


def test_baseline_rejects_invalid_clips_before_database():
    sb = Mock()
    with pytest.raises(ValueError):
        worker.save_baseline(sb, "owner", [valid(), valid(), missing_clip("silence")])
    sb.rpc.assert_not_called()


def test_expired_claim_cannot_count_as_saved(monkeypatch):
    sb = database(worker.pending_audio(wav_audio()))
    sb.rpc.return_value.execute.side_effect = [
        SimpleNamespace(data=[{"id": "turn-1", "voice_energy": {**worker.pending_audio(wav_audio()), "claim_token": "old"}}]),
        SimpleNamespace(data=False),
    ]
    monkeypatch.setattr(worker, "measure_wav", Mock(return_value=valid()))
    assert worker.process_pending(lambda: sb) == {"processed": 0, "failed": 0, "skipped": 1}


@pytest.mark.parametrize("audio", [b"not WAV", b"", wav_audio()[:-3]])
def test_invalid_or_truncated_audio_rejected_before_queue(audio):
    with pytest.raises(ValueError):
        worker.pending_audio(audio)
