"""Retry session review extraction from persisted, unfinished message rows.

NULL user feedback plus feedback_requested_at marks durable pending work; [] is
a completed extraction with no corrections. Completion marks exact user rows
atomically, so reopening and clock skew cannot include new active turns. No UI
state or conversation prompt is changed here. The caller supplies its existing
turn pairing function so the worker and History use the same source pairs.

Locks/backoff are process-local. Multiple replicas may duplicate model requests;
conditional writes protect stored results, not exactly-once provider billing.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid

from ai.generate_feedback import generate_session_feedback

_MESSAGE_PAGE_SIZE = 500
_SESSION_PAGE_SIZE = 10
_RETRY_SECONDS = 30.0
_MAX_RETRY_SECONDS = 300.0
_guard = threading.Lock()
_inflight: set[str] = set()
_retry_at: dict[str, float] = {}
_failures: dict[str, int] = {}


def _claim(conversation_id: str) -> bool:
    with _guard:
        if conversation_id in _inflight or time.monotonic() < _retry_at.get(conversation_id, 0):
            return False
        _inflight.add(conversation_id)
        return True


def _release(conversation_id: str, failed: bool) -> None:
    with _guard:
        _inflight.discard(conversation_id)
        if failed:
            attempts = min(_failures.get(conversation_id, 0) + 1, 5)
            _failures[conversation_id] = attempts
            _retry_at[conversation_id] = time.monotonic() + min(
                _RETRY_SECONDS * (2 ** (attempts - 1)), _MAX_RETRY_SECONDS,
            )
        else:
            _failures.pop(conversation_id, None)
            _retry_at.pop(conversation_id, None)


def _session_messages(db, conversation_id: str) -> list[dict]:
    messages = []
    offset = 0
    while True:
        response = (db.table("messages")
                    .select("id,role,transcript,feedback,feedback_requested_at,created_at")
                    .eq("session_id", conversation_id)
                    .order("created_at").order("id")
                    .range(offset, offset + _MESSAGE_PAGE_SIZE - 1).execute())
        page = response.data or []
        messages.extend(page)
        if len(page) < _MESSAGE_PAGE_SIZE:
            return messages
        offset += len(page)


def _with_stable_ids(conversation_id: str, turn_id: str, items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        # Explanation edits do not change the identity of an existing correction.
        identity = json.dumps([
            "pally-session-feedback-v1", conversation_id, turn_id,
            item["original"], item["corrected"],
        ], ensure_ascii=False, separators=(",", ":"))
        result.append({**item, "id": str(uuid.uuid5(uuid.NAMESPACE_URL, identity))})
    return result


def process_session(get_db, conversation_id: str, build_turns) -> dict:
    """Process finalized pending pairs, without changing closed/active state.

    get_db is a zero-argument factory; build_turns is the History pairing helper.
    Only user rows explicitly marked by the completion transaction are eligible.
    A marked closed segment may finish while its session is active again; new,
    unmarked turns are never extracted. No app/DB timestamp comparison is used.
    Returns processed/failed/skipped counts.
    """
    counts = {"processed": 0, "failed": 0, "skipped": 0}
    if not _claim(conversation_id):
        counts["skipped"] = 1
        return counts
    retry = False
    try:
        db = get_db()
        response = (db.table("sessions").select("id,level")
                    .eq("id", conversation_id).execute())
        if not response.data:
            return counts  # Deleted sessions have no work to retain.
        session = response.data[0]
        messages = _session_messages(db, conversation_id)
        pending_ids = {
            message["id"] for message in messages
            if message["role"] == "user" and message.get("feedback") is None
            and message.get("feedback_requested_at") is not None
        }
        pairs = [
            {"turn_id": turn["id"], "user_transcript": turn["user_transcript"],
             "pally_text": turn["pally_text"]}
            for turn in build_turns(messages)
            if turn["id"] in pending_ids
            and turn.get("user_transcript", "") and turn.get("pally_text", "")
        ]
        counts["skipped"] = len(pending_ids) - len(pairs)
        if not pairs:
            return counts  # Incomplete pairs stay NULL, never become "no correction".
        extracted = generate_session_feedback(pairs, session["level"])
        ids = [entry["turn_id"] for entry in extracted]
        if len(ids) != len(set(ids)) or set(ids) != {pair["turn_id"] for pair in pairs}:
            raise ValueError("Feedback extraction returned mismatched turn IDs")
        for entry in extracted:
            if entry["failed"]:
                counts["failed"] += 1
                retry = True
                continue
            try:
                feedback = _with_stable_ids(conversation_id, entry["turn_id"], entry["items"])
                saved = (db.table("messages").update({"feedback": feedback})
                         .eq("session_id", conversation_id).eq("id", entry["turn_id"])
                         .eq("role", "user").is_("feedback", "null")
                         .not_.is_("feedback_requested_at", "null").execute())
                if saved.data:
                    counts["processed"] += 1
                else:
                    counts["skipped"] += 1  # Another worker completed it, or it was deleted.
            except Exception as exc:
                counts["failed"] += 1
                retry = True
                logging.warning("Session feedback save failed: %s", type(exc).__name__)
        return counts
    except Exception as exc:
        retry = True
        counts["failed"] += 1
        logging.warning("Session feedback processing failed: %s", type(exc).__name__)
        return counts
    finally:
        _release(conversation_id, retry)


def _scan_page(get_db, build_turns, cursor: str | None, should_stop) -> str | None:
    query = (get_db().table("messages").select("id,session_id")
             .eq("role", "user").is_("feedback", "null")
             .not_.is_("feedback_requested_at", "null")
             .order("id").limit(_SESSION_PAGE_SIZE))
    if cursor:
        query = query.gt("id", cursor)
    rows = query.execute().data or []
    seen_sessions = set()
    for row in rows:
        if should_stop():
            break
        if row["session_id"] not in seen_sessions:
            seen_sessions.add(row["session_id"])
            process_session(get_db, row["session_id"], build_turns)
    # Advance even after extraction failures; a bad early session cannot starve
    # later rows. Once a scan ends, start again to discover new pending rows.
    return rows[-1]["id"] if len(rows) == _SESSION_PAGE_SIZE else None


async def worker(get_db, stop: asyncio.Event, build_turns) -> None:
    """Rediscover pending rows on startup and periodically, after process loss."""
    cursor = None
    while not stop.is_set():
        try:
            cursor = await asyncio.to_thread(_scan_page, get_db, build_turns, cursor, stop.is_set)
        except Exception as exc:
            logging.warning("Session feedback scan failed: %s", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=_RETRY_SECONDS)
        except asyncio.TimeoutError:
            continue
