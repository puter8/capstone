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
    for method in ("select", "eq", "order", "insert", "limit", "update", "is_", "range"):
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
    monkeypatch.setattr(main, "_cumulative_state", lambda *_: dict(main._INITIAL_AXES))
    monkeypatch.setattr(main, "_intimacy_from_access_days", lambda *_: AXES["Intimacy"])
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
    assert user["raw_axes"] == {**AXES, "Energy": 100}  # the vote uses the analyzer score, not the display
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


def test_missing_baseline_is_allowed_when_not_required(monkeypatch):
    monkeypatch.setenv("PALLY_VOICE_BASELINE_REQUIRED", "false")
    _, messages = install_turn(monkeypatch, baseline=None)
    asyncio.run(main.create_turn("conversation-1", Request({"type": "http"}), upload(pcm_wav()), "user-1", "key"))
    user, _ = messages.insert.call_args.args[0]
    assert user["voice_energy"] is None  # no baseline -> nothing queued for pitch measurement
    main._reserve_turn.assert_called_once()


@pytest.mark.parametrize("energy", [{"status": "ready", "score": 75, "reason": None},
    {"status": "retained", "score": 75, "reason": "insufficient_valid_clips"}])
def test_complete_uses_atomic_energy_rpc_and_returns_immutable_final_snapshot(monkeypatch, energy):
    opened = {"id": "conversation-1", "user_id": "user-1", "ended_at": None, "reopen_count": 2, "title": "Title"}
    closed = {**opened, "ended_at": "now", "current_axes": AXES, "energy": energy}
    sb = Mock()
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data=closed)
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    voted = {**closed, "axes_contribution": {"mean": AXES, "turns": 1, "first_completed_at": "now"}}
    monkeypatch.setattr(main, "_owned_session", Mock(side_effect=[opened, voted]))
    record = Mock(return_value=1)
    monkeypatch.setattr(main, "_record_vote", record)
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
    # first close only: before closing (recoverable) and after (exact); the retry does not vote again
    assert record.call_args_list == [((sb, "user-1", "conversation-1", None),)] * 2
    refresh.assert_called_once_with(sb, "user-1")
    measure.assert_not_called()


def vote(x, at):
    return {"mean": {k: x for k in AXES}, "turns": 1, "first_completed_at": at}


def test_record_vote_is_the_raw_mean_and_keeps_a_reopened_conversations_slot():
    messages, sessions = query(), query()
    messages.range.return_value = messages
    messages.execute.return_value = SimpleNamespace(data=[
        {"id": "m1", "transcript": "a", "raw_axes": {**AXES, "Humor": 0}},
        {"id": "m2", "transcript": "b", "raw_axes": {**AXES, "Humor": 100}}])
    sessions.execute.return_value = SimpleNamespace(data=[{"id": "conversation-1"}])
    sb = Mock()
    sb.table.side_effect = lambda name: {"messages": messages, "sessions": sessions}[name]
    previous = vote(0, "2026-10-01T00:00:00+00:00")
    assert main._record_vote(sb, "user-1", "conversation-1", previous) == 2
    recorded = sessions.update.call_args.args[0]["axes_contribution"]
    assert recorded == {"mean": {**AXES, "Humor": 50.0}, "turns": 2, "first_completed_at": previous["first_completed_at"]}


def test_record_vote_that_matches_no_row_is_a_failure_not_a_silent_success():
    messages, sessions = query(), query()
    messages.range.return_value = messages
    messages.execute.return_value = SimpleNamespace(data=[])
    sessions.execute.return_value = SimpleNamespace(data=[])
    sb = Mock()
    sb.table.side_effect = lambda name: {"messages": messages, "sessions": sessions}[name]
    with pytest.raises(main.AppError) as caught:
        main._record_vote(sb, "user-1", "conversation-1", None)
    assert caught.value.code == "persistence_failed"


def completed_sessions(rows):
    sessions = query()
    sessions.range.return_value = sessions
    sessions.execute.return_value = SimpleNamespace(data=rows)
    sb = Mock()
    sb.table.side_effect = lambda name: {"sessions": sessions}[name]
    return sb


def test_cumulative_state_replays_votes_in_first_completed_order():
    sb = completed_sessions([
        {"id": "open", "ended_at": None, "axes_contribution": {"mean": {k: 100 for k in AXES}, "turns": 1,
                                                               "first_completed_at": None}},
        {"id": "b", "ended_at": "x", "axes_contribution": vote(100, "2026-10-02T00:00:00+00:00")},
        {"id": "a", "ended_at": "x", "axes_contribution": vote(0, "2026-10-01T00:00:00+00:00")},
        {"id": "empty", "ended_at": "2026-10-03T00:00:00+00:00",
         "axes_contribution": {"mean": None, "turns": 0, "first_completed_at": None}}])
    # a(0) with α=1/2, b(100) with α=1/3; the empty conversation moves nothing
    first = {k: round(v / 2) for k, v in main._INITIAL_AXES.items()}
    assert main._cumulative_state(sb, "user-1") == {k: round(first[k] + (100 - first[k]) / 3) for k in first}
    # a new conversation goes last, after the empty one: n=3 -> α=1/5
    then = main._cumulative_state(sb, "user-1", ("new", {k: 0 for k in AXES}, None))
    assert then == {k: round(v * 4 / 5) for k, v in main._cumulative_state(sb, "user-1").items()}


def test_reopened_conversation_is_replayed_in_its_original_slot_not_counted_twice():
    rows = [{"id": "a", "ended_at": "x", "axes_contribution": vote(0, "2026-10-01T00:00:00+00:00")},
            *[{"id": f"z{i}", "ended_at": "x", "axes_contribution": vote(0, f"2026-10-0{i + 2}T00:00:00+00:00")}
              for i in range(3)],
            {"id": "e", "ended_at": "x", "axes_contribution": vote(100, "2026-10-09T00:00:00+00:00")}]
    final = main._cumulative_state(completed_sessions(rows), "user-1")
    # Reopen "a" without changing its mean: the turn preview must equal the completed state.
    others = [r for r in rows if r["id"] != "a"]
    preview = main._cumulative_state(completed_sessions(others), "user-1",
                                     ("a", {k: 0 for k in AXES}, "2026-10-01T00:00:00+00:00"))
    assert preview == final


def test_profile_refresh_rewrites_until_it_matches_the_latest_votes(monkeypatch):
    """동시에 끝낸 다른 대화가 표를 더한 경우: 쓴 뒤 다시 계산한 값이 다르면 다시 쓴다."""
    stale, fresh = {**AXES, "Formality": 25}, {**AXES, "Formality": 50}
    monkeypatch.setattr(main, "_profile_axes", Mock(side_effect=[stale, fresh, fresh]))
    profiles = query()
    profiles.execute.return_value = SimpleNamespace(data=[{"id": "user-1"}])
    sb = Mock()
    sb.table.side_effect = lambda name: {"profiles": profiles}[name]
    assert main._refresh_profile_traits(sb, "user-1") is True
    writes = [c.args[0] for c in profiles.update.call_args_list]
    assert [w["current_axes"] for w in writes] == [stale, fresh]
    assert writes[-1]["traits"] == main._axes_to_traits(fresh)


def test_profile_axes_use_votes_access_days_and_latest_confirmed_energy(monkeypatch):
    monkeypatch.setattr(main, "_cumulative_state", lambda *_: {**AXES, "Energy": 5, "Intimacy": 99})
    monkeypatch.setattr(main, "_intimacy_from_access_days", lambda *_: 35)
    monkeypatch.setattr(main.voice_energy, "latest_snapshot", Mock(return_value={"current_axes": AXES}))
    assert main._profile_axes(Mock(), "user-1") == {**AXES, "Intimacy": 35}


@pytest.mark.parametrize("energy", [None, {"status": "ready", "score": 0, "reason": None}])
def test_invalid_completion_snapshot_is_not_reported_as_success(monkeypatch, energy):
    opened = {"id": "conversation-1", "user_id": "user-1", "ended_at": None, "reopen_count": 0}
    sb = Mock()
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data={
        **opened, "ended_at": "now", "current_axes": AXES, "energy": energy,
    })
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_record_vote", Mock(return_value=1))
    monkeypatch.setattr(main, "_owned_session", Mock(return_value=opened))
    tasks = BackgroundTasks()
    with pytest.raises(main.AppError) as caught:
        asyncio.run(main.complete_conversation("conversation-1", tasks, "user-1", "key"))
    assert caught.value.code == "persistence_failed"
    assert tasks.tasks == []


# ── 온보딩 목소리 등록 — 화면이 필요로 하는 계약 ─────────────────────────────


def test_baseline_get_hands_the_screen_its_prompts_and_limits(monkeypatch):
    """질문과 길이 규칙을 서버가 준다. 화면이 하드코딩하면 문항을 바꿀 때마다
    프론트를 배포해야 하고, 클립 수·길이 규칙이 서버와 어긋날 수 있다."""
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main.voice_energy, "get_baseline", Mock(return_value=None))
    body = TestClient(main.app).get("/api/energy/baseline", headers={"Authorization": "Bearer t"}).json()

    assert body["status"] == "required"
    assert len(body["prompts"]) == body["limits"]["clips"] == 3
    assert all(p.strip().endswith("?") for p in body["prompts"])
    assert body["limits"] == {"clips": 3, "min_seconds": 5, "max_seconds": 30}


def test_a_clip_under_five_seconds_is_told_apart_from_a_silent_one(monkeypatch):
    """화면은 reason 으로 분기한다. 짧게 말한 것과 목소리가 안 담긴 것은 사용자가
    해야 할 행동이 달라서 같은 문구로 묶으면 안 된다."""
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main.voice_energy, "get_baseline", Mock(return_value=None))
    client = TestClient(main.app)

    for reason, expected in (("clip_too_short", "5초 이상"), ("insufficient_voiced_frames", "목소리가 충분히")):
        monkeypatch.setattr(main, "measure_wav", Mock(return_value=core.missing_clip(reason)), raising=False)
        monkeypatch.setattr(core, "measure_wav", Mock(return_value=core.missing_clip(reason)))
        response = client.post(
            "/api/energy/baseline",
            headers={"Authorization": "Bearer t", "Idempotency-Key": "k"},
            files=[("audio", (f"{i}.wav", pcm_wav(), "audio/wav")) for i in range(3)],
        )
        assert response.status_code == 422, response.text
        detail = response.json()["error"]
        assert detail["details"] == {"clip_index": 1, "reason": reason}
        assert expected in detail["message"]


def test_baseline_measurement_enforces_the_minimum_length(monkeypatch):
    """5초 규칙은 기준 등록에서만 쓴다. 대화 턴 측정까지 걸면 짧게 답한 발화가
    통째로 버려진다."""
    short = core.measure_wav(pcm_wav(), require_min_duration=True)
    assert short.range_st is None and short.missing_reason == "clip_too_short"

    # 같은 1초 클립이라도 턴 경로에서는 길이로 거르지 않는다
    assert core.measure_wav(pcm_wav()).missing_reason != "clip_too_short"


def test_warm_up_runs_the_measurement_once_and_never_raises(monkeypatch):
    """부팅 때 JIT 컴파일을 끝내 둔다(실측 첫 호출 7.9초, 이후 2.7초).
    실패해도 서버 기동을 막지 않는다 — 예열이 안 됐을 뿐이다."""
    from lib import voice_energy as worker_module

    called = Mock(return_value=core.missing_clip("empty_audio"))
    monkeypatch.setattr(worker_module, "measure_wav", called)
    worker_module.warm_up()
    called.assert_called_once()

    monkeypatch.setattr(worker_module, "measure_wav", Mock(side_effect=RuntimeError("librosa missing")))
    worker_module.warm_up()  # 예외가 밖으로 나가면 서버가 못 뜬다


def test_intimacy_counts_kst_days_not_page_loads():
    events = query()
    events.range.return_value = events
    # 23:00 KST on 10-14, then 01:00 and 11:00 KST on 10-15 -> two access days
    events.execute.return_value = SimpleNamespace(data=[
        {"received_at": "2026-10-14T14:00:00+00:00"},
        {"received_at": "2026-10-14T16:00:00+00:00"},
        {"received_at": "2026-10-15T02:00:00+00:00"}])
    sb = Mock()
    sb.table.side_effect = lambda name: {"activity_events": events}[name]
    assert main._intimacy_from_access_days(sb, "user-1") == 15  # 100*2/12 = 16.7 -> 15


def test_axis_analysis_failure_refunds_the_turn_and_saves_nothing(monkeypatch):
    _, messages = install_turn(monkeypatch)
    monkeypatch.setattr(main, "_analyze_axes", Mock(side_effect=RuntimeError("model down")))
    release = Mock()
    monkeypatch.setattr(main, "_release_turn", release)
    with pytest.raises(main.AppError) as caught:
        asyncio.run(main.create_turn("conversation-1", Request({"type": "http"}), upload(pcm_wav()), "user-1", "key"))
    assert caught.value.code == "analysis_failed"
    release.assert_called_once()
    messages.insert.assert_not_called()


def test_reopening_keeps_the_first_completion_time_as_the_vote_slot(monkeypatch):
    session = {"id": "conversation-1", "user_id": "user-1", "ended_at": "2026-10-01T00:00:00+00:00",
               "reopen_count": 0, "axes_contribution": {"mean": AXES, "turns": 1, "first_completed_at": None}}
    sessions = query()
    sessions.execute.return_value = SimpleNamespace(data=[{**session, "ended_at": None}])
    sb = Mock()
    sb.table.side_effect = lambda name: {"sessions": sessions}[name]
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_owned_session", lambda *_: session)
    asyncio.run(main.reopen_conversation("conversation-1", "user-1", "key"))
    update = sessions.update.call_args.args[0]
    assert update["ended_at"] is None
    assert update["axes_contribution"]["first_completed_at"] == "2026-10-01T00:00:00+00:00"


def test_another_reopened_conversation_still_counts_while_it_is_open():
    reopened = {"id": "a", "ended_at": None, "axes_contribution": vote(0, "2026-10-01T00:00:00+00:00")}
    closed = {"id": "a", "ended_at": "2026-10-05T00:00:00+00:00", "axes_contribution": reopened["axes_contribution"]}
    assert main._cumulative_state(completed_sessions([reopened]), "user-1") == \
        main._cumulative_state(completed_sessions([closed]), "user-1")


def test_reopening_a_legacy_conversation_without_a_vote_keeps_its_slot(monkeypatch):
    session = {"id": "conversation-1", "user_id": "user-1", "ended_at": "2026-10-01T00:00:00+00:00",
               "reopen_count": 0, "axes_contribution": None}
    sessions = query()
    sessions.execute.return_value = SimpleNamespace(data=[{**session, "ended_at": None}])
    sb = Mock()
    sb.table.side_effect = lambda name: {"sessions": sessions}[name]
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_owned_session", lambda *_: session)
    asyncio.run(main.reopen_conversation("conversation-1", "user-1", "key"))
    assert sessions.update.call_args.args[0]["axes_contribution"] == {
        "mean": None, "turns": 0, "first_completed_at": "2026-10-01T00:00:00+00:00"}


def test_profile_refresh_that_matches_no_row_is_reported(monkeypatch):
    monkeypatch.setattr(main, "_profile_axes", lambda *_: dict(AXES))
    profiles = query()
    profiles.execute.return_value = SimpleNamespace(data=[])
    sb = Mock()
    sb.table.side_effect = lambda name: {"profiles": profiles}[name]
    assert main._refresh_profile_traits(sb, "user-1") is False
