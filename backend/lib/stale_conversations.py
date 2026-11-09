"""Close conversations the user walked away from without pressing End.

History lists only completed conversations, and review feedback and titles are
generated on completion. A conversation abandoned by closing the tab stayed
active forever: it never appeared in History and never got feedback. This
worker completes such conversations through the same path as /complete.

A conversation is stale when its latest activity (last message, reopen, or
creation) is older than _IDLE_SECONDS. Reopening a conversation refreshes it.
Completion is idempotent and guarded by reopen_count in the RPC, so a user who
returns mid-close gets a clean 409 instead of a half-closed session.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

_IDLE_SECONDS = 60 * 60
_SCAN_INTERVAL_SECONDS = 10 * 60
_PAGE_SIZE = 50


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _last_activity(db, session: dict) -> datetime:
    latest = (db.table("messages").select("created_at")
              .eq("session_id", session["id"])
              .order("created_at", desc=True).limit(1).execute()).data
    candidates = [
        _parse(session.get("created_at")),
        _parse(session.get("reopened_at")),
        _parse(latest[0]["created_at"]) if latest else None,
    ]
    return max(moment for moment in candidates if moment is not None)


def close_stale(get_db, complete: Callable[[object, dict, str], None],
                should_stop: Callable[[], bool], now: datetime | None = None) -> int:
    """Complete every active conversation idle for _IDLE_SECONDS. Returns the count closed.

    complete(db, session, user_id) runs the shared completion path and schedules
    feedback/title work; one failing conversation never blocks the others.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=_IDLE_SECONDS)
    db = get_db()
    closed = 0
    offset = 0
    while not should_stop():
        # Only sessions created before the cutoff can be idle past it.
        page = (db.table("sessions")
                .select("id,user_id,created_at,reopened_at,reopen_count,ended_at,axes_contribution,title")
                .is_("ended_at", "null").not_.is_("user_id", "null")
                .lt("created_at", cutoff.isoformat())
                .order("created_at").range(offset, offset + _PAGE_SIZE - 1).execute()).data or []
        closed_here = 0
        for session in page:
            if should_stop():
                return closed
            try:
                if _last_activity(db, session) >= cutoff:
                    continue
                complete(db, session, session["user_id"])
                closed += 1
                closed_here += 1
            except Exception as exc:
                # Includes a user reopening/resuming mid-close (409): retried next scan.
                logging.warning("Stale conversation close failed: %s", type(exc).__name__)
        if len(page) < _PAGE_SIZE:
            return closed
        # Closed rows drop out of the "ended_at is null" result, so skip only the rows still open.
        offset += len(page) - closed_here
    return closed


async def worker(get_db, stop: asyncio.Event, complete) -> None:
    while not stop.is_set():
        try:
            closed = await asyncio.to_thread(close_stale, get_db, complete, stop.is_set)
            if closed:
                logging.info("Closed %d stale conversation(s)", closed)
        except Exception as exc:
            logging.warning("Stale conversation scan failed: %s", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=_SCAN_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue
