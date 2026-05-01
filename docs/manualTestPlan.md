# duoVoiceCoach — Manual Test Plan

**Purpose:** Step-by-step test procedures for phase gate sign-offs. Record results in `manualTestLog.md`.

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

The three coaching modes work as follows:

- **On demand** — the coach stays quiet about errors and keeps the conversation flowing. If you want feedback, just ask mid-sentence (e.g. "corrígeme" or "was that right?") and the coach will review that turn.
- **Explicit** — the coach flags every grammar or vocabulary mistake after each turn, whether you asked or not. Good for deliberate practice where you want a running account of errors.
- **Shadowing** — the coach never breaks out corrections. Instead, when it detects a mistake, it naturally uses the correct form in its reply — you absorb the right usage through context rather than explicit feedback.

**Check:**
- [x] A "Coaching mode" label and dropdown are visible
- [x] Dropdown shows three options: "On demand", "Explicit", "Shadowing"
- [x] Default selected is "On demand"

**Pass:** All checks satisfied.

---

### MT-3-3: on_demand mode — coach stays silent on errors unprompted

1. Ensure dropdown is set to "On demand".
2. Say "Yo quiero ir al mercado." (deliberate use of optional pronoun).
3. Wait for the coach reply.

**Check:**
- [x] Coach replies in Spanish and keeps the conversation going
- [x] No correction overlay appears — the coach did not volunteer feedback
- [x] Transcript shows user turn and coach reply normally

**Pass:** No correction overlay visible.
**Fail:** Correction overlay appears even though you didn't ask for feedback.

---

### MT-3-4: on_demand mode — corrections appear when you ask

Continuing the same session from MT-3-3:

1. Say "Corrígeme, yo quiero ir al mercado."
2. Wait for the coach reply.

**Check:**
- [x] A correction overlay appears below the VoiceButton
- [x] Overlay shows at least one correction with original text, corrected text, and explanation
- [x] Coach reply is spoken aloud

**Pass:** Overlay visible with correction fields populated.
**Fail:** No overlay after explicitly requesting feedback, or overlay appears with blank fields.

---

### MT-3-5: explicit mode — every error flagged automatically

1. Change dropdown to "Explicit". Wait 2 seconds for new session to initialise.
2. Say "Yo quiero ir al mercado."
3. Wait for reply.

**Check:**
- [x] Coach replies in Spanish
- [x] A correction overlay appears without you having to ask (Claude flagging the optional "yo")
- [x] Correction fields (original, corrected, explanation) are all populated

**Pass:** Overlay visible automatically after the turn.
**Fail:** No overlay despite speaking with a known error.

Note: If Claude doesn't flag "yo quiero", try a more obvious error like "Ayer yo come tacos" (present tense instead of past).

---

### MT-3-6: shadowing mode — no overlay, correct form absorbed through conversation

1. Change dropdown to "Shadowing". Wait 2 seconds for new session.
2. Say "Yo quiero ir al mercado."
3. Wait for reply.

**Check:**
- [x] No correction overlay appears — the coach never breaks out explicit feedback
- [x] The coach reply may use the correct form naturally (e.g. "quiero ir al mercado también") without labelling it as a correction
- [x] Conversation continues without interruption

**Pass:** No overlay. Coach reply is natural, flowing Spanish.
**Fail:** Overlay appears — corrections should never surface in shadowing mode.

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

## Phase 7 — Android / PWA

### Prerequisites

- Android device with Chrome (version 89+)
- ngrok installed on the laptop: https://ngrok.com/download (free account sufficient)
- `.env` contains `ANTHROPIC_API_KEY` (and optionally `ELEVENLABS_API_KEY`)
- Both laptop and Android device connected to the internet (ngrok handles the tunnel)

### Setup

```bash
# Step 1 — build the frontend (required; backend serves the built dist/)
cd frontend && npm run build && cd ..

# Step 2 — start the backend (Terminal 1)
uv run --env-file .env uvicorn backend.main:app --host 0.0.0.0 --port 8001

# Step 3 — start ngrok (Terminal 2)
ngrok http 8001
```

Copy the `https://...` URL printed by ngrok (e.g. `https://abc123.ngrok-free.app`). Use this URL for all Android tests below. The URL changes each ngrok session on the free plan.

---

### MT-7-1: Automated tests pass

```bash
uv run --env-file .env pytest -v
cd frontend && npm test -- --run
```

**Pass:** All backend and frontend tests pass. 2 skipped Whisper live tests are acceptable.
**Fail:** Any test failure or error.

---

### MT-7-2: Backend serves frontend build as static files

With the backend running and frontend built:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/
```

**Expected output:** `200`

Also open `http://localhost:8001` in a desktop browser.

**Check:**
- [ ] App loads at the backend port (no separate frontend dev server needed)
- [ ] Transcript, VoiceButton, SessionConfig all render
- [ ] No console errors

**Pass:** App fully functional served from backend port alone.
**Fail:** 404, blank page, or console errors.

---

### MT-7-3: PWA manifest and service worker present

```bash
curl -s http://localhost:8001/manifest.json | python3 -m json.tool
```

**Expected:** JSON with at minimum `name`, `short_name`, `start_url`, `display: "standalone"`, and `icons`.

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/sw.js
```

**Expected output:** `200`

**Pass:** Both resources return 200 with valid content.
**Fail:** 404 for either resource.

---

### MT-7-4: App loads on Android Chrome over ngrok

On the Android device:

1. Open Chrome.
2. Navigate to the ngrok HTTPS URL (e.g. `https://abc123.ngrok-free.app`).

**Check:**
- [ ] App loads without a blank screen or security warning
- [ ] VoiceButton, SessionConfig, and Transcript are all visible
- [ ] No JavaScript errors in Chrome DevTools remote debug (optional but preferred)

**Pass:** App renders correctly on Android Chrome.
**Fail:** Blank screen, security error, or missing components.

---

### MT-7-5: Mic capture works on Android

On the Android device (ngrok URL open in Chrome):

1. Click the voice button.
2. When Chrome prompts for microphone permission, tap **Allow**.
3. Say "Hola, ¿cómo estás?" clearly.
4. Tap the button again to stop recording.

**Check:**
- [ ] Button transitions: idle → recording → processing → playing → idle
- [ ] Your transcript appears in the conversation panel
- [ ] Coach reply appears below it
- [ ] Coach reply is spoken aloud (browser TTS or ElevenLabs)

**Pass:** Full voice round-trip works on Android.
**Fail:** Mic permission denied (check Chrome site settings), silent recording, empty transcript, or no coach reply.

---

### MT-7-6: Touch targets are adequately sized

On the Android device, verify the voice button is comfortably tappable:

- [ ] Button is large enough to tap confidently without zooming (minimum ~48×48dp visual size)
- [ ] No accidental taps on adjacent elements when targeting the button

**Pass:** Button is easily tappable on a standard Android screen.
**Fail:** Button is too small or taps miss consistently.

---

### MT-7-7: PWA install to home screen

On the Android device in Chrome:

1. Tap the browser menu (⋮).
2. Tap **Add to Home screen** (or **Install app** if the banner appears).
3. Confirm the install.
4. Open the installed PWA from the home screen.

**Check:**
- [ ] App opens in standalone mode (no Chrome address bar visible)
- [ ] Full voice session works from the installed PWA (repeat MT-7-5 steps)

**Pass:** PWA installs and functions in standalone mode.
**Fail:** "Add to Home screen" option missing, or app opens in browser tab instead of standalone.

Note: The "Add to Home screen" option requires a valid `manifest.json` and service worker (verified in MT-7-3). If the option is missing, check that the ngrok URL is HTTPS and MT-7-3 passed.

---

### MT-7-8: Multiple turns on Android

Conduct a 3-turn conversation on the Android device:

1. Speak turn 1 (any Spanish sentence).
2. Wait for the coach reply and TTS playback to finish.
3. Speak turn 2 ("Quiero practicar más.").
4. Wait for reply.
5. Speak turn 3 ("Corrígeme, yo fui al mercado.").
6. Wait for reply.

**Check:**
- [ ] All 3 user turns and 3 coach replies visible in transcript
- [ ] Turn 3 triggers corrections (on_demand mode, phrase "corrígeme" detected)
- [ ] Correction overlay visible after turn 3
- [ ] No UI freezes or layout shifts between turns

**Pass:** 3-turn session completes without issues.
**Fail:** Freeze after any turn, missing transcript entries, or correction not triggered.

---

## Sign-Off Checklist

Before recording sign-off in `manualTestLog.md`, confirm:

- [x] MT-0-1 through MT-0-4 all passed (Phase 0)
- [x] MT-1-1 through MT-1-8 all passed (Phase 1)
- [x] MT-2-1 through MT-2-7 all passed (Phase 2)
- [x] MT-3-1 through MT-3-8 all passed (Phase 3)
- [x] MT-4-1 through MT-4-8 all passed (Phase 4)
- [x] MT-5-1 through MT-5-6 all passed (Phase 5)
- [x] MT-6-1 through MT-6-7 all passed (Phase 6)
- [ ] MT-7-1 through MT-7-8 all passed (Phase 7)
- [x] Phase 8 smoke test passed (refactor — no regressions, 93 backend / 47 frontend)
- [x] Phase 9 smoke test passed (two-pane layout, collapsible config, CoachOverlay auto-dismiss, mobile drawer)
- [ ] No unexpected browser console errors observed during any test
- [ ] No unhandled exceptions in backend terminal output during any test

**Current sign-off status:** Phases 0–6, 8, and 9 passed and recorded in `docs/manualTestLog.md`. Phase 7 Android/PWA manual smoke test pending (Android device test required).

Record in `docs/manualTestLog.md`:
- Date tested
- Tester name / email
- Any observed issues or deviations (note if a test passed with caveats)
- Whisper model version used (check: `uv run --env-file .env python3 -c "import whisper; print(whisper.__version__)"`)
- Claude model used (currently `claude-sonnet-4-6`)

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

Start backend and frontend:

```bash
# Terminal 1 — backend
uv run --env-file .env uvicorn backend.main:app --reload --port 8001

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`.

### MT-6-1: Automated tests pass

```bash
uv run --env-file .env pytest -v
cd frontend && npm test -- --run
```

Expected: all backend tests pass; all frontend tests pass (≥ 46).

### MT-6-2: `/tts-voices` route returns curated list

```bash
curl -s http://localhost:8001/tts-voices | python3 -m json.tool
```

Expected: JSON array with 4 voice objects, each with `id`, `label`, `description`.

### MT-6-3: Browser TTS still works (regression)

1. Backend and frontend already running from Setup above
2. Open http://localhost:5173
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

1. Temporarily remove `ELEVENLABS_API_KEY` from `.env` and restart backend (`uv run --env-file .env uvicorn backend.main:app --reload --port 8001`)
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

---

## Phase 8 — Code Review & Refactor

**Goal:** Verify no regressions after refactor fixes.

### Pre-conditions
- Backend running: `uv run --env-file .env uvicorn backend.main:app --reload --port 8001`
- Frontend running: `npm run dev` (or served from FastAPI dist)
- All backend + frontend automated tests pass

### Smoke Test Steps

1. Open the app in Chrome at `http://localhost:5173` (or `http://localhost:8001` if using FastAPI static serve)
2. Verify the page loads with no console errors
3. Start a new session (topic: Ordering food, level 5, coaching mode: On-demand, TTS: Browser)
4. Record: "Hola, quiero ordenar una mesa para dos personas"
5. Verify: transcript appears, coach responds in Spanish, browser TTS plays the reply
6. Record: "¿Corrígeme si digo algo mal?"
7. Verify: coach responds and corrections overlay appears (on-demand trigger phrase detected)
8. Click "New Conversation", select a different topic, verify session resets cleanly
9. Open Session History, verify the previous session appears with the correct turn count
10. Click the previous session to reload it; verify transcript restores correctly

### Pass Criteria
- No console errors throughout
- Voice round-trip works end-to-end (mic → transcription → coach response → TTS playback)
- Corrections overlay appears on step 6
- Session history shows correct entry after new session
- Session reload restores transcript

### Sign-off
Record date, tester, and any deviations in `docs/manualTestLog.md`.

---

## Phase 9 — GUI Layout Redesign

**Goal:** Verify the two-pane desktop layout renders and functions correctly.

### Desktop layout
1. Open the app at the dev URL (frontend: `npm run dev` in `frontend/`, backend: `uv run --env-file .env uvicorn backend.main:app --reload --port 8001`)
2. Confirm left pane (~65% width) shows the transcript area with VoiceButton pinned to the bottom
3. Confirm right pane (~35% width) shows: collapsed Session Config, Corrections area, Session History

### Session Config collapsible
4. Click the "Session Config" summary row — confirm it expands to reveal all config fields
5. Click again — confirm it collapses

### Transcript bubbles
6. Complete a voice turn (speak → process → coach responds)
7. Confirm your utterance appears as a right-aligned bubble
8. Confirm coach response appears as a left-aligned bubble

### CoachOverlay auto-dismiss
9. Trigger a correction (speak with a deliberate error in Explicit coaching mode)
10. Confirm the corrections panel appears in the right pane
11. Wait ~8 seconds — confirm it disappears automatically

### Mobile/Android drawer (≤768px)
12. Resize browser to ≤768px width or open on Android Chrome
13. Confirm the right pane collapses to a 48px bottom bar showing "▲ Tools"
14. Tap the bar — confirm the drawer opens to ~60% of viewport height
15. Confirm all right-pane content (Session Config, Corrections, Session History) is accessible in the drawer
16. Confirm the left pane (transcript + voice button) remains accessible above the drawer

### Regression
17. Complete a full 3-turn Spanish voice session — confirm all existing functionality works (mic → STT → Claude → TTS → corrections)

---

## Phase A — Flashcards + Translation

**Goal:** Verify both new practice modes work correctly and that the tab nav switches the left pane without breaking the conversation pipeline.

### Prerequisites

Start backend and frontend:
```bash
# Terminal 1
uv run --env-file .env uvicorn backend.main:app --reload --port 8001
# Terminal 2
cd frontend && npm run dev
```

Open `http://localhost:5173`.

### Tab navigation

1. Confirm four tabs in the app header: Conversation, Flashcards, Translation, Pronunciation
2. Click each tab — confirm the left pane content switches; right pane (Session Config, Coach Overlay, Session History) is unchanged
3. Confirm the active tab is highlighted

### Flashcards

4. Click the Flashcards tab
5. Select a topic from the dropdown (e.g. General)
6. Click a level band (e.g. Beginner)
7. Confirm a card appears showing an English word or phrase
8. Click the card — confirm it flips to show the Spanish translation
9. Click Next — confirm the next card appears with the English side showing (flip state reset)
10. Click Previous — confirm it returns to the previous card; Previous is disabled on the first card
11. Advance through all cards — confirm "Deck complete" message appears
12. Click Restart — confirm the deck resets to the first card
13. Change topic or level band — confirm the deck reloads

### Translation

14. Click the Translation tab
15. Click "Record English phrase"
16. Say an English phrase (e.g. "Where is the library?")
17. Click Stop Recording
18. Confirm the English transcription appears above the Spanish translation
19. Confirm TTS plays the Spanish translation
20. Record a second phrase — confirm the previous result is replaced

### Regression

21. Click the Conversation tab and complete a full voice session — confirm all existing functionality works

---

## Phase B — Pronunciation Practice

**Goal:** Verify all three pronunciation sub-features function correctly and that sub-feature C correctly hands phrases across mode boundaries.

> **Prerequisite:** Phase A must be implemented and passing before running the Vocabulary tab tests (steps 1–6 below). Phase A provides the `/flashcards/deck` endpoint and the NavTabs component that the vocabulary tab and step 11 depend on. The Challenges tab (steps 7–10) and Sub-feature C (steps 11–16) can be tested independently once Phase A's tab nav exists.

### Prerequisites

Start backend and frontend:
```bash
# Terminal 1
uv run --env-file .env uvicorn backend.main:app --reload --port 8001
# Terminal 2
cd frontend && npm run dev
```

Open `http://localhost:5173`.

### Vocabulary tab

1. Click the Pronunciation tab in the left-pane header — confirm Vocabulary sub-tab is active by default
2. Select a topic from the dropdown and a level band (e.g. Beginner)
3. Confirm a Spanish word or phrase appears as the target in the center card
4. Click Record and say the target phrase aloud
5. Click Stop — confirm score (0–100), feedback text, and any sound issues appear below the card
6. Click Next card — confirm a new target appears and the scoring area resets

### Challenges tab

7. Click the Challenges sub-tab — confirm a list of phonetic challenges appears
8. Click any challenge (e.g. "perro") — confirm target phrase and hint text appear
9. Record the phrase — confirm score and feedback appear
10. Click ← Challenges — confirm the challenge list reappears

### Sub-feature C — Practice from conversation

11. Click the Conversation tab (or home icon) to return to conversation mode
12. Conduct a short session (2–3 voice turns) — confirm coach responses appear in the transcript
13. Locate a coach turn bubble — confirm a small "Practice" button appears in the turn header
14. Click Practice — confirm the app switches to the Pronunciation tab showing "From conversation" header and the coach's exact phrase as the target
15. Record the phrase — confirm score and feedback appear
16. Click ← Back — confirm the header disappears, normal Vocabulary/Challenges tabs return, and the conversation transcript is shown

### Regression

17. Conversation tab: complete a full 3-turn voice session — confirm all existing functionality works
18. Pronunciation tab: all sub-features work after returning from conversation

---

## Phase 11 — Windows 11 Packaging

**Goal:** Verify the Docker Compose packaging path starts the full stack on Windows 11 with persistent session data and no local Python/Node toolchain required.

### Prerequisites

- Windows 11 machine
- Docker Desktop installed and running with Linux containers enabled
- Repo cloned locally
- Root `.env` file populated with required keys

### MT-11-1: Build and start the packaged app

From the repo root in PowerShell or Windows Terminal:

```bash
docker compose build
docker compose up
```

**Pass:**
- Image builds successfully
- `app` container starts without crash-looping
- Logs show uvicorn listening on `0.0.0.0:8001`

### MT-11-2: Browser load and health check

1. Open `http://localhost:8001` in a desktop browser.
2. In a separate terminal:

```bash
curl http://localhost:8001/health
```

**Pass:**
- Browser loads the app shell successfully
- Health endpoint returns `{"status":"ok"}`

### MT-11-3: Full voice session through Docker

1. Start a new conversation in the browser
2. Record a Spanish utterance
3. Stop recording and wait for the coach response

**Pass:**
- Mic capture works in browser
- Transcript appears
- Coach response appears
- TTS playback works

### MT-11-4: Persistence survives restart

1. Complete at least one conversation turn
2. Stop the stack:

```bash
docker compose down
```

3. Start it again:

```bash
docker compose up
```

4. Confirm session history still contains the earlier session

**Pass:**
- Session history remains after restart
- Previously saved session can be opened

### MT-11-5: Named volume exists

Run:

```bash
docker volume ls
```

**Pass:**
- `duo_data` appears in the volume list

### Record Results

Record sign-off or failures in `docs/manualTestLog.md`.
