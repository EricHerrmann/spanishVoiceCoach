# Phase C — Conversation Hint System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conversation hint strip below the record button seeded from the topic starter phrase, overridable by a translation result, with source labeling and hide/show toggle — and add a Practice pronunciation button to the Translation tab.

**Architecture:** A `conversationHint` object `{ text, source }` in `App.jsx` is the single source of truth. It is seeded by a `useEffect` on `[config.topic, topics]` and overridden by translation results via a callback. `pronunciationTarget` is upgraded from a plain string to `{ text, source }` so PronunciationView can show the correct "From conversation" / "From translation" label. ConversationView owns hide/show state locally.

**Tech Stack:** React (JSX, no TypeScript), Vitest + @testing-library/react

---

## File Map

| File | Change |
|---|---|
| `frontend/src/App.jsx` | Add `conversationHint` state + seeding effect, upgrade `pronunciationTarget` shape, add `handleTranslationResult`, pass new props |
| `frontend/src/components/Transcript.jsx` | Pass `'conversation'` source to `onPractice` call |
| `frontend/src/components/PronunciationView.jsx` | Accept `{text, source}` for `pronunciationTarget`, show dynamic source label |
| `frontend/src/components/ConversationView.jsx` | Accept `hint` prop, render with hide/show toggle |
| `frontend/src/components/TranslationView.jsx` | Add `onResult` + `onPractice` props, add Practice button |
| `frontend/src/__tests__/PronunciationView.test.jsx` | Update 3 existing tests to object shape, add 2 source label tests |
| `frontend/src/__tests__/ConversationView.test.jsx` | **New file** — 6 hint display/toggle tests |
| `frontend/src/__tests__/App.hint.test.jsx` | **New file** — topic starter seeding integration tests |
| `frontend/src/__tests__/App.crossmode.test.jsx` | Add Translation tab switch test |
| `frontend/src/__tests__/TranslationView.test.jsx` | Add 2 tests: accepts new props, no Practice button initially |

---

### Task 1: Upgrade pronunciationTarget to {text, source} and show dynamic source label in PronunciationView

**Files:**
- Modify: `frontend/src/__tests__/PronunciationView.test.jsx` (lines 76–95, add 2 tests)
- Modify: `frontend/src/App.jsx` (lines 34–38)
- Modify: `frontend/src/components/Transcript.jsx` (line 34)
- Modify: `frontend/src/components/PronunciationView.jsx` (lines 3–8 area, 55–59, 115)

- [ ] **Step 1: Update PronunciationView single-phrase tests to use object shape and add source label tests**

In `frontend/src/__tests__/PronunciationView.test.jsx`, replace the entire `describe('PronunciationView — single-phrase mode', ...)` block (lines 76–95) with:

```jsx
describe('PronunciationView — single-phrase mode', () => {
  it('when pronunciationTarget is set, shows that phrase without tabs', () => {
    render(<PronunciationView pronunciationTarget={{ text: 'Muy bien, gracias.', source: 'conversation' }} onClearTarget={vi.fn()} />)
    expect(screen.getByText('Muy bien, gracias.')).toBeInTheDocument()
    expect(screen.queryByText('Vocabulary')).not.toBeInTheDocument()
    expect(screen.queryByText('Challenges')).not.toBeInTheDocument()
  })

  it('shows a back button in single-phrase mode', () => {
    render(<PronunciationView pronunciationTarget={{ text: 'Muy bien.', source: 'conversation' }} onClearTarget={vi.fn()} />)
    expect(screen.getByText('← Back')).toBeInTheDocument()
  })

  it('back button calls onClearTarget', () => {
    const onClearTarget = vi.fn()
    render(<PronunciationView pronunciationTarget={{ text: 'Muy bien.', source: 'conversation' }} onClearTarget={onClearTarget} />)
    fireEvent.click(screen.getByText('← Back'))
    expect(onClearTarget).toHaveBeenCalled()
  })

  it('shows "From conversation" source label when source is conversation', () => {
    render(<PronunciationView pronunciationTarget={{ text: 'Muy bien.', source: 'conversation' }} onClearTarget={vi.fn()} />)
    expect(screen.getByText('From conversation')).toBeInTheDocument()
  })

  it('shows "From translation" source label when source is translation', () => {
    render(<PronunciationView pronunciationTarget={{ text: 'El gato es bonito.', source: 'translation' }} onClearTarget={vi.fn()} />)
    expect(screen.getByText('From translation')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx vitest run src/__tests__/PronunciationView.test.jsx
```
Expected: 3 existing single-phrase tests FAIL (prop is now a string, not object), 2 new source label tests FAIL.

- [ ] **Step 3: Add SOURCE_LABELS constant and update pronunciationTarget usage in PronunciationView.jsx**

In `frontend/src/components/PronunciationView.jsx`:

Add `SOURCE_LABELS` immediately after the `BANDS` array (after line 8):
```jsx
const SOURCE_LABELS = {
  conversation: 'From conversation',
  translation: 'From translation',
}
```

Replace the `target` derivation (lines 55–59):
```jsx
  const target = pronunciationTarget
    ? pronunciationTarget.text
    : tab === 'vocabulary'
    ? vocabDeck[vocabIndex]?.spanish ?? null
    : selectedChallenge?.target ?? null
```

Replace the hardcoded source label (line 115 — inside the `pronunciationTarget` conditional block):
```jsx
          <span className="pronunciation-source-label">
            {SOURCE_LABELS[pronunciationTarget.source] ?? 'From session'}
          </span>
```

- [ ] **Step 4: Update handlePractice in App.jsx to accept a source parameter**

In `frontend/src/App.jsx`, replace `handlePractice` (lines 34–38):
```jsx
  function handlePractice(text, source = 'conversation') {
    if (!text) return
    setPronunciationTarget({ text, source })
    setMode('pronunciation')
  }
```

- [ ] **Step 5: Update Transcript.jsx to pass 'conversation' as source**

In `frontend/src/components/Transcript.jsx`, replace line 34:
```jsx
                  onClick={() => onPractice?.(text, 'conversation')}
```

- [ ] **Step 6: Run tests to verify all PronunciationView and crossmode tests pass**

```bash
cd frontend && npx vitest run src/__tests__/PronunciationView.test.jsx src/__tests__/App.crossmode.test.jsx
```
Expected: all 11 PronunciationView tests PASS, 2 crossmode tests PASS.

- [ ] **Step 7: Run full frontend suite**

```bash
cd frontend && npx vitest run
```
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.jsx frontend/src/components/Transcript.jsx frontend/src/components/PronunciationView.jsx frontend/src/__tests__/PronunciationView.test.jsx
git commit -m "feat: upgrade pronunciationTarget to {text,source}, show dynamic source label in PronunciationView"
```

---

### Task 2: ConversationView hint display with hide/show toggle

**Files:**
- Create: `frontend/src/__tests__/ConversationView.test.jsx`
- Modify: `frontend/src/components/ConversationView.jsx`

- [ ] **Step 1: Create ConversationView.test.jsx with hint tests**

Create `frontend/src/__tests__/ConversationView.test.jsx`:

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ConversationView from '../components/ConversationView'

const defaultProps = {
  state: 'idle',
  turns: [],
  error: null,
  onRecord: vi.fn(),
  onStop: vi.fn(),
  onPractice: vi.fn(),
  coachingMode: 'on_demand',
}

describe('ConversationView — hint', () => {
  it('renders hint text when hint is provided', () => {
    render(<ConversationView {...defaultProps} hint={{ text: 'Hola, ¿cómo estás?', source: 'topic' }} />)
    expect(screen.getByText('Hola, ¿cómo estás?')).toBeInTheDocument()
  })

  it('shows "Try saying" label for topic source', () => {
    render(<ConversationView {...defaultProps} hint={{ text: 'Hola', source: 'topic' }} />)
    expect(screen.getByText('Try saying')).toBeInTheDocument()
  })

  it('shows "You translated" label for translation source', () => {
    render(<ConversationView {...defaultProps} hint={{ text: 'El gato es bonito.', source: 'translation' }} />)
    expect(screen.getByText('You translated')).toBeInTheDocument()
  })

  it('hides hint text after clicking Hide', () => {
    render(<ConversationView {...defaultProps} hint={{ text: 'Hola', source: 'topic' }} />)
    fireEvent.click(screen.getByText('Hide'))
    expect(screen.queryByText('Hola')).not.toBeInTheDocument()
  })

  it('shows hint text again after clicking Show', () => {
    render(<ConversationView {...defaultProps} hint={{ text: 'Hola', source: 'topic' }} />)
    fireEvent.click(screen.getByText('Hide'))
    fireEvent.click(screen.getByText('Show'))
    expect(screen.getByText('Hola')).toBeInTheDocument()
  })

  it('renders nothing hint-related when hint is null', () => {
    render(<ConversationView {...defaultProps} hint={null} />)
    expect(screen.queryByText('Try saying')).not.toBeInTheDocument()
    expect(screen.queryByText('You translated')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx vitest run src/__tests__/ConversationView.test.jsx
```
Expected: 6 tests FAIL (hint prop not rendered yet).

- [ ] **Step 3: Rewrite ConversationView.jsx to accept hint prop and render it**

Replace all of `frontend/src/components/ConversationView.jsx`:

```jsx
import { useState } from 'react'
import VoiceButton from './VoiceButton'
import Transcript from './Transcript'

const HINT_SOURCE_LABELS = {
  topic: 'Try saying',
  translation: 'You translated',
}

export default function ConversationView({ state, turns, error, onRecord, onStop, onPractice, coachingMode, hint }) {
  const [hintVisible, setHintVisible] = useState(true)

  return (
    <>
      <Transcript turns={turns} onPractice={onPractice} />
      <VoiceButton state={state} onRecord={onRecord} onStop={onStop} error={error} coachingMode={coachingMode} />
      {hint && (
        <div className="conversation-hint">
          <div className="conversation-hint-header">
            <span className="conversation-hint-source">{HINT_SOURCE_LABELS[hint.source] ?? 'Hint'}</span>
            <button
              className="conversation-hint-toggle"
              onClick={() => setHintVisible((v) => !v)}
            >
              {hintVisible ? 'Hide' : 'Show'}
            </button>
          </div>
          {hintVisible && (
            <span className="conversation-hint-text">{hint.text}</span>
          )}
        </div>
      )}
    </>
  )
}
```

- [ ] **Step 4: Run tests to verify all 6 hint tests pass**

```bash
cd frontend && npx vitest run src/__tests__/ConversationView.test.jsx
```
Expected: 6 PASS.

- [ ] **Step 5: Run full frontend suite**

```bash
cd frontend && npx vitest run
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ConversationView.jsx frontend/src/__tests__/ConversationView.test.jsx
git commit -m "feat: add conversation hint strip with hide/show toggle to ConversationView"
```

---

### Task 3: conversationHint state seeded from topic starter in App

**Files:**
- Create: `frontend/src/__tests__/App.hint.test.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Create App.hint.test.jsx**

Create `frontend/src/__tests__/App.hint.test.jsx`:

```jsx
import { render, screen, waitFor } from '@testing-library/react'
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

const MOCK_TOPICS = [
  { id: 'general', label: 'General', starter: 'Hola, ¿cómo estás?' },
  { id: 'food', label: 'Food', starter: '¿Qué quieres comer?' },
]

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url === '/topics') return Promise.resolve({ json: () => Promise.resolve(MOCK_TOPICS) })
    return Promise.resolve({ json: () => Promise.resolve([]) })
  }))
})

afterEach(() => { vi.unstubAllGlobals() })

describe('App — conversation hint from topic starter', () => {
  it('shows topic starter phrase as hint when topics load', async () => {
    render(<App />)
    await waitFor(() => expect(screen.getByText('Hola, ¿cómo estás?')).toBeInTheDocument())
  })

  it('shows "Try saying" label for topic starter hint', async () => {
    render(<App />)
    await waitFor(() => expect(screen.getByText('Try saying')).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx vitest run src/__tests__/App.hint.test.jsx
```
Expected: 2 tests FAIL (hint not wired in App yet).

- [ ] **Step 3: Add conversationHint state, seeding effect, and reset to App.jsx**

In `frontend/src/App.jsx`:

After line 31 (`const [pronunciationTarget, setPronunciationTarget] = useState(null)`), add:
```jsx
  const [conversationHint, setConversationHint] = useState(null)
```

Add a new `useEffect` after the existing initial load `useEffect` block (after the closing `}, [])` on line 57):
```jsx
  useEffect(() => {
    const topic = topics.find((t) => t.id === config.topic)
    setConversationHint(topic?.starter ? { text: topic.starter, source: 'topic' } : null)
  }, [config.topic, topics])
```

Replace `onNewSession` (lines 63–69) to reset the hint on new conversation:
```jsx
  function onNewSession() {
    const topic = config.topic.trim() || 'general'
    const topicObj = topics.find((t) => t.id === topic)
    setConversationHint(topicObj?.starter ? { text: topicObj.starter, source: 'topic' } : null)
    newSession({ ...config, topic }).then((sessionId) => {
      setSelectedSessionId(sessionId)
      refreshSessions()
    })
  }
```

Add `hint={conversationHint}` to the `<ConversationView>` JSX (lines 97–105):
```jsx
        {mode === 'conversation' && (
          <ConversationView
            state={state}
            turns={turns}
            error={error}
            onRecord={startRecording}
            onStop={stopRecording}
            onPractice={handlePractice}
            coachingMode={config.coaching_mode}
            hint={conversationHint}
          />
        )}
```

- [ ] **Step 4: Run App.hint tests to verify they pass**

```bash
cd frontend && npx vitest run src/__tests__/App.hint.test.jsx
```
Expected: 2 PASS.

- [ ] **Step 5: Run full frontend suite**

```bash
cd frontend && npx vitest run
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx frontend/src/__tests__/App.hint.test.jsx
git commit -m "feat: seed conversationHint from topic starter in App, reset on new session"
```

---

### Task 4: Translation → conversationHint and Translation → Pronunciation Practice button

**Files:**
- Modify: `frontend/src/__tests__/TranslationView.test.jsx`
- Modify: `frontend/src/__tests__/App.crossmode.test.jsx`
- Modify: `frontend/src/components/TranslationView.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add tests to TranslationView.test.jsx and App.crossmode.test.jsx**

In `frontend/src/__tests__/TranslationView.test.jsx`, add these two tests inside the existing `describe('TranslationView', ...)` block:

```jsx
  it('accepts onResult and onPractice props without crashing', () => {
    render(<TranslationView config={DEFAULT_CONFIG} onResult={vi.fn()} onPractice={vi.fn()} />)
    expect(screen.getByText('Record English phrase')).toBeInTheDocument()
  })

  it('does not show Practice button when there is no result', () => {
    render(<TranslationView config={DEFAULT_CONFIG} onResult={vi.fn()} onPractice={vi.fn()} />)
    expect(screen.queryByText(/practice/i)).not.toBeInTheDocument()
  })
```

In `frontend/src/__tests__/App.crossmode.test.jsx`, add at the end of the file:

```jsx
describe('App — Translation tab', () => {
  it('switches to Translation view when Translation tab clicked', () => {
    const { container } = render(<App />)
    fireEvent.click(screen.getByText('Translation'))
    expect(container.querySelector('.translation-view')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify new tests pass immediately**

```bash
cd frontend && npx vitest run src/__tests__/TranslationView.test.jsx src/__tests__/App.crossmode.test.jsx
```
Expected: all PASS (the two new tests test existing behavior; the tab switch test works with current code).

- [ ] **Step 3: Add onResult and onPractice props + Practice button to TranslationView.jsx**

In `frontend/src/components/TranslationView.jsx`:

Replace the function signature (line 3):
```jsx
export default function TranslationView({ config, onResult, onPractice }) {
```

In `submitAudio`, after `setResult({ english: data.english, spanish: data.spanish })` (line 54), add the `onResult` call on the next line:
```jsx
      setResult({ english: data.english, spanish: data.spanish })
      onResult?.({ text: data.spanish, source: 'translation' })
```

Replace the result display block (lines 95–99):
```jsx
      {result && (
        <div className="translation-result">
          <p className="translation-english">{result.english}</p>
          <p className="translation-spanish">{result.spanish}</p>
          <button
            className="translation-practice-btn"
            onClick={() => onPractice?.(result.spanish, 'translation')}
          >
            Practice pronunciation
          </button>
        </div>
      )}
```

- [ ] **Step 4: Add handleTranslationResult to App.jsx and wire TranslationView**

In `frontend/src/App.jsx`, add after `clearPronunciationTarget` (after line 43):
```jsx
  function handleTranslationResult(hint) {
    setConversationHint(hint)
  }
```

Replace the `TranslationView` render line (line 108):
```jsx
        {mode === 'translation' && (
          <TranslationView
            config={config}
            onResult={handleTranslationResult}
            onPractice={handlePractice}
          />
        )}
```

- [ ] **Step 5: Run full frontend suite**

```bash
cd frontend && npx vitest run
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx frontend/src/components/TranslationView.jsx frontend/src/__tests__/TranslationView.test.jsx frontend/src/__tests__/App.crossmode.test.jsx
git commit -m "feat: translation result updates conversationHint; Practice pronunciation button on translation result"
```

---

## Manual Smoke Tests

After all four tasks complete and tests pass:

1. **Topic starter hint** — open app, Conversation tab. Hint strip shows below record button with "Try saying" label and the topic's Spanish starter phrase. Clicking Hide collapses it; Show restores it.
2. **Topic change resets hint** — change topic in Coaching Setup. Hint updates to new topic's starter phrase.
3. **New Conversation resets hint** — click New Conversation. Hint resets to current topic's starter (replacing any translation hint).
4. **Translation → hint** — go to Translation tab, record an English phrase, get a result. Switch back to Conversation tab. Hint now shows the Spanish translation with "You translated" label.
5. **Translation → Pronunciation** — get a translation result. Click "Practice pronunciation". Pronunciation tab opens with the Spanish phrase pre-loaded and "From translation" in the header. ← Back returns to Translation tab.
6. **Conversation → Pronunciation source label** — in Conversation tab, get a coach response. Click Practice on the coach bubble. Pronunciation tab shows "From conversation" in the header.
