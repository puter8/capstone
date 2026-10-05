"""STT v2 (Chirp 2) contract, auth caching, and error-handling regression tests."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import main


class _FakeCredentials:
    def __init__(self):
        self.valid = False
        self.token = None
        self.refresh_calls = 0

    def refresh(self, _request):
        self.refresh_calls += 1
        self.valid = True
        self.token = f"fake-token-{self.refresh_calls}"


@pytest.fixture(autouse=True)
def _reset_stt_singleton(monkeypatch):
    # _load_stt_credentials caches at module level; each test needs a clean slate.
    monkeypatch.setattr(main, "_stt_credentials", None)
    monkeypatch.setattr(main, "_stt_project_id", None)
    monkeypatch.setattr(main, "GOOGLE_STT_SA_JSON", json.dumps({"project_id": "test-project"}))
    monkeypatch.setattr(main, "GOOGLE_STT_REGION", "us-central1")


def _install_fake_credentials(monkeypatch):
    fake = _FakeCredentials()
    monkeypatch.setattr(
        main.gcp_service_account.Credentials,
        "from_service_account_info",
        classmethod(lambda cls, info, scopes: fake),
    )
    return fake


def _install_transport(monkeypatch, handler):
    """Patches the httpx.AsyncClient constructor (so TestClient's lifespan-created
    client is also mocked) and hands back one ready instance for direct calls
    that bypass the lifespan (no TestClient context)."""
    requests_seen = []
    original_client = httpx.AsyncClient

    def wrapped(request):
        requests_seen.append(request)
        return handler(request)

    def create_client(**kwargs):
        return original_client(transport=httpx.MockTransport(wrapped), **kwargs)

    monkeypatch.setattr(main.httpx, "AsyncClient", create_client)
    main.app.state.http_client = create_client()
    return requests_seen


def test_recognize_uses_chirp2_and_autodecoding(monkeypatch):
    _install_fake_credentials(monkeypatch)

    def handler(request):
        assert "/locations/us-central1/recognizers/_:recognize" in str(request.url)
        assert request.headers["authorization"] == "Bearer fake-token-1"
        body = json.loads(request.content)
        assert body["config"]["model"] == "chirp_2"
        assert body["config"]["autoDecodingConfig"] == {}
        assert body["config"]["languageCodes"] == ["en-US"]
        return httpx.Response(200, json={
            "results": [{"alternatives": [{"transcript": "she wants cookies", "confidence": 0.97}]}],
        })

    requests_seen = _install_transport(monkeypatch, handler)

    import asyncio
    transcript, confidence = asyncio.run(main._call_google_stt(b"fake-wav-bytes"))

    assert transcript == "she wants cookies"
    assert confidence == 0.97
    assert len(requests_seen) == 1


def test_token_is_cached_across_calls_until_invalid(monkeypatch):
    fake = _install_fake_credentials(monkeypatch)

    def handler(_request):
        return httpx.Response(200, json={"results": []})

    _install_transport(monkeypatch, handler)

    import asyncio
    asyncio.run(main._call_google_stt(b"a"))
    asyncio.run(main._call_google_stt(b"b"))

    # valid stays True after the first refresh, so the second call must not refresh again.
    assert fake.refresh_calls == 1


def test_empty_results_returns_empty_transcript(monkeypatch):
    _install_fake_credentials(monkeypatch)
    _install_transport(monkeypatch, lambda req: httpx.Response(200, json={"results": []}))

    import asyncio
    transcript, confidence = asyncio.run(main._call_google_stt(b"silence"))

    assert transcript == ""
    assert confidence == 0.0


def test_provider_error_raises(monkeypatch):
    _install_fake_credentials(monkeypatch)
    _install_transport(monkeypatch, lambda req: httpx.Response(500, text="boom"))

    import asyncio
    with pytest.raises(RuntimeError, match="Google STT error 500"):
        asyncio.run(main._call_google_stt(b"a"))


def test_missing_credentials_raises_without_network_call(monkeypatch):
    monkeypatch.setattr(main, "GOOGLE_STT_SA_JSON", "")

    import asyncio
    with pytest.raises(RuntimeError, match="GOOGLE_STT_SA_JSON not configured"):
        asyncio.run(main._call_google_stt(b"a"))


def test_api_stt_endpoint_returns_transcript(monkeypatch):
    _install_fake_credentials(monkeypatch)
    _install_transport(monkeypatch, lambda req: httpx.Response(200, json={
        "results": [{"alternatives": [{"transcript": "hello", "confidence": 0.9}]}],
    }))

    with TestClient(main.app) as client:
        resp = client.post("/api/stt", files={"audio": ("test.wav", b"RIFF....WAVEfmt ", "audio/wav")})

    assert resp.status_code == 200
    assert resp.json() == {"transcript": "hello", "confidence": 0.9}


def test_api_stt_endpoint_502s_on_provider_failure(monkeypatch):
    _install_fake_credentials(monkeypatch)
    _install_transport(monkeypatch, lambda req: httpx.Response(500, text="boom"))

    with TestClient(main.app) as client:
        resp = client.post("/api/stt", files={"audio": ("test.wav", b"data", "audio/wav")})

    assert resp.status_code == 502


def test_api_stt_rejects_empty_audio(monkeypatch):
    _install_fake_credentials(monkeypatch)

    with TestClient(main.app) as client:
        resp = client.post("/api/stt", files={"audio": ("test.wav", b"", "audio/wav")})

    assert resp.status_code == 400
