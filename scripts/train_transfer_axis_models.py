"""Train frozen pretrained embeddings + human-only regression heads.

Run: python -m scripts.train_transfer_axis_models --download-encoder
Later runs are offline: python -m scripts.train_transfer_axis_models
Artifacts and aggregate dev metrics go under gitignored data/models/.
No final-eval predictions are made and no user utterances leave the machine.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import joblib

from ai.embedding_axis_adapter import AXES, DEFAULT_ENCODER, EmbeddingAxisAdapter
from ai.ml_baseline import _load_jsonl_axis_dataset
from ai.ridge_axis_adapter import RidgeAxisAdapter

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data/fixtures"
TRAIN = FIXTURES / "pally_purpose_v3_train_dev_split_train.jsonl"
DEV = FIXTURES / "pally_purpose_v3_train_dev_split_dev.jsonl"
FINAL = FIXTURES / "pally_purpose_v3_eval_partition.jsonl"
ENCODER_DIR = ROOT / "data/models/minilm-base"
OUTPUT_DIR = ROOT / "data/models/transfer-fhc"


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


def series(group: str) -> str:
    return group[:6] if re.fullmatch(r"(?:ES|IS|TS)\d{4}[a-d]", group) else group


def assert_human_labels(rows: list[dict]) -> None:
    for row in rows:
        for axis in row["axes"]:
            source = row["label_source"].get(axis, "")
            if source != "single_rater_v3_eunheay" and not source.startswith("human_consensus"):
                raise ValueError(f"unverified human provenance for {row['item_id']}: {axis}")


def eligible_training_indices(train: list[dict], reserved: list[dict]) -> list[int]:
    if any(not row.get("source_group") for row in train + reserved):
        raise ValueError("source_group is required to prevent meeting leakage")
    groups = {series(row["source_group"].split(".")[0]) for row in reserved}
    texts = {normalized(row["utterance"]) for row in reserved}
    return [i for i, row in enumerate(train)
            if series(row["source_group"].split(".")[0]) not in groups
            and normalized(row["utterance"]) not in texts]


def tier(value: float) -> int:
    return 0 if value <= 33 else 1 if value <= 66 else 2


def metrics(rows: list[dict], predictions: list[dict]) -> dict:
    if len(rows) != len(predictions):
        raise ValueError("prediction count does not match dev rows")
    result = {}
    for axis in AXES:
        confusion = [[0, 0, 0] for _ in range(3)]
        errors = []
        missing = 0
        for row, pred in zip(rows, predictions):
            if axis not in row["axes"]:
                continue
            if pred.get(axis) is None:
                missing += 1
                continue
            gold = row["axes"][axis]
            errors.append(abs(gold - pred[axis]))
            confusion[tier(gold)][tier(pred[axis])] += 1
        support = [sum(r) for r in confusion]
        recalls = [confusion[t][t] / n if n else None for t, n in enumerate(support)]
        supported = [r for r in recalls if r is not None]
        macro = sum(supported) / len(supported) if supported else None
        false_high = confusion[0][2] / support[0] if support[0] else None
        # Never pass an axis with missing predictions or an untested tier.
        if missing:
            gate = "FAIL_MISSING_PREDICTIONS"
        elif any(n < 10 for n in support):
            gate = "INSUFFICIENT_EVIDENCE"
        elif macro >= 0.70 and min(recalls) >= 0.60 and false_high <= 0.10:
            gate = "PASS"
        else:
            gate = "FAIL"
        result[axis] = {
            "n": len(errors), "missing_predictions": missing,
            "mae": sum(errors) / len(errors) if errors else None,
            "macro_recall_observed_tiers": macro, "tier_support": support,
            "tier_recall": recalls, "false_high_rate": false_high,
            "confusion": confusion, "gate": gate,
        }
    return result


def download_encoder() -> None:
    from huggingface_hub import HfApi, snapshot_download

    revision = HfApi().model_info(DEFAULT_ENCODER).sha
    if not revision:
        raise RuntimeError("encoder revision could not be resolved")
    snapshot_download(
        DEFAULT_ENCODER, revision=revision, local_dir=ENCODER_DIR,
        allow_patterns=["*.json", "*.txt", "model.safetensors", "1_Pooling/*"],
    )
    (ENCODER_DIR / "pally_source.json").write_text(
        json.dumps({"model": DEFAULT_ENCODER, "revision": revision}, indent=2), encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-encoder", action="store_true")
    args = parser.parse_args()
    if args.download_encoder:
        download_encoder()
    if not (ENCODER_DIR / "pally_source.json").exists():
        raise FileNotFoundError("run with --download-encoder once to install the pretrained encoder")

    train_rows, dev_rows = read_rows(TRAIN), read_rows(DEV)
    assert_human_labels(train_rows + dev_rows)
    # Final labels are not used. Only group/text exclusions protect the holdout.
    reserved = [{"source_group": r["source_group"], "utterance": r["utterance"]}
                for r in read_rows(FINAL)]
    indices = eligible_training_indices(train_rows, dev_rows + reserved)
    examples = _load_jsonl_axis_dataset(TRAIN, allow_partial=True)
    train = [examples[i] for i in indices]
    if not train:
        raise ValueError("no training rows remain after leakage protection")
    print(f"human train={len(train)} (excluded={len(train_rows) - len(train)}), dev={len(dev_rows)}", flush=True)

    baseline = RidgeAxisAdapter(alpha=1.0).fit(train)
    transfer = EmbeddingAxisAdapter(
        alpha=1.0, model_name=str(ENCODER_DIR), local_files_only=True,
    ).fit(train)
    texts = [r["utterance"] for r in dev_rows]
    report = {
        "method": "frozen pretrained sentence encoder + human-only Ridge heads; no RLHF",
        "encoder": json.loads((ENCODER_DIR / "pally_source.json").read_text(encoding="utf-8")),
        "alpha": 1.0, "alpha_selection": "fixed before dev evaluation; no dev tuning",
        "train_count": len(train), "dev_count": len(dev_rows),
        "excluded_train_count": len(train_rows) - len(train),
        "training_label_sources": dict(Counter(v for e in train for v in e.label_source.values())),
        "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (TRAIN, DEV, FINAL)},
        "baseline": metrics(dev_rows, [baseline.predict_partial(t) for t in texts]),
        "transfer": metrics(dev_rows, transfer.predict_many(texts)),
        "limitations": [
            "Dev is exploratory and previously reused; final holdout has not been scored.",
            "Pretrained encoder is English; this experiment does not validate Korean.",
            "Original pretraining corpus overlap is unknown; local split guards cannot rule it out.",
            "PASS requires at least 10 human dev examples in every tier.",
        ],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Save learned heads separately; the immutable encoder lives in ENCODER_DIR.
    joblib.dump({"axis_models": transfer.axis_models, "model_name": str(ENCODER_DIR),
                 "alpha": transfer.alpha, "encoder_source": report["encoder"]}, OUTPUT_DIR / "heads.joblib")
    restored = EmbeddingAxisAdapter.from_artifact(OUTPUT_DIR / "heads.joblib")
    # Reuse the frozen encoder to check serialized heads without loading a second copy.
    restored.encoder = transfer.encoder
    if restored.predict_many(texts) != transfer.predict_many(texts):
        raise RuntimeError("restored regression heads do not reproduce dev predictions")
    report["artifact_roundtrip_verified"] = True
    (OUTPUT_DIR / "metrics.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False))
    print(f"Saved artifacts: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
