import base64
import json
import os
import pathlib
import tempfile
from typing import Literal
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from backend.session import (
    Session,
    TurnError,
    get_audio_store_dir,
    list_sessions,
    load_session,
    new_session,
    save_session,
    should_save_audio,
)
from backend.tts import ELEVENLABS_VOICES, ElevenLabsTTSProvider
from backend.stt import WhisperSTT
from backend.coach import CoachSession
from backend.ai.claude import ClaudeProvider

_TOPICS = [
    {"id": "general", "label": "General conversation", "starter": "Hola, ¿de qué quieres hablar hoy?"},
    {"id": "ordering_food", "label": "Ordering food", "starter": "Hola, ¿qué me recomiendas del menú?"},
    {"id": "directions_transport", "label": "Directions & transport", "starter": "Disculpe, ¿cómo llego a la estación de metro?"},
    {"id": "shopping_markets", "label": "Shopping & markets", "starter": "Buenas, estoy buscando algo de temporada."},
    {"id": "work_daily_routine", "label": "Work & daily routine", "starter": "¿Cómo fue tu día en el trabajo?"},
    {"id": "travel_tourism", "label": "Travel & tourism", "starter": "¿Qué lugares me recomiendas visitar aquí?"},
]

_PROVIDERS = [
    {"id": "claude", "label": "Claude (Anthropic)"},
]

stt_provider = WhisperSTT()
claude_provider = ClaudeProvider()
sessions: dict[str, Session] = {}
app = FastAPI()


class SessionStartRequest(BaseModel):
    topic: str = "general"
    level: int = Field(default=5, ge=1, le=10)
    ai_provider: Literal["claude"] = "claude"
    coaching_mode: Literal["on_demand", "explicit", "shadowing"] = "on_demand"
    tts_provider: Literal["browser", "elevenlabs"] = "browser"
    tts_voice_id: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/topics")
def get_topics():
    return _TOPICS


@app.get("/providers")
def get_providers():
    return _PROVIDERS


@app.get("/tts-voices")
def get_tts_voices():
    return ELEVENLABS_VOICES


@app.post("/session/start")
def session_start(body: SessionStartRequest | None = Body(default=None)):
    req = body or SessionStartRequest()
    session = new_session(
        topic=req.topic,
        level=req.level,
        ai_provider=req.ai_provider,
        coaching_mode=req.coaching_mode,
        tts_provider=req.tts_provider,
        tts_voice_id=req.tts_voice_id,
    )
    sessions[session.id] = session
    save_session(session)
    return {"session_id": session.id}


@app.get("/sessions")
def get_sessions():
    return list_sessions()


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    return _get_session(session_id).to_dict()


def _get_session(session_id: str) -> Session:
    session = sessions.get(session_id)
    if session is not None:
        return session
    try:
        session = load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    sessions[session.id] = session
    return session


def _save_audio_file(session_id: str, audio_bytes: bytes, turn_index: int) -> str | None:
    if not should_save_audio():
        return None

    audio_dir = get_audio_store_dir() / session_id
    audio_dir.mkdir(parents=True, exist_ok=True)
    path = audio_dir / f"turn-{turn_index:04d}.wav"
    path.write_bytes(audio_bytes)
    return str(path)


@app.post("/turn")
async def post_turn(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
):
    session = _get_session(session_id)
    audio_bytes = await audio.read()
    audio_file = _save_audio_file(session_id, audio_bytes, len(session.turns) + 1)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        stt_result = stt_provider.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)

    if isinstance(stt_result, TurnError):
        return {
            "transcript_raw": None,
            "transcript_norm": None,
            "coach_text": None,
            "corrections": [],
            "audio_b64": None,
            "tts_error": None,
            "error": {
                "stage": stt_result.stage,
                "message": stt_result.message,
                "recoverable": stt_result.recoverable,
            },
        }

    transcript_raw, transcript_norm = stt_result
    # CoachSession is re-instantiated per request; conversation history is
    # preserved via session.turns on the Session object, not on this instance.
    user_turn_index = len(session.turns)
    coach = CoachSession(session, claude_provider)
    turn_result = coach.handle_turn(transcript_norm)
    if user_turn_index < len(session.turns) and session.turns[user_turn_index].speaker == "user":
        session.turns[user_turn_index].transcript_raw = transcript_raw
        session.turns[user_turn_index].audio_file = audio_file
    save_session(session)

    if isinstance(turn_result, TurnError):
        return {
            "transcript_raw": transcript_raw,
            "transcript_norm": transcript_norm,
            "coach_text": None,
            "corrections": [],
            "audio_b64": None,
            "tts_error": None,
            "error": {
                "stage": turn_result.stage,
                "message": turn_result.message,
                "recoverable": turn_result.recoverable,
            },
        }

    # --- TTS ---
    audio_b64 = None
    tts_error = None
    if session.tts_provider == "elevenlabs" and session.tts_voice_id:
        try:
            tts = ElevenLabsTTSProvider(session.tts_voice_id)
            tts_result = tts.synthesize(turn_result.coach_text)
            if isinstance(tts_result, bytes):
                audio_b64 = base64.b64encode(tts_result).decode("ascii")
            elif isinstance(tts_result, TurnError):
                tts_error = {
                    "stage": tts_result.stage,
                    "message": tts_result.message,
                    "recoverable": tts_result.recoverable,
                }
        except RuntimeError as exc:
            tts_error = {"stage": "tts", "message": str(exc), "recoverable": False}

    return {
        "transcript_raw": transcript_raw,
        "transcript_norm": transcript_norm,
        "coach_text": turn_result.coach_text,
        "corrections": [
            {
                "original": c.original,
                "corrected": c.corrected,
                "explanation": c.explanation,
                "triggered_by": c.triggered_by,
            }
            for c in turn_result.corrections
        ],
        "audio_b64": audio_b64,
        "tts_error": tts_error,
        "error": None,
    }


_PRONUNCIATION_CHALLENGES_PATH = pathlib.Path(__file__).parent / "data" / "pronunciation_challenges.json"


@app.get("/pronunciation/challenges")
def get_pronunciation_challenges():
    try:
        with open(_PRONUNCIATION_CHALLENGES_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Pronunciation challenges data not found")


@app.post("/pronunciation/evaluate")
async def pronunciation_evaluate(
    audio: UploadFile = File(...),
    target: str = Form(...),
):
    audio_bytes = await audio.read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        stt_result = stt_provider.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)

    if isinstance(stt_result, TurnError):
        return {
            "transcript": None,
            "score": None,
            "feedback": None,
            "issues": [],
            "error": {
                "stage": stt_result.stage,
                "message": stt_result.message,
                "recoverable": stt_result.recoverable,
            },
        }

    _, transcript_norm = stt_result
    eval_result = claude_provider.evaluate_pronunciation(target, transcript_norm)

    if isinstance(eval_result, TurnError):
        return {
            "transcript": transcript_norm,
            "score": None,
            "feedback": None,
            "issues": [],
            "error": {
                "stage": eval_result.stage,
                "message": eval_result.message,
                "recoverable": eval_result.recoverable,
            },
        }

    return {
        "transcript": transcript_norm,
        "score": eval_result.score,
        "feedback": eval_result.feedback,
        "issues": [{"sound": iss.sound, "said": iss.said, "expected": iss.expected} for iss in eval_result.issues],
        "error": None,
    }


_DIST = pathlib.Path(__file__).parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")
