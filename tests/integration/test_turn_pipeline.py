import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
FIXTURE_WAV = os.path.join(os.path.dirname(__file__), "..", "fixtures", "hola_sample.wav")


def test_turn_with_valid_wav_returns_transcript():
    with open(FIXTURE_WAV, "rb") as f:
        response = client.post("/turn", files={"audio": ("hola_sample.wav", f, "audio/wav")})
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["transcript_raw"] == "Hola, como estás?"
    assert body["transcript_norm"] == "hola como estás"


def test_turn_response_includes_echo():
    with open(FIXTURE_WAV, "rb") as f:
        response = client.post("/turn", files={"audio": ("hola_sample.wav", f, "audio/wav")})
    assert response.status_code == 200
    body = response.json()
    assert "echo" in body
    assert body["echo"] == body["transcript_norm"]


def test_turn_with_corrupted_wav_returns_structured_error(tmp_path):
    bad_wav = tmp_path / "bad.wav"
    bad_wav.write_bytes(b"not a valid wav")
    with open(bad_wav, "rb") as f:
        response = client.post("/turn", files={"audio": ("bad.wav", f, "audio/wav")})
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is not None
    assert body["error"]["stage"] == "stt"
    assert body["error"]["recoverable"] is True
    assert body["transcript_raw"] is None
    assert body["transcript_norm"] is None
