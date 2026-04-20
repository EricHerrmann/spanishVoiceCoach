import tempfile
import os
from fastapi import FastAPI, UploadFile, File
from backend.session import TurnError
from backend.stt import WhisperSTT

stt_provider = WhisperSTT()
app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/turn")
async def post_turn(audio: UploadFile = File(...)):
    """Accept a WAV upload, transcribe it, and return transcript + echo.

    Phase 1: No AI — echo response equals transcript_norm.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        result = stt_provider.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)

    if isinstance(result, TurnError):
        return {
            "transcript_raw": None,
            "transcript_norm": None,
            "echo": None,
            "error": {
                "stage": result.stage,
                "message": result.message,
                "recoverable": result.recoverable,
            },
        }

    transcript_raw, transcript_norm = result
    return {
        "transcript_raw": transcript_raw,
        "transcript_norm": transcript_norm,
        "echo": transcript_norm,
        "error": None,
    }
