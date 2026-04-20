import os
import pytest
from fastapi.testclient import TestClient

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Skip API tests if the key is not set or is a test/dummy value
requires_api_key = pytest.mark.skipif(
    not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "test-key",
    reason="ANTHROPIC_API_KEY not set or is a test key",
)


def make_client():
    """Create a fresh TestClient with a fresh app instance to avoid session state leakage."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    from backend.main import app
    return TestClient(app)


FIXTURE_WAV = os.path.join(os.path.dirname(__file__), "..", "fixtures", "hola_sample.wav")


class TestSessionStart:
    def test_returns_session_id(self):
        client = make_client()
        response = client.post("/session/start")
        assert response.status_code == 200
        body = response.json()
        assert "session_id" in body
        assert isinstance(body["session_id"], str)
        assert len(body["session_id"]) > 0

    def test_each_call_returns_unique_session_id(self):
        client = make_client()
        r1 = client.post("/session/start").json()
        r2 = client.post("/session/start").json()
        assert r1["session_id"] != r2["session_id"]


class TestTurnRoute:
    def test_unknown_session_id_returns_404(self):
        client = make_client()
        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/turn",
                files={"audio": ("hola_sample.wav", f, "audio/wav")},
                data={"session_id": "nonexistent-id"},
            )
        assert response.status_code == 404

    def test_corrupted_wav_returns_structured_stt_error(self, tmp_path):
        client = make_client()
        session_id = client.post("/session/start").json()["session_id"]
        bad_wav = tmp_path / "bad.wav"
        bad_wav.write_bytes(b"not a valid wav")
        with open(bad_wav, "rb") as f:
            response = client.post(
                "/turn",
                files={"audio": ("bad.wav", f, "audio/wav")},
                data={"session_id": session_id},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["error"] is not None
        assert body["error"]["stage"] == "stt"
        assert body["error"]["recoverable"] is True
        assert body["transcript_raw"] is None
        assert body["transcript_norm"] is None

    @requires_api_key
    def test_valid_wav_returns_coach_text(self):
        client = make_client()
        session_id = client.post("/session/start").json()["session_id"]
        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/turn",
                files={"audio": ("hola_sample.wav", f, "audio/wav")},
                data={"session_id": session_id},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["error"] is None
        assert body["transcript_raw"] == "Hola, como estás?"
        assert body["transcript_norm"] == "hola como estás"
        assert isinstance(body["coach_text"], str)
        assert len(body["coach_text"]) > 0
        assert isinstance(body["corrections"], list)

    @requires_api_key
    def test_conversation_history_maintained_across_turns(self):
        client = make_client()
        session_id = client.post("/session/start").json()["session_id"]
        for _ in range(2):
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/turn",
                    files={"audio": ("hola_sample.wav", f, "audio/wav")},
                    data={"session_id": session_id},
                )
            body = response.json()
            assert body["error"] is None
            assert isinstance(body["coach_text"], str)
