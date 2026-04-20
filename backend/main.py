import os
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from backend.session import Session, TurnError, new_session
from backend.stt import WhisperSTT
from backend.coach import CoachSession
from backend.ai.claude import ClaudeProvider

stt_provider = WhisperSTT()
claude_provider = ClaudeProvider()
sessions: dict[str, Session] = {}
app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/session/start")
def session_start():
    session = new_session(
        topic="general",
        level=5,
        ai_provider="claude",
        coaching_mode="on_demand",
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
