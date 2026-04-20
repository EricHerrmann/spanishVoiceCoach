import os
import pytest
from backend.stt import WhisperSTT, normalize_transcript
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
    def test_nonexistent_file_returns_turn_error(self):
        stt = WhisperSTT()
        result = stt.transcribe("/nonexistent/path/audio.wav")
        assert isinstance(result, TurnError)
        assert result.stage == "stt"
        assert result.recoverable is True

    def test_corrupted_wav_returns_turn_error(self, tmp_path):
        bad_wav = tmp_path / "bad.wav"
        bad_wav.write_bytes(b"this is not a valid wav file")
        stt = WhisperSTT()
        result = stt.transcribe(str(bad_wav))
        assert isinstance(result, TurnError)
        assert result.stage == "stt"
        assert result.recoverable is True

    def test_fixture_returns_tuple_of_strings(self):
        stt = WhisperSTT()
        result = stt.transcribe(FIXTURE_WAV)
        assert isinstance(result, tuple), f"Expected tuple, got TurnError: {result}"
        raw, norm = result
        assert isinstance(raw, str)
        assert isinstance(norm, str)

    def test_fixture_norm_is_lowercase(self):
        stt = WhisperSTT()
        result = stt.transcribe(FIXTURE_WAV)
        assert isinstance(result, tuple)
        _, norm = result
        assert norm == norm.lower()

    def test_fixture_norm_contains_hola(self):
        stt = WhisperSTT()
        result = stt.transcribe(FIXTURE_WAV)
        assert isinstance(result, tuple)
        _, norm = result
        assert "hola" in norm

    def test_fixture_exact_transcript(self):
        # Whisper base model, hola_sample.wav (gTTS "hola, ¿cómo estás?" es, 16kHz mono)
        # Verified 2026-04-19
        stt = WhisperSTT()
        result = stt.transcribe(FIXTURE_WAV)
        assert isinstance(result, tuple)
        raw, norm = result
        assert raw == "Hola, como estás?"
        assert norm == "hola como estás"
