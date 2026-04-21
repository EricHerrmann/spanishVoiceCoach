"""Unit tests for TTS providers."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from backend.tts import AbstractTTSProvider, BrowserTTSProvider, ElevenLabsTTSProvider
from backend.session import TurnError


def test_abstract_tts_raises_not_implemented():
    class ConcreteNoOp(AbstractTTSProvider):
        def synthesize(self, text: str):
            return super().synthesize(text)

    provider = ConcreteNoOp()
    with pytest.raises(NotImplementedError):
        provider.synthesize("hola")


def test_browser_tts_returns_none():
    provider = BrowserTTSProvider()
    result = provider.synthesize("hola, ¿cómo estás?")
    assert result is None


class TestElevenLabsTTSProvider:
    def test_missing_api_key_raises_runtime_error(self):
        clean_env = {k: v for k, v in os.environ.items() if k != "ELEVENLABS_API_KEY"}
        with patch.dict("os.environ", clean_env, clear=True):
            with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
                ElevenLabsTTSProvider("some-voice-id")

    def test_successful_call_returns_bytes(self):
        mock_response = MagicMock()
        mock_response.content = b"fake-mp3-bytes"
        mock_response.raise_for_status = MagicMock()
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
            with patch("backend.tts.httpx.post", return_value=mock_response) as mock_post:
                provider = ElevenLabsTTSProvider("voice-id-abc")
                result = provider.synthesize("Hola, ¿cómo estás?")

        assert result == b"fake-mp3-bytes"
        call_args = mock_post.call_args
        assert "voice-id-abc" in call_args[0][0]
        assert call_args[1]["json"]["text"] == "Hola, ¿cómo estás?"
        assert call_args[1]["json"]["model_id"] == "eleven_multilingual_v2"

    def test_network_error_returns_turn_error(self):
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
            with patch("backend.tts.httpx.post", side_effect=Exception("connection refused")):
                provider = ElevenLabsTTSProvider("voice-id-abc")
                result = provider.synthesize("hola")

        assert isinstance(result, TurnError)
        assert result.stage == "tts"
        assert result.recoverable is True

    def test_http_error_response_returns_turn_error(self):
        import httpx as httpx_lib

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx_lib.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=MagicMock()
        )
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "bad-key"}):
            with patch("backend.tts.httpx.post", return_value=mock_response):
                provider = ElevenLabsTTSProvider("voice-id-abc")
                result = provider.synthesize("hola")

        assert isinstance(result, TurnError)
        assert result.stage == "tts"
        assert result.recoverable is True
