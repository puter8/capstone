"""Durable, bounded local voice measurement. Closed snapshots never change."""
from __future__ import annotations

import asyncio
import base64
from dataclasses import asdict
import hashlib
from io import BytesIO
import logging
import threading
import wave

from ai.voice_energy import (
    ALGORITHM_VERSION, MAX_SECONDS, MAX_WAV_BYTES, SAMPLE_RATE, ClipMeasurement,
    make_baseline, measure_wav,
)

_guard = threading.Lock()


def pending_audio(audio_bytes: bytes) -> dict:
    if not isinstance(audio_bytes, bytes) or len(audio_bytes) > MAX_WAV_BYTES:
        raise ValueError("WAV exceeds the supported size")
    try:
        with wave.open(BytesIO(audio_bytes), "rb") as source:
            if (source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getcomptype()) != (1, 2, SAMPLE_RATE, "NONE"):
                raise ValueError("Voice Energy requires mono PCM16 16 kHz WAV")
            frames = source.getnframes()
            if not 0 < frames <= SAMPLE_RATE * MAX_SECONDS:
                raise ValueError("WAV must contain nonempty audio of at most thirty seconds")
            if len(source.readframes(frames)) != frames * 2:
                raise ValueError("Truncated WAV audio")
    except (wave.Error, EOFError) as exc:
        raise ValueError("Invalid WAV audio") from exc
    return {"status": "pending", "method": ALGORITHM_VERSION,
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_sha256": hashlib.sha256(audio_bytes).hexdigest()}


def get_baseline(sb, user_id: str) -> dict | None:
    rows = sb.table("voice_energy_baselines").select("*").eq("user_id", user_id).execute().data
    return rows[0] if rows else None


def save_baseline(sb, user_id: str, measurements: list[ClipMeasurement]) -> dict:
    if len(measurements) != 3:
        raise ValueError("baseline requires exactly three clips")
    baseline = make_baseline(measurements)
    result = sb.rpc("save_voice_energy_baseline", {
        "p_user_id": user_id, "p_range_st": baseline.range_st,
        "p_measurements": [asdict(item) for item in measurements],
        "p_method": ALGORITHM_VERSION,
    }).execute().data
    if not isinstance(result, dict) or result.get("user_id") != user_id:
        raise ValueError("Invalid baseline response")
    return result


def latest_snapshot(sb, user_id: str) -> dict | None:
    rows = (sb.table("voice_energy_snapshots").select("*").eq("user_id", user_id)
            .order("created_at", desc=True).limit(1).execute().data)
    return rows[0] if rows else None


def process_pending(get_db, limit: int = 1) -> dict:
    counts = {"processed": 0, "failed": 0, "skipped": 0}
    if not _guard.acquire(blocking=False):
        counts["skipped"] = 1
        return counts
    try:
        sb = get_db()
        for _ in range(max(0, min(limit, 10))):
            jobs = sb.rpc("claim_voice_energy_job", {}).execute().data or []
            if not jobs:
                break
            job = jobs[0]
            payload = job["voice_energy"]
            try:
                audio = base64.b64decode(payload["audio_base64"], validate=True)
                if hashlib.sha256(audio).hexdigest() != payload["audio_sha256"]:
                    raise ValueError("Audio identity mismatch")
                measured = measure_wav(audio)
                result = {**asdict(measured), "status": "ready" if measured.range_st is not None else "missing",
                          "method": ALGORITHM_VERSION, "audio_sha256": payload["audio_sha256"]}
            except Exception as exc:
                logging.exception("Voice Energy measurement failed for turn %s", job["id"])
                counts["failed"] += 1
                result = {"status": "error", "missing_reason": "measurement_failed",
                          "error_type": type(exc).__name__, "method": ALGORITHM_VERSION,
                          "audio_sha256": payload.get("audio_sha256")}
            saved = sb.rpc("finish_voice_energy_job", {
                "p_message_id": job["id"], "p_token": payload["claim_token"], "p_result": result,
            }).execute().data
            counts["processed" if saved else "skipped"] += 1
    except Exception:
        logging.exception("Voice Energy queue failed; leased jobs remain recoverable")
        counts["failed"] += 1
    finally:
        _guard.release()
    return counts


async def worker(get_db, stop: asyncio.Event) -> None:
    while not stop.is_set():
        await asyncio.to_thread(process_pending, get_db)
        try:
            await asyncio.wait_for(stop.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass
