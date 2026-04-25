import os
import pytest
from unittest.mock import MagicMock, patch
from backend.stt import WhisperSTT, OpenAIWhisperSTT, get_stt_provider, normalize_transcript
from backend.session import TurnError

FIXTURE_WAV = os.path.join(os.path.dirname(__file__), "..", "fixtures", "hola_sample.wav")


class TestNormalizeTranscript:
    def test_lowercases_text(self):
        assert normalize_transcript("Hola Cómo Estás") == "hola cómo estás"

    def test_removes_standard_punctuation(self):
        assert normalize_transcript("¡Buenos días!") == "buenos días"

    def test_removes_question_marks_and_inverted(self):
        assert normalize_transcript("¿Cómo estás?") == "cómo estás"

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_transcript("  hola  ") == "hola"

    def test_collapses_internal_whitespace(self):
        assert normalize_transcript("hola,  cómo  estás") == "hola  cómo  estás"

    def test_empty_string(self):
        assert normalize_transcript("") == ""


class TestWhisperSTT:
    def test_corrupted_bytes_returns_turn_error(self):
        stt = WhisperSTT()
        result = stt.transcribe(b"this is not a valid wav file", "bad.wav")
        assert isinstance(result, TurnError)
        assert result.stage == "stt"
        assert result.recoverable is True

    def test_fixture_returns_tuple_of_strings(self):
        stt = WhisperSTT()
        with open(FIXTURE_WAV, "rb") as f:
            audio_bytes = f.read()
        result = stt.transcribe(audio_bytes, "hola_sample.wav")
        assert isinstance(result, tuple), f"Expected tuple, got TurnError: {result}"
        raw, norm = result
        assert isinstance(raw, str)
        assert isinstance(norm, str)

    def test_fixture_norm_is_lowercase(self):
        stt = WhisperSTT()
        with open(FIXTURE_WAV, "rb") as f:
            audio_bytes = f.read()
        result = stt.transcribe(audio_bytes, "hola_sample.wav")
        assert isinstance(result, tuple)
        _, norm = result
        assert norm == norm.lower()

    def test_fixture_norm_contains_hola(self):
        stt = WhisperSTT()
        with open(FIXTURE_WAV, "rb") as f:
            audio_bytes = f.read()
        result = stt.transcribe(audio_bytes, "hola_sample.wav")
        assert isinstance(result, tuple)
        _, norm = result
        assert "hola" in norm

    def test_fixture_exact_transcript(self):
        # Whisper base model, hola_sample.wav (gTTS "hola, ¿cómo estás?" es, 16kHz mono)
        # Verified 2026-04-19
        stt = WhisperSTT()
        with open(FIXTURE_WAV, "rb") as f:
            audio_bytes = f.read()
        result = stt.transcribe(audio_bytes, "hola_sample.wav")
        assert isinstance(result, tuple)
        raw, norm = result
        assert raw == "Hola, como estás?"
        assert norm == "hola como estás"


class TestOpenAIWhisperSTT:
    def test_returns_raw_and_normalized_transcript(self):
        mock_result = MagicMock()
        mock_result.text = "  Hola, ¿cómo estás?  "
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_result

        with patch("openai.OpenAI", return_value=mock_client):
            stt = OpenAIWhisperSTT()
            result = stt.transcribe(b"fake-audio", "audio.webm")

        assert isinstance(result, tuple)
        raw, norm = result
        assert raw == "Hola, ¿cómo estás?"
        assert norm == "hola cómo estás"

    def test_api_error_returns_turn_error(self):
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = Exception("API timeout")

        with patch("openai.OpenAI", return_value=mock_client):
            stt = OpenAIWhisperSTT()
            result = stt.transcribe(b"fake-audio", "audio.webm")

        assert isinstance(result, TurnError)
        assert result.stage == "stt"
        assert result.recoverable is True

    def test_passes_filename_and_bytes_to_api(self):
        mock_result = MagicMock()
        mock_result.text = "hola"
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_result

        with patch("openai.OpenAI", return_value=mock_client):
            stt = OpenAIWhisperSTT()
            stt.transcribe(b"fake-audio", "audio.webm")

        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["file"] == ("audio.webm", b"fake-audio")
        assert call_kwargs["language"] == "es"

    def test_uses_whisper_1_model(self):
        mock_result = MagicMock()
        mock_result.text = "hola"
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_result

        with patch("openai.OpenAI", return_value=mock_client):
            stt = OpenAIWhisperSTT()
            stt.transcribe(b"fake-audio", "audio.wav")

        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["model"] == "whisper-1"


class TestGetSttProvider:
    def test_defaults_to_whisper_stt(self, monkeypatch):
        monkeypatch.delenv("STT_PROVIDER", raising=False)
        assert isinstance(get_stt_provider(), WhisperSTT)

    def test_local_returns_whisper_stt(self, monkeypatch):
        monkeypatch.setenv("STT_PROVIDER", "local")
        assert isinstance(get_stt_provider(), WhisperSTT)

    def test_openai_returns_openai_whisper_stt(self, monkeypatch):
        monkeypatch.setenv("STT_PROVIDER", "openai")
        assert isinstance(get_stt_provider(), OpenAIWhisperSTT)
