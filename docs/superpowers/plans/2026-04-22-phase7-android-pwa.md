# Phase 7 — Android / PWA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make duoVoiceCoach installable on Android Chrome as a PWA and fully functional over an ngrok HTTPS tunnel backed by a local FastAPI server.

**Architecture:** Add a PWA manifest + minimal service worker for installability; fix two Android Chrome audio incompatibilities in `useVoice.js` (MIME type and AudioContext autoplay); bump VoiceButton touch targets; serve the Vite build output as static files from FastAPI so one ngrok URL covers both the app and the API; document the Android setup flow.

**Tech Stack:** Vite (PWA manifest, service worker), FastAPI `StaticFiles`, ngrok, `aiofiles` (required by FastAPI `StaticFiles`).

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `frontend/public/manifest.json` | Create | PWA manifest — name, icons, display mode |
| `frontend/public/sw.js` | Create | Minimal service worker (fetch passthrough for installability) |
| `frontend/index.html` | Modify | Link manifest, register service worker |
| `frontend/src/hooks/useVoice.js` | Modify | MIME type detection + eager AudioContext resume on user gesture |
| `frontend/src/index.css` | Modify | Touch target min-size for `.voice-btn` |
| `pyproject.toml` | Modify | Add `aiofiles` dependency (required by FastAPI StaticFiles) |
| `backend/main.py` | Modify | Mount `frontend/dist` as static files at `/` |
| `docs/android-setup.md` | Create | Step-by-step Android + ngrok setup guide |
| `claudeSpanishCoachPlan.md` | Modify | Check off Phase 7 tasks; add Phase 8 stub |

---

## Task 1: PWA Manifest

**Files:**
- Create: `frontend/public/manifest.json`
- Modify: `frontend/index.html`

- [ ] **Step 1: Create manifest.json**

```json
{
  "name": "duoVoiceCoach",
  "short_name": "DuoVoice",
  "description": "Voice-first AI Spanish conversation coach",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#aa3bff",
  "icons": [
    {
      "src": "/favicon.svg",
      "sizes": "any",
      "type": "image/svg+xml",
      "purpose": "any maskable"
    }
  ]
}
```

Save to `frontend/public/manifest.json`.

- [ ] **Step 2: Link manifest in index.html**

Replace the existing `<head>` section of `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="manifest" href="/manifest.json" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#aa3bff" />
    <title>duoVoiceCoach</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/manifest.json frontend/index.html
git commit -m "feat: add PWA manifest and link in index.html"
```

---

## Task 2: Minimal Service Worker

**Files:**
- Create: `frontend/public/sw.js`
- Modify: `frontend/index.html`

- [ ] **Step 1: Create sw.js**

Save the following to `frontend/public/sw.js`:

```js
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request))
})
```

This is the minimum required for Chrome's PWA install criteria — a service worker with a fetch handler. It passes all requests through to the network with no caching.

- [ ] **Step 2: Register the service worker in index.html**

Add the registration script before `</body>` in `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="manifest" href="/manifest.json" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#aa3bff" />
    <title>duoVoiceCoach</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
    <script>
      if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
          navigator.serviceWorker.register('/sw.js')
        })
      }
    </script>
  </body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/sw.js frontend/index.html
git commit -m "feat: add minimal service worker for PWA installability"
```

---

## Task 3: Fix Android Chrome Audio Compatibility in useVoice.js

**Files:**
- Modify: `frontend/src/hooks/useVoice.js`

Two fixes in one commit:

**Fix A — MIME type:** Android Chrome's `MediaRecorder` records `audio/webm;codecs=opus`, not `audio/wav`. Currently the code creates `new MediaRecorder(stream)` with no explicit MIME type and then wraps chunks in `new Blob(..., { type: 'audio/wav' })`. This mismatch means the blob header says WAV but the content is WebM, which can cause Whisper to fail. Fix: detect the supported MIME type before creating the recorder, pass it explicitly, and use `recorder.mimeType` on the blob.

**Fix B — AudioContext autoplay:** Android Chrome suspends `AudioContext` until a user gesture. The `resume()` call in `playAudioB64` runs after several async hops from the original tap, so the gesture context has expired. Fix: call `getAudioCtx().resume()` synchronously at the top of `startRecording`, while still in the gesture handler.

- [ ] **Step 1: Apply both fixes to useVoice.js**

Replace the `startRecording` function (lines 67–96) with:

```js
async function startRecording() {
  if (!sessionIdRef.current) {
    setError({ stage: 'mic', message: 'Session not ready, please try again.', recoverable: true })
    return
  }
  setError(null)
  // Resume AudioContext synchronously inside the user gesture (Android Chrome autoplay policy)
  getAudioCtx().resume()
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/wav'
    const recorder = new MediaRecorder(stream, { mimeType })
    chunksRef.current = []

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }

    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop())
      setState('processing')
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
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
```

- [ ] **Step 2: Verify existing Vitest suite still passes**

```bash
cd frontend && npx vitest run
```

Expected: all existing tests pass. The `startRecording` change is not unit-tested (jsdom has no `MediaRecorder`); correctness is verified in the manual smoke test.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useVoice.js
git commit -m "fix: Android Chrome MIME type and AudioContext resume in useVoice.js"
```

---

## Task 4: VoiceButton Touch Target

**Files:**
- Modify: `frontend/src/index.css`

The `.voice-btn` class has no explicit size rules. On a mobile screen, the button may render below the 48×48dp minimum Google recommends for touch targets. Add a minimal rule to `index.css`.

- [ ] **Step 1: Add touch target rule to index.css**

Append to the end of `frontend/src/index.css`:

```css
.voice-btn {
  min-height: 48px;
  min-width: 48px;
  padding: 12px 24px;
}
```

- [ ] **Step 2: Verify Vitest still passes**

```bash
cd frontend && npx vitest run
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "fix: ensure VoiceButton meets 48dp touch target minimum for mobile"
```

---

## Task 5: Serve Frontend from FastAPI

**Files:**
- Modify: `pyproject.toml`
- Modify: `backend/main.py`

FastAPI's `StaticFiles` requires `aiofiles`. The static mount must be added **after** all route definitions so API routes take precedence.

- [ ] **Step 1: Add aiofiles to pyproject.toml**

In `pyproject.toml`, add `"aiofiles>=24"` to the `dependencies` list:

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "openai-whisper>=20240930",
    "anthropic>=0.49",
    "python-multipart>=0.0.20",
    "httpx>=0.28",
    "aiofiles>=24",
]
```

- [ ] **Step 2: Install the new dependency**

```bash
uv sync
```

Expected: `aiofiles` installed, `uv.lock` updated.

- [ ] **Step 3: Add StaticFiles mount to backend/main.py**

Add these imports at the top of `backend/main.py` (after the existing imports):

```python
import pathlib
from fastapi.staticfiles import StaticFiles
```

Add the static file mount at the **very end** of `backend/main.py`, after all `@app.*` route definitions:

```python
_DIST = pathlib.Path(__file__).parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")
```

The `html=True` flag makes `GET /` serve `frontend/dist/index.html`. The guard means the backend still starts normally in development (no build required).

- [ ] **Step 4: Run the backend test suite to confirm no regressions**

```bash
uv run pytest
```

Expected: same pass/skip counts as before (92 passing, 2 skipped).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock backend/main.py
git commit -m "feat: serve frontend build output as static files from FastAPI"
```

---

## Task 6: Android Setup Documentation

**Files:**
- Create: `docs/android-setup.md`

- [ ] **Step 1: Create the setup guide**

Save the following to `docs/android-setup.md`:

```markdown
# Android Setup Guide

Run duoVoiceCoach on an Android device using ngrok to expose the local backend over HTTPS (required for mic access on Android Chrome).

## Prerequisites

- Backend dependencies installed: `uv sync`
- Frontend built: `cd frontend && npm run build`
- ngrok installed: https://ngrok.com/download (free account, no paid plan needed)

## Steps

### 1. Build the frontend

```bash
cd frontend
npm run build
cd ..
```

This creates `frontend/dist/` which the backend serves as static files.

### 2. Start the backend

```bash
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

`--host 0.0.0.0` makes the server reachable on the network (not just localhost).

### 3. Start ngrok

In a second terminal:

```bash
ngrok http 8001
```

ngrok will print a line like:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8001
```

Copy the `https://...` URL.

### 4. Open on Android

1. Open Android Chrome.
2. Navigate to the ngrok HTTPS URL.
3. To install as a PWA: tap the browser menu → "Add to Home screen".

### Notes

- Both laptop and phone must be running (the phone hits the laptop's ngrok tunnel).
- The ngrok URL changes each session on the free plan — you'll need to copy a new URL each time.
- If mic access is denied on first visit, go to Chrome site settings and grant microphone permission for the ngrok URL.
- Rebuild the frontend (`npm run build`) after any UI changes before testing on Android.
```

- [ ] **Step 2: Commit**

```bash
git add docs/android-setup.md
git commit -m "docs: add Android setup guide for ngrok + PWA workflow"
```

---

## Task 7: Update claudeSpanishCoachPlan.md

**Files:**
- Modify: `claudeSpanishCoachPlan.md`

- [ ] **Step 1: Mark Phase 7 tasks complete and add Phase 8 stub**

In `claudeSpanishCoachPlan.md`:

1. Update the Phase 7 task list — replace the existing `[ ]` items with:

```markdown
### Tasks

- [x] Add `manifest.json` and service worker to frontend — PWA installable in Chrome
- [x] Audit `useVoice.js` for mobile mic/audio compatibility — fix MIME type detection and AudioContext resume on user gesture
- [x] Tune `VoiceButton` touch targets for mobile screen sizes — 48dp minimum
- [x] Serve frontend build output (`frontend/dist`) as static files from FastAPI — single ngrok URL covers both app and API
- [x] Evaluate hosting: local network + ngrok chosen for Phase 7; cloud deployment moved to Phase 8
- [x] Document Android setup in `docs/android-setup.md`
- [ ] Manual smoke test on Android device: full session — mic capture → Whisper → coach response → TTS playback
- [ ] Add Phase 7 procedures to `docs/manualTestPlan.md`
```

2. Update the Phase 7 gate:

```markdown
### Phase 7 Gate

- [ ] PWA installable on Android Chrome
- [ ] Full voice session works on Android
- [ ] Manual smoke test signed off in `docs/manualTestLog.md`
```

3. Append Phase 8 after Phase 7:

```markdown
---

## Phase 8 — Cloud Deployment

**Goal:** Deploy the backend to a cloud host so the app works on Android anywhere, without needing a laptop running ngrok.

**Before writing any implementation code**, explore and document answers to the following in `docs/superpowers/specs/` as a decision doc:

- **STT — local Whisper vs API-based:** Whisper `base` needs ~1 GB RAM, ruling out most free cloud tiers. Candidates to evaluate:
  - OpenAI Whisper API: pay-per-minute, no RAM concern, same model family
  - Deepgram: faster transcription, competitive pricing, strong Spanish accuracy
  - Benchmark: cost-per-session, round-trip latency, Spanish accuracy vs local Whisper `base`
- **Hosting options:** Evaluate RAM requirements vs tier pricing for Fly.io, Railway, Render, plain VPS. Document which tiers support ≥1 GB RAM if staying with local Whisper, and which are adequate for an API-based STT swap.
- **HTTPS:** Handled by the platform — no ngrok required. Document TLS setup expectations per host.
- **Secrets management:** `ANTHROPIC_API_KEY` and `ELEVENLABS_API_KEY` go in the host's secret store, not `.env` files. Document the mechanism per candidate host.
- **Usability delta:** Measure whether cloud latency (STT API round-trip + coach response over internet) feels noticeably worse than local Whisper in a real session. Run a test session with a representative ngrok → cloud-hosted backend and note perceived lag.

### Tasks

- [ ] Explore API-based STT options (OpenAI Whisper API, Deepgram) — benchmark cost, latency, Spanish accuracy vs local Whisper `base`
- [ ] Evaluate hosting options — document which platforms support the RAM and pricing requirements
- [ ] Evaluate HTTPS and secrets management per candidate host
- [ ] Run a test session to measure cloud latency vs local Whisper — document perceived usability delta
- [ ] Write decision doc to `docs/superpowers/specs/YYYY-MM-DD-phase8-cloud-decision.md`
- [ ] Implement chosen approach based on decision doc

### Phase 8 Gate

- [ ] Decision doc written and committed before implementation begins
- [ ] App accessible on Android without ngrok
- [ ] Manual smoke test signed off
```

4. Update the phase status table at the top to add Phase 8:

```markdown
| 7 — Android / PWA | PWA packaging, mobile UX | ⏳ In progress | — | Local network + ngrok |
| 8 — Cloud Deployment | Cloud hosting, STT evaluation | ⏳ Not started | — | Decision doc before implementation |
```

- [ ] **Step 2: Commit**

```bash
git add claudeSpanishCoachPlan.md
git commit -m "docs: update Phase 7 tasks and add Phase 8 cloud deployment stub"
```

---

## Task 8: Manual Smoke Test

This task is manual — no code to write. Complete after all code tasks are committed.

- [ ] **Step 1: Build and start**

```bash
cd frontend && npm run build && cd ..
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8001
# In a second terminal:
ngrok http 8001
```

- [ ] **Step 2: Verify desktop still works**

Open `http://localhost:8001` in desktop Chrome. Confirm:
- App loads (static files served from FastAPI)
- New session starts, mic works, Whisper transcribes, coach responds, TTS plays

- [ ] **Step 3: Verify Android**

Open the ngrok HTTPS URL in Android Chrome. Confirm:
- App loads
- "Add to Home screen" option appears in the browser menu (PWA installable)
- Mic permission granted → recording works → coach responds → audio plays
- No silent failures (AudioContext, MIME type)

- [ ] **Step 4: Sign off**

Add a sign-off entry to `docs/manualTestLog.md`:

```markdown
## Phase 7 — Android / PWA

**Date:** 2026-04-22
**Tester:** [name]

- PWA manifest loads; "Add to Home Screen" available in Android Chrome
- Full voice session completed on Android: mic → Whisper → coach response → TTS playback
- Desktop session still works after static file serving change
- No audio errors (MIME type, AudioContext)

**Status: PASS**
```

- [ ] **Step 5: Update Phase 7 gate in claudeSpanishCoachPlan.md**

Check off the remaining gate items and update the phase status table row to `✅ Complete`.

- [ ] **Step 6: Final commit**

```bash
git add docs/manualTestLog.md claudeSpanishCoachPlan.md
git commit -m "docs: Phase 7 manual test sign-off"
```
