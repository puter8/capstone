"""Durable review scheduling semantics, using an in-memory PostgREST boundary."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest

from backend.lib import session_feedback as review


CLOSED = "2026-10-05T10:00:00+00:00"
REOPENED = "2026-10-05T11:00:00+00:00"
EARLY = "2026-10-05T09:00:00+00:00"
LATE = "2026-10-05T12:00:00+00:00"


class Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.filters, self.orders = [], []
        self.window, self.maximum, self.changes = None, None, None
        self.negate = False

    def select(self, fields):
        return self

    def eq(self, field, value):
        self.filters.append(lambda row: row.get(field) == value)
        return self

    def gt(self, field, value):
        self.filters.append(lambda row: row[field] > value)
        return self

    @property
    def not_(self):
        self.negate = True
        return self

    def is_(self, field, value):
        assert value == "null"
        negate = self.negate
        self.negate = False
        self.filters.append(lambda row: (row.get(field) is None) != negate)
        return self

    def order(self, field):
        self.orders.append(field)
        return self

    def range(self, first, last):
        self.window = (first, last + 1)
        self.db.message_pages += 1
        return self

    def limit(self, count):
        self.maximum = count
        return self

    def update(self, changes):
        self.changes = changes
        return self

    def execute(self):
        rows = [row for row in self.db.rows[self.table] if all(test(row) for test in self.filters)]
        for field in reversed(self.orders):
            rows.sort(key=lambda row: row[field])
        if self.window:
            rows = rows[self.window[0]:self.window[1]]
        if self.maximum is not None:
            rows = rows[:self.maximum]
        if self.changes is not None:
            if self.db.fail_updates:
                raise RuntimeError("Persistence unavailable")
            for row in rows:
                row.update(deepcopy(self.changes))
            self.db.updated.extend(row["id"] for row in rows)
        return SimpleNamespace(data=deepcopy(rows))


class DB:
    def __init__(self, sessions=None):
        self.rows = {"sessions": sessions if sessions is not None else [session()], "messages": []}
        self.message_pages = 0
        self.fail_updates = False
        self.updated = []

    def table(self, name):
        return Query(self, name)

    def pair(self, turn_id="u1", at=EARLY, feedback=None, session_id="s1", complete=True, requested_at=CLOSED):
        self.rows["messages"].append({
            "id": turn_id, "session_id": session_id, "role": "user",
            "transcript": "she want cookies", "feedback": feedback, "created_at": at,
            "feedback_requested_at": requested_at,
        })
        if complete:
            self.rows["messages"].append({
                "id": f"{turn_id}-reply", "session_id": session_id, "role": "pally",
                "transcript": "She wants cookies? What kind?", "feedback": None, "created_at": at,
                "feedback_requested_at": None,
            })


def session(sid="s1", ended=CLOSED, reopened=None):
    return {"id": sid, "level": "B1", "ended_at": ended, "reopened_at": reopened}


def build_turns(messages):
    replies = {row["id"]: row for row in messages if row["role"] == "pally"}
    return [{
        "id": row["id"], "user_transcript": row["transcript"],
        "pally_text": replies.get(f'{row["id"]}-reply', {}).get("transcript"),
    } for row in messages if row["role"] == "user"]


def successful(pairs, level):
    assert level == "B1"
    return [{"turn_id": pair["turn_id"], "items": [{
        "original": "she want", "corrected": "She wants", "explanation_ko": "주어에 맞게 동사를 바꿔요.",
    }], "failed": False} for pair in pairs]


@pytest.fixture(autouse=True)
def isolated_worker(monkeypatch):
    review._inflight.clear()
    review._retry_at.clear()
    review._failures.clear()
    monkeypatch.setattr(review, "generate_session_feedback", successful)
    yield
    review._inflight.clear()
    review._retry_at.clear()
    review._failures.clear()


def test_closed_session_saves_review_and_existing_results_are_untouched():
    db = DB()
    db.pair()
    db.pair("u2", feedback=[])
    result = review.process_session(lambda: db, "s1", build_turns)
    assert result == {"processed": 1, "failed": 0, "skipped": 0}
    assert db.updated == ["u1"]
    assert db.rows["messages"][0]["feedback"][0]["id"]
    assert review.process_session(lambda: db, "s1", build_turns)["processed"] == 0


def test_new_active_session_unmarked_rows_are_never_extracted(monkeypatch):
    db = DB([session(ended=None)])
    db.pair(requested_at=None)
    monkeypatch.setattr(review, "generate_session_feedback", lambda *args: pytest.fail("Active session reached AI"))
    assert review.process_session(lambda: db, "s1", build_turns)["processed"] == 0
    assert db.updated == []


@pytest.mark.parametrize("new_turn_at", [EARLY, REOPENED, LATE])
def test_reopened_session_only_extracts_marked_rows_regardless_of_clock_skew(new_turn_at):
    db = DB([session(ended=None, reopened=REOPENED)])
    db.pair()
    db.pair("u2", at=new_turn_at, requested_at=None)
    review.process_session(lambda: db, "s1", build_turns)
    assert db.updated == ["u1"]
    assert next(row for row in db.rows["messages"] if row["id"] == "u2")["feedback"] is None


def test_later_completion_marks_new_rows_without_reprocessing_old_rows():
    db = DB([session(ended=LATE, reopened=REOPENED)])
    db.pair()
    db.pair("u2", at=REOPENED, requested_at=None)
    review.process_session(lambda: db, "s1", build_turns)
    assert db.updated == ["u1"]
    next(row for row in db.rows["messages"] if row["id"] == "u2")["feedback_requested_at"] = LATE
    review.process_session(lambda: db, "s1", build_turns)
    assert db.updated == ["u1", "u2"]


def test_incomplete_pair_stays_pending_and_never_becomes_empty_success(monkeypatch):
    db = DB()
    db.pair(complete=False)
    monkeypatch.setattr(review, "generate_session_feedback", lambda *args: pytest.fail("Incomplete pair reached AI"))
    assert review.process_session(lambda: db, "s1", build_turns)["skipped"] == 1
    assert db.rows["messages"][0]["feedback"] is None


def test_no_corrections_is_persisted_as_completed_empty_array(monkeypatch):
    db = DB()
    db.pair()
    monkeypatch.setattr(review, "generate_session_feedback", lambda pairs, level: [
        {"turn_id": pair["turn_id"], "items": [], "failed": False} for pair in pairs
    ])
    review.process_session(lambda: db, "s1", build_turns)
    assert db.rows["messages"][0]["feedback"] == []


def test_provider_failure_preserves_null_and_backoff_then_retries(monkeypatch):
    db = DB()
    db.pair()
    now = [100.0]
    calls = []
    monkeypatch.setattr(review.time, "monotonic", lambda: now[0])

    def fail(pairs, level):
        calls.append(pairs)
        return [{"turn_id": "u1", "items": [], "failed": True}]

    monkeypatch.setattr(review, "generate_session_feedback", fail)
    assert review.process_session(lambda: db, "s1", build_turns)["failed"] == 1
    assert db.rows["messages"][0]["feedback"] is None
    assert review.process_session(lambda: db, "s1", build_turns)["skipped"] == 1
    assert len(calls) == 1
    now[0] += 31
    monkeypatch.setattr(review, "generate_session_feedback", successful)
    assert review.process_session(lambda: db, "s1", build_turns)["processed"] == 1


def test_save_failure_preserves_null_for_retry():
    db = DB()
    db.pair()
    db.fail_updates = True
    assert review.process_session(lambda: db, "s1", build_turns)["failed"] == 1
    assert db.rows["messages"][0]["feedback"] is None


def test_pending_rows_are_rediscovered_after_process_state_is_lost(monkeypatch):
    db = DB()
    db.pair()
    monkeypatch.setattr(review, "generate_session_feedback", lambda *args: [{"turn_id": "u1", "items": [], "failed": True}])
    review.process_session(lambda: db, "s1", build_turns)
    review._retry_at.clear()
    review._failures.clear()
    monkeypatch.setattr(review, "generate_session_feedback", successful)
    assert review._scan_page(lambda: db, build_turns, None, lambda: False) is None
    assert db.updated == ["u1"]


def test_same_process_duplicate_request_does_not_run_provider_twice(monkeypatch):
    db = DB()
    db.pair()
    nested = []

    def provider(pairs, level):
        nested.append(review.process_session(lambda: db, "s1", build_turns))
        return successful(pairs, level)

    monkeypatch.setattr(review, "generate_session_feedback", provider)
    assert review.process_session(lambda: db, "s1", build_turns)["processed"] == 1
    assert nested == [{"processed": 0, "failed": 0, "skipped": 1}]


def test_conditional_write_cannot_overwrite_another_replica_result(monkeypatch):
    db = DB()
    db.pair()
    existing = [{"id": "already-saved", "original": "she want", "corrected": "she wants", "explanation_ko": "기존 설명"}]

    def provider(pairs, level):
        db.rows["messages"][0]["feedback"] = deepcopy(existing)
        return successful(pairs, level)

    monkeypatch.setattr(review, "generate_session_feedback", provider)
    assert review.process_session(lambda: db, "s1", build_turns)["skipped"] == 1
    assert db.rows["messages"][0]["feedback"] == existing


def test_feedback_ids_are_stable_across_retries_but_distinct_across_turns():
    item = successful([{"turn_id": "u1"}], "B1")[0]["items"]
    first = review._with_stable_ids("s1", "u1", item)[0]["id"]
    item[0]["explanation_ko"] = "설명을 다듬었어요."
    assert review._with_stable_ids("s1", "u1", item)[0]["id"] == first
    assert review._with_stable_ids("s1", "u2", item)[0]["id"] != first


def test_large_session_messages_are_paginated(monkeypatch):
    db = DB()
    for i in range(4):
        db.pair(f"u{i}")
    monkeypatch.setattr(review, "_MESSAGE_PAGE_SIZE", 3)
    assert review.process_session(lambda: db, "s1", build_turns)["processed"] == 4
    assert db.message_pages == 3


def test_scanner_advances_past_failed_sessions_and_wraps(monkeypatch):
    db = DB([session(f"s{i}") for i in range(5)])
    for i in range(5):
        db.pair(f"u{i}", session_id=f"s{i}")
    seen = []
    monkeypatch.setattr(review, "_SESSION_PAGE_SIZE", 2)
    monkeypatch.setattr(review, "process_session", lambda get_db, sid, helper: seen.append(sid))
    cursor = review._scan_page(lambda: db, build_turns, None, lambda: False)
    assert cursor == "u1"
    cursor = review._scan_page(lambda: db, build_turns, cursor, lambda: False)
    assert cursor == "u3"
    assert review._scan_page(lambda: db, build_turns, cursor, lambda: False) is None
    assert seen == [f"s{i}" for i in range(5)]


def test_scanner_only_discovers_marked_pending_user_rows_and_deduplicates_sessions(monkeypatch):
    db = DB([session("s1", ended=None, reopened=REOPENED), session("s2")])
    db.pair("u1")
    db.pair("u2")
    db.pair("u3", requested_at=None)
    db.pair("u4", feedback=[])
    db.pair("u5", session_id="s2", requested_at=None)
    seen = []
    monkeypatch.setattr(review, "process_session", lambda get_db, sid, helper: seen.append(sid))
    assert review._scan_page(lambda: db, build_turns, None, lambda: False) is None
    assert seen == ["s1"]


def test_closed_session_timestamps_alone_never_request_extraction(monkeypatch):
    db = DB()
    db.pair(requested_at=None)
    monkeypatch.setattr(review, "generate_session_feedback", lambda *args: pytest.fail("Unmarked row reached AI"))
    assert review.process_session(lambda: db, "s1", build_turns)["processed"] == 0
    assert review._scan_page(lambda: db, build_turns, None, lambda: False) is None
    assert db.updated == []


def test_worker_scans_at_startup_and_honors_stop(monkeypatch):
    async def exercise():
        stop = asyncio.Event()
        calls = []

        def scan(get_db, helper, cursor, should_stop):
            calls.append(cursor)
            loop.call_soon_threadsafe(stop.set)
            return None

        loop = asyncio.get_running_loop()
        monkeypatch.setattr(review, "_scan_page", scan)
        await asyncio.wait_for(review.worker(lambda: None, stop, build_turns), timeout=1)
        assert calls == [None]

    asyncio.run(exercise())
