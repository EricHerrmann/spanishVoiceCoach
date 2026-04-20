# duoVoiceCoach — Manual Test Plan: Phases 0, 1 & 2

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

---

## Phase 2 — AI Conversation Core

### Prerequisites

- `ANTHROPIC_API_KEY` set in your environment (real key required for this phase)
- Backend running on port 8001, frontend on 5173

### Setup

Start both servers in separate terminals:

```bash
# Terminal 1 — backend
ANTHROPIC_API_KEY=<your-key> uv run uvicorn backend.main:app --reload --port 8001

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`.

---

### MT-2-1: Automated tests pass

```bash
ANTHROPIC_API_KEY=test-key uv run pytest -v
cd frontend && npm test -- --run
```

**Pass:** 36 backend tests pass, 2 skipped (API-key gated); 12 frontend tests pass.
**Fail:** Any failure or error.

---

### MT-2-2: Session initialises on page load

Open `http://localhost:5173`. In the browser DevTools Network tab, verify:

- [ ] A `POST /session/start` request fires immediately on page load
- [ ] The response is `200` with body `{"session_id": "<uuid>"}`
- [ ] No error message appears in the UI

**Pass:** `/session/start` called once on load, `session_id` received silently.
**Fail:** Network error, 500, or error message in UI.

---

### MT-2-3: First Spanish turn gets a real coach reply

1. Click the record button.
2. Say "Hola, me gustaría practicar español" clearly.
3. Click Stop.

**Check:**
- [ ] Your transcript appears in the conversation panel
- [ ] A coach reply appears below it (Spanish text, not an echo of what you said)
- [ ] Browser speaks the coach reply aloud in Spanish
- [ ] Button returns to idle state

**Pass:** Distinct Spanish reply from Claude visible and spoken.
**Fail:** Echo of user speech, empty reply, or error message.

---

### MT-2-4: Coach replies are contextually appropriate for level 5

Conduct a short exchange on the default topic (general, level 5):

1. Say "¿Qué puedo hacer en el mercado?"
2. Wait for reply. Say "Quiero comprar frutas y verduras."
3. Wait for reply.

**Check:**
- [ ] Replies are in Spanish throughout
- [ ] Vocabulary is intermediate (not baby-talk, not academic)
- [ ] Coach does not spontaneously correct your grammar (on_demand mode is default)
- [ ] Each reply is contextually relevant to what you said

**Pass:** Two coherent in-context Spanish replies.
**Fail:** English reply, off-topic reply, or unsolicited grammar corrections.

---

### MT-2-5: Conversation history is maintained across turns

Continue the session from MT-2-4 (do not refresh the page):

1. Say "¿Y qué más puedo hacer allí?"

**Check:**
- [ ] The coach's reply references the conversation context (market, fruit/vegetables) rather than starting fresh
- [ ] All prior turns still visible in the transcript

**Pass:** Coach reply shows awareness of prior exchange.
**Fail:** Coach ignores context, asks "How can I help you?" again, or transcript resets.

---

### MT-2-6: AI error path — `/turn` with invalid session_id via curl

In a terminal (backend must be running):

```bash
curl -s -X POST http://localhost:8001/turn \
  -F "audio=@tests/fixtures/hola_sample.wav;type=audio/wav" \
  -F "session_id=invalid-id" | python3 -m json.tool
```

**Expected:** HTTP 404 response.
**Pass:** Status 404 returned.
**Fail:** 200, 500, or exception in server logs.

---

### MT-2-7: Full response structure via curl

```bash
# Start a session
SESSION=$(curl -s -X POST http://localhost:8001/session/start | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

# Submit a turn
curl -s -X POST http://localhost:8001/turn \
  -F "audio=@tests/fixtures/hola_sample.wav;type=audio/wav" \
  -F "session_id=$SESSION" | python3 -m json.tool
```

**Expected response structure:**
```json
{
  "transcript_raw": "Hola, como estás?",
  "transcript_norm": "hola como estás",
  "coach_text": "<Spanish reply from Claude>",
  "corrections": [],
  "error": null
}
```

**Pass:** All five keys present; `coach_text` is non-empty Spanish text; `error` is null.
**Fail:** Missing keys, empty `coach_text`, or non-null `error`.

---

## Sign-Off Checklist

Before recording sign-off in `manualTestLog.md`, confirm:

- [ ] MT-0-1 through MT-0-4 all passed (Phase 0)
- [ ] MT-1-1 through MT-1-8 all passed (Phase 1)
- [ ] MT-2-1 through MT-2-7 all passed (Phase 2)
- [ ] No unexpected browser console errors observed during any test
- [ ] No unhandled exceptions in backend terminal output during any test

Record in `docs/manualTestLog.md`:
- Date tested
- Tester name / email
- Any observed issues or deviations (note if a test passed with caveats)
- Whisper model version used (check: `uv run python3 -c "import whisper; print(whisper.__version__)"`)
- Claude model used (currently `claude-sonnet-4-6`)
