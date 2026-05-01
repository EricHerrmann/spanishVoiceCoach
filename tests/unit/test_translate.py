import os
from unittest.mock import patch
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

from fastapi.testclient import TestClient
from backend.main import app
from backend.session import TurnError

FIXTURE_WAV = os.path.join(os.path.dirname(__file__), "..", "fixtures", "hola_sample.wav")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
requires_api_key = pytest.mark.skipif(
    not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "test-key",
    reason="ANTHROPIC_API_KEY not set or is a test key",
)

client = TestClient(app)


class TestTranslateEndpoint:
    def test_bad_audio_returns_structured_error(self):
        response = client.post(
            "/translate",
            files={"audio": ("bad.wav", b"not-a-wav-file", "audio/wav")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert data["english"] is None
        assert data["spanish"] is None
        assert data["audio_b64"] is None

    def test_response_shape_with_mocked_translate(self):
        with patch("backend.main.get_ai_provider") as mock_get_provider:
            mock_provider = mock_get_provider.return_value
            mock_provider.translate.return_value = "hola"
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/translate",
                    files={"audio": ("test.wav", f, "audio/wav")},
                )
        assert response.status_code == 200
        data = response.json()
        assert "english" in data
        assert "spanish" in data
        assert "audio_b64" in data
        assert "tts_error" in data
        assert "error" in data
        assert data["error"] is None
        assert data["spanish"] == "hola"

    def test_translate_error_returns_structured_error(self):
        with patch("backend.main.get_ai_provider") as mock_get_provider:
            mock_provider = mock_get_provider.return_value
            mock_provider.translate.return_value = TurnError(
                stage="ai", message="API down", recoverable=True
            )
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/translate",
                    files={"audio": ("test.wav", f, "audio/wav")},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert data["spanish"] is None

    @requires_api_key
    def test_live_translate_returns_spanish(self):
        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/translate",
                files={"audio": ("test.wav", f, "audio/wav")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert data["english"] is not None
        assert data["spanish"] is not None
