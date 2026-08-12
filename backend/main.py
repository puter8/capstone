# -*- coding: utf-8 -*-
import asyncio
import base64
import json
import logging
import os
import re
import sys

import uuid
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
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


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = f"req_{uuid.uuid4().hex}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
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
    raw_axes = analyze_utterance(req.utterance)

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
    raw_axes = analyze_utterance(req.utterance)

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


@app.post("/api/conversations/{conversation_id}/turns", status_code=201)
async def create_turn(
    conversation_id: str,
    audio: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    idem_key: str = Depends(require_idempotency_key),
):
    """
    음성 turn 1개 처리: 오디오 → STT → 5축/EMA → Gemini 답변 → TTS → 저장.
    - 소유권: 본인 conversation 이 아니면 404.
    - 실패/완료 구분: STT 무음/실패는 저장하지 않고 명시적 에러(빈 데이터로 숨기지 않음).
    - 중복방지: 같은 conversation·같은 Idempotency-Key 재시도는 외부 재호출 없이 저장된 turn 재반환.
    """
    if not GOOGLE_CLOUD_API_KEY or not GOOGLE_AI_API_KEY:
        raise AppError(503, "service_unavailable", "Speech/AI provider not configured")

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
            "warnings": [],
        }

    # 3. 오디오
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise AppError(400, "invalid_audio", "Empty audio file")

    # 4. STT (실패는 저장하지 않고 명시적 에러)
    try:
        transcript, _conf = await _stt_from_bytes(audio_bytes, audio.content_type or "")
    except Exception as e:
        logging.warning(f"turn STT failed: {e}")
        raise AppError(502, "stt_failed", "Speech recognition failed")
    if not transcript:
        raise AppError(422, "speech_not_recognized", "No recognizable speech in audio")

    # 5. 이전 이력 + 누적 axes 로드
    try:
        prior = sb.table("messages").select("role, transcript, axes, created_at").eq("session_id", conversation_id).order("created_at").execute()
    except Exception as e:
        logging.error(f"turn history read failed: {e}")
        raise AppError(503, "persistence_failed", "Failed to load history")
    prior_rows = prior.data or []
    history = [ChatMessage(role=m["role"], content=m["transcript"]) for m in prior_rows]
    current_axes = None
    for m in reversed(prior_rows):
        if m["role"] == "user" and m.get("axes"):
            current_axes = m["axes"]
            break

    # 6. 5축 → EMA → character (AI 룰 엔진 호출)
    raw_axes = analyze_utterance(transcript)
    smoothed = apply_ema(current_axes, raw_axes) if current_axes else raw_axes
    character = compute_character(smoothed)

    # 7. Gemini 답변 (기존 함수 호출; 실패 시 silent fallback 없이 명시적 실패)
    try:
        reply = await _call_gemini_chat(transcript, history, session["character_name"], session["level"])
    except Exception as e:
        logging.warning(f"turn Gemini failed: {e}")
        raise AppError(502, "ai_engine_failed", "Reply generation failed")

    # 8. TTS (비핵심 — 실패해도 turn 은 완료, audio 만 null)
    tts_audio: Optional[str] = None
    try:
        tts_audio = await _call_google_tts(_strip_emoji(reply))
    except Exception as e:
        logging.warning(f"turn TTS failed (non-fatal): {e}")
        tts_audio = None

    # 9. 저장 — user 행에만 idem_key (unique index 로 중복 저장 차단)
    try:
        save = sb.table("messages").insert([
            {
                "session_id": conversation_id,
                "role": "user",
                "transcript": transcript,
                "axes": smoothed,
                "character": character,
                "idempotency_key": idem_key,
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
        raise AppError(503, "persistence_failed", "Failed to save turn")

    # turn 식별: user 행이 곧 turn. turn_id/created_at 을 저장 결과에서 가져온다.
    user_row = next((r for r in (save.data or []) if r.get("role") == "user"), None)
    turn_id = user_row["id"] if user_row else None
    turn_created = user_row["created_at"] if user_row else None

    # TTS 만 실패한 경우 partial + warnings (계약 §4.6). 대화 텍스트는 정상.
    status = "completed"
    warnings: list = []
    if tts_audio is None:
        status = "partial"
        warnings.append({
            "code": "tts_failed",
            "message": "음성 생성에 실패했어요. 텍스트로 계속할 수 있어요.",
        })

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
        "warnings": warnings,
    }
