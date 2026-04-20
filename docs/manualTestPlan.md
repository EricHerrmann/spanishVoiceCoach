# duoVoiceCoach — Manual Test Plan: Phases 0 & 1

**Purpose:** Step-by-step test procedures for the Phase 0 and Phase 1 gate sign-offs. Run these after all automated tests pass. Record results in `manualTestLog.md`.

**Prerequisites:**
- `uv` installed, Python 3.12+ available
- Node 18+ and npm installed
- Microphone connected and browser mic permission granted
- Working directory: repo root (`duoVoiceCoach/`)

---

## Phase 0 — Scaffolding & Contracts

### Setup

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### MT-0-1: Automated tests pass

```bash
uv run pytest -v
```

**Pass:** All 6 tests collected and pass. Output ends with `X passed`.
**Fail:** Any test fails or errors.

---

### MT-0-2: Backend health endpoint responds

```bash
# Terminal 1 — start backend
uv run uvicorn backend.main:app --reload --port 8001

# Terminal 2 — verify health
curl -s http://localhost:8001/health
```

**Expected response:**
```json
{"status": "ok"}
```

**Pass:** Response matches exactly.
**Fail:** Connection refused, 500 error, or different response body.

---

### MT-0-3: POST /turn returns stub JSON

```bash
curl -s -X POST http://localhost:8001/turn \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@tests/fixtures/hola_sample.wav;type=audio/wav" | python3 -m json.tool
```

**Expected:** JSON response with keys `transcript_raw`, `transcript_norm`, `echo`, `error`.
**Pass:** Response is valid JSON with those four keys present.
**Fail:** 422, 500, or missing keys.

---

### MT-0-4: Frontend dev server loads without errors

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173` in a browser.

**Pass:** Page loads without console errors. React app renders (any content).
**Fail:** Blank page, build error, or red console errors.

Stop backend and frontend servers.

---

**Record Phase 0 sign-off in `docs/manualTestLog.md`.**

---

## Phase 1 — Voice Pipeline MVP

### Setup

Start both servers in separate terminals:

```bash
# Terminal 1 — backend
uv run uvicorn backend.main:app --reload --port 8001

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173` in a browser.

---

### MT-1-1: Automated tests pass

```bash
uv run pytest -v
cd frontend && npm test
```

**Pass:** All 21 backend tests and 12 frontend tests pass.
**Fail:** Any failure or error.

---

### MT-1-2: UI renders correctly in idle state

Open `http://localhost:5173`.

**Check:**
- [ ] Page title "duoVoiceCoach" is visible
- [ ] A button is present with text indicating it starts recording ("Start Speaking" or similar)
- [ ] Transcript area is present and empty
- [ ] No error messages visible
- [ ] No browser console errors

**Pass:** All checks above satisfied.

---

### MT-1-3: Basic recording flow

1. Click the record button.

**Check during recording:**
- [ ] Button text changes to "Stop Recording" (or similar)
- [ ] Browser prompts for mic permission (first time only)

2. Say "Hola, ¿cómo estás?" clearly into the microphone.
3. Click "Stop Recording".

**Check during processing:**
- [ ] Button becomes disabled with "Processing..." text

**Check after completion:**
- [ ] Button returns to idle state ("Start Speaking")
- [ ] Your transcription appears in the transcript area
- [ ] `transcript_norm` displayed is lowercase with punctuation removed (e.g., `hola ¿cómo estás?` → `hola cómo estás` or similar)
- [ ] A coach echo entry appears in the transcript (coach repeating back what was said)
- [ ] Browser speaks the echo aloud via `speechSynthesis`

**Pass:** All checks above satisfied.
**Fail:** Button never returns to idle, transcript missing, or browser doesn't speak.

---

### MT-1-4: Whisper transcription accuracy

Speak each phrase and verify the transcript contains the expected words (exact punctuation and casing in `transcript_norm` may vary):

| Spoken phrase | Expected words in `transcript_norm` |
|---|---|
| "Hola, ¿cómo estás?" | `hola`, `cómo`, `estás` or `estas` |
| "Me llamo Juan" | `me`, `llamo`, `juan` |
| "Buenos días" | `buenos`, `días` or `dias` |

**Pass:** Each phrase produces a transcript containing the expected key words.
**Fail:** Completely wrong transcription or empty transcript for clear speech.

---

### MT-1-5: Multiple turns accumulate in transcript

Complete three recording→stop cycles with different phrases.

**Check:**
- [ ] All three user turns appear in the transcript, oldest first
- [ ] Each user turn is followed by a coach echo entry
- [ ] Transcript does not reset between turns

**Pass:** 6 entries total (3 user, 3 coach) visible in correct order.

---

### MT-1-6: Error handling — mic permission denied

1. In browser settings, block microphone access for `localhost`.
2. Click the record button.

**Check:**
- [ ] Button returns to idle state (does not stay in recording or processing)
- [ ] A retry/error message appears in the UI (e.g., "try again" or similar)
- [ ] No unhandled exceptions in browser console

3. Re-grant mic permission and verify a normal recording still works afterward.

**Pass:** Error is surfaced gracefully; recording works again after re-granting permission.
**Fail:** Page freezes, unhandled exception, or button stuck in a non-idle state.

---

### MT-1-7: API error handling — verify via curl

Send a deliberately corrupted audio file to the backend:

```bash
echo "not a wav file" > /tmp/bad.wav

curl -s -X POST http://localhost:8001/turn \
  -F "audio=@/tmp/bad.wav;type=audio/wav" | python3 -m json.tool
```

**Expected response structure:**
```json
{
  "transcript_raw": null,
  "transcript_norm": null,
  "echo": null,
  "error": {
    "stage": "stt",
    "message": "...",
    "recoverable": true
  }
}
```

**Pass:** Response is 200 with `error.stage == "stt"`, `error.recoverable == true`, and null transcripts.
**Fail:** 500 error, exception in server logs, or `error` field missing.

---

### MT-1-8: `speechSynthesis` language check

After a successful recording, listen to the echo playback.

**Check:**
- [ ] Browser speaks the text (any voice — quality may be robotic)
- [ ] Language sounds Spanish (or at least not English gibberish)
- [ ] Playback completes and button returns to idle state

**Pass:** Audio plays and button recovers.
**Fail:** Silent, button stuck in "Playing..." state.

---

## Sign-Off Checklist

Before recording sign-off in `manualTestLog.md`, confirm:

- [ ] MT-0-1 through MT-0-4 all passed (Phase 0)
- [ ] MT-1-1 through MT-1-8 all passed (Phase 1)
- [ ] No unexpected browser console errors observed during any test
- [ ] No unhandled exceptions in backend terminal output during any test

Record in `docs/manualTestLog.md`:
- Date tested
- Tester name
- Any observed issues or deviations (note if a test passed with caveats)
- Whisper model version used (check: `uv run python3 -c "import whisper; print(whisper.__version__)"`)
