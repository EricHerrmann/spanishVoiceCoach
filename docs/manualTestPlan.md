# duoVoiceCoach — Manual Test Plan: Phases 0–5

**Purpose:** Step-by-step test procedures for phase gate sign-offs. Phases 0–5 are complete and passed. Record results in `manualTestLog.md`.

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
uv run --env-file .env pytest -v
```

**Pass:** All 6 tests collected and pass. Output ends with `X passed`.
**Fail:** Any test fails or errors.

---

### MT-0-2: Backend health endpoint responds

```bash
# Terminal 1 — start backend
uv run --env-file .env uvicorn backend.main:app --reload --port 8001

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
uv run --env-file .env uvicorn backend.main:app --reload --port 8001

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173` in a browser.

---

### MT-1-1: Automated tests pass

```bash
uv run --env-file .env pytest -v
cd frontend && npm test
```

**Pass:** All 21 backend tests and 12 frontend tests pass.
**Fail:** Any failure or error.

---

### MT-1-2: UI renders correctly in idle state

Open `http://localhost:5173`.

**Check:**
- [x] Page title "duoVoiceCoach" is visible
- [x] A button is present with text indicating it starts recording ("Start Speaking" or similar)
- [x] Transcript area is present and empty
- [x] No error messages visible
- [x] No browser console errors

**Pass:** All checks above satisfied.

---

### MT-1-3: Basic recording flow

1. Click the record button.

**Check during recording:**
- [x] Button text changes to "Stop Recording" (or similar)
- [x] Browser prompts for mic permission (first time only)

2. Say "Hola, ¿cómo estás?" clearly into the microphone.
3. Click "Stop Recording".

**Check during processing:**
- [x] Button becomes disabled with "Processing..." text

**Check after completion:**
- [x] Button returns to idle state ("Start Speaking")
- [x] Your transcription appears in the transcript area
- [x] `transcript_norm` displayed is lowercase with punctuation removed (e.g., `hola ¿cómo estás?` → `hola cómo estás` or similar)
- [x] A coach echo entry appears in the transcript (coach repeating back what was said)
- [x] Browser speaks the echo aloud via `speechSynthesis`

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
- [x] All three user turns appear in the transcript, oldest first
- [x] Each user turn is followed by a coach echo entry
- [x] Transcript does not reset between turns

**Pass:** 6 entries total (3 user, 3 coach) visible in correct order.

---

### MT-1-6: Error handling — mic permission denied

1. In browser settings, block microphone access for `localhost`.
2. Click the record button.

**Check:**
- [x] Button returns to idle state (does not stay in recording or processing)
- [x] A retry/error message appears in the UI (e.g., "try again" or similar)
- [x] No unhandled exceptions in browser console

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
- [x] Browser speaks the text (any voice — quality may be robotic)
- [x] Language sounds Spanish (or at least not English gibberish)
- [x] Playback completes and button returns to idle state

**Pass:** Audio plays and button recovers.
**Fail:** Silent, button stuck in "Playing..." state.

---

---

## Phase 2 — AI Conversation Core

### Prerequisites

- `.env` contains `ANTHROPIC_API_KEY` (real key required for live Claude checks)
- Backend running on port 8001, frontend on 5173

### Setup

Start both servers in separate terminals:

```bash
# Terminal 1 — backend
uv run --env-file .env uvicorn backend.main:app --reload --port 8001

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`.

---

### MT-2-1: Automated tests pass

```bash
uv run --env-file .env pytest -v
cd frontend && npm test -- --run
```

**Pass:** Backend and frontend suites pass. The backend reads `ANTHROPIC_API_KEY` from `.env`; live API-key-gated checks run when the key is real and are skipped only when the key is absent or dummy.
**Fail:** Any failure or error.

---

### MT-2-2: Session initialises on page load

Open `http://localhost:5173`. In the browser DevTools Network tab, verify:

- [x] A `POST /session/start` request fires immediately on page load
- [x] The response is `200` with body `{"session_id": "<uuid>"}`
- [x] No error message appears in the UI

**Pass:** `/session/start` called once on load, `session_id` received silently.
**Fail:** Network error, 500, or error message in UI.

---

### MT-2-3: First Spanish turn gets a real coach reply

1. Click the record button.
2. Say "Hola, me gustaría practicar español" clearly.
3. Click Stop.

**Check:**
- [x] Your transcript appears in the conversation panel
- [x] A coach reply appears below it (Spanish text, not an echo of what you said)
- [x] Browser speaks the coach reply aloud in Spanish
- [x] Button returns to idle state

**Pass:** Distinct Spanish reply from Claude visible and spoken.
**Fail:** Echo of user speech, empty reply, or error message.

---

### MT-2-4: Coach replies are contextually appropriate for level 5

Conduct a short exchange on the default topic (general, level 5):

1. Say "¿Qué puedo hacer en el mercado?"
2. Wait for reply. Say "Quiero comprar frutas y verduras."
3. Wait for reply.

**Check:**
- [x] Replies are in Spanish throughout
- [x] Vocabulary is intermediate (not baby-talk, not academic)
- [x] Coach does not spontaneously correct your grammar (on_demand mode is default)
- [x] Each reply is contextually relevant to what you said

**Pass:** Two coherent in-context Spanish replies.
**Fail:** English reply, off-topic reply, or unsolicited grammar corrections.

---

### MT-2-5: Conversation history is maintained across turns

Continue the session from MT-2-4 (do not refresh the page):

1. Say "¿Y qué más puedo hacer allí?"

**Check:**
- [x] The coach's reply references the conversation context (market, fruit/vegetables) rather than starting fresh
- [x] All prior turns still visible in the transcript

**Pass:** Coach reply shows awareness of prior exchange.
**Fail:** Coach ignores context, asks "How can I help you?" again, or transcript resets.

---

### MT-2-6: AI error path — `/turn` with invalid session_id via curl

In a terminal (backend must be running):

```bash
curl -si -X POST http://localhost:8001/turn \
  -F "audio=@tests/fixtures/hola_sample.wav;type=audio/wav" \
  -F "session_id=invalid-id"
```

**Expected output includes:**
```
HTTP/1.1 404 Not Found
...
{"detail":"Session not found"}
```

**Pass:** Status line shows `404 Not Found`.
**Fail:** 200, 500, or connection error.

---

### MT-2-7: Full response structure via curl

> **Run from the repo root** (`duoVoiceCoach/`) — the fixture path is relative to the project root.

```bash
# Capture and inspect session-start JSON
START_RESPONSE=$(curl -s -X POST http://localhost:8001/session/start)
printf '%s\n' "$START_RESPONSE" | python3 -m json.tool

# Parse the session id from the inspected response
SESSION=$(printf '%s\n' "$START_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "$SESSION"

# Inspect the captured session JSON
curl -s "http://localhost:8001/sessions/$SESSION" | python3 -m json.tool

# Submit a turn
curl -s -X POST http://localhost:8001/turn \
  -F "audio=@tests/fixtures/hola_sample.wav;type=audio/wav" \
  -F "session_id=$SESSION" | python3 -m json.tool
```

**Expected session-start response:**
```json
{
  "session_id": "<uuid>"
}
```

**Expected captured session fields before submitting a turn:** `id` equals `$SESSION`; `topic`, `level`, `ai_provider`, and `coaching_mode` are present; `turns` is an empty array.

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

## Phase 3 — Coaching Layer

### Prerequisites

- `.env` contains `ANTHROPIC_API_KEY` (real key required for live Claude checks)
- Backend running on port 8001, frontend on 5173

### Setup

```bash
# Terminal 1 — backend
uv run --env-file .env uvicorn backend.main:app --reload --port 8001

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`.

---

### MT-3-1: Automated tests pass

```bash
uv run --env-file .env pytest -v
cd frontend && npm test -- --run
```

**Pass:** Backend and frontend suites pass. The backend reads `ANTHROPIC_API_KEY` from `.env`; live API-key-gated checks run when the key is real and are skipped only when the key is absent or dummy.
**Fail:** Any failure or error.

---

### MT-3-2: SessionConfig renders correctly

Open `http://localhost:5173`.

**Check:**
- [x] A "Coaching mode" label and dropdown are visible
- [x] Dropdown shows three options: "On demand", "Explicit", "Shadowing"
- [x] Default selected is "On demand"

**Pass:** All checks satisfied.

---

### MT-3-3: on_demand mode — no automatic corrections

1. Ensure dropdown is set to "On demand".
2. Say "Yo quiero ir al mercado." (deliberate use of optional pronoun).
3. Wait for the coach reply.

**Check:**
- [x] Coach replies in Spanish
- [x] No correction overlay appears
- [x] Transcript shows user turn and coach reply normally

**Pass:** No correction overlay visible.
**Fail:** Correction overlay appears without the user asking.

---

### MT-3-4: on_demand mode — corrections surface on request

Continuing the same session from MT-3-3:

1. Say "Corrígeme, yo quiero ir al mercado."
2. Wait for the coach reply.

**Check:**
- [x] A correction overlay appears below the VoiceButton
- [x] Overlay shows at least one correction with original text, corrected text, and explanation
- [x] Coach reply is spoken aloud

**Pass:** Overlay visible with correction fields populated.
**Fail:** No overlay, or overlay appears with blank fields.

---

### MT-3-5: explicit mode — automatic corrections appear

1. Change dropdown to "Explicit". Wait 2 seconds for new session to initialise.
2. Say "Yo quiero ir al mercado."
3. Wait for reply.

**Check:**
- [x] Coach replies in Spanish
- [x] A correction overlay appears (Claude flagging the optional "yo")
- [x] Correction fields (original, corrected, explanation) are all populated

**Pass:** Overlay visible after turn in explicit mode.
**Fail:** No overlay despite speaking with a known error.

Note: If Claude doesn't flag "yo quiero" as an error, try a clearer error like "Ayer yo come tacos" (wrong tense).

---

### MT-3-6: shadowing mode — no overlay, error woven into reply

1. Change dropdown to "Shadowing". Wait 2 seconds for new session.
2. Say "Yo quiero ir al mercado."
3. Wait for reply.

**Check:**
- [x] No correction overlay appears
- [x] Coach reply may naturally model the correct form ("quiero ir") in its response
- [x] Conversation flows naturally

**Pass:** No overlay. Coach reply is natural Spanish.
**Fail:** Overlay appears in shadowing mode.

---

### MT-3-7: Mode change resets session

1. Set mode to "Explicit", complete one turn, note the transcript content.
2. Change dropdown to "Shadowing".

**Check:**
- [x] Transcript clears (new session started)
- [x] CoachOverlay clears
- [x] New turn works normally in shadowing mode (no overlay)

**Pass:** Session resets on mode change; new turns work in new mode.
**Fail:** Old transcript persists, or new session fails to start.

---

### MT-3-8: Full response structure via curl (explicit mode)

> **Run from the repo root** (`duoVoiceCoach/`) — the fixture path is relative to the project root.

```bash
# Capture and inspect session-start JSON
START_RESPONSE=$(curl -s -X POST http://localhost:8001/session/start \
  -H "Content-Type: application/json" \
  -d '{"coaching_mode": "explicit"}')
printf '%s\n' "$START_RESPONSE" | python3 -m json.tool

# Parse the session id from the inspected response
SESSION=$(printf '%s\n' "$START_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "$SESSION"

# Inspect the captured session JSON
curl -s "http://localhost:8001/sessions/$SESSION" | python3 -m json.tool

# Submit a turn
curl -s -X POST http://localhost:8001/turn \
  -F "audio=@tests/fixtures/hola_sample.wav;type=audio/wav" \
  -F "session_id=$SESSION" | python3 -m json.tool
```

**Expected session-start response:**
```json
{
  "session_id": "<uuid>"
}
```

**Expected captured session fields before submitting a turn:** `id` equals `$SESSION`; `coaching_mode` is `"explicit"`; `turns` is an empty array.

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

**Pass:** All five keys present; `coach_text` is non-empty; `error` is null.
**Fail:** Missing keys or non-null error.

---

## Phase 4 — Session Config UI

### Prerequisites

- `.env` contains `ANTHROPIC_API_KEY`
- Backend running on port 8001, frontend on 5173
- Run from the repo root (`duoVoiceCoach/`) for all curl commands

### Setup

```bash
# Terminal 1 — backend
uv run --env-file .env uvicorn backend.main:app --reload --port 8001

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`.

---

### MT-4-1: Automated tests pass

```bash
uv run --env-file .env pytest -v
cd frontend && npm test -- --run
```

**Pass:** Backend and frontend suites pass. The backend reads `ANTHROPIC_API_KEY` from `.env`; live API-key-gated checks run when the key is real and are skipped only when the key is absent or dummy.
**Fail:** Any failure or error.

---

### MT-4-2: SessionConfig renders all controls

Open `http://localhost:5173`.

**Check:**
- [x] "Topic" label and dropdown visible; preset options present; last option is "Custom…"
- [x] Selected preset topic's Spanish starter phrase is visible beneath the topic dropdown
- [x] "Level: 5" label and slider visible; slider moves between 1 and 10
- [x] "Provider" label and dropdown visible; shows "Claude (Anthropic)" only
- [x] "Coaching mode" label and dropdown visible; three options present
- [x] "New Conversation" button visible and enabled

**Pass:** All controls visible and interactive.

---

### MT-4-3: Topic picker — preset and custom

1. Open the Topic dropdown and select "Ordering food".

**Check:**
- [x] Dropdown shows "Ordering food" selected
- [x] Starter phrase updates to "Hola, ¿qué me recomiendas del menú?"
- [x] No text input appears beneath the dropdown

2. Select "Custom…".

**Check:**
- [x] A text input appears beneath the dropdown
- [x] Preset starter phrase is hidden
- [x] Type "cooking at home" into the input

**Pass:** Preset selection is clean; Custom reveals text input.

---

### MT-4-4: Level slider

1. Drag the Level slider to position 8.

**Check:**
- [x] Label updates to "Level: 8"
- [x] Band labels beneath the slider are visible (Beginner · Elementary · Intermediate · Advanced)

**Pass:** Slider moves and label updates.

---

### MT-4-5: Provider dropdown shows only Claude

**Check:**
- [x] "Claude (Anthropic)" is the only option in the Provider dropdown

**Pass:** No other providers visible.

---

### MT-4-6: New Conversation starts a fresh session with selected config

1. Complete one turn in the default session (say anything in Spanish).
2. Change Topic to "Ordering food", Level to 3, Coaching mode to "Explicit".
3. Click "New Conversation".

**Check:**
- [x] Transcript clears
- [x] CoachOverlay clears
- [x] New turn uses the selected topic and level (coach should respond with simpler vocabulary appropriate for level 3)

**Pass:** Session resets; new config takes effect.

---

### MT-4-7: `/topics` and `/providers` via curl

> **Run from the repo root** (`duoVoiceCoach/`).

```bash
curl -s http://localhost:8001/topics | python3 -m json.tool
curl -s http://localhost:8001/providers | python3 -m json.tool
```

**Expected for /topics:** Array of objects each with `id`, `label`, `starter`. `general` entry present.
**Expected for /providers:** `[{"id": "claude", "label": "Claude (Anthropic)"}]`

**Pass:** Both responses are valid JSON matching the above structure.

---

### MT-4-8: Full `/session/start` with config via curl

> **Run from the repo root** (`duoVoiceCoach/`).

```bash
START_RESPONSE=$(curl -s -X POST http://localhost:8001/session/start \
  -H "Content-Type: application/json" \
  -d '{"topic": "ordering_food", "level": 3, "ai_provider": "claude", "coaching_mode": "explicit"}')
printf '%s\n' "$START_RESPONSE" | python3 -m json.tool

SESSION=$(printf '%s\n' "$START_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

echo "$SESSION"
curl -s "http://localhost:8001/sessions/$SESSION" | python3 -m json.tool

curl -s -X POST http://localhost:8001/turn \
  -F "audio=@tests/fixtures/hola_sample.wav;type=audio/wav" \
  -F "session_id=$SESSION" | python3 -m json.tool
```

**Expected session-start response:** JSON object with `session_id`.
**Expected captured session fields before submitting a turn:** `id` equals `$SESSION`; `topic` is `"ordering_food"`; `level` is `3`; `ai_provider` is `"claude"`; `coaching_mode` is `"explicit"`; `turns` is an empty array.

**Pass:** `$SESSION` is a UUID; captured session fields match the request; turn response has all five keys (`transcript_raw`, `transcript_norm`, `coach_text`, `corrections`, `error: null`).
**Fail:** Empty `$SESSION`, missing keys, or non-null error.

---

## Phase 5 — Persistence & Session History

### Prerequisites

- `.env` contains `ANTHROPIC_API_KEY`
- Backend running on port 8001, frontend on 5173
- Run from the repo root (`duoVoiceCoach/`) for all curl commands
- Phase 5 uses an explicit test persistence directory: `/tmp/duoVoiceCoach-manual`. Use the same `DVC_DATA_DIR` every time you start or restart the backend during this phase.

### Setup

Run these from the repo root unless noted.

```bash
# Terminal 1 — backend
export DVC_DATA_DIR=/tmp/duoVoiceCoach-manual
mkdir -p "$DVC_DATA_DIR"
echo "$DVC_DATA_DIR"
uv run --env-file .env uvicorn backend.main:app --reload --port 8001
```

The `echo "$DVC_DATA_DIR"` command should print:

```text
/tmp/duoVoiceCoach-manual
```

Keep Terminal 1 open. In Terminal 2, use the same directory variable for curl/file checks:

```bash
cd ~/projects/duoVoiceCoach
export DVC_DATA_DIR=/tmp/duoVoiceCoach-manual
echo "$DVC_DATA_DIR"
```

From Terminal 2, start the frontend:

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173`.

---

### MT-5-1: Automated tests pass

```bash
uv run --env-file .env pytest -v
cd frontend && npm test -- --run
```

**Pass:** Backend and frontend suites pass. The backend reads `ANTHROPIC_API_KEY` from `.env`; live API-key-gated checks run when the key is real and are skipped only when the key is absent or dummy.
**Fail:** Any failure or error.

---

### MT-5-2: Session JSON is persisted on start

Start a session through the backend:

```bash
START_RESPONSE=$(curl -s -X POST http://localhost:8001/session/start \
  -H "Content-Type: application/json" \
  -d '{"topic": "general", "level": 5, "ai_provider": "claude", "coaching_mode": "on_demand"}')
printf '%s\n' "$START_RESPONSE" | python3 -m json.tool

SESSION=$(printf '%s\n' "$START_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

echo "$SESSION"
curl -s "http://localhost:8001/sessions/$SESSION" | python3 -m json.tool
```

**Check:**
- [x] `$SESSION` is a UUID
- [x] Session-start inspection returns a JSON object with `session_id`
- [x] Captured session inspection shows `id` equal to `$SESSION`
- [x] Captured session inspection shows `topic: "general"`, `level: 5`, `ai_provider: "claude"`, `coaching_mode: "on_demand"`, and `turns: []`
- [x] `echo "$DVC_DATA_DIR"` prints `/tmp/duoVoiceCoach-manual`
- [x] A JSON file exists:

```bash
test -f "$DVC_DATA_DIR/sessions/$SESSION.json" && echo "session file exists"
```

**Pass:** Session file exists immediately after `/session/start`.

---

### MT-5-3: `/sessions` lists saved session summaries

```bash
curl -s http://localhost:8001/sessions | python3 -m json.tool
```

**Expected:** Array of summaries with `id`, `started_at`, `topic`, `level`, `ai_provider`, `coaching_mode`, `turn_count`, and `correction_count`.

**Pass:** Newly created session appears in the list.

---

### MT-5-4: Full session survives backend restart

1. Complete one spoken turn in the browser.
2. Stop the backend server.
3. Restart the backend server with the same `DVC_DATA_DIR`:

```bash
export DVC_DATA_DIR=/tmp/duoVoiceCoach-manual
echo "$DVC_DATA_DIR"
uv run --env-file .env uvicorn backend.main:app --reload --port 8001
```

4. Load the saved session:

```bash
curl -s http://localhost:8001/sessions/$SESSION | python3 -m json.tool
```

**Check:**
- [x] Response has the same `id`
- [x] `turns` contains the user and coach turns
- [x] User turn includes `transcript_raw` and `transcript_norm`
- [x] Coach turn includes `coach_text`
- [x] `echo "$DVC_DATA_DIR"` still prints `/tmp/duoVoiceCoach-manual`

**Pass:** Transcript data remains after restart.

---

### MT-5-5: Frontend session history can review a saved session

1. Open `http://localhost:5173`.
2. Complete one spoken turn.
3. Click "Refresh" in Session history if needed.
4. Click the saved session row.

**Check:**
- [x] Session history shows topic, level, mode, turn count, and correction count
- [x] Clicking a saved session restores its transcript
- [x] Session config updates to match the saved session

**Pass:** Past session can be reviewed from the UI.

---

### MT-5-6: Audio retention is opt-in

With default config (`DVC_SAVE_AUDIO` unset or false):

```bash
curl -s http://localhost:8001/sessions/$SESSION | python3 -m json.tool
```

**Check:**
- [x] User turn `audio_file` is `null`

Restart backend with `DVC_SAVE_AUDIO=true` and the same `DVC_DATA_DIR`, complete a new turn, then reload that session.

```bash
export DVC_DATA_DIR=/tmp/duoVoiceCoach-manual
export DVC_SAVE_AUDIO=true
echo "$DVC_DATA_DIR"
uv run --env-file .env uvicorn backend.main:app --reload --port 8001
```

**Check:**
- [x] User turn `audio_file` contains a path under `/tmp/duoVoiceCoach-manual/audio/`
- [x] The referenced WAV file exists

**Pass:** Audio files are saved only when explicitly enabled.

---

## Sign-Off Checklist

Before recording sign-off in `manualTestLog.md`, confirm:

- [x] MT-0-1 through MT-0-4 all passed (Phase 0)
- [x] MT-1-1 through MT-1-8 all passed (Phase 1)
- [x] MT-2-1 through MT-2-7 all passed (Phase 2)
- [x] MT-3-1 through MT-3-8 all passed (Phase 3)
- [x] MT-4-1 through MT-4-8 all passed (Phase 4)
- [x] MT-5-1 through MT-5-6 all passed (Phase 5)
- [x] No unexpected browser console errors observed during any test
- [x] No unhandled exceptions in backend terminal output during any test

**Current sign-off status:** Phases 0–5 passed on 2026-04-21 and are recorded in `docs/manualTestLog.md`. Ready to proceed to Phase 6.

Record in `docs/manualTestLog.md`:
- Date tested
- Tester name / email
- Any observed issues or deviations (note if a test passed with caveats)
- Whisper model version used (check: `uv run --env-file .env python3 -c "import whisper; print(whisper.__version__)"`)
- Claude model used (currently `claude-sonnet-4-6`)
