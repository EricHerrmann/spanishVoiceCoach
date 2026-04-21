# Phase 4 — Session Config UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose full session configuration in the UI — topic picker (preset + freeform), level slider, AI provider dropdown, coaching mode — with an explicit "New Conversation" button that starts a fresh session using the selected config.

**Architecture:** Backend gains `GET /topics`, `GET /providers`, and an expanded `POST /session/start` that accepts topic, level, ai_provider, and coaching_mode. Frontend refactors `useVoice` from a config-reactive hook into a zero-parameter hook that exposes `newSession(config)`. `SessionConfig` is expanded with the new controls; `App` holds a single config state and calls `newSession` on mount and on button click.

**Tech Stack:** Python 3.12 / FastAPI / Pydantic / pytest (backend); React + Vite / Vitest / @testing-library/react (frontend).

---

## File Map

**Modify — backend:**
- `backend/main.py` — add `_TOPICS`, `_PROVIDERS` constants; add `GET /topics`, `GET /providers` routes; expand `SessionStartRequest` with `topic`, `level`, `ai_provider` fields; update `session_start` handler.

**Modify — tests:**
- `tests/integration/test_turn_pipeline.py` — add `TestGetTopics`, `TestGetProviders` classes; add cases to `TestSessionStart`.

**Modify — frontend:**
- `frontend/src/hooks/useVoice.js` — remove `coachingMode` param; add `newSession(config)` function; remove session-start `useEffect`.
- `frontend/src/components/SessionConfig.jsx` — expand with topic select, level slider, provider select, "New Conversation" button.
- `frontend/src/__tests__/SessionConfig.test.jsx` — replace with updated tests for all controls.
- `frontend/src/App.jsx` — fetch `/topics` and `/providers` on mount; hold single `config` state; call `newSession` on mount and on button click.

**Modify — docs:**
- `docs/manualTestPlan.md` — add Phase 4 procedures.

---

## Task 1: `GET /topics` and `GET /providers` routes

**Files:**
- Modify: `backend/main.py`
- Modify: `tests/integration/test_turn_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/integration/test_turn_pipeline.py` after `TestSessionStart`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestGetTopics tests/integration/test_turn_pipeline.py::TestGetProviders -v
```

Expected: All 7 tests FAIL with 404 (routes don't exist yet).

- [ ] **Step 3: Add constants and routes to `backend/main.py`**

Add the following directly after the `import` block (before `stt_provider = WhisperSTT()`):

```python
_TOPICS = [
    {"id": "general", "label": "General conversation", "starter": "Hola, ¿de qué quieres hablar hoy?"},
    {"id": "ordering_food", "label": "Ordering food", "starter": "Hola, ¿qué me recomiendas del menú?"},
    {"id": "directions_transport", "label": "Directions & transport", "starter": "Disculpe, ¿cómo llego a la estación de metro?"},
    {"id": "shopping_markets", "label": "Shopping & markets", "starter": "Buenas, estoy buscando algo de temporada."},
    {"id": "work_daily_routine", "label": "Work & daily routine", "starter": "¿Cómo fue tu día en el trabajo?"},
    {"id": "travel_tourism", "label": "Travel & tourism", "starter": "¿Qué lugares me recomiendas visitar aquí?"},
]

_PROVIDERS = [
    {"id": "claude", "label": "Claude (Anthropic)"},
]
```

Then add these two routes after the `@app.get("/health")` route:

```python
@app.get("/topics")
def get_topics():
    return _TOPICS


@app.get("/providers")
def get_providers():
    return _PROVIDERS
```

- [ ] **Step 4: Run the new tests**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestGetTopics tests/integration/test_turn_pipeline.py::TestGetProviders -v
```

Expected: All 7 tests pass.

- [ ] **Step 5: Run full backend test suite to confirm no regressions**

```bash
ANTHROPIC_API_KEY=test-key uv run pytest tests/ -q
```

Expected: 56 passed, 2 skipped (same as before + 7 new = 63 passed, 2 skipped).

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/integration/test_turn_pipeline.py
git commit -m "feat: add GET /topics and GET /providers routes"
```

---

## Task 2: Expand `POST /session/start`

**Files:**
- Modify: `backend/main.py`
- Modify: `tests/integration/test_turn_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Add inside the existing `TestSessionStart` class in `tests/integration/test_turn_pipeline.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestSessionStart -v
```

Expected: 3 existing tests pass; 4 new tests FAIL (SessionStartRequest doesn't accept topic/level/ai_provider yet; level validation not present).

- [ ] **Step 3: Update `SessionStartRequest` and `session_start` in `backend/main.py`**

Add `Field` to the pydantic import at the top of `main.py`:

```python
from pydantic import BaseModel, Field
```

Replace the existing `SessionStartRequest` class:

```python
class SessionStartRequest(BaseModel):
    topic: str = "general"
    level: int = Field(default=5, ge=1, le=10)
    ai_provider: Literal["claude"] = "claude"
    coaching_mode: Literal["on_demand", "explicit", "shadowing"] = "on_demand"
```

Replace the existing `session_start` handler:

```python
@app.post("/session/start")
def session_start(body: SessionStartRequest | None = Body(default=None)):
    req = body or SessionStartRequest()
    session = new_session(
        topic=req.topic,
        level=req.level,
        ai_provider=req.ai_provider,
        coaching_mode=req.coaching_mode,
    )
    sessions[session.id] = session
    return {"session_id": session.id}
```

- [ ] **Step 4: Run all session/start tests**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestSessionStart -v
```

Expected: All 7 tests pass (3 existing + 4 new).

- [ ] **Step 5: Run full backend suite**

```bash
ANTHROPIC_API_KEY=test-key uv run pytest tests/ -q
```

Expected: 67 passed, 2 skipped.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/integration/test_turn_pipeline.py
git commit -m "feat: expand /session/start to accept topic, level, ai_provider"
```

---

## Task 3: `useVoice` refactor — expose `newSession(config)`

**Files:**
- Modify: `frontend/src/hooks/useVoice.js`

No new tests for this task — the hook behaviour is verified through the App wiring (Task 5) and the manual smoke test. Existing frontend tests must continue to pass.

- [ ] **Step 1: Replace `frontend/src/hooks/useVoice.js`**

```js
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
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller
    sessionIdRef.current = null
    setTurns([])
    setCorrections([])
    setError(null)
    fetch('/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: config.topic,
        level: config.level,
        ai_provider: config.ai_provider,
        coaching_mode: config.coaching_mode,
      }),
      signal: controller.signal,
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.session_id) {
          sessionIdRef.current = data.session_id
        } else {
          setError({ stage: 'mic', message: 'Failed to start session', recoverable: false })
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError({ stage: 'mic', message: 'Failed to start session', recoverable: false })
        }
      })
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
      speakCoachText(data.coach_text)
    } catch (err) {
      setError({ stage: 'stt', message: 'Network error', recoverable: true })
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

  return { state, turns, corrections, error, startRecording, stopRecording, newSession }
}
```

- [ ] **Step 2: Run existing frontend tests to confirm no regressions**

```bash
cd frontend && npm test -- --run
```

Expected: 19 tests pass (all existing tests — none of them test the session-start path directly).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useVoice.js
git commit -m "feat: useVoice exposes newSession(config) instead of reacting to coachingMode prop"
```

---

## Task 4: `SessionConfig` expansion

**Files:**
- Modify: `frontend/src/components/SessionConfig.jsx`
- Modify: `frontend/src/__tests__/SessionConfig.test.jsx`

- [ ] **Step 1: Replace the test file**

Replace the full contents of `frontend/src/__tests__/SessionConfig.test.jsx`:

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SessionConfig from '../components/SessionConfig'

const TOPICS = [
  { id: 'general', label: 'General conversation', starter: 'Hola' },
  { id: 'ordering_food', label: 'Ordering food', starter: 'Hola menú' },
]
const PROVIDERS = [{ id: 'claude', label: 'Claude (Anthropic)' }]
const DEFAULT_CONFIG = {
  topic: 'general',
  level: 5,
  ai_provider: 'claude',
  coaching_mode: 'on_demand',
}

function renderConfig(overrides = {}) {
  const props = {
    config: DEFAULT_CONFIG,
    onConfigChange: vi.fn(),
    topics: TOPICS,
    providers: PROVIDERS,
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

  it('selecting Custom reveals a text input', () => {
    renderConfig()
    fireEvent.change(screen.getByLabelText(/topic/i), { target: { value: 'custom' } })
    expect(screen.getByPlaceholderText(/enter a topic/i)).toBeInTheDocument()
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
    fireEvent.change(screen.getByLabelText(/provider/i), { target: { value: 'claude' } })
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npm test -- --run 2>&1 | tail -20
```

Expected: Most new tests FAIL — `SessionConfig` doesn't accept the new props yet.

- [ ] **Step 3: Replace `frontend/src/components/SessionConfig.jsx`**

```jsx
export default function SessionConfig({ config, onConfigChange, topics, providers, onNewSession, state }) {
  const isCustomTopic = topics.length > 0 && !topics.some((t) => t.id === config.topic)

  return (
    <div className="session-config">
      <div className="session-config-field">
        <label htmlFor="topic">Topic</label>
        <select
          id="topic"
          value={isCustomTopic ? 'custom' : config.topic}
          onChange={(e) => {
            if (e.target.value === 'custom') {
              onConfigChange({ topic: '' })
            } else {
              onConfigChange({ topic: e.target.value })
            }
          }}
        >
          {topics.map((t) => (
            <option key={t.id} value={t.id}>{t.label}</option>
          ))}
          <option value="custom">Custom…</option>
        </select>
        {isCustomTopic && (
          <input
            type="text"
            placeholder="Enter a topic"
            value={config.topic}
            onChange={(e) => onConfigChange({ topic: e.target.value })}
          />
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
        <label htmlFor="ai-provider">Provider</label>
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

- [ ] **Step 4: Run SessionConfig tests**

```bash
cd frontend && npm test -- --run 2>&1 | tail -20
```

Expected: All tests pass. Total frontend count increases from 19 to 28 (9 new SessionConfig tests replacing 3 old ones — net +6 across 4 describe blocks + 3 carried over).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SessionConfig.jsx frontend/src/__tests__/SessionConfig.test.jsx
git commit -m "feat: expand SessionConfig with topic picker, level slider, provider select, New Conversation button"
```

---

## Task 5: `App.jsx` wiring

**Files:**
- Modify: `frontend/src/App.jsx`

No new tests — App wiring is covered by SessionConfig component tests and the manual smoke test. All existing tests must continue to pass.

- [ ] **Step 1: Replace `frontend/src/App.jsx`**

```jsx
import { useState, useEffect } from 'react'
import { useVoice } from './hooks/useVoice'
import VoiceButton from './components/VoiceButton'
import Transcript from './components/Transcript'
import CoachOverlay from './components/CoachOverlay'
import SessionConfig from './components/SessionConfig'
import './App.css'

const DEFAULT_CONFIG = {
  topic: 'general',
  level: 5,
  ai_provider: 'claude',
  coaching_mode: 'on_demand',
}

function App() {
  const [topics, setTopics] = useState([])
  const [providers, setProviders] = useState([])
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const { state, turns, corrections, error, startRecording, stopRecording, newSession } = useVoice()

  useEffect(() => {
    fetch('/topics').then((r) => r.json()).then(setTopics).catch(() => {})
    fetch('/providers').then((r) => r.json()).then(setProviders).catch(() => {})
    newSession(DEFAULT_CONFIG)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function onConfigChange(patch) {
    setConfig((prev) => ({ ...prev, ...patch }))
  }

  function onNewSession() {
    const topic = config.topic.trim() || 'general'
    newSession({ ...config, topic })
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
    </div>
  )
}

export default App
```

- [ ] **Step 2: Run all frontend tests**

```bash
cd frontend && npm test -- --run
```

Expected: All tests pass (same count as after Task 4).

- [ ] **Step 3: Run all backend tests**

```bash
ANTHROPIC_API_KEY=test-key uv run pytest tests/ -q
```

Expected: 67 passed, 2 skipped.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: wire SessionConfig and newSession into App for Phase 4 config UI"
```

---

## Task 6: Manual test plan

**Files:**
- Modify: `docs/manualTestPlan.md`

- [ ] **Step 1: Append Phase 4 section to `docs/manualTestPlan.md`**

Add the following before the Sign-Off Checklist:

````markdown
---

## Phase 4 — Session Config UI

### Prerequisites

- `ANTHROPIC_API_KEY` set in your environment
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
ANTHROPIC_API_KEY=test-key uv run pytest -v
cd frontend && npm test -- --run
```

**Pass:** 67 backend tests pass, 2 skipped; frontend tests pass.
**Fail:** Any failure or error.

---

### MT-4-2: SessionConfig renders all controls

Open `http://localhost:5173`.

**Check:**
- [ ] "Topic" label and dropdown visible; preset options present; last option is "Custom…"
- [ ] "Level: 5" label and slider visible; slider moves between 1 and 10
- [ ] "Provider" label and dropdown visible; shows "Claude (Anthropic)" only
- [ ] "Coaching mode" label and dropdown visible; three options present
- [ ] "New Conversation" button visible and enabled

**Pass:** All controls visible and interactive.

---

### MT-4-3: Topic picker — preset and custom

1. Open the Topic dropdown and select "Ordering food".

**Check:**
- [ ] Dropdown shows "Ordering food" selected
- [ ] No text input appears beneath the dropdown

2. Select "Custom…".

**Check:**
- [ ] A text input appears beneath the dropdown
- [ ] Type "cooking at home" into the input

**Pass:** Preset selection is clean; Custom reveals text input.

---

### MT-4-4: Level slider

1. Drag the Level slider to position 8.

**Check:**
- [ ] Label updates to "Level: 8"
- [ ] Band labels beneath the slider are visible (Beginner · Elementary · Intermediate · Advanced)

**Pass:** Slider moves and label updates.

---

### MT-4-5: Provider dropdown shows only Claude

**Check:**
- [ ] "Claude (Anthropic)" is the only option in the Provider dropdown

**Pass:** No other providers visible.

---

### MT-4-6: New Conversation starts a fresh session with selected config

1. Complete one turn in the default session (say anything in Spanish).
2. Change Topic to "Ordering food", Level to 3, Coaching mode to "Explicit".
3. Click "New Conversation".

**Check:**
- [ ] Transcript clears
- [ ] CoachOverlay clears
- [ ] Button is briefly disabled while recording/processing (if you record immediately)
- [ ] New turn uses the selected topic and level (coach should respond with simpler vocabulary appropriate for level 3)

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
SESSION=$(curl -s -X POST http://localhost:8001/session/start \
  -H "Content-Type: application/json" \
  -d '{"topic": "ordering_food", "level": 3, "ai_provider": "claude", "coaching_mode": "explicit"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

echo $SESSION

curl -s -X POST http://localhost:8001/turn \
  -F "audio=@tests/fixtures/hola_sample.wav;type=audio/wav" \
  -F "session_id=$SESSION" | python3 -m json.tool
```

**Pass:** `$SESSION` is a UUID; turn response has all five keys (`transcript_raw`, `transcript_norm`, `coach_text`, `corrections`, `error: null`).
**Fail:** Empty `$SESSION`, missing keys, or non-null error.
````

- [ ] **Step 2: Update the Sign-Off Checklist in `docs/manualTestPlan.md`**

Add to the existing checklist:

```markdown
- [ ] MT-4-1 through MT-4-8 all passed (Phase 4)
```

- [ ] **Step 3: Commit**

```bash
git add docs/manualTestPlan.md
git commit -m "docs: add Phase 4 manual test plan (MT-4-1 through MT-4-8)"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|---|---|
| `GET /topics` with id, label, starter | Task 1 |
| `GET /providers` — Claude only, no OpenAI | Task 1 |
| `/session/start` accepts topic, level, ai_provider, coaching_mode | Task 2 |
| level validated 1–10 (422 outside range) | Task 2 |
| invalid ai_provider returns 422 | Task 2 |
| `useVoice` zero-param, exposes `newSession(config)` | Task 3 |
| `SessionConfig` topic picker with preset + Custom option | Task 4 |
| Custom topic reveals text input | Task 4 |
| Level slider min=1 max=10 with band labels | Task 4 |
| Provider select from props | Task 4 |
| "New Conversation" button calls `onNewSession` | Task 4 |
| Button disabled when state !== 'idle' | Task 4 |
| App fetches /topics and /providers on mount | Task 5 |
| App calls `newSession(DEFAULT_CONFIG)` on mount | Task 5 |
| Empty custom topic falls back to "general" | Task 5 (in `onNewSession`) |
| Manual test plan Phase 4 procedures | Task 6 |

**Placeholder scan:** None found — all steps contain complete code.

**Type consistency:**
- `newSession(config)` in `useVoice` matches call sites in `App` (`newSession(DEFAULT_CONFIG)` and `newSession({ ...config, topic })`). ✓
- `onConfigChange` receives `{ topic }`, `{ level: Number }`, `{ ai_provider }`, `{ coaching_mode }` — all match `SessionConfig` fire sites. ✓
- `SessionStartRequest` fields `topic`, `level`, `ai_provider`, `coaching_mode` match the JSON body sent by `useVoice.newSession`. ✓
- `isCustomTopic` guard uses `topics.length > 0` to avoid false-positive on empty array during initial fetch. ✓
