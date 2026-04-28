"""Orchestration logic for the /translate endpoint."""
from backend.session import TurnError
from backend.tts_helpers import synthesize_tts


def process_translation(
    audio_bytes: bytes,
    filename: str,
    tts_provider_id: str,
    tts_voice_id: str | None,
    stt_provider,
    ai_provider,
) -> dict:
    """Run the full STT → translate → TTS pipeline.

    Returns the full response dict in the same shape as the /translate endpoint response.
    """
    stt_result = stt_provider.transcribe(audio_bytes, filename)

    if isinstance(stt_result, TurnError):
        return {
            "english": None,
            "spanish": None,
            "audio_b64": None,
            "tts_error": None,
            "error": {
                "stage": stt_result.stage,
                "message": stt_result.message,
                "recoverable": stt_result.recoverable,
            },
        }

    _, transcript_norm = stt_result
    translation_result = ai_provider.translate(transcript_norm)

    if isinstance(translation_result, TurnError):
        return {
            "english": transcript_norm,
            "spanish": None,
            "audio_b64": None,
            "tts_error": None,
            "error": {
                "stage": translation_result.stage,
                "message": translation_result.message,
                "recoverable": translation_result.recoverable,
            },
        }

    spanish = translation_result
    audio_b64, tts_error = synthesize_tts(spanish, tts_provider_id, tts_voice_id)

    return {
        "english": transcript_norm,
        "spanish": spanish,
        "audio_b64": audio_b64,
        "tts_error": tts_error,
        "error": None,
    }
