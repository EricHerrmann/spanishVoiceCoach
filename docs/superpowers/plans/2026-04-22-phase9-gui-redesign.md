# Phase 9 — GUI Layout Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the app from a single-column layout into a two-pane desktop layout — left pane has the conversation transcript + pinned voice button, right pane has session config (collapsible), corrections (auto-dismiss 8s), and session history. Below 768px the right pane collapses into a bottom drawer.

**Architecture:** Pure CSS grid layout — no new dependencies or state libraries. `App.jsx` gains a `drawerOpen` boolean for mobile drawer toggle. `CoachOverlay` gains a `useEffect` timer for auto-dismiss. `SessionConfig` gains a `<details>` wrapper. All other components keep their existing props/interfaces unchanged.

**Tech Stack:** React (existing), CSS custom properties + grid (no Tailwind or CSS-in-JS), Vitest + React Testing Library (existing), jsdom.

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `frontend/src/App.jsx` | Modify | Two-pane structure, `drawerOpen` state, drawer toggle button |
| `frontend/src/App.css` | Rewrite | Remove Vite scaffold CSS; add layout grid, bubble styles, drawer, responsive |
| `frontend/src/index.css` | Modify | `#root` full-height, `body` overflow hidden |
| `frontend/src/components/CoachOverlay.jsx` | Modify | Add `useEffect` 8s auto-dismiss timer |
| `frontend/src/components/SessionConfig.jsx` | Modify | Wrap content in `<details>` |
| `frontend/src/__tests__/App.test.jsx` | Create | Two-pane layout structure tests |
| `frontend/src/__tests__/CoachOverlay.test.jsx` | Modify | Add timer auto-dismiss tests |
| `frontend/src/__tests__/SessionConfig.test.jsx` | Modify | Add `<details>` wrapper test |
| `docs/manualTestPlan.md` | Modify | Add Phase 9 procedures |

**No changes needed:** `Transcript.jsx`, `VoiceButton.jsx`, `SessionHistory.jsx`, `useVoice.js`, all backend files. The transcript bubble alignment is handled entirely by CSS acting on the existing `turn--user`/`turn--coach` class names already output by `Transcript.jsx`.

---

## Task 1: App layout structure tests + two-pane App.jsx + CSS

**Files:**
- Create: `frontend/src/__tests__/App.test.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/index.css`

### Step 1.1: Write the failing layout tests

Create `frontend/src/__tests__/App.test.jsx`:

```jsx
import { render } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'

vi.mock('../hooks/useVoice', () => ({
  useVoice: () => ({
    state: 'idle',
    turns: [],
    corrections: [],
    error: null,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    newSession: vi.fn(() => Promise.resolve('session-test')),
    loadSession: vi.fn(),
  }),
}))

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    json: () => Promise.resolve([]),
  }))
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App — two-pane layout', () => {
  it('renders left pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-left')).toBeInTheDocument()
  })

  it('renders right pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-right')).toBeInTheDocument()
  })

  it('renders Transcript inside left pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-left .transcript')).toBeInTheDocument()
  })

  it('renders VoiceButton container inside left pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-left .voice-button-container')).toBeInTheDocument()
  })

  it('renders SessionConfig details inside right pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-right .session-config-details')).toBeInTheDocument()
  })

  it('renders SessionHistory inside right pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-right .session-history')).toBeInTheDocument()
  })

  it('renders drawer toggle button', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.drawer-toggle')).toBeInTheDocument()
  })
})
```

### Step 1.2: Run tests to verify they fail

```bash
cd frontend && npx vitest run src/__tests__/App.test.jsx
```

Expected: FAIL — `querySelector('.app-left')` returns null (old structure has `.app` without panes).

### Step 1.3: Rewrite App.jsx with two-pane structure

Replace `frontend/src/App.jsx` with:

```jsx
import { useState, useEffect } from 'react'
import { useVoice } from './hooks/useVoice'
import VoiceButton from './components/VoiceButton'
import Transcript from './components/Transcript'
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
        </header>
        <Transcript turns={turns} />
        <VoiceButton
          state={state}
          onRecord={startRecording}
          onStop={stopRecording}
          error={error}
        />
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

### Step 1.4: Rewrite App.css

Replace `frontend/src/App.css` entirely with:

```css
/* ── Layout ─────────────────────────────────────────── */

.app {
  display: grid;
  grid-template-columns: 65fr 35fr;
  height: 100svh;
  overflow: hidden;
}

.app-left {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--border);
}

.app-right {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  border-left: none;
}

/* ── Left pane header ───────────────────────────────── */

.app-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.app-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-h);
  letter-spacing: -0.2px;
}

/* ── Transcript ─────────────────────────────────────── */

.transcript {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.turn {
  display: flex;
  flex-direction: column;
  max-width: 78%;
}

.turn--user {
  align-self: flex-end;
  align-items: flex-end;
}

.turn--coach {
  align-self: flex-start;
  align-items: flex-start;
}

.turn-label {
  font-size: 11px;
  color: var(--text);
  margin-bottom: 3px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.turn-text {
  background: var(--code-bg);
  border-radius: 16px;
  padding: 8px 14px;
  line-height: 1.45;
  font-size: 16px;
}

.turn--user .turn-text {
  background: var(--accent-bg);
  border: 1px solid var(--accent-border);
  border-bottom-right-radius: 4px;
}

.turn--coach .turn-text {
  border-bottom-left-radius: 4px;
}

/* ── VoiceButton area ───────────────────────────────── */

.voice-button-container {
  flex-shrink: 0;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--border);
}

/* ── Right pane ─────────────────────────────────────── */

.drawer-toggle {
  display: none;
}

.right-pane-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Session config (collapsible) ───────────────────── */

.session-config-details {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.session-config-details > summary {
  padding: 10px 14px;
  cursor: pointer;
  font-weight: 500;
  color: var(--text-h);
  user-select: none;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 6px;
}

.session-config-details > summary::-webkit-details-marker {
  display: none;
}

.session-config-details > summary::before {
  content: '▶';
  font-size: 10px;
  transition: transform 0.15s;
}

.session-config-details[open] > summary::before {
  transform: rotate(90deg);
}

.session-config {
  padding: 12px 14px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.session-config-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-config-field label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-h);
}

.session-config-field select,
.session-config-field input[type="text"],
.session-config-field input[type="range"] {
  width: 100%;
  box-sizing: border-box;
}

.level-bands {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text);
  margin-top: 2px;
}

.topic-starter {
  margin-top: 4px;
  color: var(--text-h);
  font-size: 13px;
  line-height: 1.35;
}

.mode-description {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text);
}

/* ── Coach overlay ──────────────────────────────────── */

.coach-overlay {
  border: 1px solid var(--accent-border);
  border-radius: 8px;
  padding: 12px 14px;
  background: var(--accent-bg);
}

.coach-overlay h3 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-h);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.correction {
  margin-bottom: 8px;
}

.correction:last-child {
  margin-bottom: 0;
}

.correction-original {
  color: var(--text);
  text-decoration: line-through;
  font-size: 14px;
}

.correction-arrow {
  color: var(--text);
  font-size: 14px;
}

.correction-corrected {
  color: var(--accent);
  font-weight: 600;
  font-size: 14px;
}

.correction-explanation {
  margin: 3px 0 0;
  font-size: 13px;
  color: var(--text);
  line-height: 1.4;
}

/* ── Session history ────────────────────────────────── */

.session-history {
  width: auto;
  margin: 0;
  text-align: left;
}

.session-history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.session-history-header h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.session-history-empty {
  color: var(--text);
  font-size: 14px;
}

.session-history-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.session-history-item {
  width: 100%;
  display: grid;
  gap: 2px;
  text-align: left;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: none;
  cursor: pointer;
  font-family: inherit;
  font-size: inherit;
}

.session-history-item.is-selected {
  border-color: var(--accent-border);
  background: var(--accent-bg);
}

.session-history-topic {
  color: var(--text-h);
  font-weight: 600;
  font-size: 14px;
}

.session-history-meta {
  color: var(--text);
  font-size: 12px;
}

/* ── Mobile drawer (≤768px) ─────────────────────────── */

@media (max-width: 768px) {
  .app {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr auto;
    height: 100svh;
  }

  .app-left {
    border-right: none;
    min-height: 0;
  }

  .app-right {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 48px;
    background: var(--bg);
    border-top: 1px solid var(--border);
    overflow: hidden;
    transition: height 0.25s ease;
    z-index: 100;
    display: block;
  }

  .app-right--open {
    height: 60vh;
    overflow-y: auto;
  }

  .drawer-toggle {
    display: block;
    width: 100%;
    padding: 13px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-h);
    font-family: inherit;
  }

  .right-pane-content {
    padding-top: 4px;
  }
}
```

### Step 1.5: Update index.css — full-height root, no body scroll

In `frontend/src/index.css`, replace the `body` rule and `#root` rule:

Find and replace:

```css
body {
  margin: 0;
}

#root {
  width: 1126px;
  max-width: 100%;
  margin: 0 auto;
  text-align: center;
  border-inline: 1px solid var(--border);
  min-height: 100svh;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}
```

Replace with:

```css
body {
  margin: 0;
  overflow: hidden;
}

#root {
  width: 100%;
  max-width: 100%;
  margin: 0;
  text-align: left;
  border-inline: none;
  height: 100svh;
  overflow: hidden;
}
```

### Step 1.6: Run the layout tests

```bash
cd frontend && npx vitest run src/__tests__/App.test.jsx
```

Expected: 7 tests PASS.

### Step 1.7: Run the full test suite

```bash
cd frontend && npx vitest run
```

Expected: All 47 existing + 7 new = 54 tests PASS. If any SessionConfig or SessionHistory tests fail, check that the class names in the CSS match the class names in the component files.

### Step 1.8: Commit

```bash
git add frontend/src/App.jsx frontend/src/App.css frontend/src/index.css frontend/src/__tests__/App.test.jsx
git commit -m "feat: two-pane desktop layout — left pane transcript, right pane tools"
```

---

## Task 2: CoachOverlay auto-dismiss timer

**Files:**
- Modify: `frontend/src/components/CoachOverlay.jsx`
- Modify: `frontend/src/__tests__/CoachOverlay.test.jsx`

### Step 2.1: Write the failing timer tests

Add to `frontend/src/__tests__/CoachOverlay.test.jsx` (append after existing tests):

```jsx
import { render, screen, act } from '@testing-library/react'
import { vi, describe, it, expect } from 'vitest'
// (keep existing imports at top of file)

describe('CoachOverlay — auto-dismiss timer', () => {
  it('auto-dismisses after 8 seconds', () => {
    vi.useFakeTimers()
    const corrections = [
      { original: 'yo fui', corrected: 'fui', explanation: 'Optional pronoun', triggered_by: 'auto' },
    ]
    render(<CoachOverlay corrections={corrections} />)
    expect(screen.getByText('yo fui')).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(8000) })
    expect(screen.queryByText('yo fui')).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  it('resets the timer when new corrections arrive', () => {
    vi.useFakeTimers()
    const corrections1 = [
      { original: 'yo fui', corrected: 'fui', explanation: 'Optional pronoun', triggered_by: 'auto' },
    ]
    const corrections2 = [
      { original: 'el mercado', corrected: 'al mercado', explanation: "Missing contraction", triggered_by: 'user_request' },
    ]
    const { rerender } = render(<CoachOverlay corrections={corrections1} />)
    act(() => { vi.advanceTimersByTime(5000) })
    rerender(<CoachOverlay corrections={corrections2} />)
    expect(screen.getByText('el mercado')).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(5000) })
    expect(screen.getByText('el mercado')).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(3000) })
    expect(screen.queryByText('el mercado')).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  it('hides immediately when corrections become empty', () => {
    vi.useFakeTimers()
    const corrections = [
      { original: 'yo fui', corrected: 'fui', explanation: 'Optional pronoun', triggered_by: 'auto' },
    ]
    const { rerender } = render(<CoachOverlay corrections={corrections} />)
    expect(screen.getByText('yo fui')).toBeInTheDocument()
    rerender(<CoachOverlay corrections={[]} />)
    expect(screen.queryByText('yo fui')).not.toBeInTheDocument()
    vi.useRealTimers()
  })
})
```

### Step 2.2: Run to verify the timer tests fail

```bash
cd frontend && npx vitest run src/__tests__/CoachOverlay.test.jsx
```

Expected: The 4 existing tests PASS, the 3 new timer tests FAIL (CoachOverlay has no timer, so corrections never auto-dismiss).

### Step 2.3: Update CoachOverlay.jsx with auto-dismiss timer

Replace `frontend/src/components/CoachOverlay.jsx`:

```jsx
import { useState, useEffect } from 'react'

export default function CoachOverlay({ corrections }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!corrections || corrections.length === 0) {
      setVisible(false)
      return
    }
    setVisible(true)
    const timer = setTimeout(() => setVisible(false), 8000)
    return () => clearTimeout(timer)
  }, [corrections])

  if (!visible) return null
  return (
    <div className="coach-overlay">
      <h3>Corrections</h3>
      {corrections.map((c, i) => (
        <div key={`${c.original}-${c.corrected}-${i}`} className="correction">
          <span className="correction-original">{c.original}</span>
          <span className="correction-arrow"> → </span>
          <span className="correction-corrected">{c.corrected}</span>
          <p className="correction-explanation">{c.explanation}</p>
        </div>
      ))}
    </div>
  )
}
```

### Step 2.4: Run CoachOverlay tests

```bash
cd frontend && npx vitest run src/__tests__/CoachOverlay.test.jsx
```

Expected: All 7 tests PASS (4 existing + 3 timer tests).

### Step 2.5: Run full suite

```bash
cd frontend && npx vitest run
```

Expected: All 57 tests PASS.

### Step 2.6: Commit

```bash
git add frontend/src/components/CoachOverlay.jsx frontend/src/__tests__/CoachOverlay.test.jsx
git commit -m "feat: CoachOverlay auto-dismisses after 8 seconds"
```

---

## Task 3: SessionConfig collapsible `<details>` wrapper

**Files:**
- Modify: `frontend/src/components/SessionConfig.jsx`
- Modify: `frontend/src/__tests__/SessionConfig.test.jsx`

### Step 3.1: Write the failing details test

Add to `frontend/src/__tests__/SessionConfig.test.jsx` (append after existing describe blocks):

```jsx
describe('SessionConfig — collapsible wrapper', () => {
  it('renders inside a details element', () => {
    const { container } = renderConfig()
    expect(container.querySelector('details')).toBeInTheDocument()
  })

  it('details element is collapsed by default', () => {
    const { container } = renderConfig()
    expect(container.querySelector('details')).not.toHaveAttribute('open')
  })

  it('details element has a summary with text', () => {
    const { container } = renderConfig()
    expect(container.querySelector('details > summary')).toBeInTheDocument()
    expect(container.querySelector('details > summary').textContent).toMatch(/session config/i)
  })
})
```

### Step 3.2: Run to verify the new tests fail

```bash
cd frontend && npx vitest run src/__tests__/SessionConfig.test.jsx
```

Expected: 26 existing tests PASS, 3 new tests FAIL (no `<details>` element currently).

### Step 3.3: Wrap SessionConfig content in `<details>`

In `frontend/src/components/SessionConfig.jsx`, replace the return statement:

Old:
```jsx
  return (
    <div className="session-config">
      <div className="session-config-field">
```

New:
```jsx
  return (
    <details className="session-config-details">
      <summary>Session Config</summary>
      <div className="session-config">
        <div className="session-config-field">
```

And close the `</details>` tag. The full updated return is:

```jsx
  return (
    <details className="session-config-details">
      <summary>Session Config</summary>
      <div className="session-config">
        <div className="session-config-field">
          <label htmlFor="topic">Topic</label>
          <select
            id="topic"
            value={topicSelectValue}
            onChange={handleTopicChange}
          >
            {topics.map((t) => (
              <option key={t.id} value={t.id}>{t.label}</option>
            ))}
            <option value="custom">Custom…</option>
          </select>
          {showCustomInput && (
            <input
              type="text"
              placeholder="Enter a topic"
              value={config.topic}
              onChange={(e) => onConfigChange({ topic: e.target.value })}
            />
          )}
          {!showCustomInput && selectedTopic?.starter && (
            <p className="topic-starter">{selectedTopic.starter}</p>
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
          <label htmlFor="ai-provider">AI Provider</label>
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
          <p className="mode-description">{COACHING_MODE_DESCRIPTIONS[config.coaching_mode]}</p>
        </div>

        <div className="session-config-field">
          <label htmlFor="tts-provider">Voice</label>
          <select
            id="tts-provider"
            value={config.tts_provider}
            onChange={handleTtsProviderChange}
          >
            <option value="browser">Browser (built-in)</option>
            <option value="elevenlabs">ElevenLabs</option>
          </select>
        </div>

        {config.tts_provider === 'elevenlabs' && (
          <div className="session-config-field">
            <label htmlFor="tts-voice">ElevenLabs voice</label>
            <select
              id="tts-voice"
              value={config.tts_voice_id || ''}
              onChange={(e) => onConfigChange({ tts_voice_id: e.target.value })}
            >
              {ttsVoices.map((v) => (
                <option key={v.id} value={v.id}>{v.label}</option>
              ))}
            </select>
          </div>
        )}

        <button
          onClick={onNewSession}
          disabled={state !== 'idle'}
        >
          New Conversation
        </button>
      </div>
    </details>
  )
```

### Step 3.4: Run SessionConfig tests

```bash
cd frontend && npx vitest run src/__tests__/SessionConfig.test.jsx
```

Expected: All 29 tests PASS (26 existing + 3 new).

Note: The existing tests use `screen.getByLabelText` which queries the full DOM regardless of `<details>` open/closed state in jsdom. All existing tests should continue to pass without modification.

### Step 3.5: Run full suite

```bash
cd frontend && npx vitest run
```

Expected: All 60 tests PASS.

### Step 3.6: Commit

```bash
git add frontend/src/components/SessionConfig.jsx frontend/src/__tests__/SessionConfig.test.jsx
git commit -m "feat: SessionConfig wrapped in collapsible details element"
```

---

## Task 4: Manual smoke test + plan docs update

**Files:**
- Modify: `docs/manualTestPlan.md`
- Modify: `claudeSpanishCoachPlan.md`

### Step 4.1: Start the dev server and verify visually

```bash
# Terminal 1 — backend
cd /home/oldha/projects/duoVoiceCoach
uv run uvicorn backend.main:app --reload --port 8001

# Terminal 2 — frontend
cd /home/oldha/projects/duoVoiceCoach/frontend
npm run dev
```

Open `http://localhost:5173` in a browser. Verify:
- [ ] Two-pane layout renders: left pane has transcript area + voice button at bottom
- [ ] Right pane shows collapsed "Session Config" details, CoachOverlay placeholder area, Session History
- [ ] Clicking "Session Config" summary expands/collapses the config fields
- [ ] User bubbles appear on the right, coach bubbles on the left after a voice turn
- [ ] CoachOverlay appears when corrections arrive and disappears after ~8 seconds
- [ ] Session history list appears in right pane

### Step 4.2: Add Phase 9 procedures to manualTestPlan.md

Open `docs/manualTestPlan.md` and append:

```markdown
## Phase 9 — GUI Layout Redesign

**Goal:** Verify the two-pane desktop layout renders and functions correctly.

### Desktop layout
1. Open app at `http://localhost:5173` (or `http://localhost:8001` in Docker)
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
9. Trigger a correction (speak with a deliberate error in Explicit mode)
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
```

### Step 4.3: Update claudeSpanishCoachPlan.md Phase 9 task checkboxes

In `claudeSpanishCoachPlan.md`, under Phase 9 Tasks, mark completed items:

```markdown
- [x] Update `App.jsx` — new two-column layout wrapper; right-pane composition
- [x] Update `Transcript.jsx` — full-height flex container; user/coach bubble alignment (user right, coach left)
- [x] Update `VoiceButton.jsx` — pinned bottom position within left pane
- [x] Update `SessionConfig.jsx` — wrap in collapsible `<details>`; collapsed by default
- [x] Update `CoachOverlay.jsx` — move into right pane; add 8-second auto-dismiss timer
- [x] Update `SessionHistory.jsx` — move into right pane; no structural change
- [x] Update `App.css` / `index.css` — new layout grid; responsive breakpoint at 768px
- [x] Add layout-level Vitest snapshots for two-pane structure
- [ ] Manual smoke test: full session in new layout on desktop
- [ ] Manual smoke test: right pane collapses correctly on Android
- [x] Add Phase 9 procedures to `docs/manualTestPlan.md`
```

Note: The manual smoke tests stay unchecked until performed.

### Step 4.4: Run full suite one final time

```bash
cd frontend && npx vitest run
```

Expected: All 60 tests PASS.

### Step 4.5: Commit docs

```bash
git add docs/manualTestPlan.md claudeSpanishCoachPlan.md
git commit -m "docs: Phase 9 test procedures and task progress"
```

---

## Self-Review Checklist

### Spec coverage

| Spec requirement | Task |
|-----------------|------|
| Two-pane layout (left ~65%, right ~35%) | Task 1 — App.jsx + App.css grid |
| Left pane: scrollable transcript | Task 1 — `.transcript { flex: 1; overflow-y: auto }` |
| Voice button pinned to bottom of left pane | Task 1 — `.voice-button-container` in flex column tail |
| User bubbles right / coach bubbles left | Task 1 — `.turn--user { align-self: flex-end }` |
| Right pane: Session Config collapsible | Task 3 — `<details>` wrapper in SessionConfig |
| Right pane: Corrections auto-clears 8s | Task 2 — useEffect timer in CoachOverlay |
| Right pane: Session History | Task 1 — SessionHistory in `.right-pane-content` |
| Responsive ≤768px bottom drawer | Task 1 — CSS media query in App.css |
| Layout tests | Task 1 — App.test.jsx |
| Manual test plan | Task 4 — manualTestPlan.md |

All spec requirements covered.

### Placeholder scan

No TBDs, TODOs, or vague steps — all steps contain complete code.

### Type consistency

- `drawerOpen` / `setDrawerOpen` used consistently in App.jsx
- `corrections` prop passed as array to `CoachOverlay` — matches existing interface
- `session-config-details` class name used in App.test.jsx query and SessionConfig.jsx — consistent
- `app-left` / `app-right` class names used in App.test.jsx queries and App.jsx JSX — consistent
