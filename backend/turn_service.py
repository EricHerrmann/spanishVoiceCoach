"""Orchestration logic for the /turn endpoint."""
from backend.session import Session, TurnError, get_audio_store_dir, save_session, should_save_audio
from backend.coach import CoachSession
from backend.tts_helpers import synthesize_tts


def save_audio_file(session_id: str, audio_bytes: bytes, turn_index: int) -> str | None:
    """Persist user audio to disk if DVC_SAVE_AUDIO is enabled.

    Returns the file path on success, or None if audio saving is disabled.
    """
    if not should_save_audio():
        return None

    audio_dir = get_audio_store_dir() / session_id
    audio_dir.mkdir(parents=True, exist_ok=True)
    path = audio_dir / f"turn-{turn_index:04d}.wav"
    path.write_bytes(audio_bytes)
    return str(path)


def process_turn(
    session: Session,
    audio_bytes: bytes,
    filename: str,
    stt_provider,
    ai_provider,
) -> dict:
    """Run the full STT → coach → TTS pipeline for a single user turn.

    Returns the full response dict in the same shape as the /turn endpoint response.
    Side effect: appends turns to session and persists via save_session().
    """
    audio_file = save_audio_file(session.id, audio_bytes, len(session.turns) + 1)

    stt_result = stt_provider.transcribe(audio_bytes, filename)

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
    user_turn_index = len(session.turns)
    coach = CoachSession(session, ai_provider)
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

    audio_b64, tts_error = synthesize_tts(
        turn_result.coach_text,
        session.tts_provider,
        session.tts_voice_id,
    )

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
