# -*- coding: utf-8 -*-
"""Attach adjacent-turn context without changing source utterance text."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _time_key(value: Any) -> tuple[int, float | str]:
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, str(value or ""))


def _speaker(row: dict[str, Any]) -> str | None:
    for field in ("speaker", "speaker_id", "participant_role"):
        value = row.get(field)
        if value not in (None, ""):
            return str(value)
    return None


def add_adjacent_turn_context(
    rows: list[dict[str, Any]],
    conversation_field: str,
    order_field: str,
) -> list[dict[str, Any]]:
    """Return source rows ordered within a conversation with adjacent text links."""
    grouped: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for input_index, row in enumerate(rows):
        conversation_id = str(row.get(conversation_field) or row.get("source_group") or "unknown")
        grouped[conversation_id].append((input_index, row))

    enriched_rows: list[dict[str, Any]] = []
    for conversation_id in sorted(grouped):
        ordered = sorted(
            grouped[conversation_id],
            key=lambda item: (
                _time_key(item[1].get(order_field)),
                str(item[1].get("source_record_id", "")),
                item[0],
            ),
        )
        for turn_index, (_, row) in enumerate(ordered):
            previous = ordered[turn_index - 1][1] if turn_index else None
            following = ordered[turn_index + 1][1] if turn_index + 1 < len(ordered) else None
            enriched = dict(row)
            enriched["conversation_id"] = conversation_id
            enriched["turn_index"] = turn_index
            enriched["previous_turn"] = previous.get("utterance") if previous else None
            enriched["previous_turn_speaker"] = _speaker(previous) if previous else None
            enriched["next_turn"] = following.get("utterance") if following else None
            enriched["next_turn_speaker"] = _speaker(following) if following else None
            enriched_rows.append(enriched)
    return enriched_rows
