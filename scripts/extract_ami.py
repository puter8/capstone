# -*- coding: utf-8 -*-
"""Extract attributed dialogue-act turns from the AMI manual annotations.

AMI stores orthographic words and dialogue acts in separate NXT XML files. A
dialogue-act references one contiguous range of word IDs, which makes it the
closest available unit to a natural spoken utterance. This extractor keeps the
dialogue-act label, speaker role, and recorded native-language metadata as
provenance; none of those annotations are converted into Pally axis scores.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.conversation_context import add_adjacent_turn_context
except ModuleNotFoundError:
    from conversation_context import add_adjacent_turn_context


SOURCE_NAME = "ami_real"
DEFAULT_INPUT = Path("data/external_raw/ami_manual")
DEFAULT_OUTPUT = Path("data/fixtures/ami_utterances.jsonl")
HREF_RANGE_RE = re.compile(r"#id\(([^)]+)\)(?:\.\.id\(([^)]+)\))?")
WHITESPACE_RE = re.compile(r"\s+")


def local_name(name: str) -> str:
    """Return an XML element or attribute name without its namespace prefix."""
    return name.rsplit("}", maxsplit=1)[-1].rsplit(":", maxsplit=1)[-1]


def attribute(element: ET.Element, name: str, default: str = "") -> str:
    for key, value in element.attrib.items():
        if local_name(key) == name:
            return value
    return default


def clean_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip(" -,:;")


def parse_dialogue_act_types(path: Path) -> dict[str, dict[str, str]]:
    types: dict[str, dict[str, str]] = {}
    root = ET.parse(path).getroot()
    for element in root.iter():
        if local_name(element.tag) != "da-type":
            continue
        type_id = attribute(element, "id")
        if not type_id:
            continue
        types[type_id] = {
            "name": attribute(element, "name"),
            "gloss": attribute(element, "gloss"),
        }
    return types


def parse_speaker_metadata(resources_dir: Path) -> dict[tuple[str, str], dict[str, str]]:
    participants_root = ET.parse(resources_dir / "participants.xml").getroot()
    native_languages = {
        attribute(element, "id"): attribute(element, "native_language")
        for element in participants_root.iter()
        if local_name(element.tag) == "participant"
    }

    meetings_root = ET.parse(resources_dir / "meetings.xml").getroot()
    metadata: dict[tuple[str, str], dict[str, str]] = {}
    for meeting in meetings_root.iter():
        if local_name(meeting.tag) != "meeting":
            continue
        meeting_id = attribute(meeting, "observation")
        for speaker in meeting:
            if local_name(speaker.tag) != "speaker":
                continue
            agent = attribute(speaker, "nxt_agent")
            global_name = attribute(speaker, "global_name")
            metadata[(meeting_id, agent)] = {
                "speaker_id": global_name,
                "speaker_native_language": native_languages.get(global_name, ""),
                "speaker_role": attribute(speaker, "role"),
            }
    return metadata


def parse_word_entries(path: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    root = ET.parse(path).getroot()
    entries: list[dict[str, str]] = []
    for element in root:
        kind = local_name(element.tag)
        entry_id = attribute(element, "id")
        if not entry_id:
            continue
        if kind == "w":
            entries.append(
                {
                    "id": entry_id,
                    "text": (element.text or "").strip(),
                    "punctuation": attribute(element, "punc") == "true",
                    "event": "",
                    "start_time": attribute(element, "starttime"),
                    "end_time": attribute(element, "endtime"),
                }
            )
        elif kind == "vocalsound":
            entries.append(
                {
                    "id": entry_id,
                    "text": "",
                    "punctuation": False,
                    "event": attribute(element, "type", "vocal_sound"),
                    "start_time": attribute(element, "starttime"),
                    "end_time": attribute(element, "endtime"),
                }
            )
    return entries, {entry["id"]: index for index, entry in enumerate(entries)}


def render_entries(entries: list[dict[str, str]]) -> tuple[str, list[str]]:
    tokens: list[str] = []
    events: list[str] = []
    for entry in entries:
        if entry["event"]:
            events.append(entry["event"])
            continue
        token = entry["text"]
        if not token:
            continue
        if entry["punctuation"] and tokens:
            tokens[-1] += token
        elif entry["punctuation"]:
            tokens.append(token)
        else:
            tokens.append(token)
    return clean_text(" ".join(tokens)), events


def parse_href_range(href: str) -> tuple[str, str] | None:
    match = HREF_RANGE_RE.search(href)
    if not match:
        return None
    start_id, end_id = match.groups()
    return start_id, end_id or start_id


def extract_file(
    dialogue_path: Path,
    words_dir: Path,
    act_types: dict[str, dict[str, str]],
    speaker_metadata: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    stem = dialogue_path.name.removesuffix(".dialog-act.xml")
    meeting_id, speaker = stem.rsplit(".", maxsplit=1)
    word_path = words_dir / f"{stem}.words.xml"
    if not word_path.exists():
        return []
    entries, word_indexes = parse_word_entries(word_path)
    root = ET.parse(dialogue_path).getroot()
    metadata = speaker_metadata.get((meeting_id, speaker), {})
    return extract_dialogue_act_rows(
        root,
        entries,
        word_indexes,
        meeting_id,
        speaker,
        act_types,
        metadata,
    )


def extract_dialogue_act_rows(
    root: ET.Element,
    entries: list[dict[str, str]],
    word_indexes: dict[str, int],
    meeting_id: str,
    speaker: str,
    act_types: dict[str, dict[str, str]],
    metadata: dict[str, str],
) -> list[dict[str, Any]]:
    """Render one AMI speaker file after its XML and word entries are parsed."""
    rows: list[dict[str, Any]] = []

    for act in root:
        if local_name(act.tag) != "dact":
            continue
        act_id = attribute(act, "id")
        type_id = ""
        word_range: tuple[str, str] | None = None
        for child in act:
            if local_name(child.tag) == "pointer" and attribute(child, "role") == "da-aspect":
                pointer = parse_href_range(attribute(child, "href"))
                type_id = pointer[0] if pointer else ""
            elif local_name(child.tag) == "child":
                word_range = parse_href_range(attribute(child, "href"))
        if not act_id or not word_range:
            continue
        start_id, end_id = word_range
        if start_id not in word_indexes or end_id not in word_indexes:
            continue
        start_index, end_index = word_indexes[start_id], word_indexes[end_id]
        if end_index < start_index:
            start_index, end_index = end_index, start_index
        utterance, events = render_entries(entries[start_index : end_index + 1])
        if not utterance:
            continue
        act_type = act_types.get(type_id, {})
        rows.append(
            {
                "utterance": utterance,
                "source": SOURCE_NAME,
                "axes": None,
                "source_record_id": act_id,
                "source_group": meeting_id,
                "meeting_id": meeting_id,
                "speaker": speaker,
                "speaker_id": metadata.get("speaker_id"),
                "speaker_native_language": metadata.get("speaker_native_language"),
                "speaker_role": metadata.get("speaker_role"),
                "dialogue_act": act_type.get("name", type_id) or None,
                "dialogue_act_gloss": act_type.get("gloss") or None,
                "start_time": entries[start_index].get("start_time"),
                "end_time": entries[end_index].get("end_time"),
                "annotation_events": events,
            }
        )
    return rows


def extract_corpus(input_dir: Path) -> tuple[int, int, list[dict[str, Any]]]:
    dialogue_dir = input_dir / "dialogueActs"
    words_dir = input_dir / "words"
    act_types = parse_dialogue_act_types(input_dir / "ontologies" / "da-types.xml")
    speaker_metadata = parse_speaker_metadata(input_dir / "corpusResources")
    files = sorted(dialogue_dir.glob("*.dialog-act.xml"))
    rows: list[dict[str, Any]] = []
    skipped = 0
    for path in files:
        extracted = extract_file(path, words_dir, act_types, speaker_metadata)
        if not extracted and not (words_dir / f"{path.name.removesuffix('.dialog-act.xml')}.words.xml").exists():
            skipped += 1
        rows.extend(extracted)
    return len(files), skipped, add_adjacent_turn_context(rows, "meeting_id", "start_time")


def write_jsonl(rows: Iterable[dict[str, Any]], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    file_count, skipped, rows = extract_corpus(args.input)
    count = write_jsonl(rows, args.output)
    acts = Counter(str(row["dialogue_act"] or "unknown") for row in rows)
    languages = Counter(str(row["speaker_native_language"] or "unknown") for row in rows)
    print(f"dialogue_act_files={file_count}")
    print(f"skipped_missing_word_files={skipped}")
    print(f"utterances={count}")
    print("dialogue_acts=" + ", ".join(f"{name}:{acts[name]}" for name in sorted(acts)))
    print("native_languages=" + ", ".join(f"{name}:{languages[name]}" for name in sorted(languages)))
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
