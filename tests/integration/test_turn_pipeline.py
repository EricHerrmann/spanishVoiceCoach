import os
import pytest
from fastapi.testclient import TestClient
from backend.session import CoachResponse

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Skip API tests if the key is not set or is a test/dummy value
requires_api_key = pytest.mark.skipif(
    not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "test-key",
    reason="ANTHROPIC_API_KEY not set or is a test key",
)


def make_client():
    """Return a TestClient for the app. The app module is cached, so sessions dict is shared."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")
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

    def test_accepts_coaching_mode_in_body(self):
        client = make_client()
        response = client.post(
            "/session/start",
            json={"coaching_mode": "explicit"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "session_id" in body
        assert isinstance(body["session_id"], str)

    def test_accepts_full_config_body(self):
        client = make_client()
        response = client.post(
            "/session/start",
            json={
                "topic": "ordering_food",
                "level": 3,
                "ai_provider": "claude",
                "coaching_mode": "explicit",
            },
        )
        assert response.status_code == 200
        assert "session_id" in response.json()

    def test_level_zero_returns_422(self):
        client = make_client()
        response = client.post("/session/start", json={"level": 0})
        assert response.status_code == 422

    def test_level_eleven_returns_422(self):
        client = make_client()
        response = client.post("/session/start", json={"level": 11})
        assert response.status_code == 422

    def test_invalid_ai_provider_returns_422(self):
        client = make_client()
        response = client.post("/session/start", json={"ai_provider": "openai"})
        assert response.status_code == 422


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
        # Expected output from Whisper `base` model on tests/fixtures/hola_sample.wav
        # (generated via gTTS "Hola, como estás?"). Pinned to this exact string;
        # update here if the fixture WAV or Whisper model version changes.
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


class TestGetTopics:
    def test_returns_list(self):
        client = make_client()
        response = client.get("/topics")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) > 0

    def test_each_topic_has_required_fields(self):
        client = make_client()
        body = client.get("/topics").json()
        for topic in body:
            assert "id" in topic
            assert "label" in topic
            assert "starter" in topic

    def test_general_topic_present(self):
        client = make_client()
        body = client.get("/topics").json()
        ids = [t["id"] for t in body]
        assert "general" in ids


class TestGetProviders:
    def test_returns_list(self):
        client = make_client()
        response = client.get("/providers")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) > 0

    def test_claude_present(self):
        client = make_client()
        body = client.get("/providers").json()
        ids = [p["id"] for p in body]
        assert "claude" in ids

    def test_openai_not_present(self):
        client = make_client()
        body = client.get("/providers").json()
        ids = [p["id"] for p in body]
        assert "openai" not in ids

    def test_each_provider_has_id_and_label(self):
        client = make_client()
        body = client.get("/providers").json()
        for provider in body:
            assert "id" in provider
            assert "label" in provider


class TestSessionPersistence:
    def test_session_start_persists_session_and_lists_summary(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from backend import main

        main.sessions.clear()
        client = TestClient(main.app)

        response = client.post(
            "/session/start",
            json={
                "topic": "travel_tourism",
                "level": 7,
                "ai_provider": "claude",
                "coaching_mode": "shadowing",
            },
        )

        assert response.status_code == 200
        session_id = response.json()["session_id"]
        assert (tmp_path / "sessions" / f"{session_id}.json").exists()

        list_response = client.get("/sessions")
        assert list_response.status_code == 200
        summaries = list_response.json()
        assert summaries[0]["id"] == session_id
        assert summaries[0]["topic"] == "travel_tourism"
        assert summaries[0]["level"] == 7
        assert summaries[0]["turn_count"] == 0

    def test_get_session_loads_persisted_session_after_memory_clear(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from backend import main

        main.sessions.clear()
        client = TestClient(main.app)
        session_id = client.post("/session/start", json={"topic": "general"}).json()["session_id"]
        main.sessions.clear()

        response = client.get(f"/sessions/{session_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == session_id
        assert body["topic"] == "general"
        assert body["turns"] == []

    def test_full_turn_updates_persisted_session(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from backend import main

        class FakeSTT:
            def transcribe(self, _path):
                return ("Hola", "hola")

        class FakeAIProvider:
            def chat(self, _session, _user_text):
                return CoachResponse(coach_text="¡Hola!", corrections=[])

        main.sessions.clear()
        monkeypatch.setattr(main, "stt_provider", FakeSTT())
        monkeypatch.setattr(main, "claude_provider", FakeAIProvider())
        client = TestClient(main.app)
        session_id = client.post("/session/start").json()["session_id"]

        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/turn",
                files={"audio": ("hola_sample.wav", f, "audio/wav")},
                data={"session_id": session_id},
            )

        assert response.status_code == 200
        assert response.json()["error"] is None
        main.sessions.clear()
        persisted = client.get(f"/sessions/{session_id}").json()
        assert len(persisted["turns"]) == 2
        assert persisted["turns"][0]["speaker"] == "user"
        assert persisted["turns"][0]["transcript_raw"] == "Hola"
        assert persisted["turns"][0]["transcript_norm"] == "hola"
        assert persisted["turns"][0]["audio_file"] is None
        assert persisted["turns"][1]["speaker"] == "coach"
        assert persisted["turns"][1]["coach_text"] == "¡Hola!"

    def test_audio_file_saved_only_when_opted_in(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("DVC_SAVE_AUDIO", "true")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from backend import main

        class FakeSTT:
            def transcribe(self, _path):
                return ("Hola", "hola")

        class FakeAIProvider:
            def chat(self, _session, _user_text):
                return CoachResponse(coach_text="¡Hola!", corrections=[])

        main.sessions.clear()
        monkeypatch.setattr(main, "stt_provider", FakeSTT())
        monkeypatch.setattr(main, "claude_provider", FakeAIProvider())
        client = TestClient(main.app)
        session_id = client.post("/session/start").json()["session_id"]

        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/turn",
                files={"audio": ("hola_sample.wav", f, "audio/wav")},
                data={"session_id": session_id},
            )

        assert response.status_code == 200
        persisted = client.get(f"/sessions/{session_id}").json()
        audio_file = persisted["turns"][0]["audio_file"]
        assert audio_file is not None
        assert os.path.exists(audio_file)
