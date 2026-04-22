# Phase 7 — Android / PWA Design

**Date:** 2026-04-22
**Status:** Approved

---

## Goal

Make duoVoiceCoach installable and fully functional on Android Chrome via Progressive Web App packaging. Full voice session (mic capture → Whisper → coach response → TTS playback) must work on a real Android device over an ngrok HTTPS tunnel.

## Approach

Minimal mobile: PWA installability + ngrok setup + Android Chrome mic/audio fixes + touch target bump on VoiceButton. No UI redesign. Get it working on Android as quickly as possible.

---

## PWA Installability

Add `frontend/public/manifest.json` with app name, icons, `display: standalone`, `start_url: /`.

Register a minimal service worker in `index.html` — its only job is to satisfy Chrome's PWA install criteria (a fetch handler that passes through to network, no caching strategy). No Workbox, no cache strategies.

**Why installability-only:** The app cannot function offline since it requires the backend. A caching strategy would only cover the loading screen, which isn't worth the complexity.

---

## Mobile Mic/Audio Compatibility (`useVoice.js`)

Two Android Chrome issues to fix:

**1. `MediaRecorder` MIME type**
Android Chrome does not support `audio/wav` recording natively. Use `MediaRecorder.isTypeSupported('audio/webm;codecs=opus')` to detect support and fall back to `webm` on mobile. The backend (Whisper) handles `webm` without changes.

**2. `AudioContext` autoplay policy**
Android Chrome suspends `AudioContext` until a user gesture occurs. The ElevenLabs audio playback path uses `AudioContext`; call `.resume()` inside the VoiceButton tap handler before playing audio, or it silently fails.

No other changes to `useVoice.js`.

---

## Touch Targets (`VoiceButton.jsx`)

Ensure the record button tap target is at minimum 48×48dp (Chrome's recommended minimum for mobile). Add padding if needed to hit the minimum without changing the visual size. Desktop appearance unchanged.

---

## Backend & ngrok

**Backend binding:** Add `--host 0.0.0.0` to the uvicorn start command so the backend is reachable on the LAN.

**Serve frontend from FastAPI:** Add a static file mount in `backend/main.py` that serves the Vite build output (`frontend/dist/`). This makes the frontend and API share the same origin — no CORS configuration, no env vars, no per-session rebuild when the ngrok URL changes.

**ngrok:** Documented in `docs/android-setup.md`. Steps: install ngrok, run `ngrok http 8001`, copy the HTTPS URL, open on the phone. One URL covers both the app and the API.

**Workflow for Android testing:**
1. `npm run build` (in `frontend/`)
2. `uv run uvicorn backend.main:app --host 0.0.0.0 --port 8001`
3. `ngrok http 8001`
4. Open ngrok HTTPS URL in Android Chrome

**Trade-off accepted:** Android testing requires a build step instead of `npm run dev`. This is acceptable since UI iteration happens on desktop.

---

## Phase 8 Stub — Cloud Deployment

Phase 8 is added to the plan as a not-started stub. Before any implementation, the following must be explored and a decision recorded:

- **STT: local Whisper vs API-based** — Whisper `base` needs ~1 GB RAM, ruling out most free cloud tiers. Candidates: OpenAI Whisper API (pay-per-minute), Deepgram (fast, competitive pricing, good Spanish accuracy). Exploration should benchmark cost-per-session and latency vs. current local Whisper.
- **Hosting options** — evaluate RAM requirements vs. tier pricing (Fly.io, Railway, Render, plain VPS). Minimum ~1 GB RAM instance needed if staying with local Whisper.
- **HTTPS** — handled by the platform; no ngrok needed in cloud.
- **Secrets management** — `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY` go in the host's secret store, not `.env` files.
- **Usability delta** — measure whether cloud latency (STT API round-trip + coach response) feels worse than local Whisper in a real session.

Phase 8 tasks are `[ ] Explore X` items that produce a decision document before any code is written.

---

## Testing

- Manual smoke test on a real Android device: full session — mic capture → Whisper → coach response → TTS playback
- PWA install prompt appears in Android Chrome
- No new automated tests required for PWA/ngrok plumbing; existing test suite must continue to pass

---

## Phase Gate

- PWA installable on Android Chrome
- Full voice session works on Android over ngrok
- Manual smoke test signed off in `docs/manualTestLog.md`
