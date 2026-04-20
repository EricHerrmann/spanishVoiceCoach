import re
import os
from typing import Union
from backend.session import TurnError


def normalize_transcript(text: str) -> str:
    """Lowercase and strip punctuation from a Whisper transcript."""
    text = text.lower()
    # Remove punctuation: standard ASCII + Spanish-specific ¡¿
    text = re.sub(r"[¡¿!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~]", "", text)
    return text.strip()


class WhisperSTT:
    """Speech-to-Text provider using OpenAI's Whisper model (local, base variant)."""

    _model = None

    def _get_model(self):
        if WhisperSTT._model is None:
            import whisper
            WhisperSTT._model = whisper.load_model("base")
        return WhisperSTT._model

    def transcribe(self, audio_path: str) -> Union[tuple[str, str], TurnError]:
        """Transcribe audio file to (transcript_raw, transcript_norm) or TurnError."""
        if not os.path.exists(audio_path):
            return TurnError(stage="stt", message=f"Audio file not found: {audio_path}", recoverable=True)
        try:
            model = self._get_model()
            result = model.transcribe(audio_path, language="es")
            raw = result["text"].strip()
            norm = normalize_transcript(raw)
            return (raw, norm)
        except Exception as exc:
            return TurnError(stage="stt", message=f"Transcription failed: {exc}", recoverable=True)
