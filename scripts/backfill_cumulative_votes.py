"""Fill raw_axes / axes_contribution for history saved before the cumulative-vote migration.

Run once after supabase/migrations/20261015000000_cumulative_votes.sql and BEFORE the
backend that reads these columns goes live, so existing users' Pally does not reset.

    PYTHONPATH=.:backend PALLY_AXIS_ANALYZER=researched python scripts/backfill_cumulative_votes.py          # dry run
    PYTHONPATH=.:backend PALLY_AXIS_ANALYZER=researched python scripts/backfill_cumulative_votes.py --apply  # write

Run with the production env (PALLY_AXIS_ANALYZER, PALLY_VOICE_ENERGY_ENABLED) so the analyzer and
the Energy source match the live backend. Prints counts only, never transcripts.
Idempotent and recomputes every vote: re-run it right after the new backend is live to pick up
conversations the old backend closed or changed in between.
"""
import argparse

from ai.matrix_engine import conversation_mean
from lib.supabase import get_supabase
import main


def all_rows(build):
    rows, start = [], 0
    while True:
        page = build().range(start, start + 999).execute().data
        rows += page
        if len(page) < 1000:
            return rows
        start += 1000


def run(apply: bool) -> None:
    sb = get_supabase()
    msgs = all_rows(lambda: sb.table("messages").select("id, session_id, transcript, raw_axes")
                    .eq("role", "user").order("id"))
    filled = 0
    for m in msgs:
        if m["raw_axes"] is None and m["transcript"]:
            m["raw_axes"] = main._analyze_axes(m["transcript"])
            filled += 1
            if apply:
                sb.table("messages").update({"raw_axes": m["raw_axes"]}).eq("id", m["id"]).execute()
    by_session = {}
    for m in msgs:
        if m["raw_axes"] is not None:
            by_session.setdefault(m["session_id"], []).append(m["raw_axes"])

    sessions = all_rows(lambda: sb.table("sessions").select("id, user_id, ended_at, axes_contribution")
                        .not_.is_("ended_at", "null").order("id"))
    votes = 0
    for s in sessions:
        # Recompute every vote, not only missing ones: the old backend may have reopened and
        # re-closed a conversation after a previous run. The slot (first_completed_at) is kept.
        turns = by_session.get(s["id"], [])
        previous = s["axes_contribution"]
        vote = {"mean": conversation_mean(turns) if turns else None, "turns": len(turns),
                "first_completed_at": previous["first_completed_at"] if previous else None}
        if vote != previous:
            votes += 1
            s["axes_contribution"] = vote
            if apply:
                sb.table("sessions").update({"axes_contribution": vote}).eq("id", s["id"]).execute()

    # Profiles are recomputed by the backend's own rule (votes + access days + voice Energy),
    # the same code path as a conversation ending.
    users = sorted({s["user_id"] for s in sessions if s["axes_contribution"]["mean"] is not None})
    if apply:
        for user_id in users:
            if not main._refresh_profile_traits(sb, user_id):
                raise RuntimeError("profile refresh failed; see the error log, then re-run (it is idempotent)")

    mode = "applied" if apply else "dry run"
    print(f"[{mode}] raw_axes filled: {filled}/{len(msgs)} user turns, "
          f"votes changed: {votes}/{len(sessions)} completed conversations, "
          f"profiles {'refreshed' if apply else 'to refresh'}: {len(users)} users")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write to the database (default: dry run)")
    run(parser.parse_args().apply)
