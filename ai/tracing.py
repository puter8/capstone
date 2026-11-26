"""Langfuse tracing for Gemini generateContent calls.

With LANGFUSE_PUBLIC_KEY unset the SDK disables itself: it logs one warning,
records nothing and raises nothing, so tests, CI and machines without keys run
unchanged. Spans are exported from a background thread (about 0.6 ms added to
the request path, measured 2026-11-26) and the SDK flushes them at exit.

An exception raised inside `gemini_generation` propagates unchanged; the SDK
marks the observation ERROR with the exception text as its status message.
"""

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from langfuse import Langfuse, get_client
from opentelemetry import trace

# Gemini usageMetadata key -> Langfuse usage_details key.
_USAGE_KEYS = {
    "promptTokenCount": "input",
    "candidatesTokenCount": "output",
    "thoughtsTokenCount": "reasoning",
    "totalTokenCount": "total",
}


_client: Langfuse | None = None
_client_lock = threading.Lock()


def _langfuse() -> Langfuse:
    """One client per process. Built lazily so scripts that load env files
    after import still pick up the keys. A disabled client is not cached by
    the SDK: each get_client() rebuilt it and logged the warning again."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = get_client()
    return _client


def init_tracing() -> None:
    """Build the client at startup. The first get_client() took 70-260 ms
    locally, which would otherwise land on the first traced request."""
    _langfuse()


@contextmanager
def gemini_generation(name: str, model: str) -> Iterator[None]:
    """Open a generation observation; record its details from inside with
    record_gemini_call. Wrap validation too, so a rejected output is kept
    on the ERROR observation."""
    with _langfuse().start_as_current_observation(name=name, as_type="generation", model=model):
        yield


def record_gemini_call(payload: dict, body: dict | None, output: str | None) -> None:
    """Attach the request body (never the URL or headers, which can carry the
    API key), the raw model text and the token usage to the current generation.

    A disabled client opens no span, and updating without one logs a warning
    on every call, so skip when no span is active."""
    if not trace.get_current_span().get_span_context().is_valid:
        return
    usage = None
    if body is not None and "usageMetadata" in body:
        meta = body["usageMetadata"]
        usage = {dst: meta[src] for src, dst in _USAGE_KEYS.items() if src in meta}
    _langfuse().update_current_generation(input=payload, output=output, usage_details=usage)


__all__ = ["gemini_generation", "init_tracing", "record_gemini_call"]
