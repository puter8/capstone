# -*- coding: utf-8 -*-
"""Separate Gemini pseudo-label augmentation experiment, evaluated on HUMAN dev
labels: a paired development-set comparison of R1 vs R2.

R1 = round-1 conditions exactly (scripts/compare_purpose_v3_models.py).
R2 = human train split + Gemini pseudo-labels (fhc_round2_label.py batch):
     only final (non-provisional) axes of axes that PASSED the pre-registered
     calibration gate (read from GATE_PATH, decided before any dev diagnostic).
     Accepted pseudo targets have unit weight. Both adapters fit shared TF-IDF
     statistics on all supplied rows, so a REJECTED axis is predicted by the R1
     model -- it stays exactly at R1.
R1 vs R2 tests the whole package (extra rows, Gemini supervision, selection,
corpus mixture); it does not isolate the value of active selection.

Evaluation reuses compare_purpose_v3_models.evaluate() unchanged on the 35
human dev items, after asserting every gold axis has a finite prediction
(evaluate() silently skips missing ones). The protected eval partition is read
only to assert that no training row touches its meetings or texts.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.analyzers import RuleBasedAxisAnalyzer
from ai.ml_baseline import AxisTrainingExample, TfidfKnnAxisRegressor, _load_jsonl_axis_dataset
from ai.ridge_axis_adapter import RidgeAxisAdapter
from scripts.compare_purpose_v3_models import TRAIN_PATH, evaluate, load_dev_gold, load_week2_examples
from scripts.fhc_round2_label import (
    AXES, BATCH_ROUND, GATE_PATH, PROMPT_SHA256, PSEUDO_OUT, batch_items, load_jsonl, tier, validate_artifact)
from scripts.fhc_round2_select import (
    DEV_SPLIT, EVAL_PARTITION, ami_series, hydrate_text, is_near_dup, protected_meetings, word_set)
from scripts.select_purpose_v3_active_candidates import normalize_text

BOOTSTRAP = 2000


def reserved():
    rows = load_jsonl(DEV_SPLIT) + load_jsonl(EVAL_PARTITION)
    return [normalize_text(r["utterance"]) for r in rows], [word_set(r["utterance"]) for r in rows]


def overlap_report(name: str, texts: list[str], exact: set, near: list) -> tuple[int, int]:
    n_exact = sum(normalize_text(t) in exact for t in texts)
    n_near = sum(is_near_dup(word_set(t), near) for t in texts)
    print(f"  {name}: {len(texts)} rows, exact text overlap with dev/eval {n_exact}, near-dup {n_near}")
    return n_exact, n_near


def load_pseudo(passing: list[str], gate: dict) -> list[AxisTrainingExample]:
    items = batch_items()
    cands = {r["item_id"]: r for r in items}
    # Strict lineage: same prompt + labeler code as the gate, exact candidate manifest, full coverage.
    latest, code = validate_artifact(PSEUDO_OUT, items, BATCH_ROUND)
    if gate["prompt_sha256"] != PROMPT_SHA256 or code != gate["scorer_code_sha256"]:
        raise AssertionError("pseudo labels were not produced by the prompt/code the gate was decided with")
    rows = load_jsonl(PSEUDO_OUT)
    protected = protected_meetings()
    series = {ami_series(g) for g in protected}
    leaks = [i for i, r in latest.items() if r["source_group"] in protected or ami_series(r["source_group"]) in series]
    if leaks:
        raise AssertionError(f"{len(leaks)} pseudo rows come from protected meetings/series: {leaks[:5]}")

    examples, table = [], Counter()
    for item_id, r in latest.items():
        cand = cands[item_id]
        if r["error"]:
            table[("ALL", cand["source"], cand["selection_reason"], "gemini_error")] += 1
            continue
        label = {}
        for a in AXES:
            status = r["score_status"][a]
            if a not in passing:
                status = "axis_rejected_by_gate"
            elif status == "final":
                label[a] = r["axes"][a]
                status = f"accepted_tier{tier(r['axes'][a])}"
            table[(a, cand["source"], cand["selection_reason"], status)] += 1
        if label:
            examples.append(AxisTrainingExample(
                utterance=cand["utterance"], label=label, style="conversation", source=r["source"],
                source_group=r["source_group"], label_source={a: "gemini_ai_scored" for a in label}))
    print(f"pseudo rows: {len(rows)} lines / {len(latest)} items -> {len(examples)} training examples")
    for a in ["ALL"] + AXES:
        rows_a = {k: v for k, v in table.items() if k[0] == a}
        if not rows_a:
            continue
        status = Counter()
        for (_, _, _, st), v in rows_a.items():
            status[st] += v
        print(f"  {a} status: {dict(sorted(status.items()))}")
        for idx, label in ((1, "source"), (2, "reason")):
            agg = Counter()
            for k, v in rows_a.items():
                if k[3].startswith("accepted"):
                    agg[(k[idx], k[3][-1])] += v
            groups = sorted({g for g, _ in agg})
            print(f"    accepted tiers 0/1/2 by {label}: " +
                  "; ".join(f"{g} {[agg[(g, t)] for t in '012']}" for g in groups))
    return examples


def predictions(model, dev_rows: list[dict]) -> dict:
    """utterance -> {axis: value}; asserts finite coverage of every gold axis."""
    out = {}
    for row in dev_rows:
        pred = model(row["utterance"])
        for a in row["axes"]:
            if a in AXES and (pred.get(a) is None or not math.isfinite(pred[a])):
                raise AssertionError(f"missing/non-finite {a} prediction for dev item {row['item_id']}")
        out[row["utterance"]] = pred
    return out


def macro_recall(rows: list[tuple]) -> float:
    by = {}
    for t_true, t_pred in rows:
        by.setdefault(t_true, []).append(t_true == t_pred)
    return sum(sum(v) / len(v) for v in by.values()) / len(by)


def paired_bootstrap(dev_rows, p1: dict, p2: dict, axis: str, rng: random.Random) -> str:
    """Macro-recall difference R2-R1, resampling AMI-series/meeting clusters."""
    clusters = {}
    for row in dev_rows:
        if axis in row["axes"]:
            t = tier(row["axes"][axis])
            clusters.setdefault(ami_series(row["source_group"]), []).append(
                (t, tier(p1[row["utterance"]][axis]), tier(p2[row["utterance"]][axis])))
    keys = sorted(clusters)
    r1 = lambda xs: macro_recall([(t, a) for t, a, _ in xs])
    r2 = lambda xs: macro_recall([(t, b) for t, _, b in xs])
    everything = [x for k in keys for x in clusters[k]]
    point = r2(everything) - r1(everything)
    diffs = []
    for _ in range(BOOTSTRAP):
        sample = [x for k in rng.choices(keys, k=len(keys)) for x in clusters[k]]
        diffs.append(r2(sample) - r1(sample))
    diffs.sort()
    lo, hi = diffs[int(0.025 * BOOTSTRAP)], diffs[int(0.975 * BOOTSTRAP) - 1]
    return (f"R2-R1 macro recall {point:+.1%} (95% cluster-bootstrap CI {lo:+.1%}..{hi:+.1%}, "
            f"{len(keys)} clusters, P(diff>0)={sum(d > 0 for d in diffs) / BOOTSTRAP:.2f})")


def main() -> None:
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    passing = [a for a in AXES if gate["axes"][a]["passed"]]
    for a in AXES:
        g = gate["axes"][a]
        print(f"calibration gate {a}: {'PASS' if g['passed'] else 'FAIL ' + '; '.join(g['reasons'])}")
    if not passing:
        raise SystemExit("no axis passed the pre-registered calibration gate -- stopping before training (D7)")

    dev_rows = load_dev_gold()
    if len({r["utterance"] for r in dev_rows}) != len(dev_rows):
        raise AssertionError("dev utterances are not unique")
    train = _load_jsonl_axis_dataset(TRAIN_PATH, allow_partial=True)
    week2 = load_week2_examples()
    pseudo = load_pseudo(passing, gate)

    print("training-input overlap with dev/eval texts (pseudo must be 0/0):")
    exact, near = reserved()
    exact = set(exact)
    overlap_report("human train186", [e.utterance for e in train], exact, near)
    overlap_report("week2", [e.utterance for e in week2], exact, near)
    if overlap_report("pseudo", [e.utterance for e in pseudo], exact, near) != (0, 0):
        raise AssertionError("pseudo rows overlap dev/eval texts")
    print(f"dev {len(dev_rows)} | human train {len(train)} | week2 {len(week2)} | pseudo {len(pseudo)} "
          f"| pseudo axes admitted: {passing}")

    rng = random.Random(20261013)
    conditions = [
        ("TfidfKnn", lambda ex: TfidfKnnAxisRegressor(k=5).fit(ex), []),
        ("TfidfKnn + week2", lambda ex: TfidfKnnAxisRegressor(k=5).fit(ex), week2),
        ("RidgeAxisAdapter", lambda ex: RidgeAxisAdapter(alpha=1.0).fit(ex), []),
    ]
    summary = []
    for name, fit, extra in conditions:
        r1 = fit(train + extra)
        r2 = fit(train + extra + pseudo)
        p1 = predictions(r1.predict_partial, dev_rows)

        def r2_predict(u, r1=r1, r2=r2):
            a2, a1 = r2.predict_partial(u), r1.predict_partial(u)
            return {a: (a2 if a in passing else a1)[a] for a in AXES}

        p2 = predictions(r2_predict, dev_rows)
        evaluate(f"R1 {name} (n={len(train) + len(extra)})", p1.__getitem__, dev_rows)
        evaluate(f"R2 {name} (n={len(train) + len(extra) + len(pseudo)}; rejected axes = R1)", p2.__getitem__, dev_rows)
        for a in AXES:
            summary.append(f"  {name:17s} {a:9s} {paired_bootstrap(dev_rows, p1, p2, a, rng)}"
                           f"{'' if a in passing else '  [axis rejected: R2 == R1 by construction]'}")
    rule = RuleBasedAxisAnalyzer()
    p_rule = predictions(lambda u: {a: getattr(rule.analyze(u), a) for a in AXES}, dev_rows)
    evaluate("RuleBasedAxisAnalyzer (no training; identical in R1 and R2)", p_rule.__getitem__, dev_rows)
    print("\n=== paired R2 vs R1 on human dev (uncertainty; n=35 is small) ===")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
