"""Store and read what Pally remembers about a user.

Extraction runs after a conversation is closed, out of the request path, so a
failure here never fails /complete. The facts land before the user's next
conversation is created, which is when the prompt block is built.
"""
from __future__ import annotations

import logging

from ai.user_memory import MAX_PROMPT_FACTS, extract_user_facts, memory_prompt

# Enough rows to fill MAX_PROMPT_FACTS after single-valued keys collapse to
# their newest value. Reading the whole history would grow without bound.
_READ_LIMIT = MAX_PROMPT_FACTS * 4


def recent_facts(sb, user_id: str) -> list:
    """The user's facts, newest first. Raises so the caller can decide."""
    res = (sb.table("user_memories").select("key, value")
           .eq("user_id", user_id).order("created_at", desc=True)
           .limit(_READ_LIMIT).execute())
    return res.data or []


def build_prompt(sb, user_id: str):
    """The memory block for a new conversation, or None when there is nothing.

    A read failure must not stop a conversation from starting: Pally simply
    begins without memory. The error is logged, not swallowed silently.
    """
    try:
        facts = recent_facts(sb, user_id)
    except Exception as exc:
        logging.error("Memory read failed for a new conversation: %s", type(exc).__name__)
        return None
    return memory_prompt(facts)


def save_facts(sb, user_id: str, session_id: str, facts: list) -> int:
    """Insert the conversation's facts, ignoring ones already stored.

    The primary key is (user_id, key, value), so a fact the user restates in a
    later conversation is not a new row. Returns the number of rows sent.
    """
    if not facts:
        return 0
    rows = [{"user_id": user_id, "key": fact["key"], "value": fact["value"],
             "source_session_id": session_id} for fact in facts]
    (sb.table("user_memories").upsert(
        rows, on_conflict="user_id,key,value", ignore_duplicates=True).execute())
    return len(rows)


def process_session(get_db, session_id: str, user_id: str, in_turn_order) -> int:
    """Extract and store one finished conversation's facts. Returns rows stored.

    Runs in a background task after /complete has already answered, and for
    conversations the stale-conversation worker closes. Any failure is logged
    and gives up for this conversation: the next conversation the user finishes
    extracts its own facts, and nothing in the user's flow depends on this
    having succeeded. `in_turn_order` is the caller's existing ordering, so the
    model sees the same user->reply alternation the rest of the app does.
    """
    try:
        sb = get_db()
        msgs = (sb.table("messages").select("id, role, transcript, created_at")
                .eq("session_id", session_id).order("created_at").order("id").execute())
        turns = [(row["role"], row["transcript"]) for row in in_turn_order(msgs.data or [])
                 if row.get("transcript")]
        facts = extract_user_facts(turns)
        stored = save_facts(sb, user_id, session_id, facts)
        if stored:
            logging.info("Stored %d memory fact(s) for a finished conversation", stored)
        return stored
    except Exception as exc:
        logging.warning("Memory extraction failed for a conversation: %s", type(exc).__name__)
        return 0
