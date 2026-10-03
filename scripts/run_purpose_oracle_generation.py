# -*- coding: utf-8 -*-
"""Generate a third "purpose_oracle" condition for the 20 final-test items:
same generation approach as run_purpose_aware_generation.py's condition B
(purpose_aware), but the purpose line uses the HUMAN-LABELED `purpose_primary`
instead of the classifier's `predicted_purpose`. Axis values are reused
verbatim from the existing B-condition row in
data/fixtures/pally_purpose_v1_responses.jsonl (not re-predicted).

This is a diagnostic-only script (see task): it does not modify
run_purpose_aware_generation.py or its outputs.

Usage:
  python scripts/run_purpose_oracle_generation.py --test-one   # one real call, print, eyeball
  python scripts/run_purpose_oracle_generation.py               # all 20, real Gemini calls
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_purpose_aware_generation import ROOT, build_payload, gemini_generate, load_key  # noqa: E402

ITEMS_PATH = ROOT / "data" / "fixtures" / "pally_purpose_v1_items_100.jsonl"
RESPONSES_PATH = ROOT / "data" / "fixtures" / "pally_purpose_v1_responses.jsonl"
OUT_PATH = ROOT / "data" / "fixtures" / "pally_purpose_v1_responses_oracle.jsonl"


def load_final_test_pairs() -> list[tuple[dict, dict]]:
    """Return (item, condition_b_response_row) pairs for the 20 final_test items,
    in item file order."""
    items = [json.loads(l) for l in ITEMS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    final_items = [r for r in items if r.get("split") == "final_test"]

    resp_rows = [json.loads(l) for l in RESPONSES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    b_by_item = {r["item_id"]: r for r in resp_rows if r["condition"] == "purpose_aware"}

    pairs = []
    for item in final_items:
        b = b_by_item.get(item["item_id"])
        if b is None:
            raise ValueError(f"no purpose_aware response found for {item['item_id']}")
        pairs.append((item, b))
    return pairs


def make_oracle_payload(item: dict, b_response_row: dict) -> dict:
    """Reuse build_payload's exact prompt construction (condition='purpose_aware'
    branch adds the purpose line) but with the HUMAN purpose_primary substituted
    for predicted_purpose, and the SAME predicted_axes as condition B. Relabels
    the resulting payload's condition to 'purpose_oracle' afterward."""
    human_purpose = item["purpose_primary"]
    axes = b_response_row["predicted_axes"]
    payload = build_payload(item, human_purpose, axes, "purpose_aware")
    payload["condition"] = "purpose_oracle"
    payload["human_purpose"] = human_purpose
    payload["classifier_predicted_purpose"] = b_response_row["predicted_purpose"]
    return payload


def generate_one(item: dict, b_response_row: dict, key: str) -> dict:
    payload = make_oracle_payload(item, b_response_row)
    response = gemini_generate(payload["system_prompt"], item.get("context_before"), item["target_turn"], key)
    return {**payload, "response": response}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-one", action="store_true", help="run only the first item, print, no file write")
    args = parser.parse_args()

    pairs = load_final_test_pairs()
    key = load_key()

    if args.test_one:
        item, b = pairs[0]
        result = generate_one(item, b, key)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("\nNOTE: hand-inspect this single real call before running the full batch (CLAUDE.md Sec.4).")
        return

    results = [generate_one(item, b, key) for item, b in pairs]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"generated {len(results)} purpose_oracle responses -> {OUT_PATH}")


if __name__ == "__main__":
    main()
