# Phase 6 — ElevenLabs TTS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Swap browser `speechSynthesis` for ElevenLabs TTS, with per-session TTS provider and voice selection following the existing `ai_provider` pattern.

**Architecture:** Backend calls ElevenLabs API and returns base64-encoded MP3 bytes in the `/turn` JSON response field `audio_b64`. Frontend decodes and plays via `AudioContext`; falls back to `speechSynthesis` when `audio_b64` is absent. TTS provider (`browser` / `elevenlabs`) and `voice_id` are stored on the `Session` model and selected in `SessionConfig`.

**Tech Stack:** `httpx` (sync HTTP call to ElevenLabs), `base64` (stdlib), `AudioContext` + `AudioBufferSourceNode` (browser API), ElevenLabs model `eleven_multilingual_v2`.

---

## File Map

| Action | File | What changes |
|--------|------|--------------|
| Modify | `pyproject.toml` | Move `httpx` from `dev` to main deps |
| Modify | `backend/tts.py` | Update return type; add `ELEVENLABS_VOICES` and `ElevenLabsTTSProvider` |
| Modify | `backend/session.py` | Add `tts_provider` and `tts_voice_id` fields; update `new_session()` |
| Modify | `backend/main.py` | Add `/tts-voices` route; update `SessionStartRequest`; wire TTS in `/turn` |
| Create | `tests/unit/test_tts.py` | All TTS provider unit tests |
| Modify | `tests/integration/test_turn_pipeline.py` | `/tts-voices` route tests; `session/start` TTS field tests |
| Modify | `frontend/src/hooks/useVoice.js` | Pass TTS config in `newSession()`; `AudioContext` playback in `submitAudio()` |
| Modify | `frontend/src/components/SessionConfig.jsx` | Add TTS provider select + conditional voice dropdown |
| Modify | `frontend/src/App.jsx` | Fetch `/tts-voices`; add TTS fields to config state; pass `ttsVoices` prop |
| Modify | `frontend/src/__tests__/SessionConfig.test.jsx` | Add TTS dropdown tests |
| Modify | `docs/manualTestPlan.md` | Phase 6 procedures |
| Modify | `.env.example` | Uncomment `ELEVENLABS_API_KEY` with usage notes |
| Modify | `claudeSpanishCoachPlan.md` | Tick off Phase 6 tasks as completed |

---

## Task 1: Move `httpx` to main dependencies

`httpx` is currently in `[dependency-groups] dev`. The production `/turn` route will call ElevenLabs via `httpx`, so it must be in main deps.

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update `pyproject.toml`**

In `pyproject.toml`, add `httpx>=0.28` to `[project] dependencies` and remove it from `[dependency-groups] dev`:

```toml
[project]
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "openai-whisper>=20240930",
    "anthropic>=0.49",
    "python-multipart>=0.0.20",
    "httpx>=0.28",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.26",
    "gtts>=2.5.4",
]
```

- [ ] **Step 2: Sync dependencies**

```bash
uv sync
```

Expected: lock file updated, no errors.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: move httpx to main deps for ElevenLabs TTS"
```

---

## Task 2: Implement `ElevenLabsTTSProvider` (TDD)

**Files:**
- Create: `tests/unit/test_tts.py`
- Modify: `backend/tts.py`

- [ ] **Step 1: Write all failing TTS unit tests**

Create `tests/unit/test_tts.py`:

```python
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
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
uv run pytest tests/unit/test_tts.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `ElevenLabsTTSProvider` does not exist yet.

- [ ] **Step 3: Implement `backend/tts.py`**

Replace the entire file with:

```python
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
    def synthesize(self, text: str) -> bytes | None:
        """
        Synthesize speech from text.

        Returns audio bytes on success, None if TTS is handled by the browser,
        or TurnError if the provider call fails.
        """
        raise NotImplementedError


class BrowserTTSProvider(AbstractTTSProvider):
    """Passthrough provider — TTS is handled client-side by browser speechSynthesis."""

    def synthesize(self, text: str) -> bytes | None:
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

    def synthesize(self, text: str) -> bytes | None:
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
```

- [ ] **Step 4: Run tests — verify they all pass**

```bash
uv run pytest tests/unit/test_tts.py -v
```

Expected: 6 tests, all PASS.

- [ ] **Step 5: Run full backend suite — verify no regressions**

```bash
uv run pytest -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/tts.py tests/unit/test_tts.py
git commit -m "feat: add ElevenLabsTTSProvider with curated voice list"
```

---

## Task 3: Update `Session` model for TTS config

**Files:**
- Modify: `backend/session.py`
- Modify: `tests/unit/test_session.py`

- [ ] **Step 1: Write failing tests for the new session fields**

Add to the end of `tests/unit/test_session.py`:

```python
def test_new_session_defaults_to_browser_tts():
    session = new_session(topic="food", level=5, ai_provider="claude", coaching_mode="on_demand")
    assert session.tts_provider == "browser"
    assert session.tts_voice_id is None


def test_new_session_accepts_elevenlabs_tts():
    session = new_session(
        topic="food",
        level=5,
        ai_provider="claude",
        coaching_mode="on_demand",
        tts_provider="elevenlabs",
        tts_voice_id="21m00Tcm4TlvDq8ikWAM",
    )
    assert session.tts_provider == "elevenlabs"
    assert session.tts_voice_id == "21m00Tcm4TlvDq8ikWAM"


def test_session_roundtrip_preserves_tts_config(tmp_path):
    session = new_session(
        topic="food",
        level=5,
        ai_provider="claude",
        coaching_mode="on_demand",
        tts_provider="elevenlabs",
        tts_voice_id="21m00Tcm4TlvDq8ikWAM",
    )
    restored = Session.from_dict(session.to_dict())
    assert restored.tts_provider == "elevenlabs"
    assert restored.tts_voice_id == "21m00Tcm4TlvDq8ikWAM"


def test_session_from_dict_defaults_tts_provider_for_old_sessions():
    """Sessions persisted before Phase 6 (no tts_provider key) load with browser defaults."""
    session = new_session(topic="food", level=5, ai_provider="claude", coaching_mode="on_demand")
    data = session.to_dict()
    del data["tts_provider"]
    del data["tts_voice_id"]
    restored = Session.from_dict(data)
    assert restored.tts_provider == "browser"
    assert restored.tts_voice_id is None
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/unit/test_session.py::test_new_session_defaults_to_browser_tts -v
```

Expected: FAIL — `new_session()` does not accept `tts_provider` keyword argument.

- [ ] **Step 3: Update `Session` dataclass and `new_session()` in `backend/session.py`**

In the `Session` dataclass, add two new fields after `coaching_mode` and before `turns`:

```python
@dataclass
class Session:
    id: str
    started_at: datetime
    topic: str
    level: int
    ai_provider: str
    coaching_mode: str
    tts_provider: str = "browser"        # "browser" | "elevenlabs"
    tts_voice_id: Optional[str] = None   # voice ID when tts_provider == "elevenlabs"
    turns: list[Turn] = field(default_factory=list)
```

Update `new_session()` to accept the two new parameters with defaults:

```python
def new_session(
    topic: str,
    level: int,
    ai_provider: str,
    coaching_mode: str,
    tts_provider: str = "browser",
    tts_voice_id: Optional[str] = None,
) -> Session:
    """Factory function to create a new Session with a fresh UUID and current timestamp."""
    return Session(
        id=str(uuid4()),
        started_at=datetime.now(timezone.utc),
        topic=topic,
        level=level,
        ai_provider=ai_provider,
        coaching_mode=coaching_mode,
        tts_provider=tts_provider,
        tts_voice_id=tts_voice_id,
    )
```

The `from_dict` method calls `cls(**data_copy)`. Old sessions in JSON will not have `tts_provider` or `tts_voice_id` keys, so the dataclass defaults will apply automatically — no changes needed to `from_dict`.

- [ ] **Step 4: Run the new session tests — verify they pass**

```bash
uv run pytest tests/unit/test_session.py -v
```

Expected: all session tests pass including the 4 new ones.

- [ ] **Step 5: Run full backend suite — verify no regressions**

```bash
uv run pytest -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/session.py tests/unit/test_session.py
git commit -m "feat: add tts_provider and tts_voice_id to Session model"
```

---

## Task 4: Add `/tts-voices` route and update `SessionStartRequest`

**Files:**
- Modify: `backend/main.py`
- Modify: `tests/integration/test_turn_pipeline.py`

- [ ] **Step 1: Write failing integration tests**

Add a new class to `tests/integration/test_turn_pipeline.py`:

```python
class TestGetTtsVoices:
    def test_returns_list(self):
        client = make_client()
        response = client.get("/tts-voices")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) > 0

    def test_each_voice_has_id_and_label(self):
        client = make_client()
        body = client.get("/tts-voices").json()
        for voice in body:
            assert "id" in voice
            assert "label" in voice

    def test_session_start_accepts_tts_provider(self):
        client = make_client()
        response = client.post(
            "/session/start",
            json={"tts_provider": "browser"},
        )
        assert response.status_code == 200
        assert "session_id" in response.json()

    def test_session_start_accepts_elevenlabs_tts_with_voice_id(self):
        client = make_client()
        response = client.post(
            "/session/start",
            json={"tts_provider": "elevenlabs", "tts_voice_id": "21m00Tcm4TlvDq8ikWAM"},
        )
        assert response.status_code == 200
        assert "session_id" in response.json()

    def test_session_start_invalid_tts_provider_returns_422(self):
        client = make_client()
        response = client.post(
            "/session/start",
            json={"tts_provider": "google"},
        )
        assert response.status_code == 422
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestGetTtsVoices -v
```

Expected: FAIL — `/tts-voices` route does not exist.

- [ ] **Step 3: Update `backend/main.py`**

Add `ELEVENLABS_VOICES` to the import from `backend.tts`:

```python
from backend.tts import ELEVENLABS_VOICES, ElevenLabsTTSProvider
```

Add the `/tts-voices` route after the existing `/providers` route:

```python
@app.get("/tts-voices")
def get_tts_voices():
    return ELEVENLABS_VOICES
```

Update `SessionStartRequest` to add the two new fields:

```python
class SessionStartRequest(BaseModel):
    topic: str = "general"
    level: int = Field(default=5, ge=1, le=10)
    ai_provider: Literal["claude"] = "claude"
    coaching_mode: Literal["on_demand", "explicit", "shadowing"] = "on_demand"
    tts_provider: Literal["browser", "elevenlabs"] = "browser"
    tts_voice_id: str | None = None
```

Update the `session_start` handler to pass the new fields through to `new_session()`:

```python
@app.post("/session/start")
def session_start(body: SessionStartRequest | None = Body(default=None)):
    req = body or SessionStartRequest()
    session = new_session(
        topic=req.topic,
        level=req.level,
        ai_provider=req.ai_provider,
        coaching_mode=req.coaching_mode,
        tts_provider=req.tts_provider,
        tts_voice_id=req.tts_voice_id,
    )
    sessions[session.id] = session
    save_session(session)
    return {"session_id": session.id}
```

- [ ] **Step 4: Run the new route tests — verify they pass**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestGetTtsVoices -v
```

Expected: 5 tests, all PASS.

- [ ] **Step 5: Run full backend suite — verify no regressions**

```bash
uv run pytest -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/integration/test_turn_pipeline.py
git commit -m "feat: add /tts-voices route and tts fields to SessionStartRequest"
```

---

## Task 5: Wire TTS into the `/turn` route

**Files:**
- Modify: `backend/main.py`
- Modify: `tests/integration/test_turn_pipeline.py`

- [ ] **Step 1: Write failing integration test for TTS in `/turn`**

Add to `tests/integration/test_turn_pipeline.py` inside `TestSessionPersistence` (or as a new class):

```python
class TestTurnTtsIntegration:
    def test_turn_with_browser_tts_has_no_audio_b64(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from backend import main
        from backend.session import CoachResponse

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
        session_id = client.post("/session/start", json={"tts_provider": "browser"}).json()["session_id"]

        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/turn",
                files={"audio": ("hola_sample.wav", f, "audio/wav")},
                data={"session_id": session_id},
            )

        body = response.json()
        assert body["error"] is None
        assert body["audio_b64"] is None
        assert body["tts_error"] is None

    def test_turn_with_elevenlabs_tts_returns_audio_b64(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")
        from backend import main
        from backend.session import CoachResponse
        from unittest.mock import MagicMock, patch

        class FakeSTT:
            def transcribe(self, _path):
                return ("Hola", "hola")

        class FakeAIProvider:
            def chat(self, _session, _user_text):
                return CoachResponse(coach_text="¡Hola!", corrections=[])

        fake_tts_response = MagicMock()
        fake_tts_response.content = b"fake-mp3-bytes"
        fake_tts_response.raise_for_status = MagicMock()

        main.sessions.clear()
        monkeypatch.setattr(main, "stt_provider", FakeSTT())
        monkeypatch.setattr(main, "claude_provider", FakeAIProvider())
        client = TestClient(main.app)
        session_id = client.post(
            "/session/start",
            json={"tts_provider": "elevenlabs", "tts_voice_id": "21m00Tcm4TlvDq8ikWAM"},
        ).json()["session_id"]

        with patch("backend.tts.httpx.post", return_value=fake_tts_response):
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/turn",
                    files={"audio": ("hola_sample.wav", f, "audio/wav")},
                    data={"session_id": session_id},
                )

        body = response.json()
        assert body["error"] is None
        assert body["tts_error"] is None
        import base64
        assert base64.b64decode(body["audio_b64"]) == b"fake-mp3-bytes"

    def test_turn_with_elevenlabs_tts_api_failure_returns_tts_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")
        from backend import main
        from backend.session import CoachResponse
        from unittest.mock import patch

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
        session_id = client.post(
            "/session/start",
            json={"tts_provider": "elevenlabs", "tts_voice_id": "21m00Tcm4TlvDq8ikWAM"},
        ).json()["session_id"]

        with patch("backend.tts.httpx.post", side_effect=Exception("connection refused")):
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/turn",
                    files={"audio": ("hola_sample.wav", f, "audio/wav")},
                    data={"session_id": session_id},
                )

        body = response.json()
        assert body["error"] is None           # main pipeline succeeded
        assert body["coach_text"] == "¡Hola!"  # coach text still returned
        assert body["audio_b64"] is None       # no audio
        assert body["tts_error"] is not None
        assert body["tts_error"]["stage"] == "tts"
        assert body["tts_error"]["recoverable"] is True
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestTurnTtsIntegration -v
```

Expected: FAIL — `audio_b64` key missing from response.

- [ ] **Step 3: Update the `/turn` route in `backend/main.py`**

Add `import base64` at the top of `main.py` (alongside existing stdlib imports).

Replace the final success `return` block in `post_turn` with:

```python
    # --- TTS ---
    audio_b64 = None
    tts_error = None
    if session.tts_provider == "elevenlabs" and session.tts_voice_id:
        try:
            tts = ElevenLabsTTSProvider(session.tts_voice_id)
            tts_result = tts.synthesize(turn_result.coach_text)
            if isinstance(tts_result, bytes):
                audio_b64 = base64.b64encode(tts_result).decode("ascii")
            elif isinstance(tts_result, TurnError):
                tts_error = {
                    "stage": tts_result.stage,
                    "message": tts_result.message,
                    "recoverable": tts_result.recoverable,
                }
        except RuntimeError as exc:
            tts_error = {"stage": "tts", "message": str(exc), "recoverable": False}

    return {
        "transcript_raw": transcript_raw,
        "transcript_norm": transcript_norm,
        "coach_text": turn_result.coach_text,
        "corrections": [
            {
                "original": c.original,
                "corrected": c.corrected,
                "explanation": c.explanation,
                "triggered_by": c.triggered_by,
            }
            for c in turn_result.corrections
        ],
        "audio_b64": audio_b64,
        "tts_error": tts_error,
        "error": None,
    }
```

Also add `audio_b64` and `tts_error` fields (both `None`) to the two early-return error branches (STT error and AI error):

STT error branch — replace its return with:

```python
        return {
            "transcript_raw": None,
            "transcript_norm": None,
            "coach_text": None,
            "corrections": [],
            "audio_b64": None,
            "tts_error": None,
            "error": {
                "stage": stt_result.stage,
                "message": stt_result.message,
                "recoverable": stt_result.recoverable,
            },
        }
```

AI/turn error branch — replace its return with:

```python
    if isinstance(turn_result, TurnError):
        return {
            "transcript_raw": transcript_raw,
            "transcript_norm": transcript_norm,
            "coach_text": None,
            "corrections": [],
            "audio_b64": None,
            "tts_error": None,
            "error": {
                "stage": turn_result.stage,
                "message": turn_result.message,
                "recoverable": turn_result.recoverable,
            },
        }
```

- [ ] **Step 4: Run TTS integration tests — verify they pass**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestTurnTtsIntegration -v
```

Expected: 3 tests, all PASS.

- [ ] **Step 5: Run full backend suite — verify no regressions**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/integration/test_turn_pipeline.py
git commit -m "feat: wire TTS into /turn route — audio_b64 in response when elevenlabs enabled"
```

---

## Task 6: Update `useVoice.js` for TTS config and AudioContext playback

**Files:**
- Modify: `frontend/src/hooks/useVoice.js`

- [ ] **Step 1: Update `useVoice.js`**

Replace the file with:

```javascript
import { useState, useRef } from 'react'

export function useVoice() {
  const [state, setState] = useState('idle')
  const [turns, setTurns] = useState([])
  const [corrections, setCorrections] = useState([])
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const sessionIdRef = useRef(null)
  const abortControllerRef = useRef(null)

  function newSession(config) {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setState('idle')
    const controller = new AbortController()
    abortControllerRef.current = controller
    sessionIdRef.current = null
    setTurns([])
    setCorrections([])
    setError(null)
    return fetch('/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: config.topic,
        level: config.level,
        ai_provider: config.ai_provider,
        coaching_mode: config.coaching_mode,
        tts_provider: config.tts_provider || 'browser',
        tts_voice_id: config.tts_voice_id || null,
      }),
      signal: controller.signal,
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.session_id) {
          sessionIdRef.current = data.session_id
          return data.session_id
        } else {
          setError({ stage: 'session', message: 'Failed to start session', recoverable: false })
          return null
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError({ stage: 'session', message: 'Failed to start session', recoverable: false })
        }
        return null
      })
  }

  function loadSession(session) {
    sessionIdRef.current = session.id
    setTurns(session.turns || [])
    setCorrections((session.turns || []).flatMap((turn) => turn.corrections || []))
    setError(null)
    setState('idle')
  }

  async function startRecording() {
    if (!sessionIdRef.current) {
      setError({ stage: 'mic', message: 'Session not ready, please try again.', recoverable: true })
      return
    }
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setState('processing')
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' })
        await submitAudio(blob)
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setState('recording')
    } catch (err) {
      setError({ stage: 'mic', message: err.message, recoverable: true })
      setState('idle')
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }

  async function submitAudio(blob) {
    const form = new FormData()
    form.append('audio', blob, 'recording.wav')
    form.append('session_id', sessionIdRef.current)
    try {
      const res = await fetch('/turn', { method: 'POST', body: form })
      const data = await res.json()

      if (data.error) {
        setError(data.error)
        setState('idle')
        return
      }

      setTurns((prev) => [
        ...prev,
        { speaker: 'user', transcript_norm: data.transcript_norm, coach_text: null },
        { speaker: 'coach', transcript_norm: null, coach_text: data.coach_text },
      ])
      setCorrections(data.corrections || [])
      setError(null)
      setState('playing')

      if (data.audio_b64) {
        await playAudioB64(data.audio_b64)
      } else {
        speakCoachText(data.coach_text)
      }
    } catch (err) {
      setError({ stage: 'stt', message: 'Network error', recoverable: true })
      setState('idle')
    }
  }

  async function playAudioB64(b64) {
    const binary = atob(b64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }
    const audioCtx = new AudioContext()
    try {
      const buffer = await audioCtx.decodeAudioData(bytes.buffer)
      const source = audioCtx.createBufferSource()
      source.buffer = buffer
      source.connect(audioCtx.destination)
      await new Promise((resolve) => {
        source.onended = resolve
        source.start()
      })
    } catch {
      // decodeAudioData failure — fall through to idle
    } finally {
      audioCtx.close()
      setState('idle')
    }
  }

  function speakCoachText(text) {
    if (!text || !window.speechSynthesis) {
      setState('idle')
      return
    }
    const utt = new SpeechSynthesisUtterance(text)
    utt.lang = 'es-ES'
    utt.onend = () => setState('idle')
    utt.onerror = () => setState('idle')
    speechSynthesis.speak(utt)
  }

  return { state, turns, corrections, error, startRecording, stopRecording, newSession, loadSession }
}
```

- [ ] **Step 2: Verify the dev server still starts without errors**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: build succeeds with no errors (warnings about unused vars are OK).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useVoice.js
git commit -m "feat: pass TTS config in newSession; play audio_b64 via AudioContext"
```

---

## Task 7: Update `SessionConfig.jsx` with TTS provider and voice dropdowns

**Files:**
- Modify: `frontend/src/components/SessionConfig.jsx`

- [ ] **Step 1: Update `SessionConfig.jsx`**

Replace the entire file with:

```jsx
import { useState } from 'react'

export default function SessionConfig({ config, onConfigChange, topics, providers, ttsVoices, onNewSession, state }) {
  const isKnownTopic = topics.some((t) => t.id === config.topic)
  const [customSelected, setCustomSelected] = useState(false)
  const showCustomInput = customSelected || (topics.length > 0 && !isKnownTopic && config.topic !== '')
  const selectedTopic = topics.find((t) => t.id === config.topic)

  const topicSelectValue = showCustomInput ? 'custom' : config.topic

  function handleTopicChange(e) {
    if (e.target.value === 'custom') {
      setCustomSelected(true)
      onConfigChange({ topic: '' })
    } else {
      setCustomSelected(false)
      onConfigChange({ topic: e.target.value })
    }
  }

  function handleTtsProviderChange(e) {
    const newProvider = e.target.value
    onConfigChange({
      tts_provider: newProvider,
      tts_voice_id: newProvider === 'elevenlabs' ? (ttsVoices[0]?.id || null) : null,
    })
  }

  return (
    <div className="session-config">
      <div className="session-config-field">
        <label htmlFor="topic">Topic</label>
        <select
          id="topic"
          value={topicSelectValue}
          onChange={handleTopicChange}
        >
          {topics.map((t) => (
            <option key={t.id} value={t.id}>{t.label}</option>
          ))}
          <option value="custom">Custom…</option>
        </select>
        {showCustomInput && (
          <input
            type="text"
            placeholder="Enter a topic"
            value={config.topic}
            onChange={(e) => onConfigChange({ topic: e.target.value })}
          />
        )}
        {!showCustomInput && selectedTopic?.starter && (
          <p className="topic-starter">{selectedTopic.starter}</p>
        )}
      </div>

      <div className="session-config-field">
        <label htmlFor="level">Level: {config.level}</label>
        <input
          id="level"
          type="range"
          min="1"
          max="10"
          value={config.level}
          onChange={(e) => onConfigChange({ level: Number(e.target.value) })}
        />
        <div className="level-bands">
          <span>1–2 Beginner</span>
          <span>3–4 Elementary</span>
          <span>5–6 Intermediate</span>
          <span>7–10 Advanced</span>
        </div>
      </div>

      <div className="session-config-field">
        <label htmlFor="ai-provider">AI Provider</label>
        <select
          id="ai-provider"
          value={config.ai_provider}
          onChange={(e) => onConfigChange({ ai_provider: e.target.value })}
        >
          {providers.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
      </div>

      <div className="session-config-field">
        <label htmlFor="coaching-mode">Coaching mode</label>
        <select
          id="coaching-mode"
          value={config.coaching_mode}
          onChange={(e) => onConfigChange({ coaching_mode: e.target.value })}
        >
          <option value="on_demand">On demand</option>
          <option value="explicit">Explicit</option>
          <option value="shadowing">Shadowing</option>
        </select>
      </div>

      <div className="session-config-field">
        <label htmlFor="tts-provider">Voice</label>
        <select
          id="tts-provider"
          value={config.tts_provider}
          onChange={handleTtsProviderChange}
        >
          <option value="browser">Browser (built-in)</option>
          <option value="elevenlabs">ElevenLabs</option>
        </select>
      </div>

      {config.tts_provider === 'elevenlabs' && (
        <div className="session-config-field">
          <label htmlFor="tts-voice">ElevenLabs voice</label>
          <select
            id="tts-voice"
            value={config.tts_voice_id || ''}
            onChange={(e) => onConfigChange({ tts_voice_id: e.target.value })}
          >
            {ttsVoices.map((v) => (
              <option key={v.id} value={v.id}>{v.label}</option>
            ))}
          </select>
        </div>
      )}

      <button
        onClick={onNewSession}
        disabled={state !== 'idle'}
      >
        New Conversation
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Verify build still passes**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SessionConfig.jsx
git commit -m "feat: add TTS provider select and ElevenLabs voice dropdown to SessionConfig"
```

---

## Task 8: Update `App.jsx` to wire TTS config and voices

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Update `App.jsx`**

Replace the entire file with:

```jsx
import { useState, useEffect } from 'react'
import { useVoice } from './hooks/useVoice'
import VoiceButton from './components/VoiceButton'
import Transcript from './components/Transcript'
import CoachOverlay from './components/CoachOverlay'
import SessionConfig from './components/SessionConfig'
import SessionHistory from './components/SessionHistory'
import './App.css'

const DEFAULT_CONFIG = {
  topic: 'general',
  level: 5,
  ai_provider: 'claude',
  coaching_mode: 'on_demand',
  tts_provider: 'browser',
  tts_voice_id: null,
}

function App() {
  const [topics, setTopics] = useState([])
  const [providers, setProviders] = useState([])
  const [ttsVoices, setTtsVoices] = useState([])
  const [savedSessions, setSavedSessions] = useState([])
  const [selectedSessionId, setSelectedSessionId] = useState(null)
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const { state, turns, corrections, error, startRecording, stopRecording, newSession, loadSession } = useVoice()

  function refreshSessions() {
    return fetch('/sessions').then((r) => r.json()).then(setSavedSessions).catch(() => {})
  }

  useEffect(() => {
    fetch('/topics').then((r) => r.json()).then(setTopics).catch(() => {})
    fetch('/providers').then((r) => r.json()).then(setProviders).catch(() => {})
    fetch('/tts-voices').then((r) => r.json()).then(setTtsVoices).catch(() => {})
    newSession(DEFAULT_CONFIG).then((sessionId) => {
      setSelectedSessionId(sessionId)
      refreshSessions()
    })
    refreshSessions()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function onConfigChange(patch) {
    setConfig((prev) => ({ ...prev, ...patch }))
  }

  function onNewSession() {
    const topic = config.topic.trim() || 'general'
    newSession({ ...config, topic }).then((sessionId) => {
      setSelectedSessionId(sessionId)
      refreshSessions()
    })
  }

  function onSelectSession(sessionId) {
    fetch(`/sessions/${sessionId}`)
      .then((r) => r.json())
      .then((session) => {
        setSelectedSessionId(session.id)
        setConfig({
          topic: session.topic,
          level: session.level,
          ai_provider: session.ai_provider,
          coaching_mode: session.coaching_mode,
          tts_provider: session.tts_provider || 'browser',
          tts_voice_id: session.tts_voice_id || null,
        })
        loadSession(session)
      })
      .catch(() => {})
  }

  return (
    <div className="app">
      <h1>duoVoiceCoach</h1>
      <p className="subtitle">Spanish conversation practice</p>
      <SessionConfig
        config={config}
        onConfigChange={onConfigChange}
        topics={topics}
        providers={providers}
        ttsVoices={ttsVoices}
        onNewSession={onNewSession}
        state={state}
      />
      <VoiceButton
        state={state}
        onRecord={startRecording}
        onStop={stopRecording}
        error={error}
      />
      <CoachOverlay corrections={corrections} />
      <Transcript turns={turns} />
      <SessionHistory
        sessions={savedSessions}
        selectedSessionId={selectedSessionId}
        onSelectSession={onSelectSession}
        onRefresh={refreshSessions}
      />
    </div>
  )
}

export default App
```

- [ ] **Step 2: Verify build passes**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: fetch /tts-voices in App; add TTS fields to config state and session restore"
```

---

## Task 9: Write Vitest tests for new frontend behavior

**Files:**
- Modify: `frontend/src/__tests__/SessionConfig.test.jsx`

- [ ] **Step 1: Update `SessionConfig.test.jsx`**

Replace the top of the file (the constants and `renderConfig` helper) and append the new `describe` block. The full updated file:

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SessionConfig from '../components/SessionConfig'

const TOPICS = [
  { id: 'general', label: 'General conversation', starter: 'Hola' },
  { id: 'ordering_food', label: 'Ordering food', starter: 'Hola menú' },
]
const PROVIDERS = [{ id: 'claude', label: 'Claude (Anthropic)' }]
const TTS_VOICES = [
  { id: '21m00Tcm4TlvDq8ikWAM', label: 'Rachel — Female, clear (multilingual)' },
  { id: 'ErXwobaYiN019PkySvjV', label: 'Antoni — Male, natural (multilingual)' },
]
const DEFAULT_CONFIG = {
  topic: 'general',
  level: 5,
  ai_provider: 'claude',
  coaching_mode: 'on_demand',
  tts_provider: 'browser',
  tts_voice_id: null,
}

function renderConfig(overrides = {}) {
  const props = {
    config: DEFAULT_CONFIG,
    onConfigChange: vi.fn(),
    topics: TOPICS,
    providers: PROVIDERS,
    ttsVoices: TTS_VOICES,
    onNewSession: vi.fn(),
    state: 'idle',
    ...overrides,
  }
  render(<SessionConfig {...props} />)
  return props
}

describe('SessionConfig — coaching mode', () => {
  it('renders coaching mode select with three options', () => {
    renderConfig()
    const select = screen.getByLabelText(/coaching mode/i)
    expect(select).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /on demand/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /explicit/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /shadowing/i })).toBeInTheDocument()
  })

  it('shows current coaching mode as selected', () => {
    renderConfig({ config: { ...DEFAULT_CONFIG, coaching_mode: 'explicit' } })
    expect(screen.getByLabelText(/coaching mode/i).value).toBe('explicit')
  })

  it('calls onConfigChange when coaching mode changes', () => {
    const { onConfigChange } = renderConfig()
    fireEvent.change(screen.getByLabelText(/coaching mode/i), { target: { value: 'shadowing' } })
    expect(onConfigChange).toHaveBeenCalledWith({ coaching_mode: 'shadowing' })
  })
})

describe('SessionConfig — topic picker', () => {
  it('renders topic select with preset options plus Custom', () => {
    renderConfig()
    expect(screen.getByRole('option', { name: /general conversation/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /ordering food/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /custom/i })).toBeInTheDocument()
  })

  it('shows the selected preset starter phrase', () => {
    renderConfig()
    expect(screen.getByText('Hola')).toBeInTheDocument()
  })

  it('updates the starter phrase when a different preset topic is selected', () => {
    renderConfig({ config: { ...DEFAULT_CONFIG, topic: 'ordering_food' } })
    expect(screen.getByText('Hola menú')).toBeInTheDocument()
  })

  it('selecting Custom reveals a text input', () => {
    const props = renderConfig()
    fireEvent.change(screen.getByLabelText(/topic/i), { target: { value: 'custom' } })
    expect(screen.getByPlaceholderText(/enter a topic/i)).toBeInTheDocument()
    expect(props.onConfigChange).toHaveBeenCalledWith({ topic: '' })
  })

  it('selecting Custom hides the preset starter phrase', () => {
    renderConfig()
    fireEvent.change(screen.getByLabelText(/topic/i), { target: { value: 'custom' } })
    expect(screen.queryByText('Hola')).not.toBeInTheDocument()
  })

  it('does not treat the default topic as custom while topics are loading', () => {
    renderConfig({ topics: [] })
    expect(screen.queryByPlaceholderText(/enter a topic/i)).not.toBeInTheDocument()
  })

  it('calls onConfigChange when a preset topic is selected', () => {
    const { onConfigChange } = renderConfig()
    fireEvent.change(screen.getByLabelText(/topic/i), { target: { value: 'ordering_food' } })
    expect(onConfigChange).toHaveBeenCalledWith({ topic: 'ordering_food' })
  })
})

describe('SessionConfig — level slider', () => {
  it('renders level slider with min 1 and max 10', () => {
    renderConfig()
    const slider = screen.getByLabelText(/level/i)
    expect(slider).toHaveAttribute('type', 'range')
    expect(slider).toHaveAttribute('min', '1')
    expect(slider).toHaveAttribute('max', '10')
  })

  it('calls onConfigChange with a numeric level when slider changes', () => {
    const { onConfigChange } = renderConfig()
    fireEvent.change(screen.getByLabelText(/level/i), { target: { value: '7' } })
    expect(onConfigChange).toHaveBeenCalledWith({ level: 7 })
  })
})

describe('SessionConfig — provider select', () => {
  it('renders provider select with Claude option', () => {
    renderConfig()
    expect(screen.getByRole('option', { name: /claude \(anthropic\)/i })).toBeInTheDocument()
  })

  it('calls onConfigChange when provider changes', () => {
    const { onConfigChange } = renderConfig()
    fireEvent.change(screen.getByLabelText(/ai provider/i), { target: { value: 'claude' } })
    expect(onConfigChange).toHaveBeenCalledWith({ ai_provider: 'claude' })
  })
})

describe('SessionConfig — New Conversation button', () => {
  it('calls onNewSession when clicked', () => {
    const { onNewSession } = renderConfig()
    fireEvent.click(screen.getByRole('button', { name: /new conversation/i }))
    expect(onNewSession).toHaveBeenCalled()
  })

  it('is disabled when state is not idle', () => {
    renderConfig({ state: 'recording' })
    expect(screen.getByRole('button', { name: /new conversation/i })).toBeDisabled()
  })

  it('is enabled when state is idle', () => {
    renderConfig({ state: 'idle' })
    expect(screen.getByRole('button', { name: /new conversation/i })).not.toBeDisabled()
  })
})

describe('SessionConfig — TTS provider', () => {
  it('renders voice select with browser and elevenlabs options', () => {
    renderConfig()
    expect(screen.getByRole('option', { name: /browser/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /elevenlabs/i })).toBeInTheDocument()
  })

  it('shows browser as default selected voice provider', () => {
    renderConfig()
    expect(screen.getByLabelText(/^voice$/i).value).toBe('browser')
  })

  it('hides voice dropdown when browser is selected', () => {
    renderConfig()
    expect(screen.queryByLabelText(/elevenlabs voice/i)).not.toBeInTheDocument()
  })

  it('shows voice dropdown when elevenlabs is selected', () => {
    renderConfig({
      config: { ...DEFAULT_CONFIG, tts_provider: 'elevenlabs', tts_voice_id: TTS_VOICES[0].id },
    })
    expect(screen.getByLabelText(/elevenlabs voice/i)).toBeInTheDocument()
  })

  it('voice dropdown lists all curated voices', () => {
    renderConfig({
      config: { ...DEFAULT_CONFIG, tts_provider: 'elevenlabs', tts_voice_id: TTS_VOICES[0].id },
    })
    expect(screen.getByRole('option', { name: /rachel/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /antoni/i })).toBeInTheDocument()
  })

  it('calls onConfigChange with tts_provider and first voice when switching to elevenlabs', () => {
    const { onConfigChange } = renderConfig()
    fireEvent.change(screen.getByLabelText(/^voice$/i), { target: { value: 'elevenlabs' } })
    expect(onConfigChange).toHaveBeenCalledWith({
      tts_provider: 'elevenlabs',
      tts_voice_id: TTS_VOICES[0].id,
    })
  })

  it('calls onConfigChange with null voice_id when switching back to browser', () => {
    const { onConfigChange } = renderConfig({
      config: { ...DEFAULT_CONFIG, tts_provider: 'elevenlabs', tts_voice_id: TTS_VOICES[0].id },
    })
    fireEvent.change(screen.getByLabelText(/^voice$/i), { target: { value: 'browser' } })
    expect(onConfigChange).toHaveBeenCalledWith({
      tts_provider: 'browser',
      tts_voice_id: null,
    })
  })

  it('calls onConfigChange with tts_voice_id when voice changes', () => {
    const { onConfigChange } = renderConfig({
      config: { ...DEFAULT_CONFIG, tts_provider: 'elevenlabs', tts_voice_id: TTS_VOICES[0].id },
    })
    fireEvent.change(screen.getByLabelText(/elevenlabs voice/i), {
      target: { value: TTS_VOICES[1].id },
    })
    expect(onConfigChange).toHaveBeenCalledWith({ tts_voice_id: TTS_VOICES[1].id })
  })
})
```

- [ ] **Step 2: Run all frontend tests — verify they pass**

```bash
cd frontend && npm test -- --run 2>&1 | tail -20
```

Expected: all tests pass including the 8 new TTS tests. Total frontend test count should be ≥ 46.

- [ ] **Step 3: Run full backend suite to confirm nothing broken**

```bash
uv run pytest -v 2>&1 | tail -10
```

Expected: all backend tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/__tests__/SessionConfig.test.jsx
git commit -m "test: add Vitest coverage for TTS provider and voice dropdowns in SessionConfig"
```

---

## Task 10: Update docs and `.env.example`

**Files:**
- Modify: `.env.example`
- Modify: `docs/manualTestPlan.md`
- Modify: `claudeSpanishCoachPlan.md`

- [ ] **Step 1: Update `.env.example`**

Find the TTS section (already present, currently commented out) and replace it with:

```bash
# --- TTS (Phase 6+) ----------------------------------------------------------
# Required when ElevenLabs TTS is enabled (tts_provider=elevenlabs in session config).
# Leave blank to use browser speechSynthesis (default).
# Get your key at: https://elevenlabs.io
ELEVENLABS_API_KEY=

# Optional: override the default ElevenLabs model.
# Default: eleven_multilingual_v2 (recommended for Spanish)
# ELEVENLABS_MODEL=eleven_multilingual_v2
```

- [ ] **Step 2: Append Phase 6 section to `docs/manualTestPlan.md`**

Add the following to the end of `docs/manualTestPlan.md`:

````markdown
---

## Phase 6 — ElevenLabs TTS

### Prerequisites (in addition to base prerequisites)

- ElevenLabs account and API key obtained from https://elevenlabs.io
- `ELEVENLABS_API_KEY` set in `.env`

### Setup

```bash
uv sync
cd frontend && npm install && cd ..
```

### MT-6-1: Automated tests pass

```bash
uv run pytest -v
cd frontend && npm test -- --run
```

Expected: all backend tests pass; all frontend tests pass (≥ 46).

### MT-6-2: `/tts-voices` route returns curated list

```bash
curl -s http://localhost:8000/tts-voices | python3 -m json.tool
```

Expected: JSON array with 4 voice objects, each with `id`, `label`, `description`.

### MT-6-3: Browser TTS still works (regression)

1. Start backend: `uv run --env-file .env uvicorn backend.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Leave Voice set to **Browser (built-in)**
5. Start a new conversation, speak a sentence in Spanish
6. Verify coach response plays via browser `speechSynthesis`

Expected: audio plays as before (no regression).

### MT-6-4: ElevenLabs TTS — successful playback

1. In `SessionConfig`, set **Voice** to **ElevenLabs** and choose **Rachel — Female, clear**
2. Click **New Conversation**
3. Speak a sentence in Spanish
4. Verify coach response plays with noticeably higher voice quality than browser TTS
5. Verify `audio_b64` field is present in the network response (browser DevTools → Network → `/turn`)

Expected: ElevenLabs audio plays; `audio_b64` is a non-empty base64 string.

### MT-6-5: Switch voice mid-conversation (new session required)

1. Change voice to **Antoni — Male, natural** and click **New Conversation**
2. Speak a sentence — verify different voice plays

Expected: voice changes after new session is started.

### MT-6-6: ElevenLabs TTS with missing API key

1. Temporarily remove `ELEVENLABS_API_KEY` from `.env` and restart backend
2. Set Voice to ElevenLabs, start a session, speak a sentence
3. Verify coach text is still returned and displayed
4. Verify `tts_error` is present in the network response
5. Verify no crash — app remains usable

Expected: coach text shows; `audio_b64` is null; `tts_error.stage == "tts"`.

### MT-6-7: Session restore includes TTS config

1. Start a session with ElevenLabs + Rachel, conduct 1 turn
2. Find the session in **Session History** and click it
3. Verify the Voice dropdown restores to ElevenLabs / Rachel

Expected: TTS config is restored from persisted session.
````

- [ ] **Step 3: Update `claudeSpanishCoachPlan.md` Phase 6 task list**

In `claudeSpanishCoachPlan.md`, find the Phase 6 Tasks section and mark all tasks complete:

```markdown
- [x] Implement `ElevenLabsTTSProvider` in `backend/tts.py` — calls ElevenLabs API, returns audio bytes
- [x] Update `backend/main.py` — if `tts_provider` returns bytes, include base64 audio in `/turn` response
- [x] Update `frontend/hooks/useVoice.js` — if response contains audio bytes, play via `AudioContext`; else fall back to `speechSynthesis`
- [x] Add `tts_provider` to session config (browser / elevenlabs)
- [x] Write unit test: `ElevenLabsTTSProvider` with fixture response (no live API in CI)
- [ ] Manual smoke test: ElevenLabs voice vs. browser TTS — verify quality improvement
- [ ] Add Phase 6 procedures to `docs/manualTestPlan.md`
```

Also update the status table row for Phase 6:

```markdown
| 6 — ElevenLabs TTS | Swap browser TTS via tts.py | ⏳ Implemented — awaiting manual sign-off | — | Voice quality upgrade |
```

- [ ] **Step 4: Commit**

```bash
git add .env.example docs/manualTestPlan.md claudeSpanishCoachPlan.md
git commit -m "docs: add Phase 6 manual test plan and update env example for ElevenLabs"
```

---

## Task 11: Final verification

- [ ] **Step 1: Run complete backend test suite**

```bash
uv run pytest -v 2>&1 | tail -15
```

Expected: all tests pass. Look for the count — should be ≥ 83 backend tests (74 prior + 6 TTS unit + 5 route integration + 3 turn TTS integration, minus 2 skipped).

- [ ] **Step 2: Run complete frontend test suite**

```bash
cd frontend && npm test -- --run 2>&1 | tail -15
```

Expected: ≥ 46 frontend tests, all pass (38 prior + 8 new TTS tests).

- [ ] **Step 3: Complete manual smoke tests MT-6-1 through MT-6-7**

Follow procedures in `docs/manualTestPlan.md` — Phase 6 section. Record results in `docs/manualTestLog.md`.

- [ ] **Step 4: Update `claudeSpanishCoachPlan.md` with gate sign-off**

After manual tests pass, mark the remaining Phase 6 tasks done and update the status table:

```markdown
| 6 — ElevenLabs TTS | Swap browser TTS via tts.py | ✅ Complete | ≥ 83 backend; ≥ 46 frontend | ElevenLabs voice signed off YYYY-MM-DD |
```

- [ ] **Step 5: Final commit**

```bash
git add docs/manualTestLog.md claudeSpanishCoachPlan.md
git commit -m "docs: Phase 6 gate sign-off — ElevenLabs TTS complete"
```
