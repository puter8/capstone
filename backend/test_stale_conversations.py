"""Abandoned active conversations are completed through the shared completion path."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.lib import stale_conversations as stale

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).isoformat()


class Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.filters, self.window, self.maximum = [], None, None
        self.descending, self.negate = False, False

    def select(self, _fields):
        return self

    def eq(self, field, value):
        self.filters.append(lambda row: row.get(field) == value)
        return self

    def lt(self, field, value):
        self.filters.append(lambda row: row[field] < value)
        return self

    @property
    def not_(self):
        self.negate = True
        return self

    def is_(self, field, value):
        assert value == "null"
        negate, self.negate = self.negate, False
        self.filters.append(lambda row: (row.get(field) is None) != negate)
        return self

    def order(self, _field, desc=False):
        self.descending = desc
        return self

    def range(self, first, last):
        self.window = (first, last + 1)
        return self

    def limit(self, count):
        self.maximum = count
        return self

    def execute(self):
        rows = [row for row in self.db.rows[self.table] if all(f(row) for f in self.filters)]
        rows.sort(key=lambda row: row["created_at"], reverse=self.descending)
        if self.window:
            rows = rows[self.window[0]:self.window[1]]
        if self.maximum is not None:
            rows = rows[:self.maximum]
        return SimpleNamespace(data=[dict(row) for row in rows])


class DB:
    def __init__(self):
        self.rows = {"sessions": [], "messages": []}

    def table(self, name):
        return Query(self, name)

    def session(self, sid, created, *, reopened=None, ended=None, user="user-1", last_message=None):
        self.rows["sessions"].append({"id": sid, "user_id": user, "created_at": created,
                                      "reopened_at": reopened, "ended_at": ended, "reopen_count": 0})
        if last_message:
            self.rows["messages"].append({"id": f"{sid}-m", "session_id": sid, "created_at": last_message})


def closer(db, fail=()):
    closed = []

    def complete(_db, session, user_id):
        if session["id"] in fail:
            raise RuntimeError("conversation_changed")
        closed.append((session["id"], user_id))
        for row in db.rows["sessions"]:
            if row["id"] == session["id"]:
                row["ended_at"] = NOW.isoformat()
    return complete, closed


def test_only_conversations_idle_past_the_cutoff_are_completed():
    db = DB()
    db.session("abandoned", ago(180), last_message=ago(120))
    db.session("never-spoke", ago(90))
    db.session("talking", ago(180), last_message=ago(5))
    db.session("just-reopened", ago(600), reopened=ago(10), last_message=ago(500))
    db.session("young", ago(20))
    db.session("done", ago(300), ended=ago(200))
    db.session("legacy-orphan", ago(300), user=None)
    complete, closed = closer(db)

    assert stale.close_stale(lambda: db, complete, lambda: False, now=NOW) == 2
    assert sorted(closed) == [("abandoned", "user-1"), ("never-spoke", "user-1")]


def test_one_failure_does_not_stop_the_rest():
    db = DB()
    db.session("reopened-mid-close", ago(200), last_message=ago(150))
    db.session("abandoned", ago(190), last_message=ago(140))
    complete, closed = closer(db, fail={"reopened-mid-close"})

    assert stale.close_stale(lambda: db, complete, lambda: False, now=NOW) == 1
    assert closed == [("abandoned", "user-1")]


def test_closing_rows_does_not_skip_the_next_page(monkeypatch):
    monkeypatch.setattr(stale, "_PAGE_SIZE", 2)
    db = DB()
    for index in range(5):
        db.session(f"s{index}", ago(300 - index), last_message=ago(200))
    complete, closed = closer(db)

    assert stale.close_stale(lambda: db, complete, lambda: False, now=NOW) == 5
    assert sorted(sid for sid, _ in closed) == [f"s{i}" for i in range(5)]


def test_stale_completion_uses_the_shared_completion_path(monkeypatch):
    import asyncio
    import main

    calls = []
    monkeypatch.setattr(main, "_complete_session",
                        lambda sb, session, user_id: calls.append(("complete", session["id"], user_id))
                        or ({**session, "ended_at": NOW.isoformat(), "title": None}, []))
    monkeypatch.setattr(main.session_feedback, "process_session",
                        lambda _get_db, sid, _turns: calls.append(("feedback", sid)))

    async def fake_title(sid):
        calls.append(("title", sid))

    monkeypatch.setattr(main, "_assign_conversation_title", fake_title)

    async def scenario():
        complete = main._stale_completion(asyncio.get_running_loop())
        await asyncio.to_thread(complete, object(), {"id": "s1", "title": None}, "user-1")
        await asyncio.sleep(0)  # let the scheduled title coroutine run on this loop

    asyncio.run(scenario())
    assert calls == [("complete", "s1", "user-1"), ("feedback", "s1"), ("title", "s1")]


def test_stop_request_ends_the_scan():
    db = DB()
    db.session("abandoned", ago(180), last_message=ago(120))
    complete, closed = closer(db)

    assert stale.close_stale(lambda: db, complete, lambda: True, now=NOW) == 0
    assert closed == []
