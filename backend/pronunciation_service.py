"""Orchestration logic for the /pronunciation/evaluate endpoint."""
import json
import pathlib

from backend.session import TurnError

_PRONUNCIATION_CHALLENGES_PATH: pathlib.Path = (
    pathlib.Path(__file__).parent / "data" / "pronunciation_challenges.json"
)


def load_challenges() -> list[dict]:
    """Return the pronunciation challenge list from the bundled data file."""
    with open(_PRONUNCIATION_CHALLENGES_PATH) as f:
        return json.load(f)


def process_pronunciation_eval(
    audio_bytes: bytes,
    filename: str,
    target: str,
    stt_provider,
    ai_provider,
) -> dict:
    """Run the full STT → pronunciation evaluation pipeline.

    Returns the full response dict in the same shape as the /pronunciation/evaluate response.
    """
    stt_result = stt_provider.transcribe(audio_bytes, filename)

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
    eval_result = ai_provider.evaluate_pronunciation(target, transcript_norm)

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
        "issues": [
            {"sound": iss.sound, "said": iss.said, "expected": iss.expected}
            for iss in eval_result.issues
        ],
        "error": None,
    }
