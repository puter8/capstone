# -*- coding: utf-8 -*-
import asyncio
import base64
import json
import logging
import os
import re
import sys

import hashlib
import time
import uuid
from collections import deque
from datetime import datetime, time as dtime, timedelta, timezone

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Dict, Optional

load_dotenv()

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ai.analyzer import analyze_utterance
from ai.matrix_engine import apply_ema, compute_character, describe_character

try:
    from lib.supabase import get_supabase
    _SUPABASE_ENABLED = True
except Exception:
    _SUPABASE_ENABLED = False
    get_supabase = None  # type: ignore

# AI 담당 제공: generate_feedback(utterance, pally_reply, level) -> (items, failed).
# 없으면 None → turn 의 feedback 은 [] (실패 아님, 미구현).
try:
    from ai.generate_feedback import generate_feedback
except Exception:
    generate_feedback = None  # type: ignore

# 5축 분석 어댑터 (rule|ml|hybrid, env PALLY_AXIS_ANALYZER, 기본 rule).
# 한 번만 생성해 재사용(ml/hybrid 모델 재로딩 방지). 실패하면 기존 rule 함수로 폴백.
try:
    from ai.analyzers import get_axis_analyzer
    _axis_analyzer = get_axis_analyzer()
except Exception as _axis_e:
    logging.warning(f"axis analyzer init failed → analyze_utterance(rule) fallback: {_axis_e}")
    _axis_analyzer = None


def _analyze_axes(text: str) -> Dict[str, int]:
    """5축 dict. 어댑터(rule/ml/hybrid) 사용, 실패 시 기존 rule 함수로 폴백."""
    if _axis_analyzer is not None:
        try:
            return _axis_analyzer.analyze(text).model_dump()
        except Exception as e:
            logging.warning(f"axis analyzer.analyze failed → rule fallback: {e}")
    return analyze_utterance(text)


GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")    # Gemini (AI Studio)
GOOGLE_CLOUD_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY", "")  # STT / TTS (Cloud Console)

app = FastAPI(title="Pally Backend API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# production에서만 debug route를 숨기려면 PALLY_DEBUG_ENDPOINTS=1 을 설정한 환경에서만 등록.
# Railway 운영 환경에는 이 변수를 두지 않아 /api/debug-keys 가 노출되지 않는다.
_DEBUG_ENDPOINTS_ENABLED = os.getenv("PALLY_DEBUG_ENDPOINTS") == "1"

# 무료 일일 turn 한도. 하드코딩하지 않고 config 로 빼서 정책 변경 시 재배포 없이 조정.
FREE_DAILY_TURNS = int(os.getenv("FREE_DAILY_TURNS", "20"))
_KST = timezone(timedelta(hours=9))  # 한국은 DST 없음 → 고정 UTC+9


# ── Errors — 계약 포맷 { "error": { code, message, request_id, details? } } ────


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Optional[dict] = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def _request_id(request: Request) -> str:
    """미들웨어가 심어둔 request_id를 반환 (없으면 새로 생성)."""
    return getattr(request.state, "request_id", None) or f"req_{uuid.uuid4().hex}"


# ── Observability — 구조화 로그 + turn 단계별 latency ────────────────────────
# 기존 STT/Gemini/TTS 함수는 안 건드리고, 호출부(미들웨어·create_turn)에서 시간만 잰다.

_TURN_METRICS: deque = deque(maxlen=200)  # 최근 turn latency (단일 프로세스 메모리)


def _log_event(event: str, **fields) -> None:
    """구조화 로그 한 줄(JSON). 기존 로그 포맷은 유지하고 새 이벤트만 JSON 문자열로 emit."""
    try:
        logging.info(json.dumps({"event": event, **fields}, ensure_ascii=False, default=str))
    except Exception:
        logging.info(f"event={event} {fields}")


def _pct(values: list, p: int):
    if not values:
        return None
    s = sorted(values)
    k = min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1))))
    return round(s[k])


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = f"req_{uuid.uuid4().hex}"
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # 미들웨어에서 잡힌 예외도 access 로그로 남기고 다시 올린다.
        _log_event(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=500,
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
        raise
    response.headers["X-Request-ID"] = request_id
    _log_event(
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.perf_counter() - started) * 1000),
    )
    return response


def _error_body(code: str, message: str, request_id: str, details: Optional[dict] = None) -> dict:
    error: dict = {"code": code, "message": message, "request_id": request_id}
    if details:
        error["details"] = details
    return {"error": error}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, _request_id(request), exc.details),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # FastAPI 기본 {"detail": ...} 대신 계약 포맷으로 통일.
    return JSONResponse(
        status_code=422,
        content=_error_body(
            "validation_error",
            "Request validation failed.",
            _request_id(request),
            {"errors": exc.errors()},
        ),
    )


# ── Request / Response Models ────────────────────────────────────────────────


class FeedbackRequest(BaseModel):
    utterance: str
    session_id: Optional[str] = None
    current_axes: Optional[Dict[str, int]] = None  # EMA용 이전 누적 축 점수


class FeedbackResponse(BaseModel):
    status: str
    axes: Dict[str, int]             # EMA 적용 후 누적 축 점수
    character: Dict[str, int]        # 캐릭터 파라미터
    character_labels: Dict[str, str]
    feedback: Dict[str, str]         # correction / tone_feedback / practice_prompt
    tts_audio: Optional[str] = None  # base64 MP3 (correction 문장 TTS)


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-Journey-F"
    speaking_rate: Optional[float] = 1.0


class ChatMessage(BaseModel):
    role: str   # "user" | "pally"
    content: str


class ChatRequest(BaseModel):
    utterance: str                              # STT 결과 텍스트 (FE에서 /api/stt 호출 후 전달)
    session_id: Optional[str] = None
    current_axes: Optional[Dict[str, int]] = None
    conversation_history: Optional[list[ChatMessage]] = None
    character_name: Optional[str] = "Pally"
    level: Optional[str] = "B1"                # A2 / B1 / B2 / C1


class InlineHintKo(BaseModel):
    hint: str        # 한국어 힌트 (교정 설명 또는 칭찬)
    expression: str  # 올바른 영어 표현


class ChatResponse(BaseModel):
    status: str
    transcript: str                            # 사용자 발화 텍스트 (echo)
    reply: str                                 # Pally 응답 텍스트
    tts_audio: Optional[str] = None           # base64 MP3 (Pally 응답 TTS)
    axes: Dict[str, int]
    character: Dict[str, int]
    character_labels: Dict[str, str]
    hint_ko: Optional[InlineHintKo] = None    # 인라인 한국어 힌트


# ── Health ───────────────────────────────────────────────────────────────────


@app.get("/api/health")
def health():
    # 계약: liveness만, 환경변수/키 정보 노출 금지.
    return {"status": "ok", "version": app.version}


@app.get("/api/metrics")
def metrics():
    """
    최근 turn 파이프라인 latency 요약 (STT/Gemini/TTS/save/total 의 p50·p95·평균).
    운영 데이터 노출이라 health 와 달리 debug 게이트 뒤에 둔다 (PALLY_DEBUG_ENDPOINTS=1).
    단일 프로세스 메모리 기준(최근 200 turn). 다중 인스턴스면 인스턴스별로만 집계됨.
    """
    if not _DEBUG_ENDPOINTS_ENABLED:
        raise AppError(404, "not_found", "Not found")

    turns = list(_TURN_METRICS)
    stages = ("stt_ms", "gemini_ms", "tts_ms", "feedback_ms", "save_ms", "total_ms")
    summary = {}
    for stage in stages:
        vals = [t[stage] for t in turns if t.get(stage) is not None]
        summary[stage] = {
            "p50": _pct(vals, 50),
            "p95": _pct(vals, 95),
            "avg": round(sum(vals) / len(vals)) if vals else None,
            "max": max(vals) if vals else None,
        }
    return {
        "count": len(turns),
        "stages": summary,
        "recent": turns[-20:],
    }


if _DEBUG_ENDPOINTS_ENABLED:
    # production(Railway)에는 PALLY_DEBUG_ENDPOINTS 미설정 → 이 route 자체가 등록되지 않음.
    @app.get("/api/debug-keys")
    def debug_keys():
        """서버가 로드한 API 키 확인용 (끝 4자리만 표시). 로컬 전용."""
        def mask(key: str) -> str:
            return f"...{key[-4:]}" if len(key) > 4 else "(비어있음)"
        return {
            "GOOGLE_AI_API_KEY": mask(GOOGLE_AI_API_KEY),
            "GOOGLE_CLOUD_API_KEY": mask(GOOGLE_CLOUD_API_KEY),
        }


# ── STT — Google Cloud Speech-to-Text ────────────────────────────────────────


def _detect_encoding(content_type: str) -> str:
    ct = (content_type or "").lower()
    if "webm" in ct or "opus" in ct:
        return "WEBM_OPUS"
    if "mp3" in ct or "mpeg" in ct:
        return "MP3"
    if "mp4" in ct or "m4a" in ct or "aac" in ct:
        return "MP3"  # iOS Safari MediaRecorder: audio/mp4 (AAC) → closest STT v1 encoding
    if "wav" in ct:
        return "LINEAR16"
    if "flac" in ct:
        return "FLAC"
    return "WEBM_OPUS"  # browser MediaRecorder 기본값 (Chrome/Firefox)


def _parse_wav(audio_bytes: bytes) -> tuple[bytes, int, int] | None:
    """
    WAV 파일 감지 및 파싱. RIFF 매직 바이트로 판별.
    반환: (raw_pcm_bytes, sample_rate, num_channels) 또는 None (WAV 아닌 경우)

    LINEAR16 인코딩은 raw PCM만 받음 — WAV 헤더를 포함해 보내면 헤더 바이트가
    오디오 데이터로 해석돼 빈 결과가 반환됨. 헤더를 파싱해 제거 후 전달해야 함.
    """
    if len(audio_bytes) < 44:
        return None
    if audio_bytes[:4] != b"RIFF" or audio_bytes[8:12] != b"WAVE":
        return None
    num_channels = int.from_bytes(audio_bytes[22:24], "little")
    sample_rate = int.from_bytes(audio_bytes[24:28], "little")
    # Walk RIFF chunks to find 'data'
    offset = 12
    while offset + 8 <= len(audio_bytes):
        chunk_id = audio_bytes[offset : offset + 4]
        chunk_size = int.from_bytes(audio_bytes[offset + 4 : offset + 8], "little")
        if chunk_id == b"data":
            return audio_bytes[offset + 8 : offset + 8 + chunk_size], sample_rate, num_channels
        offset += 8 + chunk_size
    # Fallback: assume standard 44-byte header
    return audio_bytes[44:], sample_rate, num_channels


@app.post("/api/stt")
async def stt(audio: UploadFile = File(...)):
    """
    오디오 파일 → 텍스트 변환 (Google Cloud Speech-to-Text v1)

    - FE: MediaRecorder로 녹음한 webm/opus 파일을 multipart/form-data로 전송
    - 응답: { transcript, confidence }
    - 제한: 동기 인식은 최대 60초. 그 이상은 longrunningrecognize 사용 필요.
    """
    if not GOOGLE_CLOUD_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_CLOUD_API_KEY not configured")

    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # WAV 감지: RIFF 매직 바이트로 판별 (Content-Type보다 신뢰도 높음)
    wav_parsed = _parse_wav(audio_bytes)
    if wav_parsed:
        pcm_bytes, sample_rate, num_channels = wav_parsed
        encoding = "LINEAR16"
        audio_bytes = pcm_bytes  # WAV 헤더 제거 — raw PCM만 Google STT에 전달
        logging.info(
            f"STT WAV detected: sample_rate={sample_rate}, channels={num_channels}, "
            f"pcm_size={len(audio_bytes)} bytes"
        )
    else:
        encoding = _detect_encoding(audio.content_type or "")
        sample_rate = None
        num_channels = None
        logging.info(
            f"STT request: content_type={audio.content_type!r}, "
            f"size={len(audio_bytes)} bytes, encoding={encoding}"
        )

    # latest_short is optimized for <2s voice commands and returns empty for longer speech.
    # Use latest_long for WAV/LINEAR16 (browser recordings are typically 3-30s).
    model = "latest_long" if encoding == "LINEAR16" else "latest_short"
    config: dict = {
        "encoding": encoding,
        "languageCode": "en-US",
        "model": model,
        "enableAutomaticPunctuation": False,
    }
    if encoding == "LINEAR16" and sample_rate:
        config["sampleRateHertz"] = sample_rate
    if encoding == "WEBM_OPUS":
        config["sampleRateHertz"] = 48000
    if num_channels and num_channels > 1:
        config["audioChannelCount"] = num_channels

    payload = {
        "config": config,
        "audio": {"content": base64.b64encode(audio_bytes).decode()},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://speech.googleapis.com/v1/speech:recognize?key={GOOGLE_CLOUD_API_KEY}",
            json=payload,
        )

    if resp.status_code != 200:
        logging.error(
            f"Google STT failed: status={resp.status_code}, "
            f"content_type={audio.content_type!r}, size={len(audio_bytes)}, "
            f"encoding={encoding}, google_response={resp.text[:500]}"
        )
        raise HTTPException(status_code=502, detail=f"Google STT error: {resp.text}")

    results = resp.json().get("results", [])
    if not results:
        return {"transcript": "", "confidence": 0.0}

    alt = results[0].get("alternatives", [{}])[0]
    return {
        "transcript": alt.get("transcript", "").strip(),
        "confidence": alt.get("confidence", 1.0),
    }


# ── TTS — Google Cloud Text-to-Speech ────────────────────────────────────────


_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"   # symbols & pictographs
    "\U0001F680-\U0001F6FF"   # transport & map symbols
    "\U0001F900-\U0001F9FF"   # supplemental symbols
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text).strip()


async def _call_google_tts(
    text: str,
    voice: str = "en-US-Journey-F",
    speaking_rate: float = 1.0,
) -> str:
    """Google Cloud TTS 호출 → base64 MP3 반환"""
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": "en-US", "name": voice},
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": speaking_rate,
            "pitch": 0.0,
            "effectsProfileId": ["headphone-class-device"],
        },
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_CLOUD_API_KEY}",
            json=payload,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=_format_google_tts_error(resp))

    return resp.json()["audioContent"]  # base64 MP3


def _format_google_tts_error(resp: httpx.Response) -> dict:
    try:
        error = resp.json().get("error", {})
    except Exception:
        return {
            "message": "Google TTS request failed.",
            "status_code": resp.status_code,
            "google_response": resp.text,
        }

    reason = None
    for detail in error.get("details", []):
        if detail.get("@type") == "type.googleapis.com/google.rpc.ErrorInfo":
            reason = detail.get("reason")
            break

    help_text = "Check the Google Cloud API key, billing, and Text-to-Speech API status."
    if reason == "API_KEY_SERVICE_BLOCKED":
        help_text = (
            "This API key is restricted from calling Cloud Text-to-Speech. "
            "In Google Cloud Console, open APIs & Services > Credentials > this API key > "
            "API restrictions, then allow Cloud Text-to-Speech API or remove API restrictions. "
            "Also confirm Cloud Text-to-Speech API is enabled for the same project."
        )
    elif error.get("status") == "PERMISSION_DENIED":
        help_text = (
            "Permission denied from Google Cloud. Confirm billing is enabled, "
            "Cloud Text-to-Speech API is enabled, and GOOGLE_CLOUD_API_KEY belongs to that project."
        )

    return {
        "message": error.get("message", "Google TTS request failed."),
        "status": error.get("status"),
        "reason": reason,
        "help": help_text,
    }


@app.post("/api/tts")
async def tts(req: TTSRequest):
    """
    텍스트 → MP3 오디오 (Google Cloud Text-to-Speech)

    - 응답: { audio_b64, voice, encoding }
    - FE: audio_b64를 Audio() 또는 <audio> 태그로 재생
    """
    if not GOOGLE_CLOUD_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_CLOUD_API_KEY not configured")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    audio_b64 = await _call_google_tts(
        _strip_emoji(req.text),
        req.voice or "en-US-Journey-F",
        req.speaking_rate or 1.0,
    )
    return {"audio_b64": audio_b64, "voice": req.voice, "encoding": "MP3"}


# ── Feedback — 5축 분석 + Gemini 피드백 + TTS ────────────────────────────────

_FEEDBACK_SYSTEM_PROMPT = """\
You are Pally, a friendly English conversation tutor.
Analyze the user's utterance and provide structured feedback.

Return ONLY valid JSON with exactly these three fields:
{
  "correction": "A natural alternative phrasing or minor correction. If already natural, offer a slight variation.",
  "tone_feedback": "One encouraging sentence about their tone, energy, or humor style.",
  "practice_prompt": "One engaging follow-up question for them to practice responding to."
}

Rules:
- Each field: 1-2 sentences max.
- Be warm, encouraging, and specific.
- Do NOT mention the numeric scores directly.
"""


async def _call_gemini_feedback(utterance: str, axes: dict) -> dict:
    """Gemini 2.5 Flash REST API 호출 → 피드백 JSON 반환"""
    user_prompt = (
        f'User utterance: "{utterance}"\n'
        f"Style analysis — Formality: {axes['Formality']}/100, "
        f"Energy: {axes['Energy']}/100, Intimacy: {axes['Intimacy']}/100, "
        f"Humor: {axes['Humor']}/100, Curiosity: {axes['Curiosity']}/100\n\n"
        "Provide feedback JSON:"
    )

    payload = {
        "system_instruction": {"parts": [{"text": _FEEDBACK_SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.7,
            "maxOutputTokens": 512,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash-lite:generateContent?key={GOOGLE_AI_API_KEY}",
            json=payload,
        )

    if resp.status_code != 200:
        raise RuntimeError(f"Gemini error {resp.status_code}: {resp.text}")

    parts = resp.json()["candidates"][0]["content"]["parts"]
    raw = " ".join(p["text"] for p in parts if not p.get("thought", False)).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


_FEEDBACK_FALLBACK = {
    "correction": "Great attempt! Try to vary your sentence structure for more natural flow.",
    "tone_feedback": "Your expression is coming through clearly — keep it up!",
    "practice_prompt": "Can you try expressing the same idea in a different way?",
}


@app.post("/api/feedback", response_model=FeedbackResponse)
async def feedback(req: FeedbackRequest):
    """
    utterance → 5축 분석 → EMA → 캐릭터 파라미터 → Gemini 피드백 → TTS

    흐름:
      1. analyze_utterance()  → raw 5축 점수
      2. apply_ema()          → 이전 축 점수 반영 (current_axes 있을 때)
      3. compute_character()  → 캐릭터 파라미터
      4. Gemini 2.5 Flash     → correction / tone_feedback / practice_prompt
      5. Google TTS           → correction 문장을 MP3로 변환 (tts_audio)
    """
    if not GOOGLE_AI_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_AI_API_KEY not configured")
    if not req.utterance.strip():
        raise HTTPException(status_code=400, detail="utterance is required")

    # 1. 5축 분석
    raw_axes = _analyze_axes(req.utterance)

    # 2. EMA — 이전 누적 점수가 있을 때만 적용
    smoothed_axes = apply_ema(req.current_axes, raw_axes) if req.current_axes else raw_axes

    # 3. 캐릭터 파라미터
    character = compute_character(smoothed_axes)
    tone_label, energy_label, humor_label = describe_character(character)

    # 4. Gemini 피드백 (실패 시 fallback)
    try:
        feedback_data = await _call_gemini_feedback(req.utterance, smoothed_axes)
        for key in ("correction", "tone_feedback", "practice_prompt"):
            if key not in feedback_data:
                raise ValueError(f"Missing key: {key}")
    except Exception as e:
        logging.warning(f"Gemini fallback triggered: {e}")
        feedback_data = _FEEDBACK_FALLBACK

    # 5. TTS — correction 문장을 음성으로 (실패해도 피드백은 정상 반환)
    tts_audio: Optional[str] = None
    correction_text = feedback_data.get("correction", "")
    if correction_text:
        try:
            tts_audio = await _call_google_tts(correction_text)
        except Exception:
            tts_audio = None

    return {
        "status": "ok",
        "axes": smoothed_axes,
        "character": character,
        "character_labels": {
            "tone": tone_label,
            "energy": energy_label,
            "humor": humor_label,
        },
        "feedback": feedback_data,
        "tts_audio": tts_audio,
    }


# ── Chat — STT 결과 → Gemini 대화 응답 → TTS + 한국어 힌트 ────────────────────

_LEVEL_GUIDE = {
    "A2": "Use very simple words and short sentences (A2 beginner level).",
    "B1": "Use everyday vocabulary and mid-length sentences (B1 intermediate level).",
    "B2": "Use varied vocabulary and natural phrasing (B2 upper-intermediate level).",
    "C1": "Use rich vocabulary and complex sentences naturally (C1 advanced level).",
}


def _build_chat_system_prompt(character_name: str, level: str) -> str:
    level_guide = _LEVEL_GUIDE.get(level, _LEVEL_GUIDE["B1"])
    return f"""\
You are {character_name}, a warm and playful English conversation friend.
{level_guide}
Keep responses to 1-3 sentences — natural, friendly, and engaging.

## Grammar correction rules
When the user makes grammar or vocabulary mistakes, do not list or explain the mistakes.
Instead, naturally recast the user's idea with the key corrected expression inside your reply.
If two errors are tightly connected in one phrase, you may fix both without explaining them.

Use this pattern:
1. React emotionally or empathetically first.
2. Rephrase the user's idea with the corrected expression.
3. Ask one short follow-up question.

Keep the spoken reply compact, usually 1-2 short sentences.
Keep the user's casual style when it is natural, such as "bestie", "hang out", "dying laughing", or "no way".
Do not over-correct slang or casual expressions unless they are actually wrong.

Example:
User: "My bestie and I watch it yesterday and we was dying laughing."
Pally: "Oh! You and your bestie watched it yesterday, and you were dying laughing? What was so funny?"

Stay in character as {character_name} at all times. Never break the fourth wall."""


async def _call_gemini_chat(
    utterance: str,
    history: list,
    character_name: str,
    level: str,
) -> str:
    """Gemini 2.5 Flash로 Pally 대화 응답 생성"""
    system_prompt = _build_chat_system_prompt(character_name, level)

    contents = []
    for msg in (history or [])[-10:]:
        role = "user" if msg.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.content}]})
    contents.append({"role": "user", "parts": [{"text": utterance}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 512,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash-lite:generateContent?key={GOOGLE_AI_API_KEY}",
            json=payload,
        )

    if resp.status_code != 200:
        raise RuntimeError(f"Gemini chat error {resp.status_code}: {resp.text}")

    candidate = resp.json()["candidates"][0]
    if candidate.get("finishReason") == "MAX_TOKENS":
        logging.warning("Gemini chat response cut off by MAX_TOKENS")

    # Skip thought parts (thinkingBudget=0이어도 방어적으로 필터)
    parts = candidate["content"]["parts"]
    reply = " ".join(p["text"] for p in parts if not p.get("thought", False)).strip()
    if not reply:
        raise RuntimeError("Gemini returned empty chat response")
    return reply


_HINT_KO_SYSTEM_PROMPT = """\
You are a Korean-speaking English tutor assistant. Given the user's English utterance and Pally's reply,
identify whether Pally implicitly corrected a grammar or vocabulary mistake (by naturally using the correct form).
Explain briefly in Korean, or give praise if no correction was needed.

Return ONLY valid JSON:
{
  "hint": "한국어 설명 1-2문장. 교정이 있으면 무엇이 어떻게 교정됐는지 설명. 없으면 '자연스러운 표현이에요!'처럼 칭찬.",
  "expression": "올바른 영어 표현 (짧은 구나 문장. 교정 없으면 사용자 표현 그대로)"
}
"""

_HINT_KO_FALLBACK = InlineHintKo(
    hint="잘 표현했어요! 계속 연습하면 더 자연스러워질 거예요.",
    expression="Keep it up!",
)


async def _call_gemini_hint_ko(utterance: str, pally_reply: str) -> InlineHintKo:
    """사용자 발화 + Pally 응답 → 한국어 인라인 힌트 (Gemini 2.5 Flash)"""
    user_prompt = (
        f'User said: "{utterance}"\n'
        f'Pally replied: "{pally_reply}"\n\n'
        "Provide Korean hint JSON:"
    )
    payload = {
        "system_instruction": {"parts": [{"text": _HINT_KO_SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.3,
            "maxOutputTokens": 512,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash-lite:generateContent?key={GOOGLE_AI_API_KEY}",
            json=payload,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini hint error {resp.status_code}: {resp.text}")
    parts = resp.json()["candidates"][0]["content"]["parts"]
    raw = " ".join(p["text"] for p in parts if not p.get("thought", False)).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    data = json.loads(raw)
    return InlineHintKo(hint=data.get("hint", ""), expression=data.get("expression", ""))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    utterance(텍스트) → 5축 분석 → EMA → 캐릭터 파라미터 → Gemini 대화 응답 → TTS + 한국어 힌트

    흐름:
      1. Supabase 세션 조회/생성 + 대화 이력 로드 (session_id 있을 때)
      2. analyze_utterance()  → raw 5축 점수
      3. apply_ema()          → EMA 평활화 (alpha=0.7)
      4. compute_character()  → 캐릭터 파라미터
      5. Gemini 2.5 Flash     → Pally 대화 응답 (자연스러운 교정 포함)
      6. TTS + 한국어 힌트    → asyncio.gather()로 병렬 실행
      7. Supabase 저장        → user + pally 메시지
    """
    if not GOOGLE_AI_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_AI_API_KEY not configured")
    if not req.utterance.strip():
        raise HTTPException(status_code=400, detail="utterance is required")

    # 1. Supabase 세션 & 대화 이력
    # Phase 1C에서는 frontend가 anonymous client UUID로 session_id를 보내면
    # 동일 세션의 이전 messages가 DB에서 로드되고 이후 요청에 conversation_history로 이어집니다.
    character_name = req.character_name or "Pally"
    level = req.level or "B1"
    history: list[ChatMessage] = req.conversation_history or []

    if req.session_id and _SUPABASE_ENABLED:
        try:
            sb = get_supabase()
            session_res = sb.table("sessions").select("id, character_name, level").eq("id", req.session_id).execute()
            if getattr(session_res, "error", None):
                raise RuntimeError(getattr(session_res.error, "message", repr(session_res.error)))
            if session_res.data:
                character_name = session_res.data[0]["character_name"]
                level = session_res.data[0]["level"]
            else:
                insert_session_res = sb.table("sessions").insert({
                    "id": req.session_id,
                    "character_name": character_name,
                    "level": level,
                }).execute()
                if getattr(insert_session_res, "error", None):
                    raise RuntimeError(getattr(insert_session_res.error, "message", repr(insert_session_res.error)))
            msg_res = sb.table("messages").select("role, transcript").eq("session_id", req.session_id).order("created_at").execute()
            if getattr(msg_res, "error", None):
                raise RuntimeError(getattr(msg_res.error, "message", repr(msg_res.error)))
            if msg_res.data:
                history = [ChatMessage(role=m["role"], content=m["transcript"]) for m in msg_res.data]
        except Exception as e:
            logging.warning(f"Supabase session load failed: {e}")

    # 2. 5축 분석
    raw_axes = _analyze_axes(req.utterance)

    # 3. EMA
    smoothed_axes = apply_ema(req.current_axes, raw_axes) if req.current_axes else raw_axes

    # 4. 캐릭터 파라미터
    character = compute_character(smoothed_axes)
    tone_label, energy_label, humor_label = describe_character(character)

    # 5. Gemini 대화 응답
    try:
        reply = await _call_gemini_chat(req.utterance, history, character_name, level)
    except Exception as e:
        logging.warning(f"Gemini chat fallback: {e}")
        reply = "I see! Tell me more."

    # 6. TTS — 이모지 제거 후 호출
    tts_result = await asyncio.gather(
        _call_google_tts(_strip_emoji(reply)),
        return_exceptions=True,
    )
    tts_audio = tts_result[0] if not isinstance(tts_result[0], Exception) else None

    # 7. Supabase 저장
    if req.session_id and _SUPABASE_ENABLED:
        try:
            sb = get_supabase()
            save_res = sb.table("messages").insert([
                {
                    "session_id": req.session_id,
                    "role": "user",
                    "transcript": req.utterance,
                    "axes": smoothed_axes,
                    "character": character,
                },
                {
                    "session_id": req.session_id,
                    "role": "pally",
                    "transcript": reply,
                    "axes": None,
                    "character": character,
                },
            ]).execute()
            if getattr(save_res, "error", None):
                raise RuntimeError(getattr(save_res.error, "message", repr(save_res.error)))
        except Exception as e:
            logging.warning(f"Supabase save failed: {e}")

    return {
        "status": "ok",
        "transcript": req.utterance,
        "reply": reply,
        "tts_audio": tts_audio,
        "axes": smoothed_axes,
        "character": character,
        "character_labels": {
            "tone": tone_label,
            "energy": energy_label,
            "humor": humor_label,
        },
        "hint_ko": None,
    }


# ── Auth — Supabase JWT 검증 ──────────────────────────────────────────────────


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Authorization: Bearer <JWT> 를 Supabase Auth로 검증하고 user_id(uuid) 반환.
    실패 시 401 unauthorized. user_id는 토큰에서만 추출하고 body 값을 신뢰하지 않는다.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "unauthorized", "Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AppError(401, "unauthorized", "Missing or invalid Authorization header")

    if not _SUPABASE_ENABLED:
        raise AppError(503, "service_unavailable", "Supabase is not configured")

    try:
        sb = get_supabase()
        user_res = sb.auth.get_user(token)
    except Exception as e:
        logging.warning(f"Auth verification failed: {e}")
        raise AppError(401, "unauthorized", "Invalid or expired token")

    user = getattr(user_res, "user", None)
    if user is None or not getattr(user, "id", None):
        raise AppError(401, "unauthorized", "Invalid or expired token")

    return user.id


def require_idempotency_key(idempotency_key: str = Header(..., alias="Idempotency-Key")) -> str:
    """
    비용·데이터 생성 POST용 멱등 키. 계약상 필수 헤더.
    이번 slice에서는 헤더 존재만 강제하고(누락 시 422), 24h replay store는 미구현.
    실제 중복 방지는 각 엔드포인트의 상태 충돌(409)로 처리한다.
    """
    key = (idempotency_key or "").strip()
    if not key:
        raise AppError(422, "validation_error", "Idempotency-Key header is required")
    return key


# ── Onboarding & Profile — profiles 테이블 (service_role 쓰기 전용) ───────────

_VALID_ENGLISH_LEVELS = {"A2", "B1", "B2", "C1"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_display_name(value: str) -> str:
    name = (value or "").strip()
    if not (1 <= len(name) <= 30):
        raise AppError(422, "validation_error", "display_name must be 1-30 characters after trimming")
    return name


def _validate_english_level(value: str) -> str:
    if value not in _VALID_ENGLISH_LEVELS:
        raise AppError(422, "validation_error", f"english_level must be one of {sorted(_VALID_ENGLISH_LEVELS)}")
    return value


class OnboardingRequest(BaseModel):
    # extra=forbid → 알 수 없는 필드(traits 등)는 422 validation_error.
    model_config = ConfigDict(extra="forbid")
    display_name: str
    english_level: str


class ProfilePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: Optional[str] = None
    english_level: Optional[str] = None


def _profile_to_response(row: dict) -> dict:
    # 계약: snake_case UserProfile. traits는 DB seed 5개(생성 로직은 후속).
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "english_level": row["english_level"],
        "onboarding_completed": row["onboarding_completed"],
        "traits": row.get("traits"),
        "created_at": row["created_at"],
        "updated_at": row.get("updated_at"),
    }


@app.post("/api/onboarding")
async def onboarding(
    req: OnboardingRequest,
    user_id: str = Depends(get_current_user_id),
    _idem: str = Depends(require_idempotency_key),
):
    """최초 프로필 생성. 이미 온보딩 완료한 사용자는 409 conflict (덮어쓰지 않음)."""
    display_name = _validate_display_name(req.display_name)
    english_level = _validate_english_level(req.english_level)

    sb = get_supabase()

    # 이미 온보딩 완료 여부 확인 (덮어쓰기 방지).
    try:
        existing = sb.table("profiles").select("onboarding_completed").eq("id", user_id).execute()
    except Exception as e:
        logging.error(f"Onboarding existence check failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to read profile")

    if existing.data and existing.data[0].get("onboarding_completed"):
        raise AppError(409, "conflict", "Onboarding already completed. Use PATCH /api/profile to edit.")

    try:
        res = sb.table("profiles").upsert({
            "id": user_id,
            "display_name": display_name,
            "english_level": english_level,
            "onboarding_completed": True,
            "updated_at": _now_iso(),
        }).execute()
    except Exception as e:
        logging.error(f"Onboarding upsert failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to save profile")

    if not res.data:
        raise AppError(503, "persistence_failed", "Failed to save profile")

    return {"profile": _profile_to_response(res.data[0])}


@app.get("/api/profile")
async def get_profile(user_id: str = Depends(get_current_user_id)):
    """본인 profile 조회. 온보딩 전(row 없음)이면 404 profile_not_found."""
    sb = get_supabase()
    try:
        res = sb.table("profiles").select("*").eq("id", user_id).execute()
    except Exception as e:
        logging.error(f"Profile fetch failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to fetch profile")

    if not res.data:
        raise AppError(404, "profile_not_found", "Profile not found. Complete onboarding first.")

    return {"profile": _profile_to_response(res.data[0])}


@app.patch("/api/profile")
async def update_profile(
    req: ProfilePatchRequest,
    user_id: str = Depends(get_current_user_id),
):
    """본인 profile 부분 수정. traits 등 unknown 필드는 422 (extra=forbid)."""
    update_fields: Dict[str, object] = {}

    if req.display_name is not None:
        update_fields["display_name"] = _validate_display_name(req.display_name)
    if req.english_level is not None:
        update_fields["english_level"] = _validate_english_level(req.english_level)

    if not update_fields:
        raise AppError(422, "validation_error", "At least one field (display_name or english_level) is required")

    update_fields["updated_at"] = _now_iso()

    sb = get_supabase()
    try:
        res = sb.table("profiles").update(update_fields).eq("id", user_id).execute()
    except Exception as e:
        logging.error(f"Profile update failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to update profile")

    if not res.data:
        raise AppError(404, "profile_not_found", "Profile not found. Complete onboarding first.")

    return {"profile": _profile_to_response(res.data[0])}


# ── Conversations & Turns — 3주차 음성 대화 (sessions/messages 재사용) ────────
#
# 경계: STT/Gemini/TTS 파이프라인 자체는 AI 영역. 여기서는 그 어댑터를 "호출"만 하고
# (기존 _call_gemini_chat / _call_google_tts, 신규 _stt_from_bytes),
# 백엔드는 conversation/turn 저장 + 소유권 + 실패/완료 구분 + 중복방지(dedup)만 담당한다.


async def _stt_from_bytes(audio_bytes: bytes, content_type: str) -> tuple[str, float]:
    """
    오디오 bytes → (transcript, confidence). turn 처리 전용 STT 어댑터 호출부.
    무음/인식실패 → ("", 0.0). Google API 비-200 → RuntimeError.
    (기존 /api/stt 는 건드리지 않고, turn 용으로 동일 파이프라인을 별도 호출한다.)
    """
    wav_parsed = _parse_wav(audio_bytes)
    if wav_parsed:
        pcm_bytes, sample_rate, num_channels = wav_parsed
        encoding = "LINEAR16"
        audio_bytes = pcm_bytes
    else:
        encoding = _detect_encoding(content_type or "")
        sample_rate = None
        num_channels = None

    model = "latest_long" if encoding == "LINEAR16" else "latest_short"
    config: dict = {
        "encoding": encoding,
        "languageCode": "en-US",
        "model": model,
        "enableAutomaticPunctuation": False,
    }
    if encoding == "LINEAR16" and sample_rate:
        config["sampleRateHertz"] = sample_rate
    if encoding == "WEBM_OPUS":
        config["sampleRateHertz"] = 48000
    if num_channels and num_channels > 1:
        config["audioChannelCount"] = num_channels

    payload = {"config": config, "audio": {"content": base64.b64encode(audio_bytes).decode()}}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://speech.googleapis.com/v1/speech:recognize?key={GOOGLE_CLOUD_API_KEY}",
            json=payload,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Google STT error {resp.status_code}: {resp.text[:300]}")

    results = resp.json().get("results", [])
    if not results:
        return "", 0.0
    alt = results[0].get("alternatives", [{}])[0]
    return alt.get("transcript", "").strip(), alt.get("confidence", 1.0)


_INITIAL_AXES = {"Formality": 50, "Energy": 50, "Intimacy": 50, "Humor": 50, "Curiosity": 50}


def _conversation_to_response(row: dict) -> dict:
    # 계약 §4.5 Conversation 모양. 생성 시점 기준 기본값(turn 없음).
    return {
        "id": row["id"],
        "status": "completed" if row.get("ended_at") else "active",
        "title": None,
        "started_at": row["created_at"],
        "last_turn_at": None,
        "completed_at": row.get("ended_at"),
        "turn_count": 0,
        "current_axes": dict(_INITIAL_AXES),
    }


@app.post("/api/conversations", status_code=201)
async def create_conversation(
    user_id: str = Depends(get_current_user_id),
    _idem: str = Depends(require_idempotency_key),
):
    """새 대화 생성. 사용자 레벨은 profile 에서 읽는다 (없으면 기본 B1)."""
    sb = get_supabase()

    level = "B1"
    try:
        prof = sb.table("profiles").select("english_level").eq("id", user_id).execute()
    except Exception as e:
        logging.error(f"create_conversation profile read failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to read profile")
    if prof.data:
        level = prof.data[0]["english_level"]

    try:
        res = sb.table("sessions").insert({
            "character_name": "Pally",
            "level": level,
            "user_id": user_id,
        }).execute()
    except Exception as e:
        logging.error(f"create_conversation insert failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to create conversation")

    if not res.data:
        raise AppError(503, "persistence_failed", "Failed to create conversation")

    return {"conversation": _conversation_to_response(res.data[0])}


def _paired_reply(sb, session_id: str, user_created_at: str) -> str:
    """dedup 재반환용: 해당 user turn 뒤에 저장된 pally 응답 텍스트를 찾는다."""
    r = (
        sb.table("messages")
        .select("transcript")
        .eq("session_id", session_id)
        .eq("role", "pally")
        .gte("created_at", user_created_at)
        .order("created_at")
        .limit(1)
        .execute()
    )
    return r.data[0]["transcript"] if r.data else ""


async def _gen_feedback(utterance: str, reply: str, level: str) -> list:
    """
    AI feedback 생성 호출 래퍼 (경계: 생성 로직은 AI, 여기선 호출·형태만).
    - 미제공(generate_feedback is None) → [] 반환 (실패 아님, 미구현).
    - 동기 함수라 asyncio.to_thread 로 offload (이벤트 루프 안 막음) + 10s 타임아웃.
    - 예외/타임아웃은 그대로 raise → 호출부(gather)가 partial + feedback_failed 로 처리.
    - id 는 계약(§5)상 BE 가 부여. AI 는 {original, corrected, explanation_ko} 만 준다.
    """
    if generate_feedback is None:
        return []
    # 계약: (items, failed). failed=True 는 생성 실패/폴백 → 빈 items 를 "교정 없음"으로
    # 보지 말라는 뜻이므로 raise 해서 호출부(gather)가 partial + feedback_failed 로 처리.
    items, failed = await asyncio.wait_for(
        asyncio.to_thread(generate_feedback, utterance, reply, level),
        timeout=10,
    )
    if failed:
        raise RuntimeError("feedback generation degraded (failed flag)")
    out = []
    for it in (items or []):
        out.append({
            "id": str(uuid.uuid4()),
            "original": it.get("original", ""),
            "corrected": it.get("corrected", ""),
            "explanation_ko": it.get("explanation_ko", ""),
        })
    return out


# ── Quota — 무료 일일 사용량 (KST bucket + 원자적 차감) ───────────────────────


def _kst_date() -> str:
    """오늘의 KST 날짜 (YYYY-MM-DD). 사용량 bucket 키."""
    return datetime.now(_KST).date().isoformat()


def _kst_reset_at() -> str:
    """다음 KST 자정(=오늘 사용량 리셋 시각)을 UTC ISO 로."""
    tomorrow = datetime.now(_KST).date() + timedelta(days=1)
    midnight_kst = datetime.combine(tomorrow, dtime.min, tzinfo=_KST)
    return midnight_kst.astimezone(timezone.utc).isoformat()


def _reserve_turn(sb, user_id: str) -> int:
    """
    turn 1개를 원자적으로 예약(차감). 반환: 예약 후 used_turns(>=1), 소진이면 -1.
    DB 함수(reserve_turn)가 행 잠금으로 동시성 race 를 막는다.
    """
    try:
        res = sb.rpc("reserve_turn", {
            "p_user_id": user_id,
            "p_date": _kst_date(),
            "p_limit": FREE_DAILY_TURNS,
        }).execute()
    except Exception as e:
        logging.error(f"reserve_turn failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to reserve quota")
    used = res.data
    if isinstance(used, list):  # 방어적: 배열로 오면 첫 값
        used = used[0] if used else None
    if used is None:
        raise AppError(503, "persistence_failed", "Quota reservation returned no result")
    return int(used)


def _release_turn(sb, user_id: str) -> None:
    """예약한 turn 을 롤백(환불). turn 이 실패했을 때만 호출. 실패해도 turn 흐름은 안 막음."""
    try:
        sb.rpc("release_turn", {"p_user_id": user_id, "p_date": _kst_date()}).execute()
    except Exception as e:
        logging.warning(f"release_turn failed (non-fatal): {e}")


@app.get("/api/usage")
async def get_usage(user_id: str = Depends(get_current_user_id)):
    """당일 무료 사용량 조회 (§4.11). 현재는 전원 free plan."""
    sb = get_supabase()
    date_kst = _kst_date()
    try:
        res = sb.table("usage_daily").select("used_turns").eq("user_id", user_id).eq("date_kst", date_kst).execute()
    except Exception as e:
        logging.error(f"get_usage failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to read usage")
    used = res.data[0]["used_turns"] if res.data else 0
    return {
        "plan": "free",
        "date": date_kst,
        "timezone": "Asia/Seoul",
        "used_turns": used,
        "remaining_turns": max(FREE_DAILY_TURNS - used, 0),
        "daily_limit": FREE_DAILY_TURNS,
        "reset_at": _kst_reset_at(),
    }


# ── Activity events — Achievements Daily Task 측정용 사실 이벤트 기록 ─────────

_ALLOWED_EVENT_TYPES = {
    "app_session_started",
    "conversation_detail_opened",
    "transcript_expanded",
    "feedback_item_opened",
    "achievements_opened",
    "profile_opened",
}


class ActivityEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    event_type: str
    occurred_at: Optional[str] = None
    conversation_id: Optional[str] = None
    feedback_item_id: Optional[str] = None


@app.post("/api/activity-events", status_code=202)
async def record_activity_event(
    req: ActivityEventRequest,
    user_id: str = Depends(get_current_user_id),
    _idem: str = Depends(require_idempotency_key),
):
    """
    화면 진입·열람형 이벤트 기록 (§4.20). 완료 평가는 하지 않고 "사실 이벤트"만 저장.
    - event_type 은 허용된 6종만 (422)
    - occurred_at 은 서버 시각 ±5분만 허용 (422). task 날짜는 서버 수신 시각 기준
    - resource(conversation_id) 있으면 소유권 검증 (타인 것 404)
    - (user_id, event_id) 유일 → 재전송은 중복 저장 없이 동일 응답 (멱등)
    """
    if req.event_type not in _ALLOWED_EVENT_TYPES:
        raise AppError(422, "validation_error", f"event_type must be one of {sorted(_ALLOWED_EVENT_TYPES)}")
    if not (req.event_id or "").strip():
        raise AppError(422, "validation_error", "event_id is required")

    if req.occurred_at:
        try:
            occ = datetime.fromisoformat(req.occurred_at.replace("Z", "+00:00"))
        except ValueError:
            raise AppError(422, "validation_error", "occurred_at must be ISO 8601")
        if occ.tzinfo is None:
            occ = occ.replace(tzinfo=timezone.utc)
        drift = abs((datetime.now(timezone.utc) - occ).total_seconds())
        if drift > 300:
            raise AppError(422, "validation_error", "occurred_at is too far from server time (>5min)")

    sb = get_supabase()

    # resource 소유권 (있을 때만) — 타인 conversation 은 404
    if req.conversation_id:
        _owned_session(sb, req.conversation_id, user_id)

    # insert-or-ignore: (user_id, event_id) 중복이면 조용히 무시 → 멱등
    try:
        sb.table("activity_events").upsert(
            {
                "user_id": user_id,
                "event_id": req.event_id,
                "event_type": req.event_type,
                "occurred_at": req.occurred_at,
                "conversation_id": req.conversation_id,
                "feedback_item_id": req.feedback_item_id,
            },
            on_conflict="user_id,event_id",
            ignore_duplicates=True,
        ).execute()
    except Exception as e:
        logging.error(f"activity event insert failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to record event")

    return {"recorded": True}


@app.post("/api/conversations/{conversation_id}/turns", status_code=201)
async def create_turn(
    conversation_id: str,
    request: Request,
    audio: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    idem_key: str = Depends(require_idempotency_key),
):
    """
    음성 turn 1개 처리: 오디오 → STT → 5축/EMA → Gemini 답변 → TTS → 저장.
    - 소유권: 본인 conversation 이 아니면 404.
    - 실패/완료 구분: STT 무음/실패는 저장하지 않고 명시적 에러(빈 데이터로 숨기지 않음).
    - 중복방지: 같은 conversation·같은 Idempotency-Key 재시도는 외부 재호출 없이 저장된 turn 재반환.
    - 관측성: STT/Gemini/TTS/save 단계별 latency 를 측정해 로그 + /api/metrics 에 노출.
    """
    if not GOOGLE_CLOUD_API_KEY or not GOOGLE_AI_API_KEY:
        raise AppError(503, "service_unavailable", "Speech/AI provider not configured")

    turn_t0 = time.perf_counter()

    sb = get_supabase()

    # 1. conversation 소유권 (타인 소유는 존재 숨김 → 404)
    try:
        sess = sb.table("sessions").select("id, character_name, level, user_id, ended_at").eq("id", conversation_id).execute()
    except Exception as e:
        logging.error(f"turn session read failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to read conversation")
    if not sess.data or sess.data[0].get("user_id") != user_id:
        raise AppError(404, "not_found", "Conversation not found")
    session = sess.data[0]
    if session.get("ended_at"):
        raise AppError(409, "conversation_closed", "Conversation is already completed")

    # 2. dedup — 같은 (conversation, idem_key) user turn 이 이미 있으면 재반환
    try:
        dup = sb.table("messages").select("*").eq("session_id", conversation_id).eq("idempotency_key", idem_key).execute()
    except Exception as e:
        logging.error(f"turn dedup read failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to check idempotency")
    if dup.data:
        u = dup.data[0]
        return {
            "conversation_id": conversation_id,
            "turn_id": u["id"],
            "status": "completed",
            "replayed": True,
            "created_at": u["created_at"],
            "user": {"transcript": u["transcript"]},
            "pally": {"text": _paired_reply(sb, conversation_id, u["created_at"]), "audio": None},
            "axes": u.get("axes"),
            "character": u.get("character"),
            "feedback": u.get("feedback") or [],
            "warnings": [],
        }

    # 3. 오디오
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise AppError(400, "invalid_audio", "Empty audio file")

    # 3.5. quota 원자적 예약 — AI 부르기 전에 차단 (초과면 여기서 429, 외부 호출 0).
    #      아래에서 turn 이 실패하면 _release_turn 으로 롤백해 차감을 취소한다.
    quota_used = _reserve_turn(sb, user_id)
    if quota_used < 0:
        raise AppError(429, "quota_exceeded", "오늘 사용할 수 있는 대화를 모두 사용했어요.",
                       {"reset_at": _kst_reset_at(), "daily_limit": FREE_DAILY_TURNS})

    # 4. STT (실패는 저장하지 않고 명시적 에러 + quota 롤백) — latency 측정
    stt_t0 = time.perf_counter()
    try:
        transcript, _conf = await _stt_from_bytes(audio_bytes, audio.content_type or "")
    except Exception as e:
        logging.warning(f"turn STT failed: {e}")
        _release_turn(sb, user_id)
        raise AppError(502, "stt_failed", "Speech recognition failed")
    stt_ms = round((time.perf_counter() - stt_t0) * 1000)
    if not transcript:
        _release_turn(sb, user_id)
        raise AppError(422, "speech_not_recognized", "No recognizable speech in audio")

    # 5. 이전 이력 + 누적 axes 로드
    try:
        prior = sb.table("messages").select("role, transcript, axes, created_at").eq("session_id", conversation_id).order("created_at").execute()
    except Exception as e:
        logging.error(f"turn history read failed: {e}")
        _release_turn(sb, user_id)
        raise AppError(503, "persistence_failed", "Failed to load history")
    prior_rows = prior.data or []
    history = [ChatMessage(role=m["role"], content=m["transcript"]) for m in prior_rows]
    current_axes = None
    for m in reversed(prior_rows):
        if m["role"] == "user" and m.get("axes"):
            current_axes = m["axes"]
            break

    # 6. 5축 → EMA → character (분석 어댑터: rule|ml|hybrid, 기본 rule)
    raw_axes = _analyze_axes(transcript)
    smoothed = apply_ema(current_axes, raw_axes) if current_axes else raw_axes
    character = compute_character(smoothed)

    # 7. Gemini 답변 (기존 함수 호출; 실패 시 silent fallback 없이 명시적 실패) — latency 측정
    gemini_t0 = time.perf_counter()
    try:
        reply = await _call_gemini_chat(transcript, history, session["character_name"], session["level"])
    except Exception as e:
        logging.warning(f"turn Gemini failed: {e}")
        _release_turn(sb, user_id)
        raise AppError(502, "ai_engine_failed", "Reply generation failed")
    gemini_ms = round((time.perf_counter() - gemini_t0) * 1000)

    # 8. TTS + feedback 병렬 (둘 다 reply 만 있으면 됨 → asyncio.gather).
    #    feedback 은 AI 담당(동기 함수)이라 to_thread 로 offload 해 이벤트 루프를 막지 않는다.
    #    TTS 가 보통 long pole 이라, feedback 을 병렬로 붙여도 turn latency 는 거의 안 늘어난다.
    timings: Dict[str, int] = {}

    async def _timed_tts():
        t0 = time.perf_counter()
        try:
            return await _call_google_tts(_strip_emoji(reply))
        finally:
            timings["tts_ms"] = round((time.perf_counter() - t0) * 1000)

    async def _timed_feedback():
        t0 = time.perf_counter()
        try:
            return await _gen_feedback(transcript, reply, session["level"])
        finally:
            timings["feedback_ms"] = round((time.perf_counter() - t0) * 1000)

    tts_result, fb_result = await asyncio.gather(
        _timed_tts(), _timed_feedback(), return_exceptions=True,
    )
    tts_ms = timings.get("tts_ms", 0)
    feedback_ms = timings.get("feedback_ms", 0)

    # TTS: 실패해도 turn 은 완료, audio 만 null.
    tts_audio: Optional[str] = None
    if isinstance(tts_result, Exception):
        logging.warning(f"turn TTS failed (non-fatal): {tts_result}")
    else:
        tts_audio = tts_result

    # feedback: 성공(list) / 실패(Exception → partial+warning) / 미구현(None 반환 → [])
    feedback_items: list = []
    feedback_failed = False
    if isinstance(fb_result, Exception):
        feedback_failed = True
        logging.warning(f"turn feedback failed (non-fatal): {fb_result}")
    elif fb_result:
        feedback_items = fb_result

    # 9. 저장 — user 행에만 idem_key (unique index 로 중복 저장 차단) — latency 측정
    save_t0 = time.perf_counter()
    try:
        save = sb.table("messages").insert([
            {
                "session_id": conversation_id,
                "role": "user",
                "transcript": transcript,
                "axes": smoothed,
                "character": character,
                "idempotency_key": idem_key,
                "feedback": feedback_items,
            },
            {
                "session_id": conversation_id,
                "role": "pally",
                "transcript": reply,
                "axes": None,
                "character": character,
            },
        ]).execute()
    except Exception as e:
        logging.error(f"turn save failed: {e}")
        _release_turn(sb, user_id)
        raise AppError(503, "persistence_failed", "Failed to save turn")
    save_ms = round((time.perf_counter() - save_t0) * 1000)

    # turn 식별: user 행이 곧 turn. turn_id/created_at 을 저장 결과에서 가져온다.
    user_row = next((r for r in (save.data or []) if r.get("role") == "user"), None)
    turn_id = user_row["id"] if user_row else None
    turn_created = user_row["created_at"] if user_row else None

    # TTS·feedback 부가 실패는 partial + warnings (계약 §4.6). 대화 텍스트는 정상.
    status = "completed"
    warnings: list = []
    if tts_audio is None:
        status = "partial"
        warnings.append({
            "code": "tts_failed",
            "message": "음성 생성에 실패했어요. 텍스트로 계속할 수 있어요.",
        })
    if feedback_failed:
        status = "partial"
        warnings.append({
            "code": "feedback_failed",
            "message": "피드백 생성에 실패했어요. 대화는 계속할 수 있어요.",
        })

    # 관측성: 단계별 latency 를 링버퍼에 저장 + 구조화 로그로 emit.
    metric = {
        "request_id": getattr(request.state, "request_id", None),
        "ts": _now_iso(),
        "conversation_id": conversation_id,
        "transcript_chars": len(transcript),
        "stt_ms": stt_ms,
        "gemini_ms": gemini_ms,
        "tts_ms": tts_ms,
        "feedback_ms": feedback_ms,
        "save_ms": save_ms,
        "total_ms": round((time.perf_counter() - turn_t0) * 1000),
        "status": status,
    }
    _TURN_METRICS.append(metric)
    _log_event("turn_metrics", **metric)

    return {
        "conversation_id": conversation_id,
        "turn_id": turn_id,
        "status": status,
        "replayed": False,
        "created_at": turn_created,
        "user": {"transcript": transcript},
        "pally": {"text": reply, "audio": tts_audio},  # audio = base64 inline (signed URL 미구현)
        "axes": smoothed,
        "character": character,
        "feedback": feedback_items,
        "warnings": warnings,
        "quota": {
            "used_turns": quota_used,
            "remaining_turns": max(FREE_DAILY_TURNS - quota_used, 0),
            "daily_limit": FREE_DAILY_TURNS,
            "exhausted": quota_used >= FREE_DAILY_TURNS,
            "resets_at": _kst_reset_at(),
        },
    }


# ── History & Detail & Complete & Reopen — 4주차 ─────────────────────────────


def _truncate(text: str, n: int) -> Optional[str]:
    t = " ".join((text or "").split())
    return t[:n] if t else None


def _owned_session(sb, conversation_id: str, user_id: str) -> dict:
    """conversation 소유권 확인. 없거나 타인 소유면 404 (존재 숨김)."""
    try:
        res = sb.table("sessions").select("*").eq("id", conversation_id).execute()
    except Exception as e:
        logging.error(f"session read failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to read conversation")
    if not res.data or res.data[0].get("user_id") != user_id:
        raise AppError(404, "not_found", "Conversation not found")
    return res.data[0]


@app.get("/api/conversations")
async def list_conversations(
    user_id: str = Depends(get_current_user_id),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    status: Optional[str] = Query(None),
):
    """History 목록. 최근 생성순, cursor(created_at) 기반 pagination, 본인 것만."""
    sb = get_supabase()
    q = sb.table("sessions").select("*").eq("user_id", user_id)
    if status == "active":
        q = q.is_("ended_at", "null")
    elif status == "completed":
        q = q.not_.is_("ended_at", "null")
    if cursor:
        q = q.lt("created_at", cursor)
    q = q.order("created_at", desc=True).limit(limit)
    try:
        sess = q.execute()
    except Exception as e:
        logging.error(f"list_conversations failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to list conversations")

    rows = sess.data or []
    ids = [s["id"] for s in rows]
    msgs_by_session: Dict[str, list] = {sid: [] for sid in ids}
    if ids:
        try:
            msgs = sb.table("messages").select("session_id, role, transcript, feedback, created_at").in_("session_id", ids).order("created_at").execute()
        except Exception as e:
            logging.error(f"list_conversations messages failed: {e}")
            raise AppError(503, "persistence_failed", "Failed to load conversation summaries")
        for m in (msgs.data or []):
            msgs_by_session.setdefault(m["session_id"], []).append(m)

    items = []
    for s in rows:
        ms = msgs_by_session.get(s["id"], [])
        user_msgs = [m for m in ms if m["role"] == "user"]
        items.append({
            "id": s["id"],
            "status": "completed" if s.get("ended_at") else "active",
            "title": _truncate(user_msgs[0]["transcript"], 60) if user_msgs else None,
            "started_at": s["created_at"],
            "last_turn_at": ms[-1]["created_at"] if ms else None,
            "completed_at": s.get("ended_at"),
            "turn_count": len(user_msgs),
            "feedback_count": sum(len(m.get("feedback") or []) for m in user_msgs),
            "preview": _truncate(user_msgs[-1]["transcript"], 120) if user_msgs else None,
        })

    next_cursor = rows[-1]["created_at"] if len(rows) == limit else None
    return {"items": items, "next_cursor": next_cursor}


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
):
    """대화 상세: conversation + turns(각 turn 의 feedback 포함). 본인 것만."""
    sb = get_supabase()
    session = _owned_session(sb, conversation_id, user_id)

    q = sb.table("messages").select("id, role, transcript, feedback, axes, created_at").eq("session_id", conversation_id)
    if cursor:
        q = q.gt("created_at", cursor)
    try:
        msgs = q.order("created_at").execute()
    except Exception as e:
        logging.error(f"get_conversation messages failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to load turns")
    ms = msgs.data or []

    # user→pally 쌍으로 turn 구성. turn_id = user 메시지 id.
    turns = []
    seq = 0
    pending_user = None
    for m in ms:
        if m["role"] == "user":
            if pending_user is not None:
                seq += 1
                turns.append(_turn_detail(pending_user, None, seq))
            pending_user = m
        else:
            seq += 1
            turns.append(_turn_detail(pending_user, m, seq))
            pending_user = None
    if pending_user is not None:
        seq += 1
        turns.append(_turn_detail(pending_user, None, seq))

    page = turns[:limit]
    next_cursor = page[-1]["created_at"] if len(turns) > limit else None

    user_msgs = [m for m in ms if m["role"] == "user"]
    conv = {
        "id": session["id"],
        "status": "completed" if session.get("ended_at") else "active",
        "title": _truncate(user_msgs[0]["transcript"], 60) if user_msgs else None,
        "started_at": session["created_at"],
        "last_turn_at": ms[-1]["created_at"] if ms else None,
        "completed_at": session.get("ended_at"),
        "reopened_at": session.get("reopened_at"),
        "reopen_count": session.get("reopen_count", 0),
        "turn_count": len(user_msgs),
    }
    return {"conversation": conv, "turns": page, "next_cursor": next_cursor}


def _turn_detail(user_msg: Optional[dict], pally_msg: Optional[dict], seq: int) -> dict:
    return {
        "id": user_msg["id"] if user_msg else (pally_msg["id"] if pally_msg else None),
        "sequence": seq,
        "status": "completed",
        "user_transcript": user_msg["transcript"] if user_msg else None,
        "pally_text": pally_msg["transcript"] if pally_msg else None,
        "feedback": (user_msg.get("feedback") if user_msg else None) or [],
        "created_at": (user_msg or pally_msg)["created_at"],
    }


@app.post("/api/conversations/{conversation_id}/complete")
async def complete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    _idem: str = Depends(require_idempotency_key),
):
    """대화 종료. 재호출해도 같은 결과(멱등)."""
    sb = get_supabase()
    session = _owned_session(sb, conversation_id, user_id)

    if not session.get("ended_at"):
        try:
            res = sb.table("sessions").update({"ended_at": _now_iso()}).eq("id", conversation_id).eq("user_id", user_id).execute()
        except Exception as e:
            logging.error(f"complete_conversation failed: {e}")
            raise AppError(503, "persistence_failed", "Failed to complete conversation")
        session = res.data[0] if res.data else session

    return {"conversation": {
        "id": session["id"],
        "status": "completed",
        "completed_at": session.get("ended_at"),
    }}


@app.post("/api/conversations/{conversation_id}/reopen")
async def reopen_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    _idem: str = Depends(require_idempotency_key),
):
    """완료된 대화를 같은 id 로 재개. 기존 turn/feedback 보존, 이후 turn append."""
    sb = get_supabase()
    session = _owned_session(sb, conversation_id, user_id)

    if not session.get("ended_at"):
        raise AppError(409, "conversation_already_active", "Conversation is already active")

    try:
        res = sb.table("sessions").update({
            "ended_at": None,
            "reopened_at": _now_iso(),
            "reopen_count": (session.get("reopen_count") or 0) + 1,
        }).eq("id", conversation_id).eq("user_id", user_id).execute()
    except Exception as e:
        logging.error(f"reopen_conversation failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to reopen conversation")

    row = res.data[0] if res.data else session
    return {"conversation": {
        "id": row["id"],
        "status": "active",
        "completed_at": None,
        "reopened_at": row.get("reopened_at"),
        "reopen_count": row.get("reopen_count", 0),
    }}


# ── Achievements — 일일 Task 3개 + Streak (5주차, A단계) ──────────────────────
#
# PM v2.0: 30개 마스터 풀에서 매일 A1 고정 + hash 로 2개 결정적 선택.
# Streak = 그날 3개 모두 완료한 날의 연속 수. 완료 판정은 서버 계산(클라이언트 못 씀).
# A단계는 "오늘 범위" Task(A/B/C/D + E6)를 판정하고, 측정이 복잡한 7개
# (A5 reopen, D1 톤변화, E1~E5 주간·추세)는 B단계로 미뤄 항상 미완료로 둔다.

# (category, title, description)
_TASK_CATALOG: Dict[str, tuple] = {
    "A1": ("A", "오늘 Pally와 대화 시작하기", "오늘 Pally와 새 대화를 시작해보세요"),
    "A2": ("A", "오늘 대화에서 3턴 이상 주고받기", "오늘 대화에서 3턴 이상 주고받아보세요"),
    "A3": ("A", "오늘 대화에서 5턴 이상 주고받기", "오늘 대화에서 5턴 이상 주고받아보세요"),
    "A4": ("A", "오늘 대화 세션 2개 이상 만들기", "오늘 새 대화를 2개 이상 시작해보세요"),
    "A5": ("A", "History에서 이전 대화 이어가기", "이전에 완료한 대화를 다시 이어가보세요"),
    "A6": ("A", "오늘 대화를 끝까지 완료하기", "오늘 대화를 완료 상태로 마무리해보세요"),
    "B1": ("B", "대화 중 질문 담긴 발화 하기", "물음표가 담긴 발화를 한 번 이상 해보세요"),
    "B2": ("B", "한 턴에 30단어 이상 길게 말해보기", "한 턴에 30단어 이상 길게 말해보세요"),
    "B3": ("B", "Energy 축 60 이상 기록하기", "활기찬 말투로 Energy를 올려보세요"),
    "B4": ("B", "Humor 축 60 이상 기록하기", "유머러스한 말투로 Humor를 올려보세요"),
    "B5": ("B", "Curiosity 축 60 이상 기록하기", "호기심 담긴 말투로 Curiosity를 올려보세요"),
    "B6": ("B", "나만의 톤으로 대화하기", "격식/비격식 어느 쪽이든 뚜렷한 톤으로 말해보세요"),
    "C1": ("C", "오늘 대화에서 교정 표현 받아보기", "오늘 대화에서 피드백을 받아보세요"),
    "C2": ("C", "지난 대화 기록 다시 열어보기", "이전 대화 상세를 다시 열어보세요"),
    "C3": ("C", "대화 로그 펼쳐서 다시 읽어보기", "대화 로그를 펼쳐서 읽어보세요"),
    "C4": ("C", "대화 로그 2번 이상 펼쳐보기", "대화 로그를 2번 이상 펼쳐보세요"),
    "C5": ("C", "대화 중 피드백 2개 이상 만들기", "오늘 피드백을 2개 이상 받아보세요"),
    "C6": ("C", "오늘 나온 교정 표현 확인하기", "오늘 받은 교정 표현을 열어 확인해보세요"),
    "D1": ("D", "대화 속에서 Pally 톤 변화 느껴보기", "말투를 바꿔 Pally의 톤 변화를 만들어보세요"),
    "D2": ("D", "오전에 대화하기", "오전(06~12시)에 대화해보세요"),
    "D3": ("D", "저녁에 대화하기", "저녁(18~24시)에 대화해보세요"),
    "D4": ("D", "주말에도 대화하기", "주말에도 대화를 이어가보세요"),
    "D5": ("D", "My Pally에서 내 프로필 확인하기", "My Pally에서 프로필을 확인해보세요"),
    "D6": ("D", "Achievements에서 Streak 확인하기", "Achievements에서 오늘의 Streak을 확인해보세요"),
    "E1": ("E", "어제에 이어 오늘도 Streak 이어가기", "어제에 이어 오늘도 3개 Task를 완료해보세요"),
    "E2": ("E", "이번 주 3일 이상 대화하기", "이번 주에 3일 이상 대화해보세요"),
    "E3": ("E", "이번 주 첫 대화 시작하기", "이번 주 첫 대화를 시작해보세요"),
    "E4": ("E", "Intimacy 축이 어제보다 상승하기", "어제보다 Intimacy를 더 올려보세요"),
    "E5": ("E", "지난 세션보다 더 긴 문장으로 말해보기", "지난 대화보다 평균적으로 더 길게 말해보세요"),
    "E6": ("E", "오늘 무료 대화량 절반 이상 채우기", "오늘 무료 대화량의 절반 이상을 사용해보세요"),
}
_FIXED_TASK = "A1"
_DEFERRED_TASKS = {"A5", "D1", "E1", "E2", "E3", "E4", "E5"}  # B단계에서 측정 채움


def _select_daily_task_ids(user_id: str, date_kst: str) -> list:
    """A1 고정 + 나머지 29개 중 hash(user_id+date) 로 2개 결정적 선택 (같은 날 불변)."""
    pool = [t for t in _TASK_CATALOG if t != _FIXED_TASK]
    ranked = sorted(pool, key=lambda t: hashlib.sha256(f"{user_id}:{date_kst}:{t}".encode()).hexdigest())
    return [_FIXED_TASK, ranked[0], ranked[1]]


def _kst_day_window_utc(date_kst: str) -> tuple:
    d = datetime.fromisoformat(date_kst).date()
    start = datetime.combine(d, dtime.min, tzinfo=_KST).astimezone(timezone.utc)
    return start.isoformat(), (start + timedelta(days=1)).isoformat()


def _gather_achievement_context(sb, user_id: str, date_kst: str) -> dict:
    start, end = _kst_day_window_utc(date_kst)
    try:
        sess = sb.table("sessions").select("id, created_at, ended_at").eq("user_id", user_id).execute()
    except Exception as e:
        logging.error(f"achievements sessions read failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to load achievements data")
    sessions = sess.data or []
    sess_ids = [s["id"] for s in sessions]
    sessions_today = [s for s in sessions if start <= s["created_at"] < end]
    completed_today = [s for s in sessions if s.get("ended_at") and start <= s["ended_at"] < end]

    user_msgs = []
    if sess_ids:
        msgs = sb.table("messages").select("role, transcript, axes, feedback, created_at").in_("session_id", sess_ids).gte("created_at", start).lt("created_at", end).execute()
        user_msgs = [m for m in (msgs.data or []) if m["role"] == "user"]

    ev = sb.table("activity_events").select("event_type").eq("user_id", user_id).gte("received_at", start).lt("received_at", end).execute()
    event_counts: Dict[str, int] = {}
    for e in (ev.data or []):
        event_counts[e["event_type"]] = event_counts.get(e["event_type"], 0) + 1

    usage = sb.table("usage_daily").select("used_turns").eq("user_id", user_id).eq("date_kst", date_kst).execute()
    used_turns = usage.data[0]["used_turns"] if usage.data else 0

    return {
        "date_kst": date_kst,
        "sessions_today": sessions_today,
        "completed_today": completed_today,
        "user_msgs": user_msgs,
        "event_counts": event_counts,
        "used_turns": used_turns,
    }


def _msg_in_kst_hour(msgs: list, h_start: int, h_end: int) -> bool:
    for m in msgs:
        dt = datetime.fromisoformat(m["created_at"].replace("Z", "+00:00")).astimezone(_KST)
        if h_start <= dt.hour < h_end:
            return True
    return False


def _eval_task(task_id: str, ctx: dict) -> bool:
    if task_id in _DEFERRED_TASKS:
        return False
    um = ctx["user_msgs"]
    ec = ctx["event_counts"]

    def axis_any(key, pred) -> bool:
        return any(pred((m.get("axes") or {}).get(key)) for m in um if m.get("axes"))

    if task_id == "A1":
        return len(ctx["sessions_today"]) >= 1
    if task_id == "A2":
        return len(um) >= 3
    if task_id == "A3":
        return len(um) >= 5
    if task_id == "A4":
        return len(ctx["sessions_today"]) >= 2
    if task_id == "A6":
        return len(ctx["completed_today"]) >= 1
    if task_id == "B1":
        return any("?" in (m.get("transcript") or "") for m in um)
    if task_id == "B2":
        return any(len((m.get("transcript") or "").split()) >= 30 for m in um)
    if task_id == "B3":
        return axis_any("Energy", lambda v: v is not None and v >= 60)
    if task_id == "B4":
        return axis_any("Humor", lambda v: v is not None and v >= 60)
    if task_id == "B5":
        return axis_any("Curiosity", lambda v: v is not None and v >= 60)
    if task_id == "B6":
        return axis_any("Formality", lambda v: v is not None and (v <= 20 or v >= 80))
    if task_id == "C1":
        return sum(len(m.get("feedback") or []) for m in um) >= 1
    if task_id == "C5":
        return sum(len(m.get("feedback") or []) for m in um) >= 2
    if task_id == "C2":
        return ec.get("conversation_detail_opened", 0) >= 1
    if task_id == "C3":
        return ec.get("transcript_expanded", 0) >= 1
    if task_id == "C4":
        return ec.get("transcript_expanded", 0) >= 2
    if task_id == "C6":
        return ec.get("feedback_item_opened", 0) >= 1
    if task_id == "D2":
        return _msg_in_kst_hour(um, 6, 12)
    if task_id == "D3":
        return _msg_in_kst_hour(um, 18, 24)
    if task_id == "D4":
        return datetime.fromisoformat(ctx["date_kst"]).weekday() >= 5 and len(um) >= 1
    if task_id == "D5":
        return ec.get("profile_opened", 0) >= 1
    if task_id == "D6":
        return ec.get("achievements_opened", 0) >= 1
    if task_id == "E6":
        return ctx["used_turns"] >= max(1, FREE_DAILY_TURNS // 2)
    return False


def _compute_streak(sb, user_id: str, today_kst: str) -> int:
    try:
        rows = sb.table("streak_days").select("date_kst, qualified").eq("user_id", user_id).order("date_kst", desc=True).limit(400).execute()
    except Exception as e:
        logging.warning(f"streak read failed: {e}")
        return 0
    qualified = {r["date_kst"] for r in (rows.data or []) if r["qualified"]}
    today = datetime.fromisoformat(today_kst).date()
    cursor = today if today_kst in qualified else today - timedelta(days=1)
    count = 0
    while cursor.isoformat() in qualified:
        count += 1
        cursor -= timedelta(days=1)
    return count


@app.get("/api/achievements")
async def get_achievements(user_id: str = Depends(get_current_user_id)):
    """
    오늘의 Daily Task 3개(완료 상태 포함) + Streak. 서버 계산만 신뢰 (클라이언트 못 씀).
    D6(achievements_opened)은 이 화면 진입 이벤트라, 이 API 자체로는 완료되지 않는다
    — 프론트가 POST /api/activity-events(achievements_opened)를 보낸 뒤 반영됨.
    """
    sb = get_supabase()
    date_kst = _kst_date()

    # 1. 오늘 선택 3개 (snapshot 고정). 선택은 결정적이라 경합해도 동일.
    try:
        snap = sb.table("daily_task_snapshots").select("task_ids").eq("user_id", user_id).eq("date_kst", date_kst).execute()
    except Exception as e:
        logging.error(f"daily_task_snapshots read failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to load daily tasks")
    if snap.data:
        task_ids = snap.data[0]["task_ids"]
    else:
        task_ids = _select_daily_task_ids(user_id, date_kst)
        try:
            sb.table("daily_task_snapshots").upsert(
                {"user_id": user_id, "date_kst": date_kst, "task_ids": task_ids},
                on_conflict="user_id,date_kst", ignore_duplicates=True,
            ).execute()
        except Exception as e:
            logging.error(f"daily_task_snapshots write failed: {e}")
            raise AppError(503, "persistence_failed", "Failed to persist daily tasks")

    # 2. 완료 평가
    ctx = _gather_achievement_context(sb, user_id, date_kst)
    completed_at = _now_iso()
    daily_tasks = []
    all_done = True
    for tid in task_ids:
        _cat, title, desc = _TASK_CATALOG.get(tid, ("?", tid, ""))
        done = _eval_task(tid, ctx)
        if not done:
            all_done = False
        daily_tasks.append({
            "id": tid,
            "title": title,
            "description": desc,
            "status": "completed" if done else "default",
            "completed_at": completed_at if done else None,
        })

    # 3. Streak: 오늘 자격 여부 기록 + 연속 카운트
    try:
        sb.table("streak_days").upsert(
            {"user_id": user_id, "date_kst": date_kst, "qualified": all_done},
            on_conflict="user_id,date_kst",
        ).execute()
    except Exception as e:
        logging.warning(f"streak_days upsert failed: {e}")
    streak_count = _compute_streak(sb, user_id, date_kst)

    return {
        "date": date_kst,
        "timezone": "Asia/Seoul",
        "streak_count": streak_count,
        "daily_tasks": daily_tasks,
    }
