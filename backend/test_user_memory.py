"""What Pally may remember about the user, and what it must refuse to store.

These are the guards that do not depend on the model behaving: the grounding
check and the closed key list. The prompt is the first line of defence, but
real calls showed it is not enough on its own - with the categories open,
gemini-2.5-flash-lite stored `health_condition: depression` on 5 of 5 runs.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import main
from ai.user_memory import (
    ALLOWED_KEYS, MAX_FACTS_PER_KEY, MAX_PROMPT_FACTS, MAX_VALUE_CHARS, SINGLE_VALUED,
    ground_facts, memory_prompt,
)
from lib import user_memory as store

TURNS = [
    ("pally", "I love playing the guitar. I also have a cat named Mochi. Do you have pets?"),
    ("user", "I have two dog. Their name is Kongi and Bori."),
    ("pally", "Kongi and Bori! Cute names."),
    ("user", "Thank you. I am study design at Hongik University."),
]


def test_a_fact_quoted_from_the_user_is_kept():
    kept = ground_facts(
        [{"key": "pet", "value": "two dogs, Kongi and Bori", "quote": "I have two dog"}], TURNS)
    assert kept == [{"key": "pet", "value": "two dogs, Kongi and Bori"}]


def test_a_fact_quoted_from_pally_is_dropped():
    """Pally's cat must never become the user's cat."""
    kept = ground_facts(
        [{"key": "pet", "value": "a cat named Mochi", "quote": "I also have a cat named Mochi"}],
        TURNS)
    assert kept == []


def test_an_invented_quote_is_dropped():
    kept = ground_facts(
        [{"key": "city", "value": "Seoul", "quote": "I live in Seoul"}], TURNS)
    assert kept == []


def test_a_key_outside_the_allowed_list_is_dropped():
    """The response schema constrains the key, but a drifting schema must not
    be the only thing standing between a health condition and the database."""
    kept = ground_facts([
        {"key": "health_condition", "value": "depression", "quote": "I have two dog"},
        {"key": "religion", "value": "Catholic", "quote": "I have two dog"},
        {"key": "pet", "value": "two dogs", "quote": "I have two dog"},
    ], TURNS)
    assert kept == [{"key": "pet", "value": "two dogs"}]


def test_no_allowed_key_can_hold_health_religion_or_income():
    for forbidden in ("health", "condition", "medic", "religio", "politic", "income",
                      "salary", "orientation", "diagnos"):
        assert not any(forbidden in key for key in ALLOWED_KEYS), forbidden


def test_one_bad_fact_does_not_throw_away_the_good_ones():
    kept = ground_facts([
        {"key": "pet", "value": "two dogs", "quote": "I have two dog"},
        {"key": "city", "value": "Busan", "quote": "I never said this"},
        {"key": "school", "value": "Hongik University", "quote": "at Hongik University"},
    ], TURNS)
    assert [fact["key"] for fact in kept] == ["pet", "school"]


def test_the_same_fact_twice_is_stored_once():
    kept = ground_facts([
        {"key": "pet", "value": "Two Dogs", "quote": "I have two dog"},
        {"key": "pet", "value": "two dogs", "quote": "I have two dog"},
    ], TURNS)
    assert kept == [{"key": "pet", "value": "Two Dogs"}]


def test_an_empty_or_overlong_value_is_handled():
    kept = ground_facts([
        {"key": "pet", "value": "   ", "quote": "I have two dog"},
        {"key": "school", "value": "H" * (MAX_VALUE_CHARS + 50), "quote": "at Hongik University"},
    ], TURNS)
    assert len(kept) == 1
    assert len(kept[0]["value"]) == MAX_VALUE_CHARS


def test_a_malformed_item_is_skipped_without_raising():
    assert ground_facts(["not an object", None, {"key": "pet"}], TURNS) == []


# ── The prompt block ────────────────────────────────────────────────────────


def test_no_facts_means_no_block():
    assert memory_prompt([]) is None


def test_a_changed_single_valued_fact_keeps_only_the_newest():
    """Facts arrive newest first. Two majors in the prompt would let Pally
    answer with the stale one."""
    block = memory_prompt([
        {"key": "field_of_study", "value": "computer science"},
        {"key": "field_of_study", "value": "product design"},
    ])
    assert "computer science" in block
    assert "product design" not in block


def test_a_multi_valued_fact_keeps_every_value():
    block = memory_prompt([
        {"key": "hobby", "value": "climbing"},
        {"key": "hobby", "value": "baking"},
    ])
    assert "climbing" in block and "baking" in block


def test_every_single_valued_key_is_a_real_key():
    assert SINGLE_VALUED <= set(ALLOWED_KEYS)


def _listed(block):
    return [line for line in block.splitlines() if line.startswith("- ")]


def test_the_block_is_capped():
    """The reply is capped at 90 characters; a long list only dilutes the prompt.

    Spread over several keys, because one key alone cannot reach the overall cap
    any more (see the per-key cap below).
    """
    keys = ["hobby", "skill", "language", "plan", "family", "pet"]
    facts = [{"key": key, "value": f"{key} {n}"} for key in keys for n in range(5)]
    assert len(_listed(memory_prompt(facts))) == MAX_PROMPT_FACTS


def test_one_key_cannot_take_the_whole_block():
    """A live account had five `pet` rows for three pets, which filled five of
    the eight slots and pushed its occupation and field of study out."""
    facts = [{"key": "pet", "value": f"pet number {n}"} for n in range(10)]
    facts += [{"key": "occupation", "value": "student"}]
    listed = _listed(memory_prompt(facts))
    assert len([line for line in listed if line.startswith("- pet:")]) == MAX_FACTS_PER_KEY
    assert "- occupation: student" in listed


def test_a_newer_value_replaces_the_stale_fact_about_the_same_pet():
    """The case this came from, with the stored values verbatim.

    "my favorite animal is dog and my pet's name is donut" was fairly read as a
    dog named Donut; two minutes later the user corrected it to a Siamese cat.
    Both rows live in storage because `pet` is multi-valued, and the prompt
    tells Pally to answer straight from the list, so the stale row is a wrong
    answer waiting to happen.
    """
    block = memory_prompt([
        {"key": "pet", "value": "a Siamese cat, Donut"},
        {"key": "pet", "value": "a dog, Dumpling"},
        {"key": "pet", "value": "dog named Donut"},
    ])
    assert "a Siamese cat, Donut" in block
    assert "dog named Donut" not in block
    # The other pet is a different animal and must survive the cleanup.
    assert "a dog, Dumpling" in block


def test_a_vaguer_restatement_does_not_cost_a_slot():
    block = memory_prompt([
        {"key": "pet", "value": "a Siamese cat, Donut"},
        {"key": "pet", "value": "cat"},
    ])
    assert _listed(block) == ["- pet: a Siamese cat, Donut"]


def test_two_pets_of_the_same_breed_are_both_kept():
    """The replacement rule keys on the name the value introduces, not on every
    capitalized word: "Siamese" is a breed, so two Siamese cats are two cats."""
    block = memory_prompt([
        {"key": "pet", "value": "a Siamese cat, Mocha"},
        {"key": "pet", "value": "a Siamese cat, Donut"},
    ])
    assert "Mocha" in block and "Donut" in block


def test_unrelated_values_of_one_key_are_all_kept():
    block = memory_prompt([
        {"key": "hobby", "value": "climbing"},
        {"key": "hobby", "value": "baking bread"},
        {"key": "hobby", "value": "playing bass"},
    ])
    assert len(_listed(block)) == 3


def test_the_block_carries_the_fact_and_the_rules_for_using_it():
    """The point of the feature: Pally can answer "how old am I", not bring it up.

    Each of these lines was added because a live run failed without it:
      - "answer it directly" after Pally said it did not remember the city that
        was sitting in the list (2 of 3 runs, when this clause came first).
      - "Never ask them for something the list already tells you" after Pally
        answered "Of course I remember! What are their names?".
      - "never speak of them as your own" after Pally called the user's dogs its
        own dogs: the reply contract has a field for Pally's own remark.
    """
    block = memory_prompt([{"key": "pet", "value": "two dogs, Kongi and Bori"}])
    assert "- pet: two dogs, Kongi and Bori" in block
    flat = " ".join(block.split())
    assert "answer it directly" in flat
    assert "Never ask them for something the list already tells you" in flat
    assert "never speak of them as your own" in flat
    assert "Never read the list out" in flat
    assert "say you do not remember instead of guessing" in flat


def test_the_rules_come_after_the_facts():
    """Order is load-bearing: with the "say you do not remember" clause last,
    Pally used it even for facts that were listed right above it."""
    block = memory_prompt([{"key": "city", "value": "Daegu"}])
    assert block.index("- city: Daegu") < block.index("answer it directly")


# ── The store ───────────────────────────────────────────────────────────────


def test_nothing_is_written_when_there_are_no_facts():
    sb = Mock()
    assert store.save_facts(sb, "user-1", "conversation-1", []) == 0
    sb.table.assert_not_called()


def test_saving_ignores_a_fact_the_user_already_told_pally():
    sb = Mock()
    stored = store.save_facts(sb, "user-1", "conversation-1", [
        {"key": "pet", "value": "two dogs"}, {"key": "city", "value": "Daegu"}])
    assert stored == 2
    sb.table.assert_called_once_with("user_memories")
    rows, kwargs = sb.table.return_value.upsert.call_args.args[0], sb.table.return_value.upsert.call_args.kwargs
    assert rows == [
        {"user_id": "user-1", "key": "pet", "value": "two dogs",
         "source_session_id": "conversation-1"},
        {"user_id": "user-1", "key": "city", "value": "Daegu",
         "source_session_id": "conversation-1"},
    ]
    assert kwargs == {"on_conflict": "user_id,key,value", "ignore_duplicates": True}


def test_a_read_failure_starts_the_conversation_without_memory(caplog):
    """A conversation must still begin when the memory read fails; the failure
    is logged rather than hidden."""
    sb = Mock()
    sb.table.side_effect = RuntimeError("postgrest is down")
    assert store.build_prompt(sb, "user-1") is None
    assert "Memory read failed" in caplog.text


def test_a_user_with_no_stored_facts_gets_no_block():
    sb = Mock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value \
        .limit.return_value.execute.return_value = SimpleNamespace(data=[])
    assert store.build_prompt(sb, "user-1") is None


def test_facts_are_read_newest_first():
    sb = Mock()
    chain = sb.table.return_value.select.return_value.eq.return_value.order.return_value
    chain.limit.return_value.execute.return_value = SimpleNamespace(
        data=[{"key": "city", "value": "Daegu"}])
    assert store.build_prompt(sb, "user-1") is not None
    sb.table.return_value.select.return_value.eq.return_value.order.assert_called_once_with(
        "created_at", desc=True)


def test_extraction_failure_never_breaks_the_finished_conversation(monkeypatch, caplog):
    """The conversation is already closed and answered when this runs."""
    monkeypatch.setattr(store, "extract_user_facts",
                        Mock(side_effect=RuntimeError("Gemini is down")))
    sb = Mock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value \
        .order.return_value.execute.return_value = SimpleNamespace(
            data=[{"id": "1", "role": "user", "transcript": "I have two dog",
                   "created_at": "2026-11-12T00:00:00+00:00"}])
    assert store.process_session(lambda: sb, "conversation-1", "user-1", lambda rows: rows) == 0
    assert "Memory extraction failed" in caplog.text


def test_a_conversation_with_no_user_speech_calls_no_model(monkeypatch):
    extract = Mock()
    monkeypatch.setattr(store, "extract_user_facts", extract)
    sb = Mock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value \
        .order.return_value.execute.return_value = SimpleNamespace(data=[])
    assert store.process_session(lambda: sb, "conversation-1", "user-1", lambda rows: rows) == 0
    extract.assert_called_once_with([])


def test_the_model_sees_role_and_transcript_pairs_in_order(monkeypatch):
    extract = Mock(return_value=[])
    monkeypatch.setattr(store, "extract_user_facts", extract)
    rows = [
        {"id": "1", "role": "pally", "transcript": "Hi!"},
        {"id": "2", "role": "user", "transcript": "I have two dog"},
        # A row with no transcript (a failed turn) must not reach the model.
        {"id": "3", "role": "user", "transcript": None},
    ]
    sb = Mock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value \
        .order.return_value.execute.return_value = SimpleNamespace(data=rows)
    store.process_session(lambda: sb, "conversation-1", "user-1", lambda given: given)
    extract.assert_called_once_with([("pally", "Hi!"), ("user", "I have two dog")])


def test_a_read_failure_is_raised_for_a_caller_that_already_has_a_block():
    """build_prompt cannot tell "no facts" from "the read failed"; a reopened
    conversation has a block to lose, so it uses rebuild_prompt instead."""
    sb = Mock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value \
        .limit.return_value.execute.side_effect = RuntimeError("connection lost")
    with pytest.raises(RuntimeError):
        store.rebuild_prompt(sb, "user-1")


def test_rebuild_returns_none_when_the_user_really_has_no_facts():
    """Deleting the conversation a fact came from cascades the row away, so an
    empty read is a real answer and must be written through, not skipped."""
    sb = Mock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value \
        .limit.return_value.execute.return_value = SimpleNamespace(data=[])
    assert store.rebuild_prompt(sb, "user-1") is None


def _reopen_with(monkeypatch, rebuild):
    """Reopen one finished conversation, returning the update that was sent."""
    session = {"id": "conversation-1", "user_id": "user-1",
               "ended_at": "2026-11-26T07:04:00+00:00", "reopen_count": 1,
               "axes_contribution": None}
    sessions = Mock()
    sessions.update.return_value.eq.return_value.eq.return_value.execute.return_value = \
        SimpleNamespace(data=[{**session, "ended_at": None}])
    sb = Mock()
    sb.table.side_effect = lambda name: {"sessions": sessions}[name]
    monkeypatch.setattr(main, "get_supabase", lambda: sb)
    monkeypatch.setattr(main, "_owned_session", lambda *_: session)
    monkeypatch.setattr(main.user_memory, "rebuild_prompt", rebuild)
    asyncio.run(main.reopen_conversation("conversation-1", "user-1", "key"))
    return sessions.update.call_args.args[0]


def test_reopening_a_conversation_refreshes_what_pally_knows(monkeypatch):
    """The bug this fixes: the user told Pally their cat's name, finished that
    conversation, came back to an older one and was told "I don't remember"
    while the fact was already stored. The block is a snapshot taken at
    creation, so reopening has to take a new one."""
    block = memory_prompt([{"key": "pet", "value": "a Siamese cat, Donut"}])
    update = _reopen_with(monkeypatch, Mock(return_value=block))
    assert update["memory_prompt"] == block
    assert "Donut" in update["memory_prompt"]
    # The rest of the reopen must still happen.
    assert update["ended_at"] is None
    assert update["reopen_count"] == 2


def test_a_memory_read_failure_does_not_cost_the_conversation_its_block(monkeypatch, caplog):
    """Writing None over the existing block on a transient error would make
    reopening lose what Pally knew. Leave the column alone instead."""
    update = _reopen_with(monkeypatch, Mock(side_effect=RuntimeError("connection lost")))
    assert "memory_prompt" not in update
    assert update["ended_at"] is None
    assert "Memory rebuild on reopen failed" in caplog.text
