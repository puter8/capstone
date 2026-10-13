# -*- coding: utf-8 -*-
"""F/H/C active-learning round 2: Gemini as the labeling oracle (pseudo-labels).

The owner banned further HUMAN labeling, so round 2 labels its candidates with
Gemini 2.5 Flash-Lite. Every row is label_source="gemini_ai_scored": a
pseudo-label, never a human label. Rubric v2.2 Sec.13 gives pseudo-labels
weight 0 in the human-grounded main experiment, so this is a SEPARATE Gemini
pseudo-label augmentation experiment evaluated on human dev labels; accepted
pseudo targets get unit weight inside that experiment only.

Protocol (rubric v2.2):
- Sec.2: the model sees ONLY the target utterance (no previous/next turn, no
  corpus name, no model/human scores, no selection cue such as laughter).
- The model records primary/secondary function, function_ambiguous,
  language_form, and per axis the component levels (Sec.5 integer 0-4),
  case_type, confidence (0-4, never used in scores or weights) and evidence;
  plus the Sec.10 Curiosity function. Weighted scores, the Curiosity clamp
  and round_to_5 (half up, matching the human workbook's Excel ROUND) are
  computed here, never taken from the model.
- Sec.11: context_insufficient -> score_status=provisional; the numeric score
  is kept for audit (never an automatic 50) and never used for training.
- One ACCEPTED annotation per item; transport failures get bounded retries
  (MAX_ATTEMPTS) and every attempt is logged in the row.

Calibration (pre-registered gate, decided before any calibration call):
items = the 221 human rows of the round-1 train/dev split. The gate uses ONLY
blind single-utterance human labels in the TRAIN split (round-1 workbook items
41-150; items 1-40 and the seed-100 consensus labels were made with the
previous turn visible). Dev items and context-exposed items are reported only
as diagnostics, after the gate decision is written to GATE_PATH. The legacy
final-test 20 and the protected eval partition are never labeled.

Santa Barbara is CC BY-ND and its text must never reach the public repo:
public rows for SB items carry no utterance, raw response, evidence or error
detail -- those go to a separate --private-audit JSONL that must live outside
the repo or in a gitignored path.

Subcommands:
  selfcheck    arithmetic/validation self-check (no API)
  smoke        score the 15 rubric anchor sentences (stdout only)
  calibration  label the 221 human items -> CALIBRATION_OUT
  batch        label fhc_round2_select.py candidates -> PSEUDO_OUT
  report       agreement report; writes the gate decision to GATE_PATH
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODEL = "gemini-2.5-flash-lite"
MAX_ATTEMPTS = 4
# Shared per-project Gemini quota with production: cap experiments at 10 requests/min.
CALL_INTERVAL_S = 6.0
CALIBRATION_OUT = ROOT / "data/fixtures/pally_purpose_v3_round2_calibration_gemini.jsonl"
PSEUDO_OUT = ROOT / "data/fixtures/pally_purpose_v3_round2_pseudo_labels.jsonl"
GATE_PATH = ROOT / "data/fixtures/pally_purpose_v3_round2_calibration_gate.json"
CANDIDATES_PATH = ROOT / "data/fixtures/pally_purpose_v3_round2_candidates.jsonl"
TRAIN_SPLIT = ROOT / "data/fixtures/pally_purpose_v3_train_dev_split_train.jsonl"
DEV_SPLIT = ROOT / "data/fixtures/pally_purpose_v3_train_dev_split_dev.jsonl"
R1_WORKBOOK = ROOT / "data/fixtures/pally_purpose_v3_labeling_workbook.xlsx"
SB_SOURCE = "santa_barbara_real"

FUNCTIONS = [
    "inform_describe", "self_disclose", "opinion_evaluate", "ask_fact_meaning",
    "ask_explain_explore", "confirm_clarify", "request_direct", "social_phatic",
    "answer_acknowledge", "express_react",
]
LANGUAGE_FORMS = [
    "standard_or_unmarked", "likely_learner_error", "conventional_nonstandard",
    "playful_deviation", "intent_unclear",
]
CASE_TYPES = ["clear", "boundary", "context_insufficient"]
# Rubric v2.2 Sec.10 function table -> allowed Curiosity range.
CURIOSITY_CLAMP = {
    "non_question_statement": (0, 15),
    "rhetorical_or_echo_question": (10, 30),
    "action_request": (10, 30),
    "confirmation_question": (25, 50),
    "phatic_or_turn_return": (30, 55),
    "fact_or_word_meaning_question": (45, 70),
    "opinion_or_choice_request": (55, 80),
    "reason_principle_process_question": (70, 95),
    "hypothetical_comparison_followup": (85, 100),
}
# Integer percent weights (rubric v2.2 Sec.6/9/10) -> exact integer arithmetic.
WEIGHTS = {
    "Formality": {"respect_face": 40, "mitigation": 35, "spoken_register": 25},
    "Humor": {"playful_framing": 40, "nonliteral_incongruity": 30,
              "humor_meme_slang_cue": 20, "expressive_reinforcement": 10},
    "Curiosity": {"inquiry_strength": 50, "exploration_depth": 25,
                  "answer_openness": 15, "epistemic_signal": 10},
}
AXES = list(WEIGHTS)
# Audit-only consistency flag between the Sec.3 function and the Sec.10 function.
QUESTION_FUNCS = {"ask_fact_meaning", "ask_explain_explore", "confirm_clarify"}
NON_QUESTION_FUNCS = {"inform_describe", "self_disclose", "opinion_evaluate", "answer_acknowledge", "express_react"}
INQUIRY_CFUNCS = {"confirmation_question", "fact_or_word_meaning_question", "opinion_or_choice_request",
                  "reason_principle_process_question", "hypothetical_comparison_followup"}

SYSTEM_PROMPT = """You annotate ONE English conversational utterance with the Pally measurement rubric v2.2. \
Per the rubric's protocol you see ONLY this target utterance: no previous or next turn, no source, no model \
or other rater scores. Judge only what the utterance itself shows. Speakers may be non-native; transcripts \
may contain disfluencies (uh, um, repeated words, false starts).

Order: (1) choose the primary function (and a secondary one only if two functions are clearly present), \
(2) choose the language form, (3) score Formality, Humor and Curiosity independently, (4) give each axis a \
case_type, a confidence and one short evidence sentence.

(1) primary_function -- what response does the utterance mainly ask of the listener? Choose one:
inform_describe (facts/situation), self_disclose (own experience/feeling/state), opinion_evaluate \
(judgment of something), ask_fact_meaning (limited info: fact, name, word meaning), ask_explain_explore \
(reasons, principles, comparisons, hypotheses, perspectives), confirm_clarify (check right/wrong, \
understanding, what was heard, which option), request_direct (asks the listener to do something or do it \
together, incl. suggestions), social_phatic (greeting, rapport, keeping the talk going), answer_acknowledge \
(answers, agrees, backchannels), express_react (surprise, joy, complaint, admiration). Humor is never a \
function. secondary_function: another code from this list, or "none". function_ambiguous: true only if the \
primary function cannot be decided.

(2) language_form: standard_or_unmarked | likely_learner_error | conventional_nonstandard (ain't, \
contractions, spoken grammar) | playful_deviation (deliberate playful spelling/grammar breaking with other \
evidence of play) | intent_unclear. Grammar accuracy, disfluency and length are NOT evidence on any axis: \
a learner error never lowers Formality or raises Humor, and disfluent repetitions are not expressive \
reinforcement.

Every component is an integer level 0-4: 0 = low end of the axis (for Humor/Curiosity: absent); \
1 = low with weak cues; 2 = middle/neutral or conflicting cues; 3 = high with clear cues; \
4 = strong, consistent cues at the high end.

FORMALITY -- bipolar: respect, mitigation and spoken register observable in the utterance (not written \
style, not grammar).
- respect_face (40%): 0 belittles/pressures/ignores the listener; 2 neutral or no interpersonal act; \
4 explicitly considers the listener's position, convenience or face.
- mitigation (35%): 0 direct command or strong demand; 2 neutral wording or an ordinary request; \
4 strongly offers permission, choice or reduced burden.
- spoken_register (25%): 0 very casual/informal; 2 everyday neutral conversation; 4 very formal/official \
spoken register.
A neutral statement with no interpersonal request puts respect_face and mitigation at 2. "please" alone, a \
long sentence or correct grammar never raises the score.
Anchors: 0 "Fix this for me." | 25 "Can you fix this for me?" | 50 "Could you help me fix this?" | \
75 "Could you help me fix this when you have a moment?" | 100 "Sorry to bother you, but would you mind \
helping me fix this when it's convenient?"

HUMOR -- unipolar: playful intent perceivable in this utterance (playful framing, non-literal meaning, \
incongruity/reversal, wordplay, exaggeration, irony, playful meme/slang use). Not whether it is trendy, \
whether you would laugh, or the speaker's personality. No playful cue at all -> all 0.
- playful_framing (40%): 0 literal/neutral delivery; 2 possible playfulness but unclear; 4 strong, \
consistent playful intent.
- nonliteral_incongruity (30%): 0 literal meaning only; 2 weak exaggeration or ambiguity; 4 wordplay, \
irony, strong reversal or violated expectation.
- humor_meme_slang_cue (20%): 0 no cue; 2 expression present but meaning/use unclear; 4 verifiable \
slang/meme expression clearly used playfully.
- expressive_reinforcement (10%): 0 none; 2 some repetition/rhythm/spelling variation; 4 a deliberate form \
that clearly reinforces the playfulness.
Slang alone is not enough for a high score. Quoting, asking what a word means or repeating someone is not \
spontaneous humor. If a literal and a playful reading are both plausible, use case_type boundary or \
context_insufficient.
Anchors: 0 "I stayed home and watched a movie." | 25 "Well, that went great." | 50 "My alarm clock and I \
are in a toxic relationship." | 75 "Girl, you ate - and left absolutely no crumbs." | 100 "My deadline saw \
me relaxing and said, 'Absolutely not,' then spawned three side quests."

CURIOSITY -- unipolar: how explicitly this utterance requests information, explanation, reasons, \
perspectives, possibilities or further exploration (not how often the speaker asks, not personality). \
No inquiry at all -> all 0. Question marks, what/why/how words, politeness and length get no direct weight.
- inquiry_strength (50%): 0 asks for no answer or information; 2 asks for a limited confirmation or \
reaction; 4 explicitly asks for information, explanation or a perspective.
- exploration_depth (25%): 0 no exploration; 2 a single fact/meaning check; 4 explores reasons, \
principles, comparisons or hypotheticals.
- answer_openness (15%): 0 no substantive answer needed; 2 a short limited answer suffices; 4 requires \
explanation, grounds or several possibilities.
- epistemic_signal (10%): 0 no not-knowing/wondering marker; 2 an information gap is indirectly visible; \
4 explicitly states what the speaker wants to know or is unsure about.
curiosity_function -- choose the one that fits the utterance's main function (the score is later limited \
to its range): non_question_statement (0-15) | rhetorical_or_echo_question (10-30, rhetorical question or \
simple echo) | action_request (10-30) | confirmation_question (25-50) | phatic_or_turn_return (30-55, ritual \
greeting or handing the turn back, e.g. "How about you?") | fact_or_word_meaning_question (45-70) | \
opinion_or_choice_request (55-80) | reason_principle_process_question (70-95) | \
hypothetical_comparison_followup (85-100, hypothesis, comparison or follow-up exploration combined in one \
utterance).
Anchors: 0 "I went hiking yesterday." | 25 "Can you open the file?" | 50 "Is this the correct answer?" | \
75 "What do you think would work better?" | 100 "Why does this happen, and how would it change if we \
removed this step?"

case_type per axis: clear (the dominant meaning and score are stable) | boundary (several readings, but \
one dominates within this utterance) | context_insufficient (the dominant meaning or intent cannot be \
decided without context). Even when context_insufficient, give the levels of the best-supported reading; \
never default to the middle just because information is missing. confidence per axis: integer 0-4, higher \
= more certain (recorded separately; it never changes the score).

Return JSON only, with exactly the keys of the response schema."""

USER_TEMPLATE = "TARGET utterance: {utterance}"


def _axis_schema(components: list[str], extra: dict | None = None) -> dict:
    props = {c: {"type": "INTEGER"} for c in components}
    props.update(extra or {})
    props["case_type"] = {"type": "STRING", "enum": CASE_TYPES}
    props["confidence"] = {"type": "INTEGER"}
    props["evidence"] = {"type": "STRING"}
    order = list(props)
    return {"type": "OBJECT", "properties": props, "required": order, "propertyOrdering": order}


TOP_KEYS = ["primary_function", "secondary_function", "function_ambiguous", "language_form",
            "formality", "humor", "curiosity"]
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "primary_function": {"type": "STRING", "enum": FUNCTIONS},
        "secondary_function": {"type": "STRING", "enum": FUNCTIONS + ["none"]},
        "function_ambiguous": {"type": "BOOLEAN"},
        "language_form": {"type": "STRING", "enum": LANGUAGE_FORMS},
        "formality": _axis_schema(list(WEIGHTS["Formality"])),
        "humor": _axis_schema(list(WEIGHTS["Humor"])),
        "curiosity": _axis_schema(
            list(WEIGHTS["Curiosity"]),
            {"curiosity_function": {"type": "STRING", "enum": list(CURIOSITY_CLAMP)}},
        ),
    },
    "required": TOP_KEYS,
    "propertyOrdering": TOP_KEYS,
}
GENERATION_CONFIG = {
    "responseMimeType": "application/json",
    "responseSchema": RESPONSE_SCHEMA,
    "temperature": 0.0,
    "maxOutputTokens": 1024,
    "thinkingConfig": {"thinkingBudget": 0},
}
PROMPT_SHA256 = hashlib.sha256(json.dumps(
    {"model": MODEL, "system": SYSTEM_PROMPT, "user_template": USER_TEMPLATE,
     "generation_config": GENERATION_CONFIG}, sort_keys=True).encode("utf-8")).hexdigest()
SCORER_CODE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
# Only these input fields may be copied into an output row (never text or human labels).
META_FIELDS = ["item_id", "calibration_set", "split", "round1_no", "context_exposed", "source",
               "source_group", "source_record_id", "selection_reason"]


def sha256_text(text: str | None) -> str | None:
    return None if text is None else hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_api_key() -> str:
    for line in (ROOT / "backend/.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("GOOGLE_AI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("GOOGLE_AI_API_KEY not found in backend/.env")


_LAST_REQUEST_START = [0.0]


def throttle() -> None:
    """At least CALL_INTERVAL_S between ANY two request starts, retries included."""
    wait = _LAST_REQUEST_START[0] + CALL_INTERVAL_S - time.time()
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_START[0] = time.time()


def call_gemini(api_key: str, utterance: str) -> dict:
    """One accepted annotation attempt with bounded transport retries.

    The key travels in a header so no exception message or log can contain it.
    Returns {"raw_text", "finish_reason", "model_version", "attempts"} or
    {"error", "raw_text", "attempts"}; it never raises for transport problems.
    """
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": USER_TEMPLATE.format(utterance=utterance)}]}],
        "generationConfig": GENERATION_CONFIG,
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    attempts = []
    status, body = None, ""
    for n in range(1, MAX_ATTEMPTS + 1):
        throttle()
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        t0 = time.time()
        try:
            resp = requests.post(url, json=payload, headers={"x-goog-api-key": api_key}, timeout=60)
            status, body, transport_error = resp.status_code, resp.text, None
        except requests.RequestException as exc:
            status, body, transport_error = None, "", type(exc).__name__
        attempts.append({"n": n, "started_utc": started, "elapsed_s": round(time.time() - t0, 2),
                         "http_status": status, "transport_error": transport_error})
        if status == 200 or (status is not None and status not in (429, 500, 503)):
            break
        if n < MAX_ATTEMPTS:
            time.sleep(max(0, 2 ** (n + 1) - CALL_INTERVAL_S))  # backoff on top of the throttle
    if status != 200:
        return {"error": f"request failed after {len(attempts)} attempt(s): "
                         f"{attempts[-1]['transport_error'] or 'HTTP ' + str(status)}",
                "raw_text": body[:2000], "attempts": attempts}
    try:
        data = json.loads(body)
        cand = data["candidates"][0]
        raw = "".join(p["text"] for p in cand["content"]["parts"] if not p.get("thought", False)).strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        return {"error": f"unreadable response envelope ({type(exc).__name__})", "raw_text": body[:2000],
                "attempts": attempts}
    return {"raw_text": raw, "finish_reason": cand.get("finishReason"),
            "model_version": data.get("modelVersion"), "attempts": attempts}


def round_to_5_half_up(x100: int) -> int:
    """x100 = score * 100 as an exact integer; nearest multiple of 5, ties up."""
    return (x100 + 250) // 500 * 5


def _strict_int(v, lo: int, hi: int, name: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise ValueError(f"{name} must be an integer {lo}-{hi}")
    return v


def compute_labels(parsed) -> dict:
    """Validate the model's structured answer and do all arithmetic here.

    Raises ValueError on any violation; the caller records an explicit error
    row, never a guessed score. Messages never echo model text.
    """
    if not isinstance(parsed, dict) or sorted(parsed) != sorted(TOP_KEYS):
        raise ValueError("top level must be an object with exactly the schema keys")
    if parsed["primary_function"] not in FUNCTIONS:
        raise ValueError("bad primary_function")
    if parsed["secondary_function"] not in FUNCTIONS + ["none"]:
        raise ValueError("bad secondary_function")
    if not isinstance(parsed["function_ambiguous"], bool):
        raise ValueError("function_ambiguous must be boolean")
    if parsed["language_form"] not in LANGUAGE_FORMS:
        raise ValueError("bad language_form")
    out = {"axes": {}, "case_type": {}, "score_status": {}, "confidence": {}, "components": {}, "evidence": {},
           "primary_function": parsed["primary_function"], "secondary_function": parsed["secondary_function"],
           "function_ambiguous": parsed["function_ambiguous"], "language_form": parsed["language_form"]}
    for axis in AXES:
        block = parsed[axis.lower()]
        expected = list(WEIGHTS[axis]) + ["case_type", "confidence", "evidence"] + (
            ["curiosity_function"] if axis == "Curiosity" else [])
        if not isinstance(block, dict) or sorted(block) != sorted(expected):
            raise ValueError(f"{axis} block must have exactly the schema keys")
        levels = {c: _strict_int(block[c], 0, 4, f"{axis}.{c}") for c in WEIGHTS[axis]}
        if block["case_type"] not in CASE_TYPES:
            raise ValueError(f"bad {axis}.case_type")
        if not isinstance(block["evidence"], str) or not block["evidence"].strip():
            raise ValueError(f"{axis}.evidence must be a non-empty string")
        x100 = 25 * sum(levels[c] * w for c, w in WEIGHTS[axis].items())
        score = round_to_5_half_up(x100)
        comps = dict(levels, raw_score=x100 / 100)
        if axis == "Curiosity":
            func = block["curiosity_function"]
            if func not in CURIOSITY_CLAMP:
                raise ValueError("bad curiosity_function")
            lo, hi = CURIOSITY_CLAMP[func]
            # Clamp bounds are multiples of 5, so clamp(round(raw)) == round(clamp(raw)).
            comps.update(curiosity_function=func, rounded_before_clamp=score, clamp=[lo, hi])
            score = min(max(score, lo), hi)
        out["axes"][axis] = score
        out["components"][axis] = comps
        out["case_type"][axis] = block["case_type"]
        out["score_status"][axis] = "provisional" if block["case_type"] == "context_insufficient" else "final"
        out["confidence"][axis] = _strict_int(block["confidence"], 0, 4, f"{axis}.confidence")
        out["evidence"][axis] = block["evidence"]
    cfunc = out["components"]["Curiosity"]["curiosity_function"]
    out["function_mismatch"] = (out["primary_function"] in QUESTION_FUNCS and cfunc == "non_question_statement") or (
        out["primary_function"] in NON_QUESTION_FUNCS and cfunc in INQUIRY_CFUNCS)
    return out


def label_one(api_key: str, item: dict, run_meta: dict) -> tuple[dict, dict | None]:
    """Returns (public_row, private_audit_row_or_None)."""
    row = {k: item[k] for k in META_FIELDS if k in item}
    row.update(run_meta)
    result = call_gemini(api_key, item["utterance"])
    raw = result.get("raw_text")
    row.update(attempts=result["attempts"], finish_reason=result.get("finish_reason"),
               model_version=result.get("model_version"), error=result.get("error"))
    if row["error"] is None and row["finish_reason"] != "STOP":
        row["error"] = f"generation not complete (finish_reason={row['finish_reason']})"
    if row["error"] is None:
        try:
            row.update(compute_labels(json.loads(raw)))
        except ValueError as exc:  # json.JSONDecodeError is a ValueError
            row["error"] = f"invalid annotation: {exc}"
    row["raw_response_sha256"] = sha256_text(raw)
    if item["source"] != SB_SOURCE:
        row["raw_response"] = raw
        return row, None
    # CC BY-ND: no SB text (raw output, evidence, error detail) in the public row.
    private = {"item_id": item["item_id"], "raw_response": raw, "evidence": row.pop("evidence", None),
               "error": row["error"], "prompt_sha256": PROMPT_SHA256}
    row["raw_response"] = None
    row["private_audit"] = True
    if row["error"]:
        row["error"] = "failed (detail in private audit)"
    return row, private


def input_manifest(items: list[dict]) -> str:
    return hashlib.sha256(json.dumps([[it["item_id"], it["utterance"]] for it in items],
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def validate_artifact(path: Path, items: list[dict], acquisition_round: str) -> tuple[dict, str]:
    """Strict lineage + coverage check of a finished labeling file.

    Returns ({item_id: latest row}, scorer_code_sha256). Raises on a corrupt
    line, foreign prompt/input/round, mixed scorer code, duplicate successes,
    missing or foreign items. Error rows count as processed (kept visible).
    """
    expected = {"prompt_sha256": PROMPT_SHA256, "input_manifest_sha256": input_manifest(items),
                "acquisition_round": acquisition_round}
    rows = read_rows(path, dict(expected, scorer_code_sha256=None), check_code=False)
    codes = {r["scorer_code_sha256"] for r in rows}
    if len(codes) != 1:
        raise ValueError(f"{path.name}: mixed scorer code hashes {sorted(codes)}")
    latest = {}
    for r in rows:  # a successful retry supersedes an earlier error row
        if not r["error"] or r["item_id"] not in latest:
            latest[r["item_id"]] = r
    ids = {it["item_id"] for it in items}
    missing, foreign = ids - set(latest), set(latest) - ids
    if missing or foreign:
        raise ValueError(f"{path.name}: {len(missing)} items missing, {len(foreign)} foreign items")
    return latest, codes.pop()


def read_rows(path: Path, run_meta: dict, check_code: bool = True) -> list[dict]:
    """Strictly read an existing output file for resume; refuse to mix runs."""
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                raise ValueError(f"{path.name} line {n} is corrupt (an interrupted trailing record?); "
                                 "inspect and remove it explicitly before resuming") from None
    keys = ["prompt_sha256", "input_manifest_sha256", "acquisition_round"] + (["scorer_code_sha256"] if check_code else [])
    for key in keys:
        found = {r.get(key) for r in rows}
        if rows and found != {run_meta[key]}:
            raise ValueError(f"refusing to resume {path.name}: {key} differs ({sorted(map(str, found))[:3]} "
                             f"vs current {run_meta[key]}); write to a new file instead")
    ok = Counter(r["item_id"] for r in rows if not r["error"])
    dup = [i for i, c in ok.items() if c > 1]
    if dup:
        raise ValueError(f"{path.name} has duplicate successful rows for {dup[:3]}")
    return rows


def run_labeling(items: list[dict], out_path: Path, private_path: Path | None, acquisition_round: str,
                 limit: int | None) -> None:
    manifest = input_manifest(items)
    run_meta = {"label_source": "gemini_ai_scored", "annotator_model": MODEL, "rubric_version": "v2.2",
                "protocol_version": "v3.1", "acquisition_round": acquisition_round,
                "prompt_sha256": PROMPT_SHA256, "scorer_code_sha256": SCORER_CODE_SHA256,
                "input_manifest_sha256": manifest}
    existing = read_rows(out_path, run_meta)
    done = {r["item_id"] for r in existing if not r["error"]}
    todo = [it for it in items if it["item_id"] not in done][:limit]
    if any(it["source"] == SB_SOURCE for it in todo) and private_path is None:
        raise SystemExit("Santa Barbara items present: pass --private-audit PATH (outside the repo or gitignored)")
    print(f"{len(done)} already labeled in {out_path.name}; labeling {len(todo)} now "
          f"(prompt {PROMPT_SHA256[:12]}, code {SCORER_CODE_SHA256[:12]}, inputs {manifest[:12]})", file=sys.stderr)
    api_key = load_api_key()
    errors = 0
    with out_path.open("a", encoding="utf-8", newline="\n") as f:
        for i, item in enumerate(todo):
            row, private = label_one(api_key, item, run_meta)
            if private is not None:
                with private_path.open("a", encoding="utf-8", newline="\n") as pf:
                    pf.write(json.dumps(private, ensure_ascii=False) + "\n")
                    pf.flush()
                    os.fsync(pf.fileno())
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
            if row["error"]:
                errors += 1
                print(f"  ERROR {item['item_id']}: {row['error']}", file=sys.stderr)
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(todo)} done ({errors} errors)", file=sys.stderr)
    print(f"labeled {len(todo)} items ({errors} errors) -> {out_path}")


# ---------------------------------------------------------------- calibration

def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


CALIBRATION_ROUND = "2026-10-r2-calibration-gemini"
BATCH_ROUND = "2026-10-active-r2-gemini"


def batch_items() -> list[dict]:
    from scripts.fhc_round2_select import hydrate_text
    return hydrate_text(load_jsonl(CANDIDATES_PATH))


def human_items() -> list[dict]:
    """The 221 human rows of the round-1 train/dev split (text + human axes).

    Human axes already omit context_insufficient axes (round-1 build rule).
    context_exposed: round-1 workbook items 1-40 and every seed-100 item were
    scored with the previous turn visible (workbook note; the seed scoring
    sheet has a context_before column) -- a rubric Sec.2 deviation.
    """
    import openpyxl

    sheet = openpyxl.load_workbook(R1_WORKBOOK, read_only=True)["v3_labeling"].iter_rows(values_only=True)
    header = next(sheet)
    workbook_no = {r[header.index("item_id")]: r[header.index("no")] for r in sheet}
    items = []
    for split, path in (("train", TRAIN_SPLIT), ("dev", DEV_SPLIT)):
        for r in load_jsonl(path):
            round1 = r["acquisition_round"] == "2026-10-active-r1"
            no = workbook_no[r["item_id"]] if round1 else None
            items.append({
                "item_id": r["item_id"], "split": split,
                "calibration_set": "round1_single_rater" if round1 else "seed100_consensus",
                "round1_no": no, "context_exposed": (not round1) or no <= 40,
                "source": r["source"], "source_group": r["source_group"], "utterance": r["utterance"],
                "_human_axes": r["axes"],
            })
    if len(items) != 221 or len({it["item_id"] for it in items}) != 221:
        raise ValueError(f"expected 221 unique human items, got {len(items)}")
    return items


def tier(v: float) -> int:
    return 0 if v <= 33 else (1 if v <= 66 else 2)


# Pre-registered (2026-10-12, before any calibration call). Exploratory admission
# rules for using an axis's pseudo-labels in training -- not a reliability claim.
GATE = {"min_spearman": 0.40, "min_qwk": 0.40, "max_false_high": 0.10, "min_tier_recall": 0.50,
        "tier_n": 10, "max_error_rate": 0.05,
        "population": "human TRAIN split, round-1 workbook items 41-150 (blind single-utterance labels), "
                      "axes whose human case_type is not context_insufficient; Gemini numeric score incl. provisional"}


def agreement(pairs: list[tuple[int, int]]) -> dict:
    """pairs = [(human, gemini)] -> agreement metrics (agreement, not accuracy)."""
    from scipy.stats import spearmanr
    from sklearn.metrics import cohen_kappa_score

    h = [p[0] for p in pairs]
    g = [p[1] for p in pairs]
    th, tg = [tier(v) for v in h], [tier(v) for v in g]
    confusion = [[sum(1 for a, b in zip(th, tg) if a == i and b == j) for j in range(3)] for i in range(3)]
    n_low = sum(confusion[0])
    defined = len(set(h)) > 1 and len(set(g)) > 1
    return {
        "n": len(pairs),
        "spearman": float(spearmanr(h, g).statistic) if defined else float("nan"),
        "mae": sum(abs(a - b) for a, b in pairs) / len(pairs),
        "signed_bias_gemini_minus_human": sum(b - a for a, b in pairs) / len(pairs),
        "tier_agreement": sum(a == b for a, b in zip(th, tg)) / len(pairs),
        "qwk": float(cohen_kappa_score(th, tg, labels=[0, 1, 2], weights="quadratic"))
        if len(set(th)) > 1 or len(set(tg)) > 1 else float("nan"),
        "tier_recall": {i: [confusion[i][i] / sum(confusion[i]), sum(confusion[i])]
                        for i in range(3) if sum(confusion[i])},
        "false_high": confusion[0][2] / n_low if n_low else float("nan"),
        "confusion": confusion,
    }


def calibration_rows() -> tuple[list[dict], dict]:
    items = human_items()
    gem, code = validate_artifact(CALIBRATION_OUT, items, CALIBRATION_ROUND)
    for g in gem.values():
        g["_code"] = code
    return items, gem


def pairs_for(items: list[dict], gem: dict, axis: str, keep, final_only: bool = False) -> tuple[list, int, int]:
    """(pairs, n_eligible_human, n_gemini_errors) for items selected by keep()."""
    pairs, eligible, errors = [], 0, 0
    for it in items:
        if not keep(it) or axis not in it["_human_axes"]:
            continue
        eligible += 1
        g = gem[it["item_id"]]
        if g["error"]:
            errors += 1
        elif not final_only or g["score_status"][axis] == "final":
            pairs.append((int(it["_human_axes"][axis]), int(g["axes"][axis])))
    return pairs, eligible, errors


def gate_population(it: dict) -> bool:
    return it["split"] == "train" and it["calibration_set"] == "round1_single_rater" and not it["context_exposed"]


def decide_gate(items: list[dict], gem: dict) -> dict:
    decision = {"pre_registered_rule": GATE, "prompt_sha256": PROMPT_SHA256,
                "scorer_code_sha256": next(iter(gem.values()))["_code"],
                "decided_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "axes": {}}
    for axis in AXES:
        pairs, eligible, errors = pairs_for(items, gem, axis, gate_population)
        if not pairs:
            decision["axes"][axis] = {"passed": False, "reasons": ["no valid human/Gemini pairs"],
                                      "eligible": eligible, "gemini_errors": errors, "metrics": None}
            continue
        m = agreement(pairs)
        reasons = []
        if not errors <= GATE["max_error_rate"] * eligible:
            reasons.append(f"gemini errors {errors}/{eligible}")
        if not m["spearman"] >= GATE["min_spearman"]:  # NaN fails
            reasons.append(f"spearman {m['spearman']:.3f} < {GATE['min_spearman']}")
        if not m["qwk"] >= GATE["min_qwk"]:
            reasons.append(f"qwk {m['qwk']:.3f} < {GATE['min_qwk']}")
        if not (m["false_high"] <= GATE["max_false_high"]):
            reasons.append(f"false_high {m['false_high']:.3f} > {GATE['max_false_high']}")
        for t, (rec, n) in m["tier_recall"].items():
            if n >= GATE["tier_n"] and rec < GATE["min_tier_recall"]:
                reasons.append(f"tier{t} recall {rec:.2f} (n={n}) < {GATE['min_tier_recall']}")
        decision["axes"][axis] = {"passed": not reasons, "reasons": reasons, "eligible": eligible,
                                  "gemini_errors": errors, "metrics": m}
    return decision


def fmt(m: dict) -> str:
    rec = " ".join(f"t{t}={r:.0%}(n{n})" for t, (r, n) in m["tier_recall"].items())
    return (f"n={m['n']:3d} rho={m['spearman']:.3f} QWK={m['qwk']:.3f} MAE={m['mae']:.1f} "
            f"bias={m['signed_bias_gemini_minus_human']:+.1f} tier_agree={m['tier_agreement']:.0%} "
            f"false_high={m['false_high']:.0%} recall[{rec}] confusion(rows=human,cols=Gemini)={m['confusion']}")


def report() -> None:
    items, gem = calibration_rows()
    rows = load_jsonl(CALIBRATION_OUT)
    print(f"calibration file: {len(rows)} rows, {sum(1 for r in rows if r['error'])} error rows, "
          f"prompt {sorted({r['prompt_sha256'][:12] for r in rows})}")
    ok = [g for g in gem.values() if not g["error"]]
    for axis in AXES:
        print(f"  Gemini {axis}: provisional {sum(g['score_status'][axis] == 'provisional' for g in ok)}/{len(ok)}, "
              f"case_type {dict(Counter(g['case_type'][axis] for g in ok))}")
    print(f"  function_mismatch flags: {sum(g['function_mismatch'] for g in ok)}/{len(ok)}")

    # 1) Decide and persist the gate from the pre-registered population only.
    decision = decide_gate(items, gem)
    GATE_PATH.write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n=== GATE (pre-registered; population: {GATE['population']}) -> written to {GATE_PATH.name} ===")
    for axis, d in decision["axes"].items():
        verdict = "PASS -> pseudo-labels admitted to R2 training" if d["passed"] else "FAIL -> excluded from training"
        print(f"  {axis}: {verdict}{'' if d['passed'] else ' | ' + '; '.join(d['reasons'])}")
        if d["metrics"]:
            print(f"    {fmt(d['metrics'])} (eligible {d['eligible']}, gemini errors {d['gemini_errors']})")

    # 2) Diagnostics only, computed after the decision was written.
    print("\n=== DIAGNOSTICS (not used for the decision; agreement is not ground truth) ===")
    subsets = [
        ("gate pop., Gemini-final only", gate_population, True),
        ("train, context-exposed round-1 #1-40", lambda it: it["split"] == "train" and
         it["calibration_set"] == "round1_single_rater" and it["context_exposed"], False),
        ("train, seed consensus (ctx-exposed)", lambda it: it["split"] == "train" and
         it["calibration_set"] == "seed100_consensus", False),
        ("dev35 (all)", lambda it: it["split"] == "dev", False),
        ("all 221", lambda it: True, False),
    ]
    for axis in AXES:
        print(f"-- {axis}")
        for name, keep, final_only in subsets:
            pairs, eligible, errors = pairs_for(items, gem, axis, keep, final_only)
            if pairs:
                print(f"  {name:38s} {fmt(agreement(pairs))} (eligible {eligible}, errors {errors})")
        for src in ("ami_real", "icsi_real", SB_SOURCE):
            pairs, eligible, errors = pairs_for(items, gem, axis, lambda it, s=src: it["source"] == s)
            if pairs:
                print(f"  corpus {src:31s} {fmt(agreement(pairs))}")


# ---------------------------------------------------------------- smoke

ANCHORS = [
    ("Formality", 0, "Fix this for me."),
    ("Formality", 25, "Can you fix this for me?"),
    ("Formality", 50, "Could you help me fix this?"),
    ("Formality", 75, "Could you help me fix this when you have a moment?"),
    ("Formality", 100, "Sorry to bother you, but would you mind helping me fix this when it's convenient?"),
    ("Humor", 0, "I stayed home and watched a movie."),
    ("Humor", 25, "Well, that went great."),
    ("Humor", 50, "My alarm clock and I are in a toxic relationship."),
    ("Humor", 75, "Girl, you ate - and left absolutely no crumbs."),
    ("Humor", 100, "My deadline saw me relaxing and said, 'Absolutely not,' then spawned three side quests."),
    ("Curiosity", 0, "I went hiking yesterday."),
    ("Curiosity", 25, "Can you open the file?"),
    ("Curiosity", 50, "Is this the correct answer?"),
    ("Curiosity", 75, "What do you think would work better?"),
    ("Curiosity", 100, "Why does this happen, and how would it change if we removed this step?"),
]


def smoke(limit: int | None) -> None:
    """Rubric anchors only (they appear in the prompt): API shape + sanity, not agreement evidence."""
    api_key = load_api_key()
    print(f"model={MODEL} prompt_sha256={PROMPT_SHA256[:16]}")
    meta = {"acquisition_round": "smoke"}
    for axis, target, text in ANCHORS[:limit]:
        row, _ = label_one(api_key, {"item_id": f"anchor_{axis}_{target}", "source": "anchor", "utterance": text}, meta)
        if row["error"]:
            print(f"{axis:9s} target={target:3d} ERROR {row['error']}")
        else:
            print(f"{axis:9s} target={target:3d} got={row['axes'][axis]:3d} tier_ok={tier(target) == tier(row['axes'][axis])} "
                  f"| all={row['axes']} case={row['case_type'][axis]} conf={row['confidence'][axis]} "
                  f"func={row['primary_function']} cfunc={row['components']['Curiosity']['curiosity_function']} "
                  f"finish={row['finish_reason']} model={row['model_version']} {row['attempts'][-1]['elapsed_s']}s")


def _self_check() -> None:
    w = lambda axis, levels: round_to_5_half_up(25 * sum(levels[c] * wt for c, wt in WEIGHTS[axis].items()))
    # Arithmetic must match the human workbook's Excel formulas exactly.
    assert w("Formality", {"respect_face": 2, "mitigation": 2, "spoken_register": 2}) == 50
    assert w("Formality", {"respect_face": 2, "mitigation": 0, "spoken_register": 2}) == 35  # 32.5 -> 35
    assert w("Curiosity", {"inquiry_strength": 0, "exploration_depth": 0, "answer_openness": 0,
                           "epistemic_signal": 1}) == 5  # 2.5 -> 5
    assert w("Humor", {c: 4 for c in WEIGHTS["Humor"]}) == 100

    def answer(**over):
        base = {
            "primary_function": "ask_explain_explore", "secondary_function": "none", "function_ambiguous": False,
            "language_form": "standard_or_unmarked",
            "formality": {"respect_face": 2, "mitigation": 2, "spoken_register": 2, "case_type": "clear",
                          "confidence": 3, "evidence": "neutral"},
            "humor": {"playful_framing": 0, "nonliteral_incongruity": 0, "humor_meme_slang_cue": 0,
                      "expressive_reinforcement": 0, "case_type": "context_insufficient", "confidence": 2,
                      "evidence": "literal"},
            "curiosity": {"inquiry_strength": 2, "exploration_depth": 2, "answer_openness": 2,
                          "epistemic_signal": 2, "curiosity_function": "reason_principle_process_question",
                          "case_type": "clear", "confidence": 3, "evidence": "why question"},
        }
        base.update(over)
        return base

    lab = compute_labels(answer())
    assert lab["axes"] == {"Formality": 50, "Humor": 0, "Curiosity": 70}, lab["axes"]  # 50 clamped up to 70
    assert lab["score_status"] == {"Formality": "final", "Humor": "provisional", "Curiosity": "final"}
    assert lab["components"]["Curiosity"]["raw_score"] == 50.0 and not lab["function_mismatch"]
    bad_formality = [dict(answer()["formality"], respect_face=v) for v in (5, True, 2.0, "2")]
    bad = [None, [], answer(function_ambiguous="false"), answer(extra=1)] + [
        answer(formality=f) for f in bad_formality] + [
        answer(humor=dict(answer()["humor"], evidence="")), answer(humor=dict(answer()["humor"], evidence=None))]
    for case in bad:
        try:
            compute_labels(case)
        except ValueError:
            continue
        raise AssertionError(f"accepted invalid answer {case!r}"[:200])
    assert compute_labels(answer(primary_function="inform_describe"))["function_mismatch"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["selfcheck", "smoke", "calibration", "batch", "report"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--private-audit", type=Path, default=None,
                        help="JSONL for Santa Barbara raw responses/evidence; keep it outside the repo or gitignored")
    args = parser.parse_args()
    _self_check()
    if args.command == "selfcheck":
        print(f"self-check passed (prompt {PROMPT_SHA256[:16]}, code {SCORER_CODE_SHA256[:16]})")
    elif args.command == "smoke":
        smoke(args.limit)
    elif args.command == "calibration":
        items = [{k: v for k, v in it.items() if not k.startswith("_")} for it in human_items()]
        run_labeling(items, CALIBRATION_OUT, args.private_audit, CALIBRATION_ROUND, args.limit)
    elif args.command == "batch":
        gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        if gate["prompt_sha256"] != PROMPT_SHA256 or gate["scorer_code_sha256"] != SCORER_CODE_SHA256:
            raise SystemExit("gate was decided with a different prompt/labeler code -- refusing to spend calls")
        if not any(a["passed"] for a in gate["axes"].values()):
            raise SystemExit("no axis passed the calibration gate -- stopping before the batch (D7)")
        run_labeling(batch_items(), PSEUDO_OUT, args.private_audit, BATCH_ROUND, args.limit)
    else:
        report()


if __name__ == "__main__":
    main()
