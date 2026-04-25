# duoVoiceCoach — Phase 10: Cloud Deployment Design Spec

**Date:** 2026-04-25  
**Status:** Approved — ready for implementation planning  
**Goal:** Deploy the app to Fly.io so it is accessible on Android (and any browser) without a laptop running ngrok.

---

## Context

Phases 0–9, A, and B delivered a fully working desktop Spanish voice coach. The backend runs locally (FastAPI + local Whisper CPU inference), accessible only on the home network or via ngrok. Phase 10 moves the backend to the cloud so both household members can use the app from Android phones anywhere.

Phase 7 (Android PWA) follows Phase 10 and adds home-screen install and mobile UX polish. After Phase 10 the app already works in Android Chrome — Phase 7 makes it feel native.

---

## Architecture

Single Fly.io container running FastAPI. The React app is built at image build time (`npm run build`) and FastAPI serves `frontend/dist/` as static files. All traffic — page loads and API calls — goes through one HTTPS endpoint.

```
Android Chrome (HTTPS)
        │
        ▼
  Fly.io app (single container, 512 MB, shared CPU)
  ┌──────────────────────────────────────────────┐
  │ FastAPI :8001                                │
  │  ├── BasicAuthMiddleware (all routes)        │
  │  ├── /turn, /session, /sessions, etc.        │
  │  │    └── OpenAIWhisperSTT ──────────────────┼──► openai.com
  │  │    └── ClaudeProvider ───────────────────-┼──► anthropic.com
  │  │    └── ElevenLabsTTS ────────────────────-┼──► elevenlabs.io
  │  └── StaticFiles /                           │
  │       └── frontend/dist/                     │
  └──────────────────────────────────────────────┘
        │ Fly persistent volume at /data
        └── session JSON files (DVC_DATA_DIR=/data)
```

**Session persistence:** Fly.io persistent volume mounted at `/data`. Survives redeploys. Priced at ~$0.15/GB/month — negligible at this scale.

**Secrets** (stored in Fly secret store, never baked into the image):
- `ANTHROPIC_API_KEY`
- `ELEVENLABS_API_KEY`
- `OPENAI_API_KEY` (Whisper API)
- `DVC_SESSION_SECRET`
- `DVC_BASIC_AUTH_USER`
- `DVC_BASIC_AUTH_PASS`

---

## STT Swap: OpenAI Whisper API

### Motivation

Local Whisper on a cloud VM CPU takes 5–15s per transcription. OpenAI Whisper API returns in 1–2s. For mobile users expecting a responsive voice interface, the latency difference is the whole experience.

### Implementation

New `OpenAIWhisperSTT` class added to `backend/stt.py`, alongside the existing `WhisperSTT`:

```python
class OpenAIWhisperSTT(AbstractSTTProvider):
    def transcribe(self, audio_bytes: bytes, filename: str) -> str | TurnError:
        client = openai.OpenAI()  # reads OPENAI_API_KEY from env
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio_bytes),
            language="es",
        )
        return result.text
```

Provider selected by `STT_PROVIDER` env var:
- `local` (default) — `WhisperSTT`, local model, used in development
- `openai` — `OpenAIWhisperSTT`, API-based, used in cloud deployment

Selection happens once at `app` startup in `main.py`; injected into route handlers via dependency injection. No other code changes required.

**Android audio format:** Android Chrome's MediaRecorder outputs WebM/Opus. OpenAI Whisper API accepts WebM/Opus natively. The filename passed to the API must carry the correct extension (e.g., `audio.webm`) so the API can detect the format. No WAV conversion required.

**Cost estimate:** ~$0.006/min of audio. A 20-minute session ≈ $0.12. At daily use for 2 people ≈ $7–9/month in STT costs.

---

## HTTP Basic Auth

A `BaseHTTPMiddleware` applied to all routes (API and static files). Credentials read from env vars; middleware is skipped when both vars are absent (local dev with no auth configured).

```python
class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        expected_user = os.environ.get("DVC_BASIC_AUTH_USER")
        expected_pass = os.environ.get("DVC_BASIC_AUTH_PASS")
        if not expected_user or not expected_pass:
            return await call_next(request)  # auth disabled locally
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            decoded = base64.b64decode(auth[6:]).decode()
            user, _, pw = decoded.partition(":")
            if secrets.compare_digest(user, expected_user) and \
               secrets.compare_digest(pw, expected_pass):
                return await call_next(request)
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="duoVoiceCoach"'}
        )
```

`secrets.compare_digest` prevents timing attacks. Android Chrome caches Basic Auth credentials after first entry — no repeated prompts.

---

## Fly.io Deployment Config

### `Dockerfile`

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y nodejs npm ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY frontend/ frontend/
RUN cd frontend && npm ci && npm run build

COPY backend/ backend/
COPY tests/fixtures/ tests/fixtures/

EXPOSE 8001
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

ffmpeg is included because `openai-whisper` is still a dependency for local dev compatibility. If whisper is removed from prod deps in a future cleanup, ffmpeg can be dropped from the image.

### `fly.toml`

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

`auto_stop_machines = "stop"` allows the container to sleep when idle (~2–3s cold start on next request). For a 2-person household this is acceptable and minimizes cost. Set `min_machines_running = 1` to keep always-on at the cost of ~$3–4/month.

### `pyproject.toml` dependency addition

Add `openai>=1.0` to the project dependencies. (`openai-whisper` for local STT is already present; `openai` is the separate API client package.)

### `.env.example` additions

```
# STT Provider (Phase 10+)
# Options: local (default, uses local Whisper), openai (uses OpenAI Whisper API)
STT_PROVIDER=local
OPENAI_API_KEY=

# Basic Auth (optional; if unset, auth is disabled — for local dev)
DVC_BASIC_AUTH_USER=
DVC_BASIC_AUTH_PASS=
```

---

## Testing

### Backend (new tests)

- `test_stt.py` — `OpenAIWhisperSTT.transcribe()`: mock `openai.OpenAI` client, assert transcript returned; assert API error returns `TurnError`
- `test_stt.py` — STT provider wiring: `STT_PROVIDER=openai` → `OpenAIWhisperSTT`; `STT_PROVIDER=local` → `WhisperSTT`
- `test_main.py` — `BasicAuthMiddleware`: valid credentials → 200; missing auth header → 401; wrong credentials → 401; auth disabled when env vars absent

### Frontend (no new tests)

No frontend code changes. The frontend sends audio bytes to `/turn` regardless of STT provider.

### Manual Smoke Test (gate)

- Open `https://<app>.fly.dev` on Android Chrome → Basic Auth prompt appears
- Enter credentials → app loads
- Complete a full voice session: mic → transcription → coach response → TTS playback
- Verify session appears in session history
- Redeploy the app → reload page → session history still present (volume survived)
- Cold start: close app, wait 5 min, reopen → note wake time (target < 5s)

---

## Phase 10 Gate Criteria

- [ ] All backend tests pass including new STT and auth tests
- [ ] All frontend tests pass (no regressions)
- [ ] App accessible at `https://<app>.fly.dev` with Basic Auth
- [ ] Full voice session works on Android Chrome end-to-end
- [ ] Session history persists across redeploy
- [ ] Manual smoke test signed off in `docs/manualTestLog.md`
