# Phase A — Flashcards + Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new practice modes — Flashcards and Translation — behind a tab nav bar that switches the left pane without touching the conversation pipeline.

**Architecture:** A `mode` state in `App.jsx` (`'conversation' | 'flashcards' | 'translation' | 'pronunciation'`) controls which view renders in the left pane. The right pane is unchanged. `NavTabs` renders in the app header. `ConversationView` extracts the current left-pane content. `FlashcardsView` and `TranslationView` are self-contained components with no shared state. The `pronunciation` tab is wired in the nav now but the view is implemented in Phase B.

**Tech Stack:** React + Vite (existing), FastAPI (existing), Whisper STT (existing), Claude via `ClaudeProvider` (new `translate` method), browser TTS / ElevenLabs (existing), Vitest + React Testing Library (existing), pytest (existing).

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/data/flashcard_deck.json` | Create | Curated vocabulary cards |
| `backend/ai/claude.py` | Modify | Add `translate()` method |
| `backend/main.py` | Modify | Add `GET /flashcards/deck`, `POST /translate` |
| `tests/unit/test_flashcards.py` | Create | Flashcard endpoint unit tests |
| `tests/unit/test_translate.py` | Create | Translate endpoint unit tests |
| `frontend/src/App.jsx` | Modify | Add `mode` state, render `NavTabs`, switch views |
| `frontend/src/App.css` | Modify | Add nav tab, flashcard, and translation styles |
| `frontend/src/components/NavTabs.jsx` | Create | Four-tab navigation bar |
| `frontend/src/components/ConversationView.jsx` | Create | Extracted left-pane conversation content |
| `frontend/src/components/FlashcardsView.jsx` | Create | Flashcard practice UI |
| `frontend/src/components/TranslationView.jsx` | Create | English-to-Spanish translation UI |
| `frontend/src/__tests__/NavTabs.test.jsx` | Create | NavTabs unit tests |
| `frontend/src/__tests__/FlashcardsView.test.jsx` | Create | FlashcardsView unit tests |
| `frontend/src/__tests__/TranslationView.test.jsx` | Create | TranslationView unit tests |

---

## Task 1: NavTabs + ConversationView + App.jsx mode switching + CSS

**Files:**
- Create: `frontend/src/components/NavTabs.jsx`
- Create: `frontend/src/components/ConversationView.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/App.css`
- Create: `frontend/src/__tests__/NavTabs.test.jsx`

- [ ] **Step 1.1: Write failing NavTabs tests**

Create `frontend/src/__tests__/NavTabs.test.jsx`:

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import NavTabs from '../components/NavTabs'

describe('NavTabs', () => {
  it('renders all four tabs', () => {
    render(<NavTabs mode="conversation" onModeChange={vi.fn()} />)
    expect(screen.getByText('Conversation')).toBeInTheDocument()
    expect(screen.getByText('Flashcards')).toBeInTheDocument()
    expect(screen.getByText('Translation')).toBeInTheDocument()
    expect(screen.getByText('Pronunciation')).toBeInTheDocument()
  })

  it('active tab has nav-tab--active class', () => {
    render(<NavTabs mode="flashcards" onModeChange={vi.fn()} />)
    expect(screen.getByText('Flashcards')).toHaveClass('nav-tab--active')
    expect(screen.getByText('Conversation')).not.toHaveClass('nav-tab--active')
  })

  it('clicking a tab calls onModeChange with correct id', () => {
    const onModeChange = vi.fn()
    render(<NavTabs mode="conversation" onModeChange={onModeChange} />)
    fireEvent.click(screen.getByText('Translation'))
    expect(onModeChange).toHaveBeenCalledWith('translation')
  })
})
```

- [ ] **Step 1.2: Run to verify tests fail**

```bash
cd frontend && npx vitest run src/__tests__/NavTabs.test.jsx
```

Expected: FAIL — `NavTabs` not found.

- [ ] **Step 1.3: Create NavTabs.jsx**

Create `frontend/src/components/NavTabs.jsx`:

```jsx
const TABS = [
  { id: 'conversation', label: 'Conversation' },
  { id: 'flashcards', label: 'Flashcards' },
  { id: 'translation', label: 'Translation' },
  { id: 'pronunciation', label: 'Pronunciation' },
]

export default function NavTabs({ mode, onModeChange }) {
  return (
    <nav className="nav-tabs">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`nav-tab${mode === tab.id ? ' nav-tab--active' : ''}`}
          onClick={() => onModeChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  )
}
```

- [ ] **Step 1.4: Run NavTabs tests — expect PASS**

```bash
cd frontend && npx vitest run src/__tests__/NavTabs.test.jsx
```

Expected: 3 tests PASS.

- [ ] **Step 1.5: Create ConversationView.jsx**

Create `frontend/src/components/ConversationView.jsx`:

```jsx
import VoiceButton from './VoiceButton'
import Transcript from './Transcript'

export default function ConversationView({ state, turns, error, onRecord, onStop }) {
  return (
    <>
      <Transcript turns={turns} />
      <VoiceButton state={state} onRecord={onRecord} onStop={onStop} error={error} />
    </>
  )
}
```

- [ ] **Step 1.6: Update App.jsx**

Replace the full contents of `frontend/src/App.jsx` with:

```jsx
import { useState, useEffect } from 'react'
import { useVoice } from './hooks/useVoice'
import NavTabs from './components/NavTabs'
import ConversationView from './components/ConversationView'
import FlashcardsView from './components/FlashcardsView'
import TranslationView from './components/TranslationView'
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
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [mode, setMode] = useState('conversation')
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
      <div className="app-left">
        <header className="app-header">
          <span className="app-title">duoVoiceCoach</span>
          <NavTabs mode={mode} onModeChange={setMode} />
        </header>
        {mode === 'conversation' && (
          <ConversationView
            state={state}
            turns={turns}
            error={error}
            onRecord={startRecording}
            onStop={stopRecording}
          />
        )}
        {mode === 'flashcards' && <FlashcardsView />}
        {mode === 'translation' && <TranslationView config={config} />}
        {mode === 'pronunciation' && (
          <div className="mode-placeholder">
            <p>Pronunciation practice — coming in Phase B.</p>
          </div>
        )}
      </div>
      <div className={`app-right${drawerOpen ? ' app-right--open' : ''}`}>
        <button
          className="drawer-toggle"
          onClick={() => setDrawerOpen((o) => !o)}
          aria-label={drawerOpen ? 'Close tools panel' : 'Open tools panel'}
        >
          {drawerOpen ? '✕ Close' : '▲ Tools'}
        </button>
        <div className="right-pane-content">
          <SessionConfig
            config={config}
            onConfigChange={onConfigChange}
            topics={topics}
            providers={providers}
            ttsVoices={ttsVoices}
            onNewSession={onNewSession}
            state={state}
          />
          <CoachOverlay corrections={corrections} />
          <SessionHistory
            sessions={savedSessions}
            selectedSessionId={selectedSessionId}
            onSelectSession={onSelectSession}
            onRefresh={refreshSessions}
          />
        </div>
      </div>
    </div>
  )
}

export default App
```

- [ ] **Step 1.7: Add nav tab + placeholder CSS to App.css**

Append to `frontend/src/App.css` after the existing `.app-header` rule, replacing it:

Find in `App.css`:
```css
.app-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
```

Replace with:
```css
.app-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px 0;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

/* ── Navigation tabs ────────────────────────────────── */

.nav-tabs {
  display: flex;
  gap: 4px;
  padding-bottom: 8px;
}

.nav-tab {
  padding: 3px 10px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
}

.nav-tab--active {
  background: var(--code-bg);
  border-color: var(--border);
  color: var(--text-h);
  font-weight: 500;
}

.nav-tab:hover:not(.nav-tab--active) {
  color: var(--text-h);
}

/* ── Mode placeholder ───────────────────────────────── */

.mode-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text);
  font-size: 14px;
}
```

- [ ] **Step 1.8: Create stub FlashcardsView and TranslationView so App renders**

Create `frontend/src/components/FlashcardsView.jsx` (stub — full implementation in Tasks 3 and 5):

```jsx
export default function FlashcardsView() {
  return <div className="mode-placeholder"><p>Flashcards loading…</p></div>
}
```

Create `frontend/src/components/TranslationView.jsx` (stub):

```jsx
export default function TranslationView() {
  return <div className="mode-placeholder"><p>Translation loading…</p></div>
}
```

- [ ] **Step 1.9: Run full frontend test suite**

```bash
cd frontend && npx vitest run
```

Expected: All existing tests + 3 NavTabs tests pass. The existing App tests still find `.app-left .transcript` and `.app-left .voice-button-container` because `ConversationView` renders `Transcript` and `VoiceButton` with those classes unchanged.

- [ ] **Step 1.10: Commit**

```bash
git add frontend/src/components/NavTabs.jsx \
        frontend/src/components/ConversationView.jsx \
        frontend/src/components/FlashcardsView.jsx \
        frontend/src/components/TranslationView.jsx \
        frontend/src/App.jsx \
        frontend/src/App.css \
        frontend/src/__tests__/NavTabs.test.jsx
git commit -m "feat: mode nav tabs + ConversationView extraction + pronunciation placeholder"
```

---

## Task 2: Flashcard data file + backend endpoint + tests

**Files:**
- Create: `backend/data/flashcard_deck.json`
- Modify: `backend/main.py`
- Create: `tests/unit/test_flashcards.py`

- [ ] **Step 2.1: Create backend/data/ directory and flashcard_deck.json**

```bash
mkdir -p backend/data
```

Create `backend/data/flashcard_deck.json` with the starter deck below. Topics must match values returned by `GET /topics` (`general`, `food`, `travel`, `work`). Each card has `id`, `english`, `spanish`, `level` (1–10), `topic`.

```json
[
  {"id": "g001", "english": "hello", "spanish": "hola", "level": 1, "topic": "general"},
  {"id": "g002", "english": "goodbye", "spanish": "adiós", "level": 1, "topic": "general"},
  {"id": "g003", "english": "please", "spanish": "por favor", "level": 1, "topic": "general"},
  {"id": "g004", "english": "thank you", "spanish": "gracias", "level": 1, "topic": "general"},
  {"id": "g005", "english": "yes", "spanish": "sí", "level": 1, "topic": "general"},
  {"id": "g006", "english": "no", "spanish": "no", "level": 1, "topic": "general"},
  {"id": "g007", "english": "excuse me", "spanish": "perdón", "level": 2, "topic": "general"},
  {"id": "g008", "english": "I don't understand", "spanish": "no entiendo", "level": 2, "topic": "general"},
  {"id": "g009", "english": "How are you?", "spanish": "¿Cómo estás?", "level": 2, "topic": "general"},
  {"id": "g010", "english": "My name is...", "spanish": "Me llamo...", "level": 2, "topic": "general"},
  {"id": "g011", "english": "I would like to practice more", "spanish": "Me gustaría practicar más", "level": 5, "topic": "general"},
  {"id": "g012", "english": "Can you repeat that, please?", "spanish": "¿Puede repetir eso, por favor?", "level": 5, "topic": "general"},
  {"id": "g013", "english": "I have been studying Spanish for two years", "spanish": "Llevo dos años estudiando español", "level": 7, "topic": "general"},
  {"id": "g014", "english": "It depends on the circumstances", "spanish": "Depende de las circunstancias", "level": 8, "topic": "general"},
  {"id": "f001", "english": "I would like a table for two", "spanish": "Quisiera una mesa para dos", "level": 3, "topic": "food"},
  {"id": "f002", "english": "The bill, please", "spanish": "La cuenta, por favor", "level": 3, "topic": "food"},
  {"id": "f003", "english": "What do you recommend?", "spanish": "¿Qué recomienda?", "level": 4, "topic": "food"},
  {"id": "f004", "english": "I am allergic to nuts", "spanish": "Soy alérgico a los frutos secos", "level": 5, "topic": "food"},
  {"id": "f005", "english": "The food was excellent", "spanish": "La comida estuvo excelente", "level": 5, "topic": "food"},
  {"id": "t001", "english": "Where is the train station?", "spanish": "¿Dónde está la estación de tren?", "level": 3, "topic": "travel"},
  {"id": "t002", "english": "How much does it cost?", "spanish": "¿Cuánto cuesta?", "level": 3, "topic": "travel"},
  {"id": "t003", "english": "I need a map of the city", "spanish": "Necesito un mapa de la ciudad", "level": 4, "topic": "travel"},
  {"id": "t004", "english": "The flight has been delayed", "spanish": "El vuelo ha sido retrasado", "level": 6, "topic": "travel"},
  {"id": "w001", "english": "I have a meeting at three o'clock", "spanish": "Tengo una reunión a las tres", "level": 4, "topic": "work"},
  {"id": "w002", "english": "Could you send me the report?", "spanish": "¿Podría enviarme el informe?", "level": 6, "topic": "work"},
  {"id": "w003", "english": "The project deadline is next Friday", "spanish": "La fecha límite del proyecto es el próximo viernes", "level": 7, "topic": "work"}
]
```

> Note: Expand this deck offline using Claude before deploying. Aim for ≥10 cards per topic per level band (beginner 1–2, elementary 3–4, intermediate 5–6, advanced 7–10).

- [ ] **Step 2.2: Write failing backend tests**

Create `tests/unit/test_flashcards.py`:

```python
import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestGetFlashcardDeck:
    def test_returns_list(self):
        response = client.get("/flashcards/deck")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_cards_have_required_fields(self):
        response = client.get("/flashcards/deck")
        for card in response.json():
            assert "id" in card
            assert "english" in card
            assert "spanish" in card
            assert "level" in card
            assert "topic" in card

    def test_topic_filter(self):
        response = client.get("/flashcards/deck?topic=general")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        for card in data:
            assert card["topic"] == "general"

    def test_level_min_filter(self):
        response = client.get("/flashcards/deck?level_min=3")
        assert response.status_code == 200
        for card in response.json():
            assert card["level"] >= 3

    def test_level_max_filter(self):
        response = client.get("/flashcards/deck?level_max=2")
        assert response.status_code == 200
        for card in response.json():
            assert card["level"] <= 2

    def test_combined_filter(self):
        response = client.get("/flashcards/deck?topic=food&level_min=3&level_max=4")
        assert response.status_code == 200
        for card in response.json():
            assert card["topic"] == "food"
            assert 3 <= card["level"] <= 4

    def test_unknown_topic_returns_empty_list(self):
        response = client.get("/flashcards/deck?topic=nonexistent_xyz")
        assert response.status_code == 200
        assert response.json() == []
```

- [ ] **Step 2.3: Run to confirm tests fail**

```bash
uv run pytest tests/unit/test_flashcards.py -v
```

Expected: FAIL — `404` or `AttributeError` (endpoint not yet defined).

- [ ] **Step 2.4: Add GET /flashcards/deck to main.py**

Add after the existing imports in `backend/main.py`:

```python
import json
```

Add after the `_DIST` path definition (near the bottom, before the static files mount):

```python
_FLASHCARD_DECK_PATH = pathlib.Path(__file__).parent / "data" / "flashcard_deck.json"


@app.get("/flashcards/deck")
def get_flashcard_deck(
    level_min: int = None,
    level_max: int = None,
    topic: str = None,
):
    with open(_FLASHCARD_DECK_PATH) as f:
        deck = json.load(f)
    if topic is not None:
        deck = [c for c in deck if c["topic"] == topic]
    if level_min is not None:
        deck = [c for c in deck if c["level"] >= level_min]
    if level_max is not None:
        deck = [c for c in deck if c["level"] <= level_max]
    return deck
```

- [ ] **Step 2.5: Run tests — expect PASS**

```bash
uv run pytest tests/unit/test_flashcards.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 2.6: Commit**

```bash
git add backend/data/flashcard_deck.json backend/main.py tests/unit/test_flashcards.py
git commit -m "feat: flashcard deck data file and GET /flashcards/deck endpoint"
```

---

## Task 3: FlashcardsView component + tests + CSS

**Files:**
- Modify: `frontend/src/components/FlashcardsView.jsx` (replace stub)
- Modify: `frontend/src/App.css`
- Create: `frontend/src/__tests__/FlashcardsView.test.jsx`

- [ ] **Step 3.1: Write failing FlashcardsView tests**

Create `frontend/src/__tests__/FlashcardsView.test.jsx`:

```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import FlashcardsView from '../components/FlashcardsView'

const MOCK_TOPICS = [{ id: 'general', label: 'General' }]
const MOCK_DECK = [
  { id: 'f001', english: 'hello', spanish: 'hola', level: 1, topic: 'general' },
  { id: 'f002', english: 'goodbye', spanish: 'adiós', level: 1, topic: 'general' },
]

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url.includes('/topics')) {
      return Promise.resolve({ json: () => Promise.resolve(MOCK_TOPICS) })
    }
    if (url.includes('/flashcards/deck')) {
      return Promise.resolve({ json: () => Promise.resolve(MOCK_DECK) })
    }
    return Promise.resolve({ json: () => Promise.resolve([]) })
  }))
})

afterEach(() => { vi.unstubAllGlobals() })

describe('FlashcardsView', () => {
  it('shows English side of first card by default', async () => {
    render(<FlashcardsView />)
    await waitFor(() => expect(screen.getByText('hello')).toBeInTheDocument())
    expect(screen.queryByText('hola')).not.toBeInTheDocument()
  })

  it('flips to Spanish when card is clicked', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    fireEvent.click(screen.getByText('hello'))
    expect(screen.getByText('hola')).toBeInTheDocument()
  })

  it('Next advances to second card and resets flip state', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    fireEvent.click(screen.getByText('hello'))
    fireEvent.click(screen.getByText('Next'))
    expect(screen.getByText('goodbye')).toBeInTheDocument()
    expect(screen.queryByText('adiós')).not.toBeInTheDocument()
  })

  it('Previous is disabled on first card', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    expect(screen.getByText('Previous')).toBeDisabled()
  })

  it('shows completion message after advancing past last card', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    expect(screen.getByText(/Deck complete/)).toBeInTheDocument()
  })

  it('Restart resets to first card', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Restart'))
    expect(screen.getByText('hello')).toBeInTheDocument()
  })

  it('changing band triggers a new fetch with correct level params', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    fireEvent.click(screen.getByText('Beginner'))
    await waitFor(() => {
      expect(vi.mocked(fetch)).toHaveBeenCalledWith(
        expect.stringContaining('level_min=1'),
      )
    })
  })
})
```

- [ ] **Step 3.2: Run to verify tests fail**

```bash
cd frontend && npx vitest run src/__tests__/FlashcardsView.test.jsx
```

Expected: FAIL — stub `FlashcardsView` renders placeholder text, not card content.

- [ ] **Step 3.3: Replace stub FlashcardsView.jsx with full implementation**

Replace `frontend/src/components/FlashcardsView.jsx`:

```jsx
import { useState, useEffect } from 'react'

const BANDS = [
  { id: 'beginner', label: 'Beginner', min: 1, max: 2 },
  { id: 'elementary', label: 'Elementary', min: 3, max: 4 },
  { id: 'intermediate', label: 'Intermediate', min: 5, max: 6 },
  { id: 'advanced', label: 'Advanced', min: 7, max: 10 },
]

export default function FlashcardsView() {
  const [topics, setTopics] = useState([])
  const [selectedTopic, setSelectedTopic] = useState('general')
  const [selectedBand, setSelectedBand] = useState('intermediate')
  const [deck, setDeck] = useState([])
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)

  useEffect(() => {
    fetch('/topics').then((r) => r.json()).then(setTopics).catch(() => {})
  }, [])

  useEffect(() => {
    const band = BANDS.find((b) => b.id === selectedBand)
    fetch(`/flashcards/deck?topic=${selectedTopic}&level_min=${band.min}&level_max=${band.max}`)
      .then((r) => r.json())
      .then((data) => { setDeck(data); setIndex(0); setFlipped(false) })
      .catch(() => {})
  }, [selectedTopic, selectedBand])

  const card = deck[index]
  const completed = deck.length > 0 && index >= deck.length

  function next() { setIndex((i) => i + 1); setFlipped(false) }
  function prev() { setIndex((i) => Math.max(0, i - 1)); setFlipped(false) }
  function restart() { setIndex(0); setFlipped(false) }

  return (
    <div className="flashcards-view">
      <div className="flashcards-controls">
        <select
          className="flashcards-topic-select"
          value={selectedTopic}
          onChange={(e) => setSelectedTopic(e.target.value)}
        >
          {topics.map((t) => (
            <option key={t.id} value={t.id}>{t.label}</option>
          ))}
        </select>
        <div className="flashcards-bands">
          {BANDS.map((b) => (
            <button
              key={b.id}
              className={`band-btn${selectedBand === b.id ? ' band-btn--active' : ''}`}
              onClick={() => setSelectedBand(b.id)}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>

      {deck.length === 0 && (
        <p className="flashcards-empty">No cards for this topic and level.</p>
      )}

      {completed && (
        <div className="flashcards-complete">
          <p>Deck complete — {deck.length} cards reviewed.</p>
          <button onClick={restart}>Restart</button>
        </div>
      )}

      {!completed && card && (
        <>
          <div className="flashcard" onClick={() => setFlipped((f) => !f)}>
            <span className="flashcard-side-label">{flipped ? 'Spanish' : 'English'}</span>
            <p className="flashcard-text">{flipped ? card.spanish : card.english}</p>
            <span className="flashcard-hint">click to flip</span>
          </div>
          <div className="flashcards-nav">
            <button onClick={prev} disabled={index === 0}>Previous</button>
            <span className="flashcards-progress">{index + 1} / {deck.length}</span>
            <button onClick={next}>Next</button>
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 3.4: Add flashcard CSS to App.css**

Append to `frontend/src/App.css`:

```css
/* ── Flashcards ─────────────────────────────────────── */

.flashcards-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  gap: 16px;
  overflow-y: auto;
}

.flashcards-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.flashcards-topic-select {
  width: 100%;
  box-sizing: border-box;
}

.flashcards-bands {
  display: flex;
  gap: 4px;
}

.band-btn {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  color: var(--text);
}

.band-btn--active {
  background: var(--code-bg);
  color: var(--text-h);
  font-weight: 500;
}

.flashcard {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 32px 24px;
  cursor: pointer;
  background: var(--code-bg);
  gap: 12px;
  min-height: 160px;
}

.flashcard:hover {
  border-color: var(--accent-border);
}

.flashcard-side-label {
  font-size: 11px;
  color: var(--text);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.flashcard-text {
  font-size: 28px;
  font-weight: 500;
  color: var(--text-h);
  text-align: center;
  margin: 0;
}

.flashcard-hint {
  font-size: 11px;
  color: var(--text);
}

.flashcards-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.flashcards-progress {
  font-size: 13px;
  color: var(--text);
}

.flashcards-empty,
.flashcards-complete {
  color: var(--text);
  font-size: 14px;
  text-align: center;
  padding: 32px;
}
```

- [ ] **Step 3.5: Run FlashcardsView tests — expect PASS**

```bash
cd frontend && npx vitest run src/__tests__/FlashcardsView.test.jsx
```

Expected: 7 tests PASS.

- [ ] **Step 3.6: Run full frontend suite**

```bash
cd frontend && npx vitest run
```

Expected: All tests PASS.

- [ ] **Step 3.7: Commit**

```bash
git add frontend/src/components/FlashcardsView.jsx \
        frontend/src/App.css \
        frontend/src/__tests__/FlashcardsView.test.jsx
git commit -m "feat: FlashcardsView with topic/level filtering, flip, and deck navigation"
```

---

## Task 4: ClaudeProvider.translate() + POST /translate + backend tests

**Files:**
- Modify: `backend/ai/claude.py`
- Modify: `backend/main.py`
- Create: `tests/unit/test_translate.py`

- [ ] **Step 4.1: Write failing backend tests**

Create `tests/unit/test_translate.py`:

```python
import os
from unittest.mock import patch
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

from fastapi.testclient import TestClient
from backend.main import app
from backend.session import TurnError

FIXTURE_WAV = os.path.join(os.path.dirname(__file__), "..", "fixtures", "hola_sample.wav")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
requires_api_key = pytest.mark.skipif(
    not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "test-key",
    reason="ANTHROPIC_API_KEY not set or is a test key",
)

client = TestClient(app)


class TestTranslateEndpoint:
    def test_bad_audio_returns_structured_error(self):
        response = client.post(
            "/translate",
            files={"audio": ("bad.wav", b"not-a-wav-file", "audio/wav")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert data["english"] is None
        assert data["spanish"] is None
        assert data["audio_b64"] is None

    def test_response_shape_with_mocked_translate(self):
        with patch("backend.main.claude_provider") as mock_provider:
            mock_provider.translate.return_value = "hola"
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/translate",
                    files={"audio": ("test.wav", f, "audio/wav")},
                )
        assert response.status_code == 200
        data = response.json()
        assert "english" in data
        assert "spanish" in data
        assert "audio_b64" in data
        assert "tts_error" in data
        assert "error" in data
        assert data["error"] is None
        assert data["spanish"] == "hola"

    def test_translate_error_returns_structured_error(self):
        with patch("backend.main.claude_provider") as mock_provider:
            mock_provider.translate.return_value = TurnError(
                stage="ai", message="API down", recoverable=True
            )
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/translate",
                    files={"audio": ("test.wav", f, "audio/wav")},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert data["spanish"] is None

    @requires_api_key
    def test_live_translate_returns_spanish(self):
        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/translate",
                files={"audio": ("test.wav", f, "audio/wav")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert data["english"] is not None
        assert data["spanish"] is not None
```

- [ ] **Step 4.2: Run to verify tests fail**

```bash
uv run pytest tests/unit/test_translate.py -v
```

Expected: FAIL — `POST /translate` returns 404.

- [ ] **Step 4.3: Add translate() method to ClaudeProvider**

In `backend/ai/claude.py`, add after the existing `chat()` method:

```python
    def translate(self, english_text: str) -> Union[str, TurnError]:
        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": (
                        "Translate this English phrase to natural Spanish. "
                        "Return only the Spanish translation, no explanation:\n\n"
                        f"{english_text}"
                    ),
                }],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            return TurnError(
                stage="ai",
                message=f"Translation failed: {exc}",
                recoverable=True,
            )
```

- [ ] **Step 4.4: Add POST /translate to main.py**

Add after the `get_flashcard_deck` route in `backend/main.py`:

```python
@app.post("/translate")
async def translate(
    audio: UploadFile = File(...),
    tts_provider: str = Form("browser"),
    tts_voice_id: str = Form(None),
):
    audio_bytes = await audio.read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        stt_result = stt_provider.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)

    if isinstance(stt_result, TurnError):
        return {
            "english": None,
            "spanish": None,
            "audio_b64": None,
            "tts_error": None,
            "error": {
                "stage": stt_result.stage,
                "message": stt_result.message,
                "recoverable": stt_result.recoverable,
            },
        }

    _, transcript_norm = stt_result
    translation_result = claude_provider.translate(transcript_norm)

    if isinstance(translation_result, TurnError):
        return {
            "english": transcript_norm,
            "spanish": None,
            "audio_b64": None,
            "tts_error": None,
            "error": {
                "stage": translation_result.stage,
                "message": translation_result.message,
                "recoverable": translation_result.recoverable,
            },
        }

    spanish = translation_result
    audio_b64 = None
    tts_error = None

    if tts_provider == "elevenlabs" and tts_voice_id:
        try:
            tts = ElevenLabsTTSProvider(tts_voice_id)
            tts_result = tts.synthesize(spanish)
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
        "english": transcript_norm,
        "spanish": spanish,
        "audio_b64": audio_b64,
        "tts_error": tts_error,
        "error": None,
    }
```

- [ ] **Step 4.5: Run tests — expect PASS**

```bash
uv run pytest tests/unit/test_translate.py -v
```

Expected: 3 tests PASS, 1 skipped (`requires_api_key`).

- [ ] **Step 4.6: Run full backend suite**

```bash
uv run pytest -v
```

Expected: All existing tests + 10 new tests PASS, 3 skipped.

- [ ] **Step 4.7: Commit**

```bash
git add backend/ai/claude.py backend/main.py tests/unit/test_translate.py
git commit -m "feat: ClaudeProvider.translate() and POST /translate endpoint"
```

---

## Task 5: TranslationView component + tests + CSS

**Files:**
- Modify: `frontend/src/components/TranslationView.jsx` (replace stub)
- Modify: `frontend/src/App.css`
- Create: `frontend/src/__tests__/TranslationView.test.jsx`

- [ ] **Step 5.1: Write failing TranslationView tests**

Create `frontend/src/__tests__/TranslationView.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import TranslationView from '../components/TranslationView'

const DEFAULT_CONFIG = { tts_provider: 'browser', tts_voice_id: null }

describe('TranslationView', () => {
  it('renders record button in idle state', () => {
    render(<TranslationView config={DEFAULT_CONFIG} />)
    expect(screen.getByText('Record English phrase')).toBeInTheDocument()
  })

  it('record button is enabled in idle state', () => {
    render(<TranslationView config={DEFAULT_CONFIG} />)
    expect(screen.getByText('Record English phrase')).not.toBeDisabled()
  })

  it('does not show a result panel initially', () => {
    render(<TranslationView config={DEFAULT_CONFIG} />)
    expect(screen.queryByRole('paragraph')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 5.2: Run to verify tests fail**

```bash
cd frontend && npx vitest run src/__tests__/TranslationView.test.jsx
```

Expected: FAIL — stub renders "Translation loading…", not the record button.

- [ ] **Step 5.3: Replace stub TranslationView.jsx with full implementation**

Replace `frontend/src/components/TranslationView.jsx`:

```jsx
import { useState, useRef } from 'react'

export default function TranslationView({ config }) {
  const [recordingState, setRecordingState] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const audioCtxRef = useRef(null)

  function getAudioCtx() {
    if (!audioCtxRef.current) audioCtxRef.current = new AudioContext()
    return audioCtxRef.current
  }

  async function startRecording() {
    setError(null)
    getAudioCtx().resume()
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/wav'
      const recorder = new MediaRecorder(stream, { mimeType })
      chunksRef.current = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setRecordingState('processing')
        await submitAudio(new Blob(chunksRef.current, { type: recorder.mimeType }))
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setRecordingState('recording')
    } catch (err) {
      setError(err.message)
      setRecordingState('idle')
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop()
  }

  async function submitAudio(blob) {
    const form = new FormData()
    form.append('audio', blob, 'recording.wav')
    form.append('tts_provider', config?.tts_provider || 'browser')
    if (config?.tts_voice_id) form.append('tts_voice_id', config.tts_voice_id)
    try {
      const res = await fetch('/translate', { method: 'POST', body: form })
      const data = await res.json()
      if (data.error) { setError(data.error.message); setRecordingState('idle'); return }
      setResult({ english: data.english, spanish: data.spanish })
      setRecordingState('playing')
      if (data.audio_b64) await playAudioB64(data.audio_b64)
      else speakText(data.spanish)
    } catch {
      setError('Network error')
      setRecordingState('idle')
    }
  }

  async function playAudioB64(b64) {
    const binary = atob(b64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    const ctx = getAudioCtx()
    try {
      await ctx.resume()
      const buffer = await ctx.decodeAudioData(bytes.buffer)
      const source = ctx.createBufferSource()
      source.buffer = buffer
      source.connect(ctx.destination)
      await new Promise((resolve) => { source.onended = resolve; source.start() })
    } catch { /* fall through */ } finally { setRecordingState('idle') }
  }

  function speakText(text) {
    if (!window.speechSynthesis) { setRecordingState('idle'); return }
    const utt = new SpeechSynthesisUtterance(text)
    utt.lang = 'es-ES'
    utt.onend = () => setRecordingState('idle')
    utt.onerror = () => setRecordingState('idle')
    speechSynthesis.speak(utt)
  }

  const isRecording = recordingState === 'recording'
  const isProcessing = recordingState === 'processing'
  const isPlaying = recordingState === 'playing'
  const disabled = isProcessing || isPlaying

  return (
    <div className="translation-view">
      {result && (
        <div className="translation-result">
          <p className="translation-english">{result.english}</p>
          <p className="translation-spanish">{result.spanish}</p>
        </div>
      )}
      {error && <p className="translation-error">{error}</p>}
      <div className="voice-button-container">
        <button
          className={`voice-btn voice-btn--${recordingState}`}
          onClick={isRecording ? stopRecording : startRecording}
          disabled={disabled}
        >
          {isRecording
            ? 'Stop Recording'
            : isProcessing
            ? 'Processing...'
            : isPlaying
            ? 'Playing...'
            : 'Record English phrase'}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 5.4: Add translation CSS to App.css**

Append to `frontend/src/App.css`:

```css
/* ── Translation ────────────────────────────────────── */

.translation-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.translation-result {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 32px 24px;
  gap: 16px;
}

.translation-english {
  font-size: 14px;
  color: var(--text);
  margin: 0;
}

.translation-spanish {
  font-size: 28px;
  font-weight: 500;
  color: var(--text-h);
  margin: 0;
  text-align: center;
}

.translation-error {
  color: var(--accent);
  font-size: 14px;
  padding: 8px 16px;
  margin: 0;
}
```

- [ ] **Step 5.5: Run TranslationView tests — expect PASS**

```bash
cd frontend && npx vitest run src/__tests__/TranslationView.test.jsx
```

Expected: 3 tests PASS.

- [ ] **Step 5.6: Run full frontend suite**

```bash
cd frontend && npx vitest run
```

Expected: All tests PASS.

- [ ] **Step 5.7: Commit**

```bash
git add frontend/src/components/TranslationView.jsx \
        frontend/src/App.css \
        frontend/src/__tests__/TranslationView.test.jsx
git commit -m "feat: TranslationView — record English, display and play Spanish translation"
```

---

## Task 6: Full suite + docs update

**Files:**
- Modify: `claudeSpanishCoachPlan.md`
- Modify: `docs/manualTestPlan.md`

- [ ] **Step 6.1: Run complete backend + frontend test suite**

```bash
uv run pytest -v
cd frontend && npx vitest run
```

Expected: All backend tests pass (existing + 10 new). All frontend tests pass (existing + 17 new). No failures.

- [ ] **Step 6.2: Manual smoke test**

Start backend and frontend:
```bash
# Terminal 1
uv run --env-file .env uvicorn backend.main:app --reload --port 8001

# Terminal 2
cd frontend && npm run dev
```

Open `http://localhost:5173`. Verify:
- [ ] Four tabs render in header: Conversation, Flashcards, Translation, Pronunciation
- [ ] Conversation tab works normally (existing functionality unaffected)
- [ ] Flashcards tab: topic dropdown and level band buttons appear; cards load and flip; Next/Previous/Restart work
- [ ] Translation tab: "Record English phrase" button appears; clicking it triggers mic; saying an English phrase produces a Spanish result and TTS plays it
- [ ] Pronunciation tab shows placeholder text (Phase B not yet implemented)

- [ ] **Step 6.3: Update claudeSpanishCoachPlan.md**

In the Phase 13 (or appropriate phase entry) section, mark Phase A tasks complete and add sign-off note. Update the status table row for Phase A to ✅ Complete.

- [ ] **Step 6.4: Add Phase A procedures to docs/manualTestPlan.md**

Append to `docs/manualTestPlan.md`:

```markdown
## Phase A — Flashcards + Translation

**Goal:** Verify both new modes function correctly alongside the existing conversation mode.

### Tab navigation
1. Open the app at `http://localhost:5173`
2. Confirm four tabs in the header: Conversation, Flashcards, Translation, Pronunciation
3. Click each tab — confirm left pane content switches; right pane is unchanged

### Flashcards
4. Click the Flashcards tab
5. Select a topic from the dropdown
6. Click a level band (e.g. Beginner)
7. Confirm a card appears showing an English word/phrase
8. Click the card — confirm it flips to show Spanish
9. Click Next — confirm the next card appears with English showing (flip state reset)
10. Click Previous — confirm it returns to the previous card
11. Advance through all cards — confirm "Deck complete" message appears
12. Click Restart — confirm deck resets to first card

### Translation
13. Click the Translation tab
14. Click "Record English phrase"
15. Say an English phrase (e.g. "Where is the library?")
16. Click Stop Recording
17. Confirm English transcription appears above the Spanish translation
18. Confirm TTS plays the Spanish translation
19. Record a second phrase — confirm the previous result is replaced

### Regression
20. Click the Conversation tab and complete a full voice session — confirm all existing functionality works
```

- [ ] **Step 6.5: Commit docs**

```bash
git add claudeSpanishCoachPlan.md docs/manualTestPlan.md
git commit -m "docs: Phase A sign-off checklist and manual test procedures"
```
