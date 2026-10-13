# -*- coding: utf-8 -*-
"""AI-scores the 70-item Humor rescue candidate shortlist using the existing
deterministic rubric (docs/AI_TACTIC/Pally_RUBRIC_v2.2_md Sec.9), via a
Gemini 2.5 Flash-Lite call per item (same REST pattern as backend/main.py).

Provenance is explicit: label_source="gemini_ai_scored", annotator_model=
"gemini-2.5-flash-lite" in every output row -- Gemini makes the subjective
component judgments, not Claude, so the provenance names the actual model
(Codex correction, 2026-10-12). This is NOT human-rated ground truth -- per
this project's own history with mislabeled "human" scores, never call this
a human label. It is useful as triage / rubric debugging / a separately-
reported pseudo-label experiment, not as the final human tier-recall
evidence Energy/Humor unfreezing needs (rubric v2.2's main human-grounded
experiment explicitly excludes pseudo-labels like this one). Every AI-made
column is prefixed `ai_` (plus case_type/score_status/provenance) so it can
never be mistaken for a human score column.

The model only scores the 4 rubric COMPONENTS (0/2/4) with brief evidence;
the final weighted Humor score is computed deterministically in this script,
never trusted from the model's own arithmetic.

Output is written one row at a time (flush + fsync) with a fixed schema, so a
crash or an API error never loses finished calls. Re-running skips item_ids
already present in the output; an API/parse failure is written as an explicit
row with `ai_error` set (the error row is kept as audit history and the item is retried on the next run).

Usage:
  python scripts/score_humor_rescue_candidates.py                  # resume into the fixture
  python scripts/score_humor_rescue_candidates.py --out X.csv --limit 2
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time

import requests

HERE = os.path.dirname(__file__)
IN_CSV = os.path.join(HERE, "..", "data", "fixtures", "pally_humor_rescue_candidates.csv")
OUT_CSV = os.path.join(HERE, "..", "data", "fixtures", "pally_humor_rescue_candidates_ai_scored.csv")
MODEL = "gemini-2.5-flash-lite"
# Shared per-project Gemini quota with production: cap experiments at 10 requests/min.
CALL_INTERVAL_S = 6.0

# Columns copied verbatim from the candidate (mining) CSV.
CANDIDATE_FIELDS = [
    "item_id", "pool", "fhc_partition", "meeting_id", "speaker", "previous_turn",
    "utterance", "next_turn", "annotation_events",
]
# Columns this script adds. Fixed up front: an error row must never introduce
# a new key mid-run (that made csv.DictWriter raise after all calls were made).
AI_FIELDS = [
    "ai_humor_score_0_100", "case_type", "score_status",
    "ai_playful_framing", "ai_nonliteral_incongruity",
    "ai_humor_meme_slang_cue", "ai_expressive_reinforcement",
    "ai_evidence", "ai_error", "label_source", "annotator_model", "rubric_version", "prompt_sha256",
]
OUT_FIELDS = CANDIDATE_FIELDS + AI_FIELDS


def load_api_key():
    env_path = os.path.join(HERE, "..", "backend", ".env")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("GOOGLE_AI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("GOOGLE_AI_API_KEY not found in backend/.env")


SYSTEM_PROMPT = """You are scoring ONE conversational utterance for Pally's "Humor" axis, \
using this exact rubric (docs/AI_TACTIC/Pally_RUBRIC_v2.2_md Sec.9). Per that rubric's \
own protocol (Sec.2), you are shown ONLY this single utterance -- no previous/next turn, \
no source corpus, no other scores. Judge only what this utterance itself shows.

Operational definition: how much deliberate playful framing, non-literal meaning, \
incongruity/reversal, wordplay, exaggeration, irony, or playful use of memes/slang is \
observable IN the target utterance. Do NOT measure whether the utterance is trendy, \
whether you personally find it funny, or the speaker's general personality.

Score each of these 4 components as exactly 0, 2, or 4:

1. playful_framing (weight 0.40): 0=literal/neutral delivery, 2=possible playfulness but \
unclear, 4=strong and consistent playful delivery intent.
2. nonliteral_incongruity (weight 0.30): 0=literal meaning only, 2=weak exaggeration or \
ambiguity, 4=wordplay/irony/strong reversal/violated expectation.
3. humor_meme_slang_cue (weight 0.20): 0=no relevant cue, 2=expression present but \
meaning/use unclear, 4=a verifiable slang/meme expression used in a clearly playful sense.
4. expressive_reinforcement (weight 0.10): 0=no reinforcing device, 2=some repetition/ \
rhythm/orthographic variation, 4=a deliberate form that clearly reinforces the playfulness.

Boundary rules from the rubric (apply honestly, don't force a score):
- Mere slang presence alone is NOT sufficient for a high score.
- A simple grammar mistake is NOT evidence of humor by itself.
- Quoting someone else's joke or asking what a slang term means is NOT spontaneous humor use.
- If both a literal and a slang reading are plausible and you cannot tell which, set \
"boundary": true.
- If there is not enough context to judge at all, set "context_insufficient": true.

5-point anchor examples (for calibration only, do not copy these scores mechanically):
- 0: "I stayed home and watched a movie." (no playful/non-literal cues)
- 25: "Well, that went great." (weak, ambiguous possible irony without intonation)
- 50: "My alarm clock and I are in a toxic relationship." (clear personification + mild incongruity)
- 75: "Girl, you ate - and left absolutely no crumbs." (verifiable slang + exaggerated playful praise)
- 100: "My deadline saw me relaxing and said, 'Absolutely not,' then spawned three side quests." (personification + reversal + exaggeration + extended playful framing)

Respond with JSON only:
{"playful_framing": <0|2|4>, "nonliteral_incongruity": <0|2|4>, \
"humor_meme_slang_cue": <0|2|4>, "expressive_reinforcement": <0|2|4>, \
"boundary": <true|false>, "context_insufficient": <true|false>, \
"evidence": "<one short sentence citing the specific words that justify the scores>"}"""

WEIGHTS = {
    "playful_framing": 0.40,
    "nonliteral_incongruity": 0.30,
    "humor_meme_slang_cue": 0.20,
    "expressive_reinforcement": 0.10,
}


def round_to_5(x):
    # With 0/2/4 levels every Humor sum is already a multiple of 5, so the
    # rounding mode never matters here.
    return int(round(x / 5.0) * 5)


PROMPT_SHA256 = hashlib.sha256(json.dumps(
    {"model": MODEL, "system": SYSTEM_PROMPT, "user_template": "TARGET utterance to score: {utterance}"},
    sort_keys=True).encode("utf-8")).hexdigest()


_LAST_REQUEST_START = [0.0]


def call_gemini(api_key, utterance, model=MODEL, attempts=4):
    # Rubric v2.2 Sec.2 is explicit: raters never see previous/next turns,
    # source corpus, other scores -- context-free single-utterance judgment
    # only (Codex correction, 2026-10-12). previous_turn/next_turn stay in
    # the CSV as candidate-mining metadata, never sent to the model here.
    user_text = f"TARGET utterance to score: {utterance}"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.0,
            "maxOutputTokens": 300,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    # Key in a header, never the URL, so exception text cannot leak it.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    status, body, problem = None, "", ""
    for attempt in range(1, attempts + 1):
        # >= CALL_INTERVAL_S between any two request starts, retries included.
        wait = _LAST_REQUEST_START[0] + CALL_INTERVAL_S - time.time()
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST_START[0] = time.time()
        try:
            resp = requests.post(url, json=payload, headers={"x-goog-api-key": api_key}, timeout=30)
            status, body, problem = resp.status_code, resp.text, f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            status, body, problem = None, "", type(exc).__name__
        if status == 200 or (status is not None and status not in (429, 500, 503)):
            break
        if attempt < attempts:
            print(f"  {problem}, retrying", file=sys.stderr)
            time.sleep(max(0, 2 ** (attempt + 1) - CALL_INTERVAL_S))  # backoff on top of the throttle
    if status != 200:
        return {"error": f"{problem} after {attempt} attempt(s): {body[:300]}"}
    try:
        data = json.loads(body)
        cand = data["candidates"][0]
        if cand.get("finishReason") != "STOP":
            return {"error": f"generation not complete (finish_reason={cand.get('finishReason')})"}
        raw = " ".join(p["text"] for p in cand["content"]["parts"] if not p.get("thought", False)).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except (ValueError, KeyError, IndexError, TypeError) as e:
        return {"error": f"parse failed: {type(e).__name__}: {e}"}


def score_row(candidate, result):
    """Build one output row with exactly OUT_FIELDS keys."""
    row = {k: candidate[k] for k in CANDIDATE_FIELDS}
    row.update({k: "" for k in AI_FIELDS})
    # Codex correction (2026-10-12): Gemini made the subjective component
    # judgments, not Claude -- provenance must name the actual model.
    row.update(label_source="gemini_ai_scored", annotator_model=MODEL, rubric_version="v2.2",
               prompt_sha256=PROMPT_SHA256)

    def fail(msg):
        row.update(ai_error=msg, case_type="extraction_error", score_status="missing")
        return row

    if not isinstance(result, dict):
        return fail("model output is not a JSON object")
    if "error" in result:
        return fail(result["error"])
    row.update(
        ai_playful_framing=result.get("playful_framing"),
        ai_nonliteral_incongruity=result.get("nonliteral_incongruity"),
        ai_humor_meme_slang_cue=result.get("humor_meme_slang_cue"),
        ai_expressive_reinforcement=result.get("expressive_reinforcement"),
        ai_evidence=result.get("evidence", ""),
    )
    # Strict types: bool is an int subclass and 2.0 == 2, so check the type exactly.
    bad = [k for k in WEIGHTS if type(result.get(k)) is not int or result[k] not in (0, 2, 4)]
    if bad:
        return fail(f"invalid component value(s): {bad}")
    flags = [k for k in ("boundary", "context_insufficient") if type(result.get(k)) is not bool]
    if flags:
        return fail(f"missing/non-boolean flag(s): {flags}")
    if not isinstance(result.get("evidence"), str):
        return fail("evidence must be a string")
    context_insufficient = result["context_insufficient"]
    # v2.2: context_insufficient still gets a supported provisional numeric
    # score, never an automatic 50 -- the model's attempted component scoring
    # is kept and only marked provisional.
    row.update(
        ai_humor_score_0_100=round_to_5(25 * sum(WEIGHTS[k] * result[k] for k in WEIGHTS)),
        case_type="context_insufficient" if context_insufficient else (
            "boundary" if result["boundary"] else "clear"),
        score_status="provisional" if context_insufficient else "final",
    )
    return row


def read_existing(path):
    """Strict resume read: refuses truncated rows and duplicate successful rows."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != OUT_FIELDS:
            raise ValueError(f"{path} has schema {reader.fieldnames}, expected {OUT_FIELDS}")
        rows = list(reader)
    for n, r in enumerate(rows, start=2):
        if None in r or None in r.values():
            raise ValueError(f"{path} line {n} is truncated/malformed; inspect and fix it explicitly")
    ok = [r["item_id"] for r in rows if not r["ai_error"]]
    dup = {i for i in ok if ok.count(i) > 1}
    if dup:
        raise ValueError(f"{path} has duplicate successful rows: {sorted(dup)[:3]}")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=OUT_CSV)
    parser.add_argument("--limit", type=int, default=None, help="score at most N not-yet-scored rows")
    args = parser.parse_args()

    with open(IN_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    missing_cols = [c for c in CANDIDATE_FIELDS if c not in rows[0]]
    if missing_cols:
        raise ValueError(f"candidate CSV lacks columns {missing_cols}; regenerate it with build_humor_rescue_candidates.py")

    existing = read_existing(args.out)
    # Error rows stay as audit history; their items are retried and appended.
    done = {r["item_id"] for r in existing if not r["ai_error"]}
    todo = [r for r in rows if r["item_id"] not in done][: args.limit]
    print(f"{len(done)} already scored in {args.out}; scoring {len(todo)} now", file=sys.stderr)
    if not todo:
        return
    foreign = {r["prompt_sha256"] for r in existing} - {PROMPT_SHA256}
    if foreign:
        raise ValueError(f"refusing to append: {args.out} holds rows from other prompt(s) {sorted(foreign)}; "
                         "use a new --out")

    api_key = load_api_key()
    write_header = not os.path.exists(args.out)
    with open(args.out, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        if write_header:
            writer.writeheader()
        for i, candidate in enumerate(todo):
            row = score_row(candidate, call_gemini(api_key, candidate["utterance"]))
            writer.writerow(row)
            f.flush()
            os.fsync(f.fileno())
            if row["ai_error"]:
                print(f"  {candidate['item_id']}: {row['ai_error'][:200]}", file=sys.stderr)
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(todo)} done", file=sys.stderr)
    print(f"wrote {len(todo)} new AI-scored rows to {args.out}")


if __name__ == "__main__":
    main()
