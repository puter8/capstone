"""TTS API contract, voice rollback and HTTP resource lifecycle regression tests."""
import json
import asyncio
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from fastapi import BackgroundTasks, UploadFile
from starlette.requests import Request

import main
from ai.conversation_rules import CONVERSATION_CORRECTION_RULES


@pytest.fixture(autouse=True)
def disable_session_feedback_poller(monkeypatch):
    # These tests exercise turn/TTS responses, not the separate database worker.
    monkeypatch.setenv("PALLY_SESSION_FEEDBACK_WORKER_ENABLED", "false")


def test_chat_prompt_includes_spoken_corrections_and_name_exemption():
    prompt = main._build_chat_system_prompt("Pally", "B1", {
        "Formality": 50, "Energy": 50, "Intimacy": 50, "Humor": 50, "Curiosity": 50,
    })

    assert prompt.count(CONVERSATION_CORRECTION_RULES) == 1
    assert "include its corrected expression in a compact, natural reply" in prompt
    assert "Fally, Pali, Palley, Polly" in prompt
    assert "Never correct, criticize, explain, or request a repetition of that name." in prompt
    assert "genuine grammar mistakes elsewhere in the same utterance can still be recast." in prompt
    assert "Never write two sentences." not in prompt


def _install_transport(monkeypatch, handler):
    clients = []
    original_client = httpx.AsyncClient

    def create_client(**kwargs):
        client = original_client(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(main.httpx, "AsyncClient", create_client)
    monkeypatch.setattr(main, "GOOGLE_CLOUD_API_KEY", "test-key")
    return clients


def test_default_voice_reuses_connection_pool_and_closes_on_shutdown(monkeypatch):
    requests = []

    def synthesize(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"audioContent": "bXAz"})

    clients = _install_transport(monkeypatch, synthesize)
    monkeypatch.setattr(main, "DEFAULT_TTS_VOICE", "en-US-Chirp3-HD-Leda")
    with TestClient(main.app) as api:
        for _ in range(2):
            response = api.post("/api/tts", json={"text": "Hello!"})
            assert response.status_code == 200
            assert response.json() == {
                "audio_b64": "bXAz", "voice": "en-US-Chirp3-HD-Leda", "encoding": "MP3",
            }
        assert len(clients) == 1
        assert not clients[0].is_closed
        assert all(r["voice"]["name"] == "en-US-Chirp3-HD-Leda" for r in requests)
        assert all(r["audioConfig"]["audioEncoding"] == "MP3" for r in requests)
    assert clients[0].is_closed
    assert main.app.state.http_client is None


def test_journey_configuration_rollback_and_explicit_override(monkeypatch):
    voices = []

    def synthesize(request):
        voices.append(json.loads(request.content)["voice"]["name"])
        return httpx.Response(200, json={"audioContent": "bXAz"})

    _install_transport(monkeypatch, synthesize)
    monkeypatch.setattr(main, "DEFAULT_TTS_VOICE", "en-US-Journey-F")
    with TestClient(main.app) as api:
        default = api.post("/api/tts", json={"text": "Hello!", "voice": None})
        explicit = api.post("/api/tts", json={"text": "Hello!", "voice": "en-US-Chirp3-HD-Leda"})
    assert default.json()["voice"] == "en-US-Journey-F"
    assert explicit.json()["voice"] == "en-US-Chirp3-HD-Leda"
    assert voices == ["en-US-Journey-F", "en-US-Chirp3-HD-Leda"]


@pytest.mark.parametrize("worker_fails", [False, True])
def test_billing_worker_and_http_pool_share_lifecycle(monkeypatch, worker_fails):
    clients = _install_transport(monkeypatch, lambda _: httpx.Response(200))
    monkeypatch.setenv("BILLING_PROVIDER", "kakaopay")
    monkeypatch.setenv("BILLING_WORKER_ENABLED", "true")

    async def scenario():
        started, stopped = asyncio.Event(), asyncio.Event()

        async def worker(get_db, stop):
            assert get_db is main.get_supabase
            assert main.app.state.http_client is clients[0]
            assert not clients[0].is_closed
            started.set()
            await stop.wait()
            assert not clients[0].is_closed
            stopped.set()
            if worker_fails:
                raise RuntimeError("test worker shutdown failure")

        monkeypatch.setattr(main.billing, "worker", worker)

        async def run_app():
            async with main.app.router.lifespan_context(main.app):
                await asyncio.wait_for(started.wait(), timeout=2)
                assert not stopped.is_set()

        if worker_fails:
            with pytest.raises(RuntimeError, match="test worker shutdown failure"):
                await run_app()
        else:
            await run_app()
        assert stopped.is_set()
        assert clients[0].is_closed
        assert main.app.state.http_client is None

    asyncio.run(scenario())


def test_complete_atomically_marks_review_work_before_scheduling_and_retries_idempotently(monkeypatch):
    completed_at = "2026-10-05T09:00:00+00:00"
    opened = {"id": "conversation-1", "user_id": "user-1", "ended_at": None, "title": None}
    closed = {**opened, "ended_at": completed_at}
    sb = Mock()
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data=closed)
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_owned_session", Mock(side_effect=[opened, closed]))
    now = Mock(side_effect=AssertionError("Completion must use the database clock and work marker"))
    monkeypatch.setattr(main, "_now_iso", now)
    refresh_traits = Mock(return_value=True)
    monkeypatch.setattr(main, "_refresh_profile_traits", refresh_traits)
    process_review = Mock(side_effect=AssertionError("Review must not execute before the close response"))
    assign_title = AsyncMock(side_effect=AssertionError("Title must not execute before the close response"))
    monkeypatch.setattr(main.session_feedback, "process_session", process_review)
    monkeypatch.setattr(main, "_assign_conversation_title", assign_title)

    async def scenario():
        first_tasks = BackgroundTasks()
        first = await main.complete_conversation("conversation-1", first_tasks, "user-1", "close-1")
        repeated_tasks = BackgroundTasks()
        repeated = await main.complete_conversation("conversation-1", repeated_tasks, "user-1", "close-2")

        expected = {
            "conversation": {"id": "conversation-1", "status": "completed", "completed_at": completed_at},
            "warnings": [],
        }
        assert first == repeated == expected
        process_review.assert_not_called()
        assign_title.assert_not_called()
        for tasks in (first_tasks, repeated_tasks):
            assert len(tasks.tasks) == 2
            review_task, title_task = tasks.tasks
            assert review_task.func is process_review
            assert review_task.args == (main.get_supabase, "conversation-1", main._conversation_turns)
            assert review_task.kwargs == {}
            assert review_task.is_async is False
            assert title_task.func is assign_title
            assert title_task.args == ("conversation-1",)

        assert sb.rpc.call_count == 2
        for rpc_call in sb.rpc.call_args_list:
            assert rpc_call.args == ("complete_conversation_with_feedback", {
                "p_conversation_id": "conversation-1",
                "p_user_id": "user-1",
                "p_expected_reopen_count": 0,
            })
        sb.table.assert_not_called()
        now.assert_not_called()
        refresh_traits.assert_called_once_with(sb, "user-1", "conversation-1")
        assert closed["ended_at"] == completed_at

    asyncio.run(scenario())


def test_repeated_complete_with_existing_title_only_reschedules_review(monkeypatch):
    completed_at = "2026-10-05T09:00:00+00:00"
    session = {
        "id": "conversation-1", "user_id": "user-1", "ended_at": completed_at,
        "title": "Cookie time", "reopen_count": 3,
    }
    sb = Mock()
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data=session)
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_owned_session", Mock(return_value=session))
    process_review = Mock()
    monkeypatch.setattr(main.session_feedback, "process_session", process_review)
    tasks = BackgroundTasks()

    response = asyncio.run(main.complete_conversation("conversation-1", tasks, "user-1", "retry-close"))

    assert response["conversation"]["completed_at"] == completed_at
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].func is process_review
    assert tasks.tasks[0].kwargs == {}
    process_review.assert_not_called()
    sb.rpc.assert_called_once_with("complete_conversation_with_feedback", {
        "p_conversation_id": "conversation-1",
        "p_user_id": "user-1",
        "p_expected_reopen_count": 3,
    })
    sb.table.assert_not_called()


@pytest.mark.parametrize("rpc_response, status_code, error_code", [
    (RuntimeError("conversation_changed"), 409, "conversation_already_active"),
    (RuntimeError("conversation_not_found"), 404, "not_found"),
    (None, 503, "persistence_failed"),
    ([], 503, "persistence_failed"),
    ("invalid session", 503, "persistence_failed"),
    ({"id": "conversation-1", "ended_at": None}, 503, "persistence_failed"),
    ({"ended_at": "2026-10-05T09:00:00+00:00"}, 503, "persistence_failed"),
], ids=["reopened", "missing", "null-response", "array-response", "string-response",
        "missing-completion", "missing-session-id"])
def test_complete_rpc_failure_does_not_schedule_background_work(
    monkeypatch, rpc_response, status_code, error_code,
):
    sb = Mock()
    if isinstance(rpc_response, Exception):
        sb.rpc.return_value.execute.side_effect = rpc_response
    else:
        sb.rpc.return_value.execute.return_value = SimpleNamespace(data=rpc_response)
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_owned_session", Mock(return_value={
        "id": "conversation-1", "user_id": "user-1", "ended_at": None, "reopen_count": 0,
    }))
    refresh_traits = Mock()
    monkeypatch.setattr(main, "_refresh_profile_traits", refresh_traits)
    tasks = BackgroundTasks()

    with pytest.raises(main.AppError) as caught:
        asyncio.run(main.complete_conversation("conversation-1", tasks, "user-1", "complete-1"))

    assert caught.value.status_code == status_code
    assert caught.value.code == error_code
    assert tasks.tasks == []
    refresh_traits.assert_not_called()


@pytest.mark.parametrize("latest_state, fail_at_insert", [
    ({"ended_at": "2026-10-05T09:00:00+00:00", "reopen_count": 0}, False),
    ({"ended_at": None, "reopen_count": 1}, False),
    ({"ended_at": None, "reopen_count": 0}, True),
], ids=["closed-during-generation", "closed-and-reopened-during-generation", "db-trigger-after-recheck"])
def test_inflight_turn_cannot_save_into_a_closed_or_reopened_session(monkeypatch, latest_state, fail_at_insert):
    original = {
        "id": "conversation-1", "user_id": "user-1", "ended_at": None,
        "reopen_count": 0, "character_name": "Pally", "level": "B1",
    }
    sessions, messages = Mock(), Mock()
    for query in (sessions, messages):
        for method in ("select", "eq", "order", "insert"):
            getattr(query, method).return_value = query
    sessions.execute.side_effect = [
        SimpleNamespace(data=[original]),
        SimpleNamespace(data=[{**original, **latest_state}]),
    ]
    message_results = [SimpleNamespace(data=[]), SimpleNamespace(data=[])]
    if fail_at_insert:
        message_results.append(RuntimeError("conversation_closed"))
    messages.execute.side_effect = message_results
    sb = Mock()
    sb.table.side_effect = lambda name: {"sessions": sessions, "messages": messages}[name]
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(main, "GOOGLE_CLOUD_API_KEY", "test-key")
    monkeypatch.setattr(main, "_read_subscription", lambda *_: None)
    monkeypatch.setattr(main, "_carried_over_axes", lambda *_: None)
    monkeypatch.setattr(main, "_reserve_turn", lambda *_: 1)
    release_turn = Mock()
    monkeypatch.setattr(main, "_release_turn", release_turn)
    monkeypatch.setattr(main, "_stt_from_bytes", AsyncMock(return_value=("she want cookies", 1.0)))
    monkeypatch.setattr(main, "_call_gemini_chat", AsyncMock(return_value="Oh, she wants cookies?"))
    monkeypatch.setattr(main, "_call_google_tts", AsyncMock(return_value="bXAz"))
    review_generation = AsyncMock(side_effect=AssertionError("Review is not a turn task"))
    monkeypatch.setattr(main, "_gen_feedback", review_generation)

    with pytest.raises(main.AppError) as caught:
        asyncio.run(main.create_turn(
            "conversation-1", Request({"type": "http"}),
            UploadFile(filename="test.wav", file=BytesIO(b"test-audio")),
            "user-1", "request-1",
        ))

    assert caught.value.status_code == 409
    assert caught.value.code == "conversation_closed"
    assert sessions.execute.call_count == 2
    if fail_at_insert:
        messages.insert.assert_called_once()
    else:
        messages.insert.assert_not_called()
    release_turn.assert_called_once_with(sb, "user-1")
    review_generation.assert_not_called()


def test_provider_failure_does_not_break_next_synthesis(monkeypatch):
    calls = []

    def synthesize(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(403, json={"error": {"status": "PERMISSION_DENIED"}})
        return httpx.Response(200, json={"audioContent": "bXAz"})

    clients = _install_transport(monkeypatch, synthesize)
    with TestClient(main.app) as api:
        assert api.post("/api/tts", json={"text": "Hello!"}).status_code == 502
        assert api.post("/api/tts", json={"text": "Hello!"}).status_code == 200
        assert len(clients) == 1


def test_turn_returns_spoken_correction_without_generating_review_cards(monkeypatch):
    """The spoken correction is immediate; session review cards are a separate job."""
    reply = "Oh, she wants cookies? What kind does she like?"
    timestamp = "2026-09-15T00:00:00+00:00"
    sessions, messages = Mock(), Mock()
    for query in (sessions, messages):
        for method in ("select", "eq", "order", "insert"):
            getattr(query, method).return_value = query
    sessions.execute.return_value = SimpleNamespace(data=[{
        "id": "conversation-1", "user_id": "user-1", "ended_at": None,
        "character_name": "Pally", "level": "B1",
    }])
    messages.execute.side_effect = [
        SimpleNamespace(data=[]), SimpleNamespace(data=[]),
        SimpleNamespace(data=[{"id": "turn-1", "role": "user", "created_at": timestamp}]),
    ]
    sb = Mock()
    sb.table.side_effect = lambda name: {"sessions": sessions, "messages": messages}[name]
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_read_subscription", lambda *_: None)
    monkeypatch.setattr(main, "_carried_over_axes", lambda *_: None)
    monkeypatch.setattr(main, "_reserve_turn", lambda *_: 1)
    monkeypatch.setattr(main, "GOOGLE_AI_API_KEY", "test-key")
    monkeypatch.setattr(main, "DEFAULT_TTS_VOICE", "en-US-Chirp3-HD-Leda")
    monkeypatch.setattr(main, "_stt_from_bytes", AsyncMock(return_value=("she want cookies", 1.0)))
    monkeypatch.setattr(main, "_call_gemini_chat", AsyncMock(return_value=reply))
    monkeypatch.setattr(main, "_TURN_METRICS", [])
    review_generation = AsyncMock(side_effect=AssertionError("Turn processing must not generate review cards"))
    monkeypatch.setattr(main, "_gen_feedback", review_generation)

    async def scenario():
        audio_ready = asyncio.Event()

        def synthesize(request):
            payload = json.loads(request.content)
            assert payload["voice"]["name"] == "en-US-Chirp3-HD-Leda"
            assert payload["input"]["text"] == reply
            audio_ready.set()
            return httpx.Response(200, json={"audioContent": "bXAz"})

        _install_transport(monkeypatch, synthesize)
        async with main.app.router.lifespan_context(main.app):
            request = Request({"type": "http"})
            request.state.request_id = "test-spoken-correction"
            result = await asyncio.wait_for(main.create_turn(
                "conversation-1", request,
                UploadFile(filename="test.wav", file=BytesIO(b"test-audio")),
                "user-1", "request-1",
            ), timeout=2)
        assert audio_ready.is_set()
        review_generation.assert_not_called()
        review_generation.assert_not_awaited()
        assert result["pally"] == {"text": reply, "audio": "bXAz"}
        assert result["user"]["transcript"] == "she want cookies"
        assert result["feedback"] == []
        assert result["feedback_pending"] is True
        assert result["status"] == "completed"
        assert result["warnings"] == []
        messages.insert.assert_called_once()
        saved_user, saved_pally = messages.insert.call_args.args[0]
        assert saved_user["feedback"] is None
        assert saved_pally["transcript"] == reply
        saved_user.update(id="turn-1", created_at=timestamp)
        saved_pally.update(id="reply-1", created_at=timestamp)
        detail = main._turn_detail(saved_user, saved_pally, 1)
        assert detail["feedback"] == []
        assert detail["feedback_pending"] is True
        assert len(main._TURN_METRICS) == 1
        assert main._TURN_METRICS[0]["request_id"] == "test-spoken-correction"
        assert main._TURN_METRICS[0]["feedback_ms"] == 0

    asyncio.run(scenario())
