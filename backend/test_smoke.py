# -*- coding: utf-8 -*-
"""
CI smoke test — 시크릿/실서비스 없이 도는 최소 검증.

목적:
- 앱이 import 되는지 (문법 에러, import 에러, 정의 안 된 참조 등)
- 핵심 라우트가 사라지지 않았는지 (PR #33 처럼 머지 사고로 엔드포인트가
  조용히 삭제되는 것을 CI 단계에서 차단)

실제 STT/Gemini/TTS/Supabase E2E 는 시크릿·비용 때문에 여기서 돌리지 않는다.
그건 로컬/별도 통합 테스트에서 실제 서비스로 검증한다.
"""
import main


def test_account_deletion_authentication_and_confirmation(monkeypatch):
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from unittest.mock import Mock

    sb = Mock()
    sb.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="caller-id"))
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_SUPABASE_ENABLED", True)
    client = TestClient(main.app)
    response = client.request("DELETE", "/api/account", json={"confirmation": "회원탈퇴"})
    assert response.status_code == 401
    for payload in ({}, {"confirmation": "yes"}, {"confirmation": "회원탈퇴", "user_id": "victim-id"}):
        response = client.request("DELETE", "/api/account", headers={"Authorization": "Bearer test"}, json=payload)
        assert response.status_code == 422
    sb.auth.admin.delete_user.assert_not_called()


def test_account_deletion_only_deletes_verified_user(monkeypatch):
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from unittest.mock import Mock

    sb = Mock()
    sb.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="caller-id"))
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data=True)
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_read_subscription", lambda *_: None)
    monkeypatch.setattr(main, "_SUPABASE_ENABLED", True)
    response = TestClient(main.app).request("DELETE", "/api/account", headers={"Authorization": "Bearer test"}, json={"confirmation": "회원탈퇴"})
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}
    sb.auth.admin.delete_user.assert_called_once_with("caller-id", should_soft_delete=False)
    sb.table.assert_not_called()


def test_account_deletion_fails_closed(monkeypatch):
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from unittest.mock import Mock

    sb = Mock()
    sb.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="caller-id"))
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_SUPABASE_ENABLED", True)
    monkeypatch.setattr(main, "_reset_supabase_client", lambda: None)
    client = TestClient(main.app)
    for ready, subscription, expected in ((False, None, 503), (True, {"will_renew": True}, 409)):
        sb.rpc.return_value.execute.return_value = SimpleNamespace(data=ready)
        monkeypatch.setattr(main, "_read_subscription", lambda *_, value=subscription: value)
        response = client.request("DELETE", "/api/account", headers={"Authorization": "Bearer test"}, json={"confirmation": "회원탈퇴"})
        assert response.status_code == expected
    sb.auth.admin.delete_user.assert_not_called()

    monkeypatch.setattr(main, "_read_subscription", lambda *_: None)
    sb.auth.admin.delete_user.side_effect = RuntimeError("database unavailable")
    response = client.request("DELETE", "/api/account", headers={"Authorization": "Bearer test"}, json={"confirmation": "회원탈퇴"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "account_deletion_failed"
    assert "database unavailable" not in response.text
    sb.table.assert_not_called()


def test_legacy_deletion_request_cannot_delete_account(monkeypatch):
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from unittest.mock import Mock

    sb = Mock()
    sb.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="caller-id"))
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_SUPABASE_ENABLED", True)
    response = TestClient(main.app).post("/api/account/deletion-request", headers={"Authorization": "Bearer test"}, json={"reason": "user_requested"})
    assert response.status_code == 410
    sb.auth.admin.delete_user.assert_not_called()


def test_axes_to_traits_uses_renderer_tier_boundaries():
    """태그는 캐릭터 렌더러와 같은 0~33 / 34~66 / 67~100 구간을 쓴다 (모습과 태그 일치)."""
    low = {"Intimacy": 33, "Humor": 0, "Energy": 33, "Curiosity": 10, "Formality": 33}
    mid = {"Intimacy": 34, "Humor": 50, "Energy": 66, "Curiosity": 34, "Formality": 66}
    high = {"Intimacy": 67, "Humor": 100, "Energy": 67, "Curiosity": 90, "Formality": 67}

    assert main._axes_to_traits(low) == ["acquaint", "serious", "calm", "indifferent", "blunt"]
    assert main._axes_to_traits(mid) == ["buddy", "funny", "lively", "curious", "casual"]
    assert main._axes_to_traits(high) == ["bestie", "ridiculous", "energetic", "inquisitive", "formal"]


def test_default_traits_match_the_default_pally_shown_to_new_users():
    """신규 가입자 기본 태그(DB default)는 홈 화면의 기본 Pally 모습과 같아야 한다.

    frontend/lib/types/character.ts 의 DEFAULT_AXES 를 태그 규칙에 넣은 결과가
    supabase/migrations/20260922000000_profiles_default_traits.sql 의 기본값이다.
    둘 중 하나를 바꾸면 이 테스트와 다른 쪽도 함께 바꿔야 한다.
    """
    frontend_default_axes = {"Formality": 50, "Energy": 30, "Intimacy": 20, "Humor": 10, "Curiosity": 15}
    assert main._axes_to_traits(frontend_default_axes) == ["acquaint", "serious", "calm", "indifferent", "casual"]


def test_axes_to_traits_always_returns_five_unique_tags():
    """profiles.traits 는 DB 제약상 정확히 5개, 프론트는 태그 텍스트를 key 로 쓴다."""
    for value in (0, 33, 34, 66, 67, 100):
        traits = main._axes_to_traits({axis: value for axis, _ in main._TRAIT_TIERS})
        assert len(traits) == 5
        assert len(set(traits)) == 5


def test_clean_title_strips_quotes_punctuation_and_whitespace():
    assert main._clean_title('  "Diet and Hunger."\n') == "Diet and Hunger"
    assert main._clean_title("“Cookie Preferences!”") == "Cookie Preferences"
    assert main._clean_title("   ") is None
    assert len(main._clean_title("word " * 40)) <= main._TITLE_MAX_CHARS


def test_conversation_title_falls_back_to_the_opener_when_nobody_spoke():
    """발화 0건 대화도 History 에 남으므로(기획) 제목이 비지 않아야 한다."""
    opener = {"role": "pally", "transcript": "Hey! Got any fun weekend plans coming up?"}
    spoke = [opener, {"role": "user", "transcript": "i went to the park"}]

    assert main._conversation_title({"title": None}, [opener]) == opener["transcript"]
    # 발화가 있으면 사용자가 말한 내용이 먼저 (오프너가 앞에 있어도)
    assert main._conversation_title({"title": None}, spoke) == "i went to the park"
    assert main._conversation_title({"title": "Park Visit"}, [opener]) == "Park Visit"
    assert main._conversation_title({"title": None}, []) is None


def test_conversation_title_prefers_stored_title_then_first_utterance():
    messages = [{"role": "user", "transcript": "i had no lunch im diet"}]
    assert main._conversation_title({"title": "Diet and Hunger"}, messages) == "Diet and Hunger"
    assert main._conversation_title({"title": None}, messages) == "i had no lunch im diet"
    assert main._conversation_title({}, []) is None


def test_generate_conversation_title_reads_json_title(monkeypatch):
    """제목만 JSON 으로 받아 정리한다 (일반 텍스트는 설명 문장이 붙는 경우가 잦았음)."""
    import asyncio
    import httpx
    from types import SimpleNamespace

    sent = {}

    class FakeClient:
        async def post(self, url, json, timeout):
            sent["payload"] = json
            body = {"candidates": [{"content": {"parts": [{"text": '{"title": "Diet and Hunger."}'}]}}]}
            return httpx.Response(200, json=body)

    monkeypatch.setattr(main.app, "state", SimpleNamespace(http_client=FakeClient()))
    turns = [{"role": "user", "transcript": "I had no lunch"}, {"role": "pally", "transcript": "Oh no!"}]

    assert asyncio.run(main._generate_conversation_title(turns)) == "Diet and Hunger"
    config = sent["payload"]["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert "User: I had no lunch" in sent["payload"]["contents"][0]["parts"][0]["text"]


def test_assign_conversation_title_only_fills_empty_title(monkeypatch):
    """제목은 title IS NULL 일 때만 저장 → 재개·재종료해도 한 번 정해진 제목은 고정."""
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock

    sessions, messages = Mock(), Mock()
    for query in (sessions, messages):
        for method in ("select", "eq", "order", "update", "is_"):
            getattr(query, method).return_value = query
    messages.execute.return_value = SimpleNamespace(data=[{"role": "user", "transcript": "hello"}])
    sb = Mock()
    sb.table.side_effect = lambda name: {"sessions": sessions, "messages": messages}[name]
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_generate_conversation_title", AsyncMock(return_value="Friendly Greetings"))

    asyncio.run(main._assign_conversation_title("conversation-1"))

    sessions.update.assert_called_once_with({"title": "Friendly Greetings"})
    sessions.is_.assert_called_once_with("title", "null")


def test_assign_conversation_title_skips_conversations_without_user_turns(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock

    messages = Mock()
    for method in ("select", "eq", "order"):
        getattr(messages, method).return_value = messages
    messages.execute.return_value = SimpleNamespace(data=[])
    sb = Mock()
    sb.table.side_effect = lambda name: messages
    generate = AsyncMock(return_value="unused")
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_generate_conversation_title", generate)

    asyncio.run(main._assign_conversation_title("conversation-1"))

    generate.assert_not_called()


def test_delete_conversation_history_resets_pally_but_keeps_usage(monkeypatch):
    """대화 기록 삭제는 Pally 를 초기화하되 사용량·연속 학습일·업적은 남긴다.

    usage_daily 를 함께 지우면 기록 삭제로 무료 한도를 초기화할 수 있어 삭제 대상이 아니다.
    """
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from unittest.mock import Mock

    touched = []

    def table(name):
        touched.append(name)
        query = Mock()
        for method in ("delete", "update", "eq"):
            getattr(query, method).return_value = query
        query.execute.return_value = SimpleNamespace(data=[{"id": "conversation-1"}])
        tables[name] = query
        return query

    tables = {}
    sb = Mock()
    sb.table.side_effect = table
    sb.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="caller-id"))
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_SUPABASE_ENABLED", True)

    response = TestClient(main.app).delete("/api/conversations", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "deleted_conversations": 1}
    assert set(touched) == {"sessions", "profiles"}
    for kept in ("usage_daily", "streak_days", "activity_events", "daily_task_snapshots", "subscriptions"):
        assert kept not in touched
    tables["sessions"].delete.assert_called_once_with()
    tables["profiles"].update.assert_called_once()
    assert tables["profiles"].update.call_args[0][0]["traits"] == main._DEFAULT_TRAITS


def test_delete_conversation_history_requires_authentication():
    from fastapi.testclient import TestClient

    assert TestClient(main.app).delete("/api/conversations").status_code == 401


def test_default_traits_constant_matches_migration_default():
    """코드의 복원값과 DB 기본값(마이그레이션)이 같아야 한다."""
    frontend_default_axes = {"Formality": 50, "Energy": 30, "Intimacy": 20, "Humor": 10, "Curiosity": 15}

    assert main._DEFAULT_TRAITS == main._axes_to_traits(frontend_default_axes)


def test_app_imports():
    assert main.app is not None


def test_core_routes_present():
    paths = {getattr(r, "path", None) for r in main.app.routes}
    # 절대 사라지면 안 되는 핵심 비즈니스 엔드포인트. 새 라우트 추가는 자유.
    required = {
        "/api/health",
        "/api/onboarding",
        "/api/profile",
        "/api/profile/avatar",
        "/api/conversations",
        "/api/conversations/{conversation_id}/turns",
    }
    missing = required - paths
    assert not missing, f"core routes missing (merge clobber?): {sorted(missing)}"


def test_extract_avatar_normalizes_oauth_metadata():
    class User:
        user_metadata = {"picture": "https://example.com/avatar.png"}

    assert main._extract_avatar(User()) == "https://example.com/avatar.png"


def test_extract_avatar_returns_none_without_profile_picture():
    class User:
        user_metadata = {"name": "Pally user"}

    assert main._extract_avatar(User()) is None


def test_extract_avatar_requests_high_resolution_google_photo():
    class User:
        user_metadata = {"picture": "https://lh3.googleusercontent.com/a/example=s96-c"}

    assert main._extract_avatar(User()) == "https://lh3.googleusercontent.com/a/example=s512-c"


def test_extract_avatar_prefers_kakao_profile_image_over_thumbnail():
    class User:
        user_metadata = {
            "avatar_url": "https://k.kakaocdn.net/thumbnail.jpg",
            "kakao_account": {
                "profile": {
                    "profile_image_url": "https://k.kakaocdn.net/profile.jpg",
                    "thumbnail_image_url": "https://k.kakaocdn.net/thumbnail.jpg",
                },
            },
        }

    assert main._extract_avatar(User()) == "https://k.kakaocdn.net/profile.jpg"


def test_retrying_query_replays_attribute_chaining():
    """postgrest 의 `q.not_.is_(...)` 처럼 호출 없는 속성 체이닝도 그대로 재현돼야 한다.

    재시도 래퍼가 이 패턴을 못 다뤄 GET /api/conversations?status=completed 가
    500 로 죽은 적이 있다. 같은 회귀를 CI 에서 차단한다.
    """
    trace = []

    class FakeBuilder:
        @property
        def not_(self):
            trace.append("not_")
            return self

        def select(self, *args):
            trace.append("select")
            return self

        def eq(self, *args):
            trace.append("eq")
            return self

        def is_(self, column, value):
            trace.append(f"is_({column},{value})")
            return self

        def execute(self):
            trace.append("execute")
            return "RESULT"

    query = main._RetryingQuery(lambda: FakeBuilder())
    result = query.select("*").eq("user_id", "u").not_.is_("ended_at", "null").execute()

    assert result == "RESULT"
    assert trace == ["select", "eq", "not_", "is_(ended_at,null)", "execute"]


def test_should_retry_is_conservative_for_writes():
    """읽기는 전송 오류 전부 재시도하되, 쓰기는 서버가 처리하지 않은 것이 확실한
    실패만 재시도한다 (중복 실행 방지)."""
    import httpx

    assert main._should_retry(httpx.ReadTimeout("x"), is_write=False) is True
    assert main._should_retry(httpx.ReadTimeout("x"), is_write=True) is False
    assert main._should_retry(httpx.ConnectError("x"), is_write=True) is True
    assert main._should_retry(ValueError("x"), is_write=False) is False


def test_should_not_retry_writes_on_ambiguous_protocol_errors():
    """A protocol error does not prove that the server skipped the mutation."""
    import httpx

    assert main._should_retry(httpx.RemoteProtocolError("goaway"), is_write=True) is False
    assert main._should_retry(httpx.RemoteProtocolError("goaway"), is_write=False) is True


def test_retrying_query_does_not_replay_write_after_protocol_error():
    """A lost response must not cause a second mutation."""
    import httpx
    import pytest

    attempts = []

    class FlakyBuilder:
        def insert(self, *args, **kwargs):
            return self

        def execute(self):
            attempts.append(1)
            if len(attempts) == 1:
                raise httpx.RemoteProtocolError("<ConnectionTerminated error_code:0>")
            return "SAVED"

    query = main._RetryingQuery(lambda: FlakyBuilder())

    with pytest.raises(httpx.RemoteProtocolError):
        query.insert({"a": 1}).execute()
    assert len(attempts) == 1


def test_rpc_claims_are_never_replayed_after_lost_responses(monkeypatch):
    import httpx
    import pytest
    from types import SimpleNamespace

    for error_type in (httpx.ReadTimeout, httpx.RemoteProtocolError):
        for params in (None, {"p_order_id": "test-order"}):
            attempts = []

            class CommittedClaim:
                def execute(self):
                    attempts.append(1)
                    if len(attempts) == 1:
                        raise error_type("Claim committed, response lost")
                    return SimpleNamespace(data=False)

            class Client:
                def rpc(self, *args):
                    return CommittedClaim()

            monkeypatch.setattr(main, "_get_supabase_raw", lambda: Client())
            with pytest.raises(error_type):
                main._RetryingSupabase().rpc("billing_claim_approval", params).execute()
            assert len(attempts) == 1


def test_rpc_retries_only_connection_establishment_failures(monkeypatch):
    import httpx

    attempts = []

    class Claim:
        def execute(self):
            attempts.append(1)
            if len(attempts) == 1:
                raise httpx.ConnectTimeout("Not sent")
            return "CLAIMED"

    class Client:
        def rpc(self, *args):
            return Claim()

    monkeypatch.setattr(main, "_get_supabase_raw", lambda: Client())
    monkeypatch.setattr(main, "_reset_supabase_client", lambda: None)
    assert main._RetryingSupabase().rpc("billing_claim_approval", {}).execute() == "CLAIMED"
    assert len(attempts) == 2


def test_conversation_turns_restore_user_before_pally_for_equal_timestamps():
    messages = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "role": "pally",
            "transcript": "That's great you're focused on your project!",
            "feedback": None,
            "created_at": "2026-09-06T10:00:00+00:00",
        },
        {
            "id": "00000000-0000-0000-0000-000000000002",
            "role": "user",
            "transcript": "just working on my project",
            "feedback": [],
            "created_at": "2026-09-06T10:00:00+00:00",
        },
    ]

    assert main._conversation_turns(messages) == [
        {
            "id": "00000000-0000-0000-0000-000000000002",
            "sequence": 1,
            "status": "completed",
            "user_transcript": "just working on my project",
            "pally_text": "That's great you're focused on your project!",
            "feedback": [],
            "feedback_pending": False,
            "created_at": "2026-09-06T10:00:00+00:00",
        }
    ]


# ── Opener — Pally 가 먼저 거는 말 ────────────────────────────────────────────


def _opener_client(monkeypatch, *, session, first_message, text="Hey! What music do you like?",
                   patch_generate=True):
    """오프너 테스트용 TestClient. DB·모델·TTS 를 끊고 라우트 로직만 본다."""
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from unittest.mock import Mock

    inserted = []
    sb = Mock()
    sb.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="caller-id"))

    def table(name):
        """messages 질의 2종을 구분한다: role=user 존재 확인, 그리고 첫 메시지 조회."""
        query = Mock()
        filters = []
        for method in ("select", "order", "limit", "neq", "in_"):
            getattr(query, method).return_value = query

        def eq(column, value):
            filters.append((column, value))
            return query

        query.eq.side_effect = eq

        def execute():
            user_probe = ("role", "user") in filters
            rows = [first_message] if first_message else []
            if user_probe:
                rows = [r for r in rows if r["role"] == "user"]
            return SimpleNamespace(data=rows)

        query.execute.side_effect = execute
        query.insert.side_effect = lambda row: inserted.append((name, row)) or query
        return query

    sb.table.side_effect = table
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_SUPABASE_ENABLED", True)
    monkeypatch.setattr(main, "_owned_session", lambda *_: session)
    monkeypatch.setattr(main, "_carried_over_axes", lambda *_: None)
    monkeypatch.setattr(main, "_recent_session_texts", lambda *_: [])

    async def fake_generate(axes, level, recent_texts):
        calls.append((axes, level, recent_texts))
        return text

    calls = []
    if patch_generate:  # False 면 실제 재시도 로직을 그대로 쓴다
        monkeypatch.setattr(main, "_generate_opener_text", fake_generate)
    return TestClient(main.app), inserted, calls


def _tts(monkeypatch, audio="BASE64AUDIO"):
    async def fake_tts(text, *_args, **_kwargs):
        if audio is None:
            raise RuntimeError("tts down")
        return audio
    monkeypatch.setattr(main, "_call_google_tts", fake_tts)


_OPENER_URL = "/api/conversations/conversation-1/opener"
_OPENER_HEADERS = {"Authorization": "Bearer test", "Idempotency-Key": "key-1"}


def test_opener_saves_pally_message_and_returns_audio(monkeypatch):
    """오프너는 role=pally 메시지로 저장되고, 사용량은 차감하지 않는다."""
    client, inserted, calls = _opener_client(
        monkeypatch, session={"id": "conversation-1", "level": "A2", "ended_at": None}, first_message=None
    )
    _tts(monkeypatch)
    reserved = []
    monkeypatch.setattr(main, "_reserve_turn", lambda *a, **k: reserved.append(a) or 1)

    response = client.post(_OPENER_URL, headers=_OPENER_HEADERS)

    assert response.status_code == 201
    assert response.json() == {
        "text": "Hey! What music do you like?", "audio": "BASE64AUDIO", "warnings": [],
    }
    assert [name for name, _ in inserted] == ["messages"]
    row = inserted[0][1]
    assert row["role"] == "pally" and row["session_id"] == "conversation-1"
    assert row["transcript"] == "Hey! What music do you like?"
    assert row["axes"] is None  # axes 는 user 발화의 것. 오프너에는 없다
    assert reserved == []  # quota 차감 없음
    # 축 출발점은 완료 대화가 없을 때 첫 Pally 와 같은 _INITIAL_AXES, 레벨은 세션 레벨
    assert calls == [(dict(main._INITIAL_AXES), "A2", [])]


def test_opener_is_refused_once_the_user_has_spoken_even_if_one_is_saved(monkeypatch):
    """저장된 오프너가 있어도 발화가 시작된 뒤에는 다시 읽어주지 않는다.

    읽어주면 Pally 가 대화 중간에 첫인사를 반복한다.
    """
    client, inserted, calls = _opener_client(
        monkeypatch, session={"id": "conversation-1", "level": "B1", "ended_at": None},
        first_message={"role": "user", "transcript": "I ate pizza"},
    )
    _tts(monkeypatch)

    response = client.post(_OPENER_URL, headers=_OPENER_HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conversation_started"
    assert inserted == [] and calls == []


def test_opener_is_idempotent_without_calling_the_model_again(monkeypatch):
    """다시 호출하면 저장된 오프너를 쓴다 — 모델 재호출·중복 저장 없음."""
    saved = {"role": "pally", "transcript": "Hey! Seen any good shows?"}
    client, inserted, calls = _opener_client(
        monkeypatch, session={"id": "conversation-1", "level": "B1", "ended_at": None}, first_message=saved
    )
    _tts(monkeypatch)

    response = client.post(_OPENER_URL, headers=_OPENER_HEADERS)

    assert response.status_code == 201
    assert response.json()["text"] == "Hey! Seen any good shows?"
    assert inserted == [] and calls == []


def test_opener_rejected_after_a_user_turn_or_on_a_closed_conversation(monkeypatch):
    """뒤늦게 오프너를 끼워 넣지 않는다: 사용자 발화가 있거나 끝난 대화면 409."""
    client, inserted, _ = _opener_client(
        monkeypatch,
        session={"id": "conversation-1", "level": "B1", "ended_at": None},
        first_message={"role": "user", "transcript": "I ate pizza"},
    )
    _tts(monkeypatch)
    response = client.post(_OPENER_URL, headers=_OPENER_HEADERS)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conversation_started"

    client, _, _ = _opener_client(
        monkeypatch,
        session={"id": "conversation-1", "level": "B1", "ended_at": "2026-10-05T00:00:00Z"},
        first_message=None,
    )
    _tts(monkeypatch)
    response = client.post(_OPENER_URL, headers=_OPENER_HEADERS)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conversation_closed"
    assert inserted == []


def test_opener_tts_failure_keeps_the_text_and_warns(monkeypatch):
    """TTS 실패는 턴과 같게 non-fatal: 텍스트는 주고 audio=null + tts_failed."""
    client, inserted, _ = _opener_client(
        monkeypatch, session={"id": "conversation-1", "level": "B1", "ended_at": None}, first_message=None
    )
    _tts(monkeypatch, audio=None)

    response = client.post(_OPENER_URL, headers=_OPENER_HEADERS)

    assert response.status_code == 201
    body = response.json()
    assert body["audio"] is None and body["text"]
    assert [w["code"] for w in body["warnings"]] == ["tts_failed"]
    assert len(inserted) == 1  # 저장은 됐으므로 재호출이 모델을 다시 부르지 않는다


def test_opener_requires_authentication_and_idempotency_key(monkeypatch):
    from fastapi.testclient import TestClient

    # 인증은 멱등 키보다 먼저 막힌다 (토큰 없이는 라우트 본문에 닿지 않는다)
    assert TestClient(main.app).post(_OPENER_URL).status_code == 401

    client, inserted, calls = _opener_client(
        monkeypatch, session={"id": "conversation-1", "level": "B1", "ended_at": None}, first_message=None
    )
    _tts(monkeypatch)
    response = client.post(_OPENER_URL, headers={"Authorization": "Bearer test"})
    assert response.status_code == 422
    assert inserted == [] and calls == []


def test_opener_failure_does_not_store_a_fallback_line(monkeypatch):
    """모델이 두 번 다 실패하면 폴백 문구를 저장하지 않고 503 (§6 #3)."""
    from ai.opener import OpenerRejected

    client, inserted, _ = _opener_client(
        monkeypatch, session={"id": "conversation-1", "level": "B1", "ended_at": None},
        first_message=None, patch_generate=False,
    )
    _tts(monkeypatch)
    attempts = []

    def always_rejected(*_args, **_kwargs):
        attempts.append(1)
        raise OpenerRejected("no_closing_question")

    monkeypatch.setattr(main, "generate_opener", always_rejected)

    response = client.post(_OPENER_URL, headers=_OPENER_HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "opener_failed"
    assert len(attempts) == 2  # 1회 재시도
    assert inserted == []


def test_opener_retries_once_and_keeps_a_valid_second_try(monkeypatch):
    """첫 호출이 규칙을 깨도 재시도가 성공하면 그 결과를 저장한다."""
    from ai.opener import OpenerRejected

    client, inserted, _ = _opener_client(
        monkeypatch, session={"id": "conversation-1", "level": "B1", "ended_at": None},
        first_message=None, patch_generate=False,
    )
    _tts(monkeypatch)
    results = [OpenerRejected("too_long"), "Hey! How was your day?"]

    def flaky(*_args, **_kwargs):
        outcome = results.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(main, "generate_opener", flaky)

    response = client.post(_OPENER_URL, headers=_OPENER_HEADERS)

    assert response.status_code == 201
    assert response.json()["text"] == "Hey! How was your day?"
    assert inserted[0][1]["transcript"] == "Hey! How was your day?"


# ── Daily tasks — 오프너만 있는 대화는 "대화했다"로 세지 않는다 ───────────────


class _FakeAchievementQuery:
    """_gather_achievement_context 가 던지는 질의 4종만 구분해 돌려주는 가짜 쿼리."""

    def __init__(self, table, data):
        self.table = table
        self.data = data
        self.columns = ""
        self.filters = []

    def select(self, columns):
        self.columns = columns
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def in_(self, column, values):
        self.filters.append((column, tuple(values)))
        return self

    def gte(self, *_):
        return self

    def lt(self, *_):
        return self

    def order(self, *_, **__):
        return self

    def limit(self, *_):
        return self

    def execute(self):
        from types import SimpleNamespace

        if self.table == "messages":
            # select("session_id") + role=user → 전체 기간 발화 세션 / 그 외 → 오늘 메시지
            key = "spoken" if self.columns.strip() == "session_id" else "today"
            return SimpleNamespace(data=self.data[key])
        return SimpleNamespace(data=self.data.get(self.table, []))


def _achievement_ctx(sessions, spoken_ids, today_msgs):
    from unittest.mock import Mock

    date_kst = main._kst_date()
    data = {
        "sessions": sessions,
        "spoken": [{"session_id": sid} for sid in spoken_ids],
        "today": today_msgs,
        "activity_events": [],
        "usage_daily": [],
    }
    sb = Mock()
    sb.table.side_effect = lambda name: _FakeAchievementQuery(name, data)
    return sb, main._gather_achievement_context(sb, "user-1", date_kst), date_kst


def _today_window():
    return main._kst_day_window_utc(main._kst_date())


def test_daily_tasks_do_not_count_a_conversation_the_user_never_spoke_in():
    """시작 버튼만 눌러도 Pally 오프너로 세션이 생기므로, 세션 존재만으로 판정하면
    한 마디도 하지 않고 A1 이 달성된다. 발화가 있는 대화만 세야 한다."""
    start, _end = _today_window()
    opener_only = {"id": "s-opener", "created_at": start, "ended_at": start, "reopened_at": None}

    sb, ctx, date_kst = _achievement_ctx([opener_only], spoken_ids=[], today_msgs=[])

    assert ctx["sessions_today"] == [] and ctx["completed_today"] == []
    assert main._eval_task(sb, "user-1", date_kst, "A1", ctx) is False  # 오늘 대화 시작
    assert main._eval_task(sb, "user-1", date_kst, "A6", ctx) is False  # 오늘 대화 완료
    assert main._eval_task(sb, "user-1", date_kst, "E3", ctx) is False  # 이번 주 첫 대화


def test_daily_tasks_count_a_conversation_once_the_user_speaks():
    start, _end = _today_window()
    spoke = {"id": "s-spoke", "created_at": start, "ended_at": start, "reopened_at": None}
    opener_only = {"id": "s-opener", "created_at": start, "ended_at": start, "reopened_at": None}
    msgs = [{"session_id": "s-spoke", "role": "user", "transcript": "i went to the park",
             "axes": None, "character": None, "created_at": start, "feedback": None}]

    sb, ctx, date_kst = _achievement_ctx([spoke, opener_only], spoken_ids=["s-spoke"], today_msgs=msgs)

    assert [s["id"] for s in ctx["sessions_today"]] == ["s-spoke"]
    assert main._eval_task(sb, "user-1", date_kst, "A1", ctx) is True
    assert main._eval_task(sb, "user-1", date_kst, "A6", ctx) is True
    assert main._eval_task(sb, "user-1", date_kst, "E3", ctx) is True
    # 발화한 대화는 1개뿐 → 세션 2개 과제는 오프너만 있는 대화로 채워지지 않는다
    assert main._eval_task(sb, "user-1", date_kst, "A4", ctx) is False


def test_a6_counts_a_conversation_spoken_yesterday_but_completed_today():
    """발화는 어제, 종료는 오늘인 대화도 A6 대상이다 — 발화 판정을 오늘로 좁히면 안 된다."""
    start, _end = _today_window()
    session = {"id": "s-old", "created_at": "2026-01-01T00:00:00+00:00", "ended_at": start, "reopened_at": None}

    sb, ctx, date_kst = _achievement_ctx([session], spoken_ids=["s-old"], today_msgs=[])

    assert [s["id"] for s in ctx["completed_today"]] == ["s-old"]
    assert main._eval_task(sb, "user-1", date_kst, "A6", ctx) is True


def test_opener_only_conversations_do_not_fill_the_weekly_streak_tasks():
    """E2(이번 주 3일)가 시작만 누른 날로 채워지지 않는다."""
    from datetime import datetime, timedelta

    from main import _KST

    today = datetime.now(_KST)
    monday = today - timedelta(days=today.weekday())
    sessions, spoken = [], []
    for day in range(3):
        at = (monday + timedelta(days=day)).isoformat()
        sessions.append({"id": f"s-open-{day}", "created_at": at, "ended_at": None, "reopened_at": None})
    for day in range(2):  # 그중 2일만 실제로 말했다
        at = (monday + timedelta(days=day)).isoformat()
        sessions.append({"id": f"s-spoke-{day}", "created_at": at, "ended_at": None, "reopened_at": None})
        spoken.append(f"s-spoke-{day}")

    sb, ctx, date_kst = _achievement_ctx(sessions, spoken_ids=spoken, today_msgs=[])

    assert len(ctx["week_conv_dates"]) == 2
    assert main._eval_task(sb, "user-1", date_kst, "E2", ctx) is False


# ── 현재 Pally 상태(current_axes) — 홈·마이페이지·다음 대화가 같은 값을 쓴다 ──


def test_carried_over_axes_skips_conversations_without_utterances_in_one_query():
    """axes 는 사용자 발화에만 붙으므로 오프너만 있는 대화는 조회에서 빠진다.

    완료 대화 수에 상한을 두지 않는다 — 시작만 누르고 나간 대화가 쌓여도 누적
    체인이 끊기면 안 된다. 그래서 세션 id 를 in_() 으로 넘기지 않고 임베딩한다.
    """
    from types import SimpleNamespace
    from unittest.mock import Mock

    calls = {"eq": [], "not_is": [], "order": [], "limit": [], "in_": []}
    query = Mock()
    query.select.return_value = query
    query.eq.side_effect = lambda c, v: calls["eq"].append((c, v)) or query
    query.not_.is_.side_effect = lambda c, v: calls["not_is"].append((c, v)) or query
    query.order.side_effect = lambda c, **kw: calls["order"].append((c, kw.get("desc"))) or query
    query.limit.side_effect = lambda n: calls["limit"].append(n) or query
    query.in_.side_effect = lambda c, v: calls["in_"].append(c) or query
    query.execute.return_value = SimpleNamespace(data=[{"axes": {"Formality": 20}}])

    sb = Mock()
    sb.table.return_value = query

    assert main._carried_over_axes(sb, "user-1") == {"Formality": 20}
    sb.table.assert_called_once_with("messages")
    assert ("role", "user") in calls["eq"]
    assert ("sessions.user_id", "user-1") in calls["eq"]
    assert ("axes", "null") in calls["not_is"]            # 발화에 축이 붙은 것만
    assert ("sessions.ended_at", "null") in calls["not_is"]  # 끝낸 대화만
    assert calls["order"] == [("sessions(ended_at)", True), ("created_at", True)]
    assert calls["limit"] == [1]
    assert calls["in_"] == []  # 세션 목록을 넘기지 않는다 = 개수 상한 없음

    query.execute.return_value = SimpleNamespace(data=[])
    assert main._carried_over_axes(sb, "user-1") is None


def test_profile_carries_pallys_current_look(monkeypatch):
    """홈이 그리는 Pally 와 마이페이지 태그가 같은 값에서 나오게 프로필이 축을 담는다."""
    from types import SimpleNamespace
    from unittest.mock import Mock

    row = {
        "id": "user-1", "display_name": "민주", "english_level": "B1",
        "onboarding_completed": True, "traits": ["acquaint"],
        "created_at": "2026-10-01T00:00:00Z", "updated_at": None,
    }
    user = SimpleNamespace(id="user-1", user_metadata={}, app_metadata={})
    sb = Mock()

    spoken = {"Formality": 34, "Energy": 37, "Intimacy": 22, "Humor": 11, "Curiosity": 21}
    monkeypatch.setattr(main, "_carried_over_axes", lambda *_: spoken)
    assert main._profile_payload(sb, row, user)["current_axes"] == spoken

    # 완료한 대화가 없으면 홈의 첫 Pally 와 같은 값
    monkeypatch.setattr(main, "_carried_over_axes", lambda *_: None)
    assert main._profile_payload(sb, row, user)["current_axes"] == main._INITIAL_AXES
def test_stt_keeps_every_segment_split_at_pauses():
    # latest_long splits "Hi Pally. (pause) Yesterday I went..." into two results.
    results = [
        {"alternatives": [{"transcript": "hi Pali", "confidence": 0.9}]},
        {"alternatives": [{"transcript": " yesterday I went to the park", "confidence": 0.8}]},
    ]
    assert main._join_stt_results(results) == ("hi Pali yesterday I went to the park", 0.8)


def test_first_pally_axes_match_the_default_traits():
    """신규 사용자의 홈 Pally(프로필 current_axes)와 마이페이지 기본 태그는 같은 모습이어야 한다."""
    assert main._axes_to_traits(main._INITIAL_AXES) == main._DEFAULT_TRAITS
    # 프론트 DEFAULT_AXES (frontend/lib/types/character.ts)
    assert main._INITIAL_AXES == {"Formality": 50, "Energy": 30, "Intimacy": 20, "Humor": 10, "Curiosity": 15}
