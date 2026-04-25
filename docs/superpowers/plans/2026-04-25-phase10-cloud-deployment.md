# Phase 10 — Cloud Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy duoVoiceCoach to Fly.io with OpenAI Whisper API for STT and HTTP Basic Auth, accessible from Android phones anywhere over HTTPS.

**Architecture:** Single Fly.io container (512 MB shared CPU) runs FastAPI, which serves both the React SPA (built to `frontend/dist/`) as static files and all API routes. A Fly persistent volume at `/data` holds session JSON files. The local Whisper model is replaced by the OpenAI Whisper API for speed; the existing `AbstractSTTProvider` pattern absorbs the swap via a factory function and a new `STT_PROVIDER` env var.

**Tech Stack:** Python 3.12 / FastAPI / `openai>=1.0` (Whisper API client) / Starlette `BaseHTTPMiddleware` / Fly.io / Docker (multi-stage build) / React/Vite

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | Modify | Add `openai>=1.0` dependency |
| `.env.example` | Modify | Document `STT_PROVIDER`, `OPENAI_API_KEY`, `DVC_BASIC_AUTH_USER`, `DVC_BASIC_AUTH_PASS` |
| `backend/stt.py` | Modify | Add `OpenAIWhisperSTT`, `get_stt_provider()`; update `WhisperSTT.transcribe` signature |
| `backend/main.py` | Modify | Wire `get_stt_provider()`, remove temp-file boilerplate from 3 routes, add `BasicAuthMiddleware` |
| `tests/unit/test_stt.py` | Modify | Update `TestWhisperSTT` for new interface; add `TestOpenAIWhisperSTT`, `TestGetSttProvider` |
| `tests/unit/test_auth.py` | Create | `TestBasicAuthMiddleware` — 4 tests |
| `tests/integration/test_turn_pipeline.py` | Modify | Update 5 `FakeSTT` classes to new 2-arg signature |
| `Dockerfile` | Create | Multi-stage build: Node 20 frontend build + Python 3.12 runtime |
| `fly.toml` | Create | Fly.io app config, persistent volume, 512 MB VM |

---

## Task 1: Add `openai` package and document new env vars

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`

- [ ] **Step 1: Add `openai>=1.0` to `pyproject.toml` dependencies**

In `pyproject.toml`, add `"openai>=1.0",` to the `dependencies` list, after the `anthropic` line:

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "openai-whisper>=20240930",
    "anthropic>=0.49",
    "openai>=1.0",
    "python-multipart>=0.0.20",
    "httpx>=0.28",
    "aiofiles>=24",
]
```

- [ ] **Step 2: Run `uv sync` to update the lock file**

```bash
uv sync
```

Expected: lock file updated, `openai` package installed.

- [ ] **Step 3: Verify the package imports**

```bash
uv run python -c "import openai; print(openai.__version__)"
```

Expected: prints a version string like `1.x.x`.

- [ ] **Step 4: Add new env vars to `.env.example`**

Append to `.env.example` after the existing `ELEVENLABS_MODEL` block:

```
# --- STT Provider (Phase 10+) ------------------------------------------------
# Options: local (default, uses local Whisper), openai (uses OpenAI Whisper API)
# Default: local
# STT_PROVIDER=local

# Required when STT_PROVIDER=openai.
OPENAI_API_KEY=

# --- Basic Auth (optional) ---------------------------------------------------
# When both vars are set, all routes require HTTP Basic Auth.
# If either is absent, auth is disabled (safe for local dev).
# DVC_BASIC_AUTH_USER=
# DVC_BASIC_AUTH_PASS=
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock .env.example
git commit -m "feat: add openai package and Phase 10 env var docs"
```

---

## Task 2: Add `OpenAIWhisperSTT`, update `WhisperSTT`, add `get_stt_provider`

**Files:**
- Modify: `backend/stt.py`
- Modify: `tests/unit/test_stt.py`

The `transcribe` interface changes from `(audio_path: str)` to `(audio_bytes: bytes, filename: str)`. `WhisperSTT` now manages its own temp file internally; `OpenAIWhisperSTT` passes bytes and filename directly to the API.

- [ ] **Step 1: Write failing tests for `OpenAIWhisperSTT` and `get_stt_provider`**

Replace the contents of `tests/unit/test_stt.py` with:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/unit/test_stt.py -v 2>&1 | tail -20
```

Expected: `ImportError` or `AttributeError` — `OpenAIWhisperSTT` and `get_stt_provider` do not exist yet.

- [ ] **Step 3: Update `backend/stt.py`**

Replace the entire contents of `backend/stt.py` with:

```python
import os
import re
import tempfile
from typing import Union
from backend.session import TurnError


def normalize_transcript(text: str) -> str:
    """Lowercase and strip punctuation from a Whisper transcript."""
    text = text.lower()
    text = re.sub(r"[¡¿!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~]", "", text)
    return text.strip()


class WhisperSTT:
    """Speech-to-Text provider using OpenAI's Whisper model (local, base variant)."""

    _model = None

    def _get_model(self):
        if WhisperSTT._model is None:
            import whisper
            WhisperSTT._model = whisper.load_model("base")
        return WhisperSTT._model

    def transcribe(self, audio_bytes: bytes, filename: str) -> Union[tuple[str, str], TurnError]:
        """Transcribe audio bytes to (transcript_raw, transcript_norm) or TurnError."""
        ext = os.path.splitext(filename)[1] or ".wav"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            model = self._get_model()
            result = model.transcribe(tmp_path, language="es")
            raw = result["text"].strip()
            norm = normalize_transcript(raw)
            return (raw, norm)
        except Exception as exc:
            return TurnError(stage="stt", message=f"Transcription failed: {exc}", recoverable=True)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)


class OpenAIWhisperSTT:
    """Speech-to-Text provider using OpenAI Whisper API."""

    def transcribe(self, audio_bytes: bytes, filename: str) -> Union[tuple[str, str], TurnError]:
        """Transcribe audio bytes to (transcript_raw, transcript_norm) or TurnError."""
        try:
            import openai
            client = openai.OpenAI()
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=(filename, audio_bytes),
                language="es",
            )
            raw = result.text.strip()
            norm = normalize_transcript(raw)
            return (raw, norm)
        except Exception as exc:
            return TurnError(stage="stt", message=f"Transcription failed: {exc}", recoverable=True)


def get_stt_provider() -> WhisperSTT | OpenAIWhisperSTT:
    """Return STT provider selected by STT_PROVIDER env var (default: local)."""
    if os.environ.get("STT_PROVIDER") == "openai":
        return OpenAIWhisperSTT()
    return WhisperSTT()
```

- [ ] **Step 4: Run tests — all should pass**

```bash
uv run pytest tests/unit/test_stt.py -v 2>&1 | tail -25
```

Expected: all tests pass. The `TestWhisperSTT` live tests that actually run Whisper will take ~10s each.

- [ ] **Step 5: Commit**

```bash
git add backend/stt.py tests/unit/test_stt.py
git commit -m "feat: add OpenAIWhisperSTT, get_stt_provider; update WhisperSTT to bytes interface"
```

---

## Task 3: Update `main.py` to use new STT interface and fix integration tests

**Files:**
- Modify: `backend/main.py`
- Modify: `tests/integration/test_turn_pipeline.py`

Three routes in `main.py` write a temp file and call `stt_provider.transcribe(tmp_path)`. This task removes that boilerplate and calls the new `transcribe(audio_bytes, filename)` interface directly. Five `FakeSTT` classes in the integration tests also need updating.

- [ ] **Step 1: Update the import and provider instantiation in `main.py`**

Find and replace these two lines near the top of `backend/main.py`:

```python
# OLD
from backend.stt import WhisperSTT
```
```python
# NEW
from backend.stt import get_stt_provider
```

And:

```python
# OLD
stt_provider = WhisperSTT()
```
```python
# NEW
stt_provider = get_stt_provider()
```

Also remove `import tempfile` from the top of `main.py` (it is no longer used after the next steps).

- [ ] **Step 2: Update the `/turn` route STT call**

In `backend/main.py`, find the block inside `post_turn`:

```python
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        stt_result = stt_provider.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)
```

Replace it with:

```python
    stt_result = stt_provider.transcribe(audio_bytes, audio.filename or "audio.wav")
```

- [ ] **Step 3: Update the `/pronunciation/evaluate` route STT call**

In `backend/main.py`, find the block inside `pronunciation_evaluate`:

```python
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        stt_result = stt_provider.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)
```

Replace it with:

```python
    stt_result = stt_provider.transcribe(audio_bytes, audio.filename or "audio.wav")
```

- [ ] **Step 4: Update the `/translate` route STT call**

In `backend/main.py`, find the block inside `translate`:

```python
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        stt_result = stt_provider.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)
```

Replace it with:

```python
    stt_result = stt_provider.transcribe(audio_bytes, audio.filename or "audio.wav")
```

- [ ] **Step 5: Update the 5 `FakeSTT` classes in `test_turn_pipeline.py`**

In `tests/integration/test_turn_pipeline.py`, find every occurrence of:

```python
        class FakeSTT:
            def transcribe(self, _path):
```

Replace each one with:

```python
        class FakeSTT:
            def transcribe(self, _bytes, _filename):
```

There are 5 occurrences — in `test_full_turn_updates_persisted_session`, `test_audio_file_saved_only_when_opted_in`, `test_turn_with_browser_tts_has_no_audio_b64`, `test_turn_with_elevenlabs_tts_returns_audio_b64`, and `test_turn_with_elevenlabs_tts_api_failure_returns_tts_error`.

- [ ] **Step 6: Run the full test suite**

```bash
uv run pytest tests/ -v --ignore=tests/unit/test_stt.py 2>&1 | tail -30
```

Expected: all tests pass (same count as before this task). If `TypeError` appears on `transcribe`, a FakeSTT was missed in step 5.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py tests/integration/test_turn_pipeline.py
git commit -m "refactor: wire get_stt_provider in main, remove temp-file boilerplate from STT routes"
```

---

## Task 4: Add `BasicAuthMiddleware` to `main.py`

**Files:**
- Modify: `backend/main.py`
- Create: `tests/unit/test_auth.py`

The middleware reads `DVC_BASIC_AUTH_USER` and `DVC_BASIC_AUTH_PASS` at dispatch time. When either var is absent (local dev), all requests pass through. When both are set, any request without valid Basic Auth credentials receives a 401.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_auth.py`:

```python
import base64
import os
import pytest
from fastapi.testclient import TestClient


def _make_auth_header(user: str, pw: str) -> str:
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return f"Basic {token}"


def _client(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DVC_DATA_DIR", "/tmp/duoVoiceCoach-auth-test")
    from backend.main import app
    return TestClient(app)


class TestBasicAuthMiddleware:
    def test_no_env_vars_allows_all_requests(self, monkeypatch):
        monkeypatch.delenv("DVC_BASIC_AUTH_USER", raising=False)
        monkeypatch.delenv("DVC_BASIC_AUTH_PASS", raising=False)
        client = _client(monkeypatch)
        assert client.get("/health").status_code == 200

    def test_valid_credentials_pass_through(self, monkeypatch):
        monkeypatch.setenv("DVC_BASIC_AUTH_USER", "alice")
        monkeypatch.setenv("DVC_BASIC_AUTH_PASS", "s3cret")
        client = _client(monkeypatch)
        response = client.get("/health", headers={"Authorization": _make_auth_header("alice", "s3cret")})
        assert response.status_code == 200

    def test_missing_auth_header_returns_401(self, monkeypatch):
        monkeypatch.setenv("DVC_BASIC_AUTH_USER", "alice")
        monkeypatch.setenv("DVC_BASIC_AUTH_PASS", "s3cret")
        client = _client(monkeypatch)
        response = client.get("/health")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_wrong_password_returns_401(self, monkeypatch):
        monkeypatch.setenv("DVC_BASIC_AUTH_USER", "alice")
        monkeypatch.setenv("DVC_BASIC_AUTH_PASS", "s3cret")
        client = _client(monkeypatch)
        response = client.get("/health", headers={"Authorization": _make_auth_header("alice", "wrong")})
        assert response.status_code == 401
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/unit/test_auth.py -v 2>&1 | tail -15
```

Expected: 3 tests fail (`test_missing_auth_header_returns_401`, `test_wrong_password_returns_401`) — the middleware doesn't exist yet, so all requests return 200.

- [ ] **Step 3: Add imports to `main.py`**

At the top of `backend/main.py`, add to the existing imports:

```python
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
```

(`base64` and `os` are already imported.)

- [ ] **Step 4: Add `BasicAuthMiddleware` class and register it in `main.py`**

After the `app = FastAPI()` line in `backend/main.py`, insert:

```python
class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        expected_user = os.environ.get("DVC_BASIC_AUTH_USER")
        expected_pass = os.environ.get("DVC_BASIC_AUTH_PASS")
        if not expected_user or not expected_pass:
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
            except Exception:
                pass
            else:
                user, _, pw = decoded.partition(":")
                if secrets.compare_digest(user, expected_user) and \
                   secrets.compare_digest(pw, expected_pass):
                    return await call_next(request)
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="duoVoiceCoach"'},
        )


app.add_middleware(BasicAuthMiddleware)
```

- [ ] **Step 5: Run auth tests — all should pass**

```bash
uv run pytest tests/unit/test_auth.py -v 2>&1 | tail -15
```

Expected: 4/4 pass.

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
uv run pytest tests/ -v 2>&1 | tail -30
```

Expected: same pass count as before this task. The integration tests use `TestClient` without auth headers; they work because `DVC_BASIC_AUTH_USER`/`DVC_BASIC_AUTH_PASS` are not set in the test environment.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py tests/unit/test_auth.py
git commit -m "feat: add BasicAuthMiddleware — all routes protected when DVC_BASIC_AUTH_USER/PASS are set"
```

---

## Task 5: Dockerfile and `fly.toml`

**Files:**
- Create: `Dockerfile`
- Create: `fly.toml`

No automated tests for deployment artifacts. Manual verification is the Fly.io deploy itself (gate criteria).

- [ ] **Step 1: Create `Dockerfile`**

Create `Dockerfile` at the project root:

```dockerfile
# Stage 1: build the React frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY backend/ backend/
COPY --from=frontend-build /app/frontend/dist frontend/dist

EXPOSE 8001
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

ffmpeg is included because `openai-whisper` lists it as a dependency; it is unused at runtime when `STT_PROVIDER=openai` but required for the package to install cleanly.

- [ ] **Step 2: Create `fly.toml`**

Create `fly.toml` at the project root:

```toml
app = "duo-voice-coach"
primary_region = "iad"

[build]

[mounts]
  source = "duo_data"
  destination = "/data"

[http_service]
  internal_port = 8001
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
```

`auto_stop_machines = "stop"` lets the container sleep when idle (~2–3s cold start on next request). To keep the app always-on, change `min_machines_running` to `1`.

- [ ] **Step 3: Add `Dockerfile` to `.gitignore` exclusion check**

Verify `fly.toml` and `Dockerfile` are not already in `.gitignore` (they should be committed):

```bash
git check-ignore fly.toml Dockerfile
```

Expected: no output (neither file is ignored).

- [ ] **Step 4: Commit**

```bash
git add Dockerfile fly.toml
git commit -m "feat: add Dockerfile (multi-stage) and fly.toml for Fly.io deployment"
```

---

## Task 6: Deploy to Fly.io

This task requires a Fly.io account and the `fly` CLI. Steps are manual; no automated tests.

- [ ] **Step 1: Install the Fly CLI (if not already installed)**

```bash
curl -L https://fly.io/install.sh | sh
```

Verify: `fly version`

- [ ] **Step 2: Authenticate**

```bash
fly auth login
```

Opens browser for login/signup.

- [ ] **Step 3: Build the React frontend locally first to validate the build**

```bash
cd frontend && npm ci && npm run build && cd ..
```

Expected: `frontend/dist/` populated with built assets.

- [ ] **Step 4: Create the Fly app**

```bash
fly apps create duo-voice-coach
```

If `duo-voice-coach` is taken, choose another name and update `fly.toml` `app = "..."`.

- [ ] **Step 5: Create the persistent volume**

```bash
fly volumes create duo_data --region iad --size 1
```

Expected: volume created, 1 GB.

- [ ] **Step 6: Set secrets in Fly**

```bash
fly secrets set \
  ANTHROPIC_API_KEY="<your key>" \
  ELEVENLABS_API_KEY="<your key>" \
  OPENAI_API_KEY="<your key>" \
  DVC_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  DVC_DATA_DIR="/data" \
  STT_PROVIDER="openai" \
  DVC_BASIC_AUTH_USER="<choose a username>" \
  DVC_BASIC_AUTH_PASS="<choose a password>"
```

- [ ] **Step 7: Deploy**

```bash
fly deploy
```

Expected: Docker image built, pushed, deployed. Visit `https://duo-voice-coach.fly.dev` (or your app name) — Basic Auth prompt appears.

- [ ] **Step 8: Smoke test on Android Chrome**

1. Open `https://<app-name>.fly.dev` on Android Chrome
2. Enter Basic Auth credentials when prompted
3. Start a Conversation session, speak a phrase in Spanish
4. Verify transcript appears and coach responds with TTS playback
5. Check session appears in Session History
6. Redeploy (`fly deploy`) and reload — verify session history persists

- [ ] **Step 9: Sign off in `docs/manualTestLog.md`**

Append Phase 10 gate sign-off entry to `docs/manualTestLog.md`:

```markdown
## Phase 10 — Cloud Deployment

**Gate criteria:**
- [ ] All tests pass (backend + frontend)
- [ ] App accessible at `https://<app>.fly.dev` with Basic Auth
- [ ] Full voice session works on Android Chrome end-to-end
- [ ] Session history persists across redeploy

**Sign-off:**
- Date:
- Tester: oldhat86@gmail.com
- Notes:
```

- [ ] **Step 10: Commit sign-off**

```bash
git add docs/manualTestLog.md
git commit -m "docs: Phase 10 manual test sign-off"
```
