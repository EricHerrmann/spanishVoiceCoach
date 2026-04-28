"""Unit tests for backend.tts_helpers.synthesize_tts."""
import base64
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from backend.session import TurnError
from backend.tts_helpers import synthesize_tts

_FIXTURE_BYTES = b"fake-mp3-audio-bytes"
_FIXTURE_B64 = base64.b64encode(_FIXTURE_BYTES).decode("ascii")
_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


class TestSynthesizeTtsBrowserProvider:
    def test_browser_provider_returns_none_none(self):
        result = synthesize_tts("Hola mundo", "browser", _VOICE_ID)
        assert result == (None, None)

    def test_none_provider_returns_none_none(self):
        result = synthesize_tts("Hola", None, _VOICE_ID)
        assert result == (None, None)


class TestSynthesizeTtsMissingVoiceId:
    def test_elevenlabs_without_voice_id_returns_none_none(self):
        result = synthesize_tts("Hola", "elevenlabs", None)
        assert result == (None, None)

    def test_elevenlabs_with_empty_voice_id_returns_none_none(self):
        result = synthesize_tts("Hola", "elevenlabs", "")
        assert result == (None, None)


class TestSynthesizeTtsElevenLabsSuccess:
    def test_successful_synthesis_returns_b64_and_no_error(self):
        mock_instance = MagicMock()
        mock_instance.synthesize.return_value = _FIXTURE_BYTES

        with patch("backend.tts_helpers.ElevenLabsTTSProvider", return_value=mock_instance):
            audio_b64, error = synthesize_tts("Hola", "elevenlabs", _VOICE_ID)

        assert error is None
        assert audio_b64 == _FIXTURE_B64
        assert base64.b64decode(audio_b64) == _FIXTURE_BYTES


class TestSynthesizeTtsTurnError:
    def test_turn_error_from_synthesize_returns_error_dict(self):
        turn_error = TurnError(stage="tts", message="API quota exceeded", recoverable=True)
        mock_instance = MagicMock()
        mock_instance.synthesize.return_value = turn_error

        with patch("backend.tts_helpers.ElevenLabsTTSProvider", return_value=mock_instance):
            audio_b64, error = synthesize_tts("Hola", "elevenlabs", _VOICE_ID)

        assert audio_b64 is None
        assert error == {
            "stage": "tts",
            "message": "API quota exceeded",
            "recoverable": True,
        }


class TestSynthesizeTtsRuntimeError:
    def test_runtime_error_during_init_returns_non_recoverable_error(self):
        with patch(
            "backend.tts_helpers.ElevenLabsTTSProvider",
            side_effect=RuntimeError("ELEVENLABS_API_KEY environment variable is not set"),
        ):
            audio_b64, error = synthesize_tts("Hola", "elevenlabs", _VOICE_ID)

        assert audio_b64 is None
        assert error is not None
        assert error["stage"] == "tts"
        assert "ELEVENLABS_API_KEY" in error["message"]
        assert error["recoverable"] is False
