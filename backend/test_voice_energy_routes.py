"""Enabled Energy route contracts with mocked providers/DB, not real-service E2E."""
import asyncio
import base64
import hashlib
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import wave

from fastapi import BackgroundTasks, UploadFile
from starlette.requests import Request
import pytest

import main
import ai.voice_energy as core

AXES = {"Formality": 35, "Energy": 75, "Intimacy": 40, "Humor": 20, "Curiosity": 65}
BASELINE = {"user_id": "user-1", "range_st": 4.0, "method": core.ALGORITHM_VERSION}


@pytest.fixture(autouse=True)
def isolated_enabled_routes(monkeypatch):
    monkeypatch.setenv("PALLY_VOICE_ENERGY_ENABLED", "true")
    monkeypatch.setenv("PALLY_SESSION_FEEDBACK_WORKER_ENABLED", "false")
    monkeypatch.setenv("BILLING_WORKER_ENABLED", "false")
    monkeypatch.setattr(main, "get_supabase", Mock(return_value=Mock()))


def upload(payload):
    return UploadFile(file=BytesIO(payload), filename="test.wav")


def pcm_wav():
    stream = BytesIO()
    with wave.open(stream, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16000)
        target.writeframes(b"\0\0" * 16000)
    return stream.getvalue()


def query():
    result = Mock()
    for method in ("select", "eq", "order", "insert", "limit", "update", "is_"):
        getattr(result, method).return_value = result
    result.not_ = result
    return result


@pytest.mark.parametrize("enabled,row,status", [(False, None, "disabled"), (True, None, "required"), (True, BASELINE, "ready")])
def test_get_baseline_states(monkeypatch, enabled, row, status):
    monkeypatch.setenv("PALLY_VOICE_ENERGY_ENABLED", str(enabled).lower())
    read = Mock(return_value=row)
    monkeypatch.setattr(main.voice_energy, "get_baseline", read)
    result = asyncio.run(main.get_energy_baseline("user-1"))
    assert result["status"] == status
    assert read.call_count == int(enabled)
    if status == "ready":
        assert result["baseline"] == {"range_st": 4.0, "valid_clips": 3, "method_version": core.ALGORITHM_VERSION}


def test_register_baseline_saves_once_and_retries_return_existing(monkeypatch):
    measured = core.ClipMeasurement(4, 100, 150, 1.5, 200, 0)
    measure = Mock(return_value=measured)
    save = Mock(return_value=BASELINE)
    monkeypatch.setattr(core, "measure_wav", measure)
    monkeypatch.setattr(main.voice_energy, "get_baseline", Mock(side_effect=[None, BASELINE]))
    monkeypatch.setattr(main.voice_energy, "save_baseline", save)
    async def run():
        first = await main.register_energy_baseline([upload(bytes([v])) for v in (1, 2, 3)], "user-1", "key")
        repeated = await main.register_energy_baseline([upload(bytes([v])) for v in (1, 2, 3)], "user-1", "key")
        assert repeated == first
    asyncio.run(run())
    assert measure.call_count == 3
    save.assert_called_once_with(main.get_supabase(), "user-1", [measured] * 3)


@pytest.mark.parametrize("payloads,missing", [([b"one", b"one", b"two"], False),
    ([b"one", b"two"], False), ([b"one", b"two", b"three"], True)])
def test_register_rejects_duplicates_wrong_count_and_invalid_clip(monkeypatch, payloads, missing):
    measure = Mock(return_value=core.missing_clip("invalid_wav") if missing else core.ClipMeasurement(4, 100, 150, 1.5, 200, 0))
    save = Mock()
    monkeypatch.setattr(core, "measure_wav", measure)
    monkeypatch.setattr(main.voice_energy, "get_baseline", Mock(return_value=None))
    monkeypatch.setattr(main.voice_energy, "save_baseline", save)
    with pytest.raises(main.AppError) as caught:
        asyncio.run(main.register_energy_baseline([upload(p) for p in payloads], "user-1", "key"))
    assert caught.value.status_code == 422
    assert caught.value.code == "invalid_audio"
    save.assert_not_called()


def install_turn(monkeypatch, baseline=BASELINE):
    sessions, messages = query(), query()
    sessions.execute.return_value = SimpleNamespace(data=[{"id": "conversation-1", "user_id": "user-1", "ended_at": None,
        "character_name": "Pally", "level": "B1", "reopen_count": 2}])
    messages.execute.side_effect = [SimpleNamespace(data=[]),
        SimpleNamespace(data=[{"id": "msg-before", "role": "user", "transcript": "Before",
                               "axes": {**AXES, "Energy": 5}, "created_at": "before"}]),
        SimpleNamespace(data=[{"id": "turn-1", "role": "user", "created_at": "now"}])]
    sb = Mock()
    sb.table.side_effect = lambda name: {"sessions": sessions, "messages": messages}[name]
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main.voice_energy, "get_baseline", Mock(return_value=baseline))
    monkeypatch.setattr(main.voice_energy, "latest_snapshot", Mock(return_value={"current_axes": AXES}))
    monkeypatch.setattr(main, "GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(main, "GOOGLE_CLOUD_API_KEY", "test-key")
    monkeypatch.setattr(main, "_read_subscription", lambda *_: None)
    monkeypatch.setattr(main, "_reserve_turn", Mock(return_value=1))
    monkeypatch.setattr(main, "_analyze_axes", Mock(return_value={**AXES, "Energy": 100}))
    monkeypatch.setattr(main, "_stt_from_bytes", AsyncMock(return_value=("I like this conversation", 1)))
    monkeypatch.setattr(main, "_call_gemini_chat", AsyncMock(return_value="What do you like about it?"))
    monkeypatch.setattr(main, "_call_google_tts", AsyncMock(return_value="audio"))
    monkeypatch.setattr(main, "_TURN_METRICS", [])
    return sb, messages


def test_turn_durably_inserts_pending_audio_without_pitch_inference_and_preserves_voice_axis(monkeypatch):
    sb, messages = install_turn(monkeypatch)
    measure = Mock(side_effect=AssertionError("Pitch must not run in the turn response path"))
    monkeypatch.setattr(core, "measure_wav", measure)
    monkeypatch.setattr(main.voice_energy, "measure_wav", measure)
    audio = pcm_wav()
    result = asyncio.run(main.create_turn("conversation-1", Request({"type": "http"}), upload(audio), "user-1", "key"))
    assert result["axes"]["Energy"] == AXES["Energy"] == 75
    assert main._call_gemini_chat.call_args.args[-1]["Energy"] == 75
    messages.insert.assert_called_once()
    user, pally = messages.insert.call_args.args[0]
    assert user["axes"]["Energy"] == 75
    assert user["voice_energy_epoch"] == 2
    pending = user["voice_energy"]
    assert pending["status"] == "pending"
    assert pending["audio_sha256"] == hashlib.sha256(audio).hexdigest()
    assert base64.b64decode(pending["audio_base64"]) == audio
    assert "voice_energy" not in pally
    measure.assert_not_called()


def test_missing_baseline_stops_before_stt_quota_or_insert(monkeypatch):
    _, messages = install_turn(monkeypatch, baseline=None)
    with pytest.raises(main.AppError) as caught:
        asyncio.run(main.create_turn("conversation-1", Request({"type": "http"}), upload(pcm_wav()), "user-1", "key"))
    assert caught.value.code == "energy_baseline_required"
    main._stt_from_bytes.assert_not_called()
    main._reserve_turn.assert_not_called()
    messages.insert.assert_not_called()


@pytest.mark.parametrize("energy", [{"status": "ready", "score": 75, "reason": None},
    {"status": "retained", "score": 75, "reason": "insufficient_valid_clips"}])
def test_complete_uses_atomic_energy_rpc_and_returns_immutable_final_snapshot(monkeypatch, energy):
    opened = {"id": "conversation-1", "user_id": "user-1", "ended_at": None, "reopen_count": 2, "title": "Title"}
    closed = {**opened, "ended_at": "now", "current_axes": AXES, "energy": energy}
    sb = Mock()
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data=closed)
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_owned_session", Mock(side_effect=[opened, closed]))
    refresh = Mock(return_value=True)
    monkeypatch.setattr(main, "_refresh_profile_traits", refresh)
    measure = Mock(side_effect=AssertionError("No extraction during completion"))
    monkeypatch.setattr(main.voice_energy, "measure_wav", measure)
    async def run():
        first = await main.complete_conversation("conversation-1", BackgroundTasks(), "user-1", "key")
        second = await main.complete_conversation("conversation-1", BackgroundTasks(), "user-1", "key")
        assert first == second
        assert first["current_axes"] == AXES
        assert first["energy"] == energy
        assert [w["code"] for w in first["warnings"]] == ([] if energy["status"] == "ready" else ["energy_unavailable"])
    asyncio.run(run())
    for call in sb.rpc.call_args_list:
        assert call.args == ("complete_conversation_with_energy", {"p_conversation_id": "conversation-1", "p_user_id": "user-1", "p_expected_reopen_count": 2})
    refresh.assert_called_once_with(sb, "user-1", "conversation-1")
    measure.assert_not_called()


def test_history_carryover_and_profile_traits_use_same_final_axes(monkeypatch):
    """세션 종료 시 확정된 축이 History 표시·마이페이지 태그·다음 대화 출발점에
    모두 같은 값으로 쓰여야 한다.

    출발점은 profiles.current_axes 한 곳에서 읽으므로(기준이 하나), 확정 스냅샷은
    종료 시 거기에 기록돼야 세 화면이 어긋나지 않는다. 마지막 발화의 텍스트 축
    (Energy 5)이 아니라 확정값(Energy 75)이 쓰이는지 확인한다.
    """
    snapshots, messages, profiles = query(), query(), query()
    snapshots.execute.return_value = SimpleNamespace(data=[{"current_axes": AXES}])
    messages.execute.return_value = SimpleNamespace(data=[{"axes": {**AXES, "Energy": 5}}])
    profiles.execute.return_value = SimpleNamespace(data=[{"current_axes": AXES}])
    sb = Mock()
    sb.table.side_effect = lambda name: {"voice_energy_snapshots": snapshots, "messages": messages, "profiles": profiles}[name]
    monkeypatch.setattr(main.voice_energy, "latest_snapshot", Mock(return_value={"current_axes": AXES}))

    assert main._session_display_axes(sb, {"id": "conversation-1"}, [{"role": "user", "axes": {**AXES, "Energy": 5}}]) == AXES
    assert main._refresh_profile_traits(sb, "user-1", "conversation-1") is True
    stored = profiles.update.call_args.args[0]
    assert stored["current_axes"] == AXES          # 확정값이 기준에 기록된다
    assert stored["traits"] == main._axes_to_traits(AXES)
    assert main._carried_over_axes(sb, "user-1") == AXES  # 다음 대화도 같은 값에서 출발


@pytest.mark.parametrize("energy", [None, {"status": "ready", "score": 0, "reason": None}])
def test_invalid_completion_snapshot_is_not_reported_as_success(monkeypatch, energy):
    opened = {"id": "conversation-1", "user_id": "user-1", "ended_at": None, "reopen_count": 0}
    sb = Mock()
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data={
        **opened, "ended_at": "now", "current_axes": AXES, "energy": energy,
    })
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_owned_session", Mock(return_value=opened))
    tasks = BackgroundTasks()
    with pytest.raises(main.AppError) as caught:
        asyncio.run(main.complete_conversation("conversation-1", tasks, "user-1", "key"))
    assert caught.value.code == "persistence_failed"
    assert tasks.tasks == []
