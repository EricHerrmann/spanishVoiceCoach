# Phase B — Pronunciation Practice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Pronunciation Practice mode with two sub-tabs (Vocabulary and Challenges), plus a "Practice" button on coach turn bubbles that sends a phrase directly into pronunciation mode.

**Architecture:** `PronunciationView` replaces the Phase A placeholder. It has internal `tab` state (`'vocabulary' | 'challenges'`) and accepts an optional `pronunciationTarget` prop — when set, it bypasses tabs and shows a single-phrase scoring UI. Sub-feature C wires a `pronunciationTarget` state in `App.jsx` with a callback passed into `ConversationView` → `Transcript`, so clicking "Practice" on any coach turn sets `mode` to `'pronunciation'` and populates `pronunciationTarget`. All sub-features share the same scoring pipeline: record audio → `POST /pronunciation/evaluate` → display score + feedback + issues.

**Tech Stack:** FastAPI (existing), ClaudeProvider tool-use pattern (existing), Whisper STT (existing), React + Vite (existing), Vitest + React Testing Library (existing), pytest (existing).

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/data/pronunciation_challenges.json` | Create | Phonetically challenging Spanish words/phrases |
| `backend/ai/claude.py` | Modify | Add `evaluate_pronunciation()` method with tool use |
| `backend/main.py` | Modify | Add `GET /pronunciation/challenges`, `POST /pronunciation/evaluate` |
| `tests/unit/test_pronunciation.py` | Create | Pronunciation endpoint tests |
| `frontend/src/components/PronunciationView.jsx` | Modify | Replace placeholder — vocabulary tab, challenges tab, single-phrase mode |
| `frontend/src/components/Transcript.jsx` | Modify | Add "Practice" button on coach turns |
| `frontend/src/components/ConversationView.jsx` | Modify | Forward `onPractice` prop to Transcript |
| `frontend/src/App.jsx` | Modify | Add `pronunciationTarget` state, wire callbacks |
| `frontend/src/App.css` | Modify | Add pronunciation view styles and practice button style |
| `frontend/src/__tests__/PronunciationView.test.jsx` | Create | PronunciationView unit tests |
| `frontend/src/__tests__/Transcript.test.jsx` | Create | Practice button unit test |

---

## Task 1: Pronunciation data + backend endpoints + tests

**Files:**
- Create: `backend/data/pronunciation_challenges.json`
- Modify: `backend/ai/claude.py`
- Modify: `backend/main.py`
- Create: `tests/unit/test_pronunciation.py`

- [ ] **Step 1.1: Create pronunciation_challenges.json**

Create `backend/data/pronunciation_challenges.json`:

```json
[
  {
    "id": "pc001",
    "target": "perro",
    "sound_focus": "rr",
    "hint": "Roll the 'rr' — vibrate the tongue tip rapidly against the ridge behind your upper teeth."
  },
  {
    "id": "pc002",
    "target": "España",
    "sound_focus": "ñ",
    "hint": "The 'ñ' sounds like 'ny' in 'canyon' — nasal air through the palate."
  },
  {
    "id": "pc003",
    "target": "bueno",
    "sound_focus": "b/v",
    "hint": "Spanish 'b' and 'v' are the same sound — a soft bilabial, not the hard English 'b'."
  },
  {
    "id": "pc004",
    "target": "mujer",
    "sound_focus": "j",
    "hint": "The Spanish 'j' is a strong 'h' sound — like clearing your throat lightly."
  },
  {
    "id": "pc005",
    "target": "para",
    "sound_focus": "vowel purity",
    "hint": "Spanish 'a' is a clean, short vowel — no glide at the end like English 'ah'."
  },
  {
    "id": "pc006",
    "target": "ferrocarril",
    "sound_focus": "rr",
    "hint": "Two 'rr' sounds in one word. Say 'ferro' (ff-EH-rroh) then 'carril' (cah-RREEL)."
  },
  {
    "id": "pc007",
    "target": "verde",
    "sound_focus": "b/v",
    "hint": "The 'v' in 'verde' is soft, almost like a 'b' — lips barely touching."
  },
  {
    "id": "pc008",
    "target": "niño",
    "sound_focus": "ñ",
    "hint": "Hold the 'ny' sound for a beat — 'NEE-nyoh', not 'NEE-noh'."
  },
  {
    "id": "pc009",
    "target": "hola",
    "sound_focus": "h (silent)",
    "hint": "The 'h' is completely silent in Spanish — say 'OH-lah'."
  },
  {
    "id": "pc010",
    "target": "gente",
    "sound_focus": "g before e/i",
    "hint": "'g' before 'e' or 'i' sounds like Spanish 'j' — a strong 'h'. Say 'HEN-teh'."
  },
  {
    "id": "pc011",
    "target": "quiero",
    "sound_focus": "vowel purity",
    "hint": "Keep the 'ie' diphthong crisp: 'KYEH-roh'. Don't add an extra vowel between them."
  },
  {
    "id": "pc012",
    "target": "trabajar",
    "sound_focus": "j",
    "hint": "Strong 'h' on the 'j': 'trah-bah-HAHR'. The final 'r' is tapped, not rolled."
  }
]
```

- [ ] **Step 1.2: Write failing backend tests**

Create `tests/unit/test_pronunciation.py`:

```python
import os
from unittest.mock import patch
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

from fastapi.testclient import TestClient
from backend.main import app

FIXTURE_WAV = os.path.join(os.path.dirname(__file__), "..", "fixtures", "hola_sample.wav")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
requires_api_key = pytest.mark.skipif(
    not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "test-key",
    reason="ANTHROPIC_API_KEY not set or is a test key",
)

client = TestClient(app)


class TestGetPronunciationChallenges:
    def test_returns_list(self):
        response = client.get("/pronunciation/challenges")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_challenges_have_required_fields(self):
        response = client.get("/pronunciation/challenges")
        for challenge in response.json():
            assert "id" in challenge
            assert "target" in challenge
            assert "sound_focus" in challenge
            assert "hint" in challenge

    def test_returns_all_challenges(self):
        response = client.get("/pronunciation/challenges")
        assert len(response.json()) >= 10


class TestPronunciationEvaluate:
    def test_bad_audio_returns_structured_error(self):
        response = client.post(
            "/pronunciation/evaluate",
            data={"target": "hola"},
            files={"audio": ("bad.wav", b"not-a-wav", "audio/wav")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert data["score"] is None
        assert data["transcript"] is None

    def test_response_shape_with_mocked_evaluate(self):
        mock_eval = {"score": 85, "feedback": "Good effort!", "issues": []}
        with patch("backend.main.claude_provider") as mock_provider:
            mock_provider.evaluate_pronunciation.return_value = mock_eval
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/pronunciation/evaluate",
                    data={"target": "hola"},
                    files={"audio": ("test.wav", f, "audio/wav")},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 85
        assert data["feedback"] == "Good effort!"
        assert data["issues"] == []
        assert data["error"] is None
        assert data["transcript"] is not None

    def test_response_shape_with_issues(self):
        mock_eval = {
            "score": 60,
            "feedback": "Work on the rr sound.",
            "issues": [{"sound": "rr", "said": "r", "expected": "rr"}],
        }
        with patch("backend.main.claude_provider") as mock_provider:
            mock_provider.evaluate_pronunciation.return_value = mock_eval
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/pronunciation/evaluate",
                    data={"target": "perro"},
                    files={"audio": ("test.wav", f, "audio/wav")},
                )
        assert response.status_code == 200
        data = response.json()
        assert len(data["issues"]) == 1
        assert data["issues"][0]["sound"] == "rr"

    def test_evaluate_error_returns_structured_error(self):
        from backend.session import TurnError
        with patch("backend.main.claude_provider") as mock_provider:
            mock_provider.evaluate_pronunciation.return_value = TurnError(
                stage="ai", message="API down", recoverable=True
            )
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/pronunciation/evaluate",
                    data={"target": "hola"},
                    files={"audio": ("test.wav", f, "audio/wav")},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert data["score"] is None

    @requires_api_key
    def test_live_evaluate_returns_score(self):
        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/pronunciation/evaluate",
                data={"target": "hola"},
                files={"audio": ("test.wav", f, "audio/wav")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 100
        assert data["feedback"] is not None
        assert isinstance(data["issues"], list)
```

- [ ] **Step 1.3: Run to confirm tests fail**

```bash
uv run pytest tests/unit/test_pronunciation.py -v
```

Expected: FAIL — `GET /pronunciation/challenges` returns 404, `POST /pronunciation/evaluate` returns 404.

- [ ] **Step 1.4: Add evaluate_pronunciation() to ClaudeProvider**

In `backend/ai/claude.py`, add the tool definition constant after `_TOOL_DEFINITION`:

```python
_PRONUNCIATION_TOOL = {
    "name": "evaluate_pronunciation",
    "description": "Return a structured pronunciation evaluation for a Spanish phrase.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": "Overall pronunciation score from 0 to 100.",
            },
            "feedback": {
                "type": "string",
                "description": "Brief, encouraging feedback on the pronunciation attempt.",
            },
            "issues": {
                "type": "array",
                "description": "Specific sound issues identified. Empty list if none.",
                "items": {
                    "type": "object",
                    "properties": {
                        "sound": {
                            "type": "string",
                            "description": "The phoneme or sound pattern (e.g. 'rr', 'ñ', 'b/v').",
                        },
                        "said": {
                            "type": "string",
                            "description": "What the learner appears to have pronounced.",
                        },
                        "expected": {
                            "type": "string",
                            "description": "The correct pronunciation.",
                        },
                    },
                    "required": ["sound", "said", "expected"],
                },
            },
        },
        "required": ["score", "feedback", "issues"],
    },
}
```

Then add the method inside `ClaudeProvider`, after the `translate()` method (which is added in Phase A):

```python
    def evaluate_pronunciation(self, target: str, transcript: str) -> Union[dict, TurnError]:
        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                tools=[_PRONUNCIATION_TOOL],
                tool_choice={"type": "tool", "name": "evaluate_pronunciation"},
                messages=[{
                    "role": "user",
                    "content": (
                        "A Spanish learner attempted to say this phrase:\n\n"
                        f"Target: {target}\n"
                        f"Whisper transcript of their attempt: {transcript}\n\n"
                        "Evaluate their pronunciation by comparing the transcript to the target. "
                        "Give a score of 100 if the transcript matches the target exactly or very closely. "
                        "Identify any specific sounds that differ. Be encouraging."
                    ),
                }],
            )
            for block in response.content:
                if block.type == "tool_use" and block.name == "evaluate_pronunciation":
                    return block.input
            return TurnError(
                stage="ai", message="No evaluation block in Claude response", recoverable=True
            )
        except Exception as exc:
            return TurnError(
                stage="ai", message=f"Pronunciation evaluation failed: {exc}", recoverable=True
            )
```

- [ ] **Step 1.5: Add GET /pronunciation/challenges and POST /pronunciation/evaluate to main.py**

Add the challenges path constant near the existing `_FLASHCARD_DECK_PATH` line in `backend/main.py`:

```python
_PRONUNCIATION_CHALLENGES_PATH = pathlib.Path(__file__).parent / "data" / "pronunciation_challenges.json"
```

Add the two routes after the `translate` route:

```python
@app.get("/pronunciation/challenges")
def get_pronunciation_challenges():
    with open(_PRONUNCIATION_CHALLENGES_PATH) as f:
        return json.load(f)


@app.post("/pronunciation/evaluate")
async def pronunciation_evaluate(
    audio: UploadFile = File(...),
    target: str = Form(...),
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
            "transcript": None,
            "score": None,
            "feedback": None,
            "issues": None,
            "error": {
                "stage": stt_result.stage,
                "message": stt_result.message,
                "recoverable": stt_result.recoverable,
            },
        }

    _, transcript_norm = stt_result
    eval_result = claude_provider.evaluate_pronunciation(target, transcript_norm)

    if isinstance(eval_result, TurnError):
        return {
            "transcript": transcript_norm,
            "score": None,
            "feedback": None,
            "issues": None,
            "error": {
                "stage": eval_result.stage,
                "message": eval_result.message,
                "recoverable": eval_result.recoverable,
            },
        }

    return {
        "transcript": transcript_norm,
        "score": eval_result["score"],
        "feedback": eval_result["feedback"],
        "issues": eval_result["issues"],
        "error": None,
    }
```

- [ ] **Step 1.6: Run tests — expect PASS**

```bash
uv run pytest tests/unit/test_pronunciation.py -v
```

Expected: 8 tests PASS (7 unit + 1 live skipped).

- [ ] **Step 1.7: Run full backend suite**

```bash
uv run pytest -v
```

Expected: All existing tests + 11 new pronunciation tests PASS, 1 skipped.

- [ ] **Step 1.8: Commit**

```bash
git add backend/data/pronunciation_challenges.json \
        backend/ai/claude.py \
        backend/main.py \
        tests/unit/test_pronunciation.py
git commit -m "feat: pronunciation challenges data, ClaudeProvider.evaluate_pronunciation(), GET /pronunciation/challenges, POST /pronunciation/evaluate"
```

---

## Task 2: PronunciationView — Vocabulary + Challenges tabs + CSS + tests

**Files:**
- Modify: `frontend/src/components/PronunciationView.jsx` (replace placeholder)
- Modify: `frontend/src/App.css`
- Create: `frontend/src/__tests__/PronunciationView.test.jsx`

- [ ] **Step 2.1: Write failing PronunciationView tests**

Create `frontend/src/__tests__/PronunciationView.test.jsx`:

```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import PronunciationView from '../components/PronunciationView'

const MOCK_TOPICS = [{ id: 'general', label: 'General' }]
const MOCK_DECK = [
  { id: 'g001', english: 'hello', spanish: 'hola', level: 1, topic: 'general' },
  { id: 'g002', english: 'goodbye', spanish: 'adiós', level: 1, topic: 'general' },
]
const MOCK_CHALLENGES = [
  { id: 'pc001', target: 'perro', sound_focus: 'rr', hint: 'Roll the rr sound.' },
  { id: 'pc002', target: 'España', sound_focus: 'ñ', hint: 'Nasal palatal sound.' },
]

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url.includes('/topics')) {
      return Promise.resolve({ json: () => Promise.resolve(MOCK_TOPICS) })
    }
    if (url.includes('/flashcards/deck')) {
      return Promise.resolve({ json: () => Promise.resolve(MOCK_DECK) })
    }
    if (url.includes('/pronunciation/challenges')) {
      return Promise.resolve({ json: () => Promise.resolve(MOCK_CHALLENGES) })
    }
    return Promise.resolve({ json: () => Promise.resolve([]) })
  }))
})

afterEach(() => { vi.unstubAllGlobals() })

describe('PronunciationView — vocabulary tab (default)', () => {
  it('shows Vocabulary tab as active by default', async () => {
    render(<PronunciationView />)
    await waitFor(() => expect(screen.getByText('Vocabulary')).toBeInTheDocument())
    expect(screen.getByText('Vocabulary').className).toContain('pronunciation-tab--active')
  })

  it('shows Spanish target text from vocab deck', async () => {
    render(<PronunciationView />)
    await waitFor(() => expect(screen.getByText('hola')).toBeInTheDocument())
  })

  it('Record button is present when a target is shown', async () => {
    render(<PronunciationView />)
    await waitFor(() => screen.getByText('hola'))
    expect(screen.getByText('Record')).toBeInTheDocument()
  })

  it('Next card advances to second card', async () => {
    render(<PronunciationView />)
    await waitFor(() => screen.getByText('hola'))
    fireEvent.click(screen.getByText('Next card'))
    expect(screen.getByText('adiós')).toBeInTheDocument()
  })
})

describe('PronunciationView — challenges tab', () => {
  it('switching to Challenges tab shows challenge list', async () => {
    render(<PronunciationView />)
    await waitFor(() => screen.getByText('Challenges'))
    fireEvent.click(screen.getByText('Challenges'))
    await waitFor(() => expect(screen.getByText('perro')).toBeInTheDocument())
  })

  it('clicking a challenge sets it as the target', async () => {
    render(<PronunciationView />)
    await waitFor(() => screen.getByText('Challenges'))
    fireEvent.click(screen.getByText('Challenges'))
    await waitFor(() => screen.getByText('perro'))
    fireEvent.click(screen.getByText('perro'))
    expect(screen.getByText(/Roll the rr sound/)).toBeInTheDocument()
  })
})

describe('PronunciationView — single-phrase mode', () => {
  it('when pronunciationTarget is set, shows that phrase without tabs', () => {
    render(<PronunciationView pronunciationTarget="Muy bien, gracias." onClearTarget={vi.fn()} />)
    expect(screen.getByText('Muy bien, gracias.')).toBeInTheDocument()
    expect(screen.queryByText('Vocabulary')).not.toBeInTheDocument()
    expect(screen.queryByText('Challenges')).not.toBeInTheDocument()
  })

  it('shows a back button in single-phrase mode', () => {
    render(<PronunciationView pronunciationTarget="Muy bien." onClearTarget={vi.fn()} />)
    expect(screen.getByText('← Back')).toBeInTheDocument()
  })

  it('back button calls onClearTarget', () => {
    const onClearTarget = vi.fn()
    render(<PronunciationView pronunciationTarget="Muy bien." onClearTarget={onClearTarget} />)
    fireEvent.click(screen.getByText('← Back'))
    expect(onClearTarget).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2.2: Run to verify tests fail**

```bash
cd frontend && npx vitest run src/__tests__/PronunciationView.test.jsx
```

Expected: FAIL — placeholder renders "Pronunciation practice — coming in Phase B."

- [ ] **Step 2.3: Replace PronunciationView.jsx with full implementation**

Replace `frontend/src/components/PronunciationView.jsx`:

```jsx
import { useState, useEffect, useRef } from 'react'

const BANDS = [
  { id: 'beginner', label: 'Beginner', min: 1, max: 2 },
  { id: 'elementary', label: 'Elementary', min: 3, max: 4 },
  { id: 'intermediate', label: 'Intermediate', min: 5, max: 6 },
  { id: 'advanced', label: 'Advanced', min: 7, max: 10 },
]

export default function PronunciationView({ pronunciationTarget, onClearTarget }) {
  const [tab, setTab] = useState('vocabulary')

  // Vocabulary tab state
  const [topics, setTopics] = useState([])
  const [selectedTopic, setSelectedTopic] = useState('general')
  const [selectedBand, setSelectedBand] = useState('intermediate')
  const [vocabDeck, setVocabDeck] = useState([])
  const [vocabIndex, setVocabIndex] = useState(0)

  // Challenges tab state
  const [challenges, setChallenges] = useState([])
  const [selectedChallenge, setSelectedChallenge] = useState(null)

  // Scoring state
  const [scoringState, setScoringState] = useState('idle') // idle | recording | processing | done
  const [evalResult, setEvalResult] = useState(null)
  const [evalError, setEvalError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  useEffect(() => {
    fetch('/topics').then((r) => r.json()).then(setTopics).catch(() => {})
    fetch('/pronunciation/challenges').then((r) => r.json()).then(setChallenges).catch(() => {})
  }, [])

  useEffect(() => {
    if (pronunciationTarget) return
    const band = BANDS.find((b) => b.id === selectedBand)
    fetch(`/flashcards/deck?topic=${selectedTopic}&level_min=${band.min}&level_max=${band.max}`)
      .then((r) => r.json())
      .then((data) => { setVocabDeck(data); setVocabIndex(0); resetScoring() })
      .catch(() => {})
  }, [selectedTopic, selectedBand, pronunciationTarget]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (pronunciationTarget) resetScoring()
  }, [pronunciationTarget])

  function resetScoring() {
    setScoringState('idle')
    setEvalResult(null)
    setEvalError(null)
  }

  const target = pronunciationTarget
    ? pronunciationTarget
    : tab === 'vocabulary'
    ? vocabDeck[vocabIndex]?.spanish ?? null
    : selectedChallenge?.target ?? null

  const activeHint = tab === 'challenges' && !pronunciationTarget ? selectedChallenge?.hint : null

  async function startRecording() {
    setEvalError(null)
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
        setScoringState('processing')
        await submitAudio(new Blob(chunksRef.current, { type: recorder.mimeType }), target)
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setScoringState('recording')
    } catch (err) {
      setEvalError(err.message)
      setScoringState('idle')
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop()
  }

  async function submitAudio(blob, currentTarget) {
    const form = new FormData()
    form.append('audio', blob, 'recording.wav')
    form.append('target', currentTarget)
    try {
      const res = await fetch('/pronunciation/evaluate', { method: 'POST', body: form })
      const data = await res.json()
      if (data.error) { setEvalError(data.error.message); setScoringState('idle'); return }
      setEvalResult(data)
      setScoringState('done')
    } catch {
      setEvalError('Network error')
      setScoringState('idle')
    }
  }

  const isRecording = scoringState === 'recording'
  const isProcessing = scoringState === 'processing'
  const disabled = isProcessing || !target

  return (
    <div className="pronunciation-view">
      {pronunciationTarget ? (
        <div className="pronunciation-external-header">
          <span className="pronunciation-source-label">From conversation</span>
          <button
            className="pronunciation-back-btn"
            onClick={() => { onClearTarget?.(); resetScoring() }}
          >
            ← Back
          </button>
        </div>
      ) : (
        <div className="pronunciation-sub-tabs">
          {['vocabulary', 'challenges'].map((t) => (
            <button
              key={t}
              className={`pronunciation-tab${tab === t ? ' pronunciation-tab--active' : ''}`}
              onClick={() => { setTab(t); resetScoring() }}
            >
              {t === 'vocabulary' ? 'Vocabulary' : 'Challenges'}
            </button>
          ))}
        </div>
      )}

      {!pronunciationTarget && tab === 'vocabulary' && (
        <div className="pronunciation-vocab-controls">
          <select
            value={selectedTopic}
            onChange={(e) => setSelectedTopic(e.target.value)}
          >
            {topics.map((tp) => (
              <option key={tp.id} value={tp.id}>{tp.label}</option>
            ))}
          </select>
          <div className="pronunciation-bands">
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
      )}

      {!pronunciationTarget && tab === 'challenges' && !selectedChallenge && (
        <ul className="pronunciation-challenge-list">
          {challenges.map((ch) => (
            <li key={ch.id}>
              <button
                className="pronunciation-challenge-item"
                onClick={() => { setSelectedChallenge(ch); resetScoring() }}
              >
                <span className="pronunciation-challenge-target">{ch.target}</span>
                <span className="pronunciation-challenge-focus">{ch.sound_focus}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {target && (
        <div className="pronunciation-scoring">
          <p className="pronunciation-target">{target}</p>

          {activeHint && (
            <p className="pronunciation-hint">{activeHint}</p>
          )}

          {evalError && <p className="pronunciation-error">{evalError}</p>}

          {evalResult && (
            <div className="pronunciation-result">
              <span className="pronunciation-score">{evalResult.score}</span>
              <p className="pronunciation-feedback">{evalResult.feedback}</p>
              {evalResult.issues.length > 0 && (
                <ul className="pronunciation-issues">
                  {evalResult.issues.map((issue, i) => (
                    <li key={i} className="pronunciation-issue">
                      <span className="issue-sound">{issue.sound}</span>
                      {' — said '}
                      <span className="issue-said">{issue.said}</span>
                      {', expected '}
                      <span className="issue-expected">{issue.expected}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <div className="pronunciation-actions">
            {tab === 'challenges' && !pronunciationTarget && selectedChallenge && (
              <button
                className="pronunciation-back-btn"
                onClick={() => { setSelectedChallenge(null); resetScoring() }}
              >
                ← Challenges
              </button>
            )}
            <button
              className={`voice-btn voice-btn--${scoringState === 'done' ? 'idle' : scoringState}`}
              onClick={isRecording ? stopRecording : startRecording}
              disabled={disabled}
            >
              {isRecording ? 'Stop' : isProcessing ? 'Processing…' : 'Record'}
            </button>
            {!pronunciationTarget && tab === 'vocabulary' && vocabDeck.length > 0 && (
              <button
                onClick={() => { setVocabIndex((i) => Math.min(i + 1, vocabDeck.length - 1)); resetScoring() }}
                disabled={vocabIndex >= vocabDeck.length - 1}
              >
                Next card
              </button>
            )}
          </div>
        </div>
      )}

      {!target && tab === 'vocabulary' && vocabDeck.length === 0 && (
        <p className="pronunciation-empty">No cards for this topic and level.</p>
      )}
    </div>
  )
}
```

- [ ] **Step 2.4: Add pronunciation CSS to App.css**

Append to `frontend/src/App.css`:

```css
/* ── Pronunciation ──────────────────────────────────── */

.pronunciation-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  gap: 16px;
  overflow-y: auto;
}

.pronunciation-sub-tabs {
  display: flex;
  gap: 4px;
}

.pronunciation-tab {
  padding: 3px 12px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
}

.pronunciation-tab--active {
  background: var(--code-bg);
  border-color: var(--border);
  color: var(--text-h);
  font-weight: 500;
}

.pronunciation-tab:hover:not(.pronunciation-tab--active) {
  color: var(--text-h);
}

.pronunciation-external-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pronunciation-source-label {
  font-size: 11px;
  color: var(--text);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.pronunciation-back-btn {
  font-size: 13px;
  background: none;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 3px 10px;
  cursor: pointer;
  font-family: inherit;
  color: var(--text);
}

.pronunciation-vocab-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pronunciation-bands {
  display: flex;
  gap: 4px;
}

.pronunciation-challenge-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pronunciation-challenge-item {
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: none;
  cursor: pointer;
  font-family: inherit;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pronunciation-challenge-item:hover {
  border-color: var(--accent-border);
  background: var(--accent-bg);
}

.pronunciation-challenge-target {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-h);
}

.pronunciation-challenge-focus {
  font-size: 12px;
  color: var(--text);
  background: var(--code-bg);
  border-radius: 4px;
  padding: 2px 6px;
}

.pronunciation-scoring {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pronunciation-target {
  font-size: 28px;
  font-weight: 500;
  color: var(--text-h);
  margin: 0;
  text-align: center;
  padding: 24px;
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
}

.pronunciation-hint {
  font-size: 13px;
  color: var(--text);
  margin: 0;
  line-height: 1.45;
}

.pronunciation-result {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pronunciation-score {
  font-size: 48px;
  font-weight: 700;
  color: var(--text-h);
  text-align: center;
}

.pronunciation-feedback {
  font-size: 14px;
  color: var(--text-h);
  margin: 0;
  text-align: center;
}

.pronunciation-issues {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pronunciation-issue {
  font-size: 13px;
  color: var(--text);
}

.issue-sound {
  font-weight: 600;
  color: var(--text-h);
}

.issue-expected {
  color: var(--accent);
  font-weight: 500;
}

.pronunciation-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
}

.pronunciation-error {
  font-size: 13px;
  color: var(--accent);
  margin: 0;
}

.pronunciation-empty {
  color: var(--text);
  font-size: 14px;
  text-align: center;
  padding: 32px;
}
```

- [ ] **Step 2.5: Run PronunciationView tests — expect PASS**

```bash
cd frontend && npx vitest run src/__tests__/PronunciationView.test.jsx
```

Expected: 10 tests PASS.

- [ ] **Step 2.6: Run full frontend suite**

```bash
cd frontend && npx vitest run
```

Expected: All tests PASS.

- [ ] **Step 2.7: Commit**

```bash
git add frontend/src/components/PronunciationView.jsx \
        frontend/src/App.css \
        frontend/src/__tests__/PronunciationView.test.jsx
git commit -m "feat: PronunciationView — vocabulary tab, challenges tab, single-phrase mode, scoring UI"
```

---

## Task 3: Sub-feature C — "Practice" button in Transcript + App.jsx cross-mode wiring + tests

**Files:**
- Modify: `frontend/src/components/Transcript.jsx`
- Modify: `frontend/src/components/ConversationView.jsx`
- Modify: `frontend/src/App.jsx`
- Create: `frontend/src/__tests__/Transcript.test.jsx`

- [ ] **Step 3.1: Write failing Transcript test**

Create `frontend/src/__tests__/Transcript.test.jsx`:

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Transcript from '../components/Transcript'

describe('Transcript — Practice button', () => {
  it('coach turns have a Practice button', () => {
    const turns = [
      { speaker: 'coach', coach_text: 'Muy bien, sigamos practicando.' },
    ]
    render(<Transcript turns={turns} onPractice={vi.fn()} />)
    expect(screen.getByText('Practice')).toBeInTheDocument()
  })

  it('user turns do not have a Practice button', () => {
    const turns = [
      { speaker: 'user', transcript_norm: 'Quiero hablar más.' },
    ]
    render(<Transcript turns={turns} onPractice={vi.fn()} />)
    expect(screen.queryByText('Practice')).not.toBeInTheDocument()
  })

  it('clicking Practice calls onPractice with the coach text', () => {
    const onPractice = vi.fn()
    const turns = [
      { speaker: 'coach', coach_text: 'Muy bien, sigamos practicando.' },
    ]
    render(<Transcript turns={turns} onPractice={onPractice} />)
    fireEvent.click(screen.getByText('Practice'))
    expect(onPractice).toHaveBeenCalledWith('Muy bien, sigamos practicando.')
  })

  it('works without onPractice prop (no crash)', () => {
    const turns = [{ speaker: 'coach', coach_text: 'Hola.' }]
    render(<Transcript turns={turns} />)
    fireEvent.click(screen.getByText('Practice'))
    // No error thrown
  })
})
```

- [ ] **Step 3.2: Run to verify test fails**

```bash
cd frontend && npx vitest run src/__tests__/Transcript.test.jsx
```

Expected: FAIL — no "Practice" button rendered on coach turns.

- [ ] **Step 3.3: Update Transcript.jsx to add Practice button on coach turns**

Replace the contents of `frontend/src/components/Transcript.jsx`:

```jsx
import { useState } from 'react'

export default function Transcript({ turns, onPractice }) {
  const [collapsed, setCollapsed] = useState(new Set())

  function toggle(i) {
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  return (
    <div className="transcript">
      {turns.map((turn, i) => {
        const isCollapsed = collapsed.has(i)
        const text = turn.speaker === 'user' ? turn.transcript_norm : turn.coach_text
        return (
          <div key={i} className={`turn turn--${turn.speaker}`}>
            <div className="turn-header">
              <span className="turn-label">{turn.speaker === 'user' ? 'You' : 'Coach'}</span>
              <button
                className="turn-toggle"
                onClick={() => toggle(i)}
                aria-label={isCollapsed ? 'Show text' : 'Hide text'}
              >
                {isCollapsed ? 'Show' : 'Hide'}
              </button>
              {turn.speaker === 'coach' && (
                <button
                  className="turn-practice-btn"
                  onClick={() => onPractice?.(text)}
                  aria-label="Practice this phrase"
                >
                  Practice
                </button>
              )}
            </div>
            <span className={`turn-text${isCollapsed ? ' turn-text--hidden' : ''}`}>
              {isCollapsed ? '···' : text}
            </span>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 3.4: Add practice button CSS to App.css**

Append to `frontend/src/App.css`:

```css
/* ── Turn practice button ───────────────────────────── */

.turn-practice-btn {
  font-size: 11px;
  color: var(--text);
  background: none;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 6px;
  cursor: pointer;
  font-family: inherit;
}

.turn-practice-btn:hover {
  color: var(--text-h);
  border-color: var(--accent-border);
}
```

- [ ] **Step 3.5: Run Transcript tests — expect PASS**

```bash
cd frontend && npx vitest run src/__tests__/Transcript.test.jsx
```

Expected: 4 tests PASS.

- [ ] **Step 3.6: Update ConversationView.jsx to accept and forward onPractice**

Replace `frontend/src/components/ConversationView.jsx`:

```jsx
import VoiceButton from './VoiceButton'
import Transcript from './Transcript'

export default function ConversationView({ state, turns, error, onRecord, onStop, onPractice }) {
  return (
    <>
      <Transcript turns={turns} onPractice={onPractice} />
      <VoiceButton state={state} onRecord={onRecord} onStop={onStop} error={error} />
    </>
  )
}
```

- [ ] **Step 3.7: Update App.jsx to wire pronunciationTarget state**

Find in `frontend/src/App.jsx`:

```jsx
  const [mode, setMode] = useState('conversation')
  const { state, turns, corrections, error, startRecording, stopRecording, newSession, loadSession } = useVoice()
```

Replace with:

```jsx
  const [mode, setMode] = useState('conversation')
  const [pronunciationTarget, setPronunciationTarget] = useState(null)
  const { state, turns, corrections, error, startRecording, stopRecording, newSession, loadSession } = useVoice()

  function handlePractice(text) {
    setPronunciationTarget(text)
    setMode('pronunciation')
  }

  function clearPronunciationTarget() {
    setPronunciationTarget(null)
  }
```

Find in `frontend/src/App.jsx`:

```jsx
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
```

Replace with:

```jsx
        {mode === 'conversation' && (
          <ConversationView
            state={state}
            turns={turns}
            error={error}
            onRecord={startRecording}
            onStop={stopRecording}
            onPractice={handlePractice}
          />
        )}
        {mode === 'flashcards' && <FlashcardsView />}
        {mode === 'translation' && <TranslationView config={config} />}
        {mode === 'pronunciation' && (
          <PronunciationView
            pronunciationTarget={pronunciationTarget}
            onClearTarget={clearPronunciationTarget}
          />
        )}
```

Also add the PronunciationView import at the top of `frontend/src/App.jsx` alongside the other imports:

```jsx
import PronunciationView from './components/PronunciationView'
```

- [ ] **Step 3.8: Run full frontend suite**

```bash
cd frontend && npx vitest run
```

Expected: All tests PASS — Transcript tests (4 new), PronunciationView tests (10), NavTabs tests (3), FlashcardsView tests (7), TranslationView tests (3), and all existing app tests.

- [ ] **Step 3.9: Commit**

```bash
git add frontend/src/components/Transcript.jsx \
        frontend/src/components/ConversationView.jsx \
        frontend/src/App.jsx \
        frontend/src/App.css \
        frontend/src/__tests__/Transcript.test.jsx
git commit -m "feat: Practice button on coach turns, cross-mode pronunciationTarget prop handoff"
```

---

## Task 4: Full suite + docs update

**Files:**
- Modify: `claudeSpanishCoachPlan.md`
- Modify: `docs/manualTestPlan.md`

- [ ] **Step 4.1: Run complete backend + frontend test suite**

```bash
uv run pytest -v
cd frontend && npx vitest run
```

Expected:
- Backend: all existing tests + 11 new pronunciation tests PASS, 1 skipped.
- Frontend: all existing tests + 18 new tests PASS (Transcript 4, PronunciationView 10, NavTabs 3, FlashcardsView 7, TranslationView 3). Zero failures.

- [ ] **Step 4.2: Manual smoke test**

Start backend and frontend:

```bash
# Terminal 1
uv run --env-file .env uvicorn backend.main:app --reload --port 8001

# Terminal 2
cd frontend && npm run dev
```

Open `http://localhost:5173`. Verify:

**Vocabulary tab:**
- [ ] Click the Pronunciation tab — Vocabulary sub-tab shown by default
- [ ] Spanish word appears as the target phrase
- [ ] Click Record, say the word, click Stop — score, feedback, and any issues appear
- [ ] Click Next card — new word shown, scoring panel resets

**Challenges tab:**
- [ ] Click Challenges sub-tab — list of phonetic challenges appears
- [ ] Click "perro" — target phrase shown with hint text
- [ ] Record the phrase — score and feedback appear
- [ ] Click ← Challenges — returns to challenge list

**Cross-mode (Sub-feature C):**
- [ ] Go to Conversation tab, conduct a brief session
- [ ] Click Practice on any coach turn bubble
- [ ] App switches to Pronunciation tab showing "From conversation" header and the coach phrase as target
- [ ] Record the phrase — score and feedback appear
- [ ] Click ← Back — "From conversation" header disappears, normal tabs return

**Regression:**
- [ ] Conversation tab: full voice session works normally
- [ ] Flashcards tab: topic/level filtering, flip, and deck navigation work
- [ ] Translation tab: record → translate → TTS round-trip works

- [ ] **Step 4.3: Update claudeSpanishCoachPlan.md**

Mark Phase B tasks complete and add sign-off note. Update the status table row for Phase B to ✅ Complete.

- [ ] **Step 4.4: Add Phase B procedures to docs/manualTestPlan.md**

Append to `docs/manualTestPlan.md`:

```markdown
## Phase B — Pronunciation Practice

**Goal:** Verify all three pronunciation sub-features function correctly and that sub-feature C correctly hands phrases across mode boundaries.

### Vocabulary tab
1. Click the Pronunciation tab — confirm Vocabulary sub-tab is active by default
2. Select a topic and level band
3. Confirm a Spanish word or phrase appears as the target
4. Click Record and say the target phrase
5. Click Stop — confirm score (0–100), feedback text, and any sound issues appear
6. Click Next card — confirm a new target appears and the scoring area resets

### Challenges tab
7. Click the Challenges sub-tab — confirm a list of phonetic challenges appears
8. Click any challenge (e.g. "perro") — confirm target and hint text appear
9. Record the phrase — confirm score and feedback appear
10. Click ← Challenges — confirm the list reappears

### Sub-feature C — Practice from conversation
11. Go to the Conversation tab and conduct a short session (2–3 turns)
12. Locate a coach turn bubble — confirm a small "Practice" button appears in the turn header
13. Click Practice — confirm the app switches to the Pronunciation tab showing "From conversation" header and the coach's phrase as the target
14. Record the phrase — confirm score and feedback appear
15. Click ← Back — confirm the normal Vocabulary/Challenges tabs return and pronunciationTarget is cleared

### Regression
16. Conversation tab: full voice session works normally
17. Flashcards tab: all existing functionality works
18. Translation tab: all existing functionality works
```

- [ ] **Step 4.5: Commit docs**

```bash
git add claudeSpanishCoachPlan.md docs/manualTestPlan.md
git commit -m "docs: Phase B sign-off checklist and manual test procedures"
```
