"""Helper for ElevenLabs TTS synthesis, shared by turn, translation, and pronunciation routes."""
import base64

from backend.session import TurnError
from backend.tts import ElevenLabsTTSProvider


def synthesize_tts(
    text: str,
    tts_provider_id: str,
    tts_voice_id: str | None,
) -> tuple[str | None, dict | None]:
    """Call ElevenLabs if configured, else return (None, None).

    Returns (audio_b64, None) on success, (None, error_dict) on TTS failure.
    If tts_provider_id is not 'elevenlabs' or tts_voice_id is missing, returns (None, None).
    """
    if tts_provider_id != "elevenlabs" or not tts_voice_id:
        return None, None

    try:
        tts = ElevenLabsTTSProvider(tts_voice_id)
        tts_result = tts.synthesize(text)
    except RuntimeError as exc:
        return None, {"stage": "tts", "message": str(exc), "recoverable": False}

    if isinstance(tts_result, bytes):
        return base64.b64encode(tts_result).decode("ascii"), None

    if isinstance(tts_result, TurnError):
        return None, {
            "stage": tts_result.stage,
            "message": tts_result.message,
            "recoverable": tts_result.recoverable,
        }

    # None or unexpected — no audio, no error
    return None, None
