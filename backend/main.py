import os
import tempfile
from typing import Literal
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from pydantic import BaseModel, Field
from backend.session import Session, TurnError, new_session
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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/topics")
def get_topics():
    return _TOPICS


@app.get("/providers")
def get_providers():
    return _PROVIDERS


@app.post("/session/start")
def session_start(body: SessionStartRequest | None = Body(default=None)):
    req = body or SessionStartRequest()
    session = new_session(
        topic=req.topic,
        level=req.level,
        ai_provider=req.ai_provider,
        coaching_mode=req.coaching_mode,
    )
    sessions[session.id] = session
    return {"session_id": session.id}


@app.post("/turn")
async def post_turn(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
):
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(await audio.read())
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
            "error": {
                "stage": stt_result.stage,
                "message": stt_result.message,
                "recoverable": stt_result.recoverable,
            },
        }

    transcript_raw, transcript_norm = stt_result
    # CoachSession is re-instantiated per request; conversation history is
    # preserved via session.turns on the Session object, not on this instance.
    coach = CoachSession(session, claude_provider)
    turn_result = coach.handle_turn(transcript_norm)

    if isinstance(turn_result, TurnError):
        return {
            "transcript_raw": transcript_raw,
            "transcript_norm": transcript_norm,
            "coach_text": None,
            "corrections": [],
            "error": {
                "stage": turn_result.stage,
                "message": turn_result.message,
                "recoverable": turn_result.recoverable,
            },
        }

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
        "error": None,
    }
