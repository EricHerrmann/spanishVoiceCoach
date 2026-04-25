import os
import re
import tempfile
from typing import Union
from backend.session import TurnError


def normalize_transcript(text: str) -> str:
    """Lowercase and strip punctuation from a Whisper transcript."""
    text = text.lower()
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

    def transcribe(self, audio_bytes: bytes, filename: str) -> Union[tuple[str, str], TurnError]:
        """Transcribe audio bytes to (transcript_raw, transcript_norm) or TurnError."""
        ext = os.path.splitext(filename)[1] or ".wav"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            model = self._get_model()
            result = model.transcribe(tmp_path, language="es")
            raw = result["text"].strip()
            norm = normalize_transcript(raw)
            return (raw, norm)
        except Exception as exc:
            return TurnError(stage="stt", message=f"Transcription failed: {exc}", recoverable=True)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)


class OpenAIWhisperSTT:
    """Speech-to-Text provider using OpenAI Whisper API."""

    def transcribe(self, audio_bytes: bytes, filename: str) -> Union[tuple[str, str], TurnError]:
        """Transcribe audio bytes to (transcript_raw, transcript_norm) or TurnError."""
        try:
            import openai
            client = openai.OpenAI()
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=(filename, audio_bytes),
                language="es",
            )
            raw = result.text.strip()
            norm = normalize_transcript(raw)
            return (raw, norm)
        except Exception as exc:
            return TurnError(stage="stt", message=f"Transcription failed: {exc}", recoverable=True)


def get_stt_provider() -> WhisperSTT | OpenAIWhisperSTT:
    """Return STT provider selected by STT_PROVIDER env var (default: local)."""
    if os.environ.get("STT_PROVIDER") == "openai":
        return OpenAIWhisperSTT()
    return WhisperSTT()
