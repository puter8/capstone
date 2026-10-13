# -*- coding: utf-8 -*-
"""v3.0 Rubric §7 model comparison, measured on the dev partition only
(never the 31-item eval partition -- that's reserved for the one-time final
report per §5).

Candidates: TfidfKnnAxisRegressor (plain train, and train+week2 ablation) vs
RuleBasedAxisAnalyzer. A Ridge-bundle adapter is a separate, not-yet-built
piece (v3.0 §4 known gap) and is intentionally NOT included here.

Gates applied follow §7.1: per-axis 3x3 tier confusion matrix (matches
PallyCanvas.tsx::tier(): 0-33/34-66/67-100), macro recall >=70%, each tier
with >=10 dev examples individually >=60% recall, and an anti-gaming check
(human-low misread as high) <=10%.
"""
import json
from pathlib import Path

from ai.ml_baseline import AxisTrainingExample, TfidfKnnAxisRegressor, _load_jsonl_axis_dataset
from ai.analyzers import RuleBasedAxisAnalyzer
from ai.ridge_axis_adapter import RidgeAxisAdapter

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "data/fixtures/pally_purpose_v3_train_dev_split_train.jsonl"
DEV_PATH = ROOT / "data/fixtures/pally_purpose_v3_train_dev_split_dev.jsonl"
WEEK2_PATH = ROOT / "data/axis_dataset_week2.jsonl"

AXES = ["Formality", "Humor", "Curiosity"]


def tier(v: float) -> int:
    if v <= 33:
        return 0
    if v <= 66:
        return 1
    return 2


def load_dev_gold() -> list[dict]:
    rows = []
    with DEV_PATH.open(encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def load_week2_examples() -> list[AxisTrainingExample]:
    return _load_jsonl_axis_dataset(WEEK2_PATH, allow_partial=False)


def evaluate(name: str, predict_fn, dev_rows: list[dict]) -> None:
    # confusion[axis][true_tier][pred_tier]
    confusion = {axis: [[0, 0, 0] for _ in range(3)] for axis in AXES}
    skipped = 0
    for row in dev_rows:
        gold = row["axes"]
        pred = predict_fn(row["utterance"])
        for axis in AXES:
            if axis not in gold or pred.get(axis) is None:
                continue
            t_true = tier(gold[axis])
            t_pred = tier(pred[axis])
            confusion[axis][t_true][t_pred] += 1

    print(f"\n=== {name} ===")
    for axis in AXES:
        m = confusion[axis]
        n_total = sum(sum(row) for row in m)
        recalls = []
        tier_notes = []
        well_sampled_tier_failed = False
        tiers_with_evidence = 0
        for t in range(3):
            n_t = sum(m[t])
            if n_t == 0:
                tier_notes.append(f"tier{t}=n/a(0)")
                continue
            tiers_with_evidence += 1
            recall_t = m[t][t] / n_t
            recalls.append(recall_t)
            if n_t >= 10:
                flag = "OK" if recall_t >= 0.60 else "FAIL(<60%,n>=10)"
                if recall_t < 0.60:
                    well_sampled_tier_failed = True
            else:
                flag = "insufficient evidence (n<10)"
            tier_notes.append(f"tier{t}=n{n_t} recall{recall_t:.0%} {flag}")
        macro_recall = sum(recalls) / len(recalls) if recalls else float("nan")
        # anti-gaming: human tier0 (low) predicted as tier2 (high)
        n_low = sum(m[0])
        false_high = m[0][2] / n_low if n_low else float("nan")
        anti_gaming_ok = n_low == 0 or false_high <= 0.10
        if tiers_with_evidence < 3:
            gate = "INSUFFICIENT_EVIDENCE (not all 3 tiers have >=1 dev example)"
        elif not recalls or macro_recall < 0.70 or well_sampled_tier_failed or not anti_gaming_ok:
            gate = "FAIL"
        else:
            gate = "PASS"
        print(f"  {axis}: n={n_total} macro_recall={macro_recall:.2%} false_high_rate={false_high:.2%} [{gate}]")
        print(f"    {' | '.join(tier_notes)}")
        print(f"    confusion (rows=true 0/1/2, cols=pred 0/1/2): {m}")


def main() -> None:
    dev_rows = load_dev_gold()
    print(f"dev set: {len(dev_rows)} items")

    train_examples = _load_jsonl_axis_dataset(TRAIN_PATH, allow_partial=True)
    knn = TfidfKnnAxisRegressor(k=5).fit(train_examples)
    evaluate("TfidfKnn (train only, n=%d)" % len(train_examples), knn.predict_partial, dev_rows)

    week2_examples = load_week2_examples()
    knn_week2 = TfidfKnnAxisRegressor(k=5).fit(train_examples + week2_examples)
    evaluate("TfidfKnn (train + week2, n=%d)" % (len(train_examples) + len(week2_examples)), knn_week2.predict_partial, dev_rows)

    rule = RuleBasedAxisAnalyzer()

    def rule_predict(utterance: str) -> dict:
        result = rule.analyze(utterance)
        return {axis: getattr(result, axis) for axis in AXES}

    evaluate("RuleBasedAxisAnalyzer", rule_predict, dev_rows)

    ridge = RidgeAxisAdapter(alpha=1.0).fit(train_examples)
    evaluate("RidgeAxisAdapter (train only, n=%d)" % len(train_examples), ridge.predict_partial, dev_rows)


if __name__ == "__main__":
    main()
