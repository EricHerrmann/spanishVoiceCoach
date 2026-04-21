from abc import ABC, abstractmethod
import os

import httpx

from backend.session import TurnError

# Pre-built ElevenLabs voices available on all accounts using eleven_multilingual_v2.
# Verify IDs at: https://api.elevenlabs.io/v1/voices (requires your API key)
ELEVENLABS_VOICES = [
    {
        "id": "21m00Tcm4TlvDq8ikWAM",
        "label": "Rachel — Female, clear (multilingual)",
        "description": "Clear female voice, natural in Spanish",
    },
    {
        "id": "ErXwobaYiN019PkySvjV",
        "label": "Antoni — Male, natural (multilingual)",
        "description": "Natural male voice, works well in Spanish",
    },
    {
        "id": "MF3mGyEYCl7XYWbV9V6O",
        "label": "Elli — Female, warm (multilingual)",
        "description": "Warm female voice, engaging in Spanish",
    },
    {
        "id": "TxGEqnHWrfWFTfGW9XjX",
        "label": "Josh — Male, deep (multilingual)",
        "description": "Deep male voice, clear in Spanish",
    },
]


class AbstractTTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @abstractmethod
    def synthesize(self, text: str) -> bytes | None | TurnError:
        """
        Synthesize speech from text.

        Returns audio bytes on success, None if TTS is handled by the browser,
        or TurnError if the provider call fails.
        """
        raise NotImplementedError


class BrowserTTSProvider(AbstractTTSProvider):
    """Passthrough provider — TTS is handled client-side by browser speechSynthesis."""

    def synthesize(self, text: str) -> bytes | None | TurnError:
        return None


class ElevenLabsTTSProvider(AbstractTTSProvider):
    """ElevenLabs TTS provider — calls the ElevenLabs API and returns MP3 bytes."""

    _BASE_URL = "https://api.elevenlabs.io"
    _MODEL_ID = "eleven_multilingual_v2"

    def __init__(self, voice_id: str) -> None:
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY environment variable is not set")
        self._api_key = api_key
        self._voice_id = voice_id

    def synthesize(self, text: str) -> bytes | None | TurnError:
        url = f"{self._BASE_URL}/v1/text-to-speech/{self._voice_id}"
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": self._MODEL_ID,
            "output_format": "mp3_44100_128",
        }
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=15.0)
            response.raise_for_status()
            return response.content
        except Exception as exc:
            return TurnError(
                stage="tts",
                message=f"ElevenLabs API error: {exc}",
                recoverable=True,
            )
