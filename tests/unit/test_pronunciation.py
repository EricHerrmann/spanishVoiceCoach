import os
from unittest.mock import patch
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

from fastapi.testclient import TestClient
from backend.main import app

FIXTURE_WAV = os.path.join(os.path.dirname(__file__), "..", "fixtures", "hola_sample.wav")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
requires_api_key = pytest.mark.skipif(
    not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "test-key",
    reason="ANTHROPIC_API_KEY not set or is a test key",
)

client = TestClient(app)


class TestGetPronunciationChallenges:
    def test_returns_list(self):
        response = client.get("/pronunciation/challenges")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_challenges_have_required_fields(self):
        response = client.get("/pronunciation/challenges")
        for challenge in response.json():
            assert "id" in challenge
            assert "target" in challenge
            assert "sound_focus" in challenge
            assert "hint" in challenge

    def test_returns_all_challenges(self):
        response = client.get("/pronunciation/challenges")
        assert len(response.json()) >= 10


class TestPronunciationEvaluate:
    def test_bad_audio_returns_structured_error(self):
        response = client.post(
            "/pronunciation/evaluate",
            data={"target": "hola"},
            files={"audio": ("bad.wav", b"not-a-wav", "audio/wav")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert data["score"] is None
        assert data["transcript"] is None

    def test_response_shape_with_mocked_evaluate(self):
        mock_eval = {"score": 85, "feedback": "Good effort!", "issues": []}
        with patch("backend.main.claude_provider") as mock_provider:
            mock_provider.evaluate_pronunciation.return_value = mock_eval
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/pronunciation/evaluate",
                    data={"target": "hola"},
                    files={"audio": ("test.wav", f, "audio/wav")},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 85
        assert data["feedback"] == "Good effort!"
        assert data["issues"] == []
        assert data["error"] is None
        assert data["transcript"] is not None

    def test_response_shape_with_issues(self):
        mock_eval = {
            "score": 60,
            "feedback": "Work on the rr sound.",
            "issues": [{"sound": "rr", "said": "r", "expected": "rr"}],
        }
        with patch("backend.main.claude_provider") as mock_provider:
            mock_provider.evaluate_pronunciation.return_value = mock_eval
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/pronunciation/evaluate",
                    data={"target": "perro"},
                    files={"audio": ("test.wav", f, "audio/wav")},
                )
        assert response.status_code == 200
        data = response.json()
        assert len(data["issues"]) == 1
        assert data["issues"][0]["sound"] == "rr"

    def test_evaluate_error_returns_structured_error(self):
        from backend.session import TurnError
        with patch("backend.main.claude_provider") as mock_provider:
            mock_provider.evaluate_pronunciation.return_value = TurnError(
                stage="ai", message="API down", recoverable=True
            )
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/pronunciation/evaluate",
                    data={"target": "hola"},
                    files={"audio": ("test.wav", f, "audio/wav")},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert data["score"] is None

    @requires_api_key
    def test_live_evaluate_returns_score(self):
        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/pronunciation/evaluate",
                data={"target": "hola"},
                files={"audio": ("test.wav", f, "audio/wav")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 100
        assert data["feedback"] is not None
        assert isinstance(data["issues"], list)
