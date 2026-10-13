"""Reproduce the supplied ten-clip experiment without APIs or human-truth claims."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ai.voice_energy import ALGORITHM_VERSION, measure_wav, score_delta

ATTACHED_RANGES = [3.5, 2.2, 1.9, 5.1, 6.9, 4.8, 4.9, 3.8, 4.2, 6.1]


def simulate(values):
    import numpy as np
    rng = random.Random(1)
    deltas, scores = [], []
    for _ in range(4000):
        ids = rng.sample(range(len(values)), 8)
        delta = float(np.median([values[i] for i in ids[3:]]) - np.median([values[i] for i in ids[:3]]))
        deltas.append(delta)
        scores.append(score_delta(delta))
    tiers = [0 if s <= 33 else 1 if s <= 66 else 2 for s in scores]
    return {"repetitions": 4000, "seed": 1, "baseline_clips": 3, "session_clips": 5,
            "delta_percentiles_5_50_95": np.percentile(deltas, [5, 50, 95]).tolist(),
            "tier_share_low_mid_high": [tiers.count(k) / 4000 for k in range(3)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recordings", type=Path, default=ROOT / "data/fixtures/녹음 결과")
    parser.add_argument("--output", type=Path, default=ROOT / "data/models/voice-energy-validation/report.json")
    args = parser.parse_args()
    files = sorted(args.recordings.glob("energy_rec_*.wav"))
    if len(files) != 10:
        raise ValueError("expected the ten supplied recordings")
    records = []
    for path in files:
        payload = path.read_bytes()
        started = time.perf_counter()
        measurement = measure_wav(payload)
        records.append({"file": path.name, "sha256": hashlib.sha256(payload).hexdigest(),
                        "seconds": time.perf_counter() - started, **asdict(measurement)})
        print(path.name, measurement.range_st, flush=True)
    values = [r["range_st"] for r in records if r["range_st"] is not None]
    if len(values) != 10:
        raise ValueError("not all supplied recordings produced a measurement")
    import librosa
    import numpy as np
    rounded = [round(v, 1) for v in values]
    report = {"algorithm_version": ALGORITHM_VERSION, "librosa_version": librosa.__version__,
              "records": records, "valid_clips": len(values), "raw_ranges": values,
              "rounded_ranges": rounded, "attached_ranges": ATTACHED_RANGES,
              "max_absolute_difference_from_attached_rounded": max(abs(a-b) for a,b in zip(values, ATTACHED_RANGES)),
              "rounded_ranges_match_attachment": rounded == ATTACHED_RANGES,
              "median_range_st": float(np.median(values)), "range_sd": float(np.std(values)),
              "exact_simulation": simulate(values), "rounded_simulation": simulate(rounded),
              "attached_rounded_simulation": simulate(ATTACHED_RANGES),
              "limitations": ["One person, one recording occasion, ten clips; not independent sessions.",
                  "Resampling stability is not accuracy or human agreement.",
                  "Folding is a heuristic, not confirmed octave error correction.",
                  "Local timing does not establish production response latency.",
                  "Only WAV files measured; no proof of WEBM-to-WAV lineage."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("valid_clips", "rounded_ranges_match_attachment", "exact_simulation", "rounded_simulation")}, indent=2))


if __name__ == "__main__":
    main()
