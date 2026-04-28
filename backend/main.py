import base64
import json
import os
import pathlib
import secrets
from collections import OrderedDict
from typing import Literal
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from backend.session import Session, TurnError, list_sessions, load_session, new_session, save_session
from backend.tts import ELEVENLABS_VOICES
from backend.stt import get_stt_provider
from backend.ai.claude import ClaudeProvider
from backend.flashcards_store import load_user_deck, save_user_deck, load_filtered_deck
from backend.turn_service import process_turn
from backend.translation_service import process_translation
from backend.pronunciation_service import load_challenges, process_pronunciation_eval

_TOPICS = [
    {"id": "general", "label": "General conversation", "starter": "Hola, ¿de qué quieres hablar hoy?"},
    {"id": "ordering_food", "label": "Ordering food", "starter": "Hola, ¿qué me recomiendas del menú?"},
    {"id": "directions_transport", "label": "Directions & transport", "starter": "Disculpe, ¿cómo llego a la estación de metro?"},
    {"id": "shopping_markets", "label": "Shopping & markets", "starter": "Buenas, estoy buscando algo de temporada."},
    {"id": "work_daily_routine", "label": "Work & daily routine", "starter": "¿Cómo fue tu día en el trabajo?"},
    {"id": "travel_tourism", "label": "Travel & tourism", "starter": "¿Qué lugares me recomiendas visitar aquí?"},
]
_PROVIDERS = [{"id": "claude", "label": "Claude (Anthropic)"}]

stt_provider = get_stt_provider()
claude_provider = ClaudeProvider()
_SESSION_CACHE_MAX = 50
sessions: OrderedDict[str, Session] = OrderedDict()
app = FastAPI()


def _cache_session(session_id: str, session: Session) -> None:
    """Insert or refresh session in the LRU cache; evict oldest entry if over cap."""
    sessions.pop(session_id, None)       # remove so reinsertion moves to end (most recent)
    sessions[session_id] = session
    while len(sessions) > _SESSION_CACHE_MAX:
        sessions.popitem(last=False)     # evict least-recently-used (front of OrderedDict)


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        expected_user = os.environ.get("DVC_BASIC_AUTH_USER")
        expected_pass = os.environ.get("DVC_BASIC_AUTH_PASS")
        if not expected_user or not expected_pass:
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
            except Exception:
                pass
            else:
                user, _, pw = decoded.partition(":")
                if secrets.compare_digest(user, expected_user) and secrets.compare_digest(pw, expected_pass):
                    return await call_next(request)
        return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="duoVoiceCoach"'})


app.add_middleware(BasicAuthMiddleware)


class SessionStartRequest(BaseModel):
    topic: str = "general"
    level: int = Field(default=5, ge=1, le=10)
    ai_provider: Literal["claude"] = "claude"
    coaching_mode: Literal["on_demand", "explicit", "shadowing"] = "on_demand"
    tts_provider: Literal["browser", "elevenlabs"] = "browser"
    tts_voice_id: str | None = None


class FlashcardGenerateRequest(BaseModel):
    text: str | None = None
    turns: list[dict] = []
    source: Literal["turn", "conversation", "translation"] = "turn"


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
    _cache_session(session.id, session)
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
    _cache_session(session.id, session)
    return session


@app.post("/turn")
async def post_turn(audio: UploadFile = File(...), session_id: str = Form(...)):
    session = _get_session(session_id)
    audio_bytes = await audio.read()
    return process_turn(session, audio_bytes, audio.filename or "audio.wav", stt_provider, claude_provider)


@app.post("/pronunciation/evaluate")
async def pronunciation_evaluate(audio: UploadFile = File(...), target: str = Form(...)):
    audio_bytes = await audio.read()
    return process_pronunciation_eval(
        audio_bytes, audio.filename or "audio.wav", target, stt_provider, claude_provider
    )


@app.get("/pronunciation/challenges")
def get_pronunciation_challenges():
    try:
        return load_challenges()
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Pronunciation challenges data not found")


@app.get("/flashcards/deck")
def get_flashcard_deck(level_min: int = None, level_max: int = None, topic: str = None):
    try:
        return load_filtered_deck(topic=topic, level_min=level_min, level_max=level_max)
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Flashcard deck data not found")


@app.post("/flashcards/generate")
def post_flashcard_generate(body: FlashcardGenerateRequest):
    result = claude_provider.generate_flashcards(body.text or "", body.turns, body.source)
    if isinstance(result, TurnError):
        raise HTTPException(status_code=500, detail=result.message)
    return save_user_deck(result)


@app.post("/translate")
async def translate(
    audio: UploadFile = File(...),
    tts_provider: str = Form("browser"),
    tts_voice_id: str = Form(None),
):
    audio_bytes = await audio.read()
    return process_translation(
        audio_bytes, audio.filename or "audio.wav", tts_provider, tts_voice_id, stt_provider, claude_provider
    )


_DIST = pathlib.Path(__file__).parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")
