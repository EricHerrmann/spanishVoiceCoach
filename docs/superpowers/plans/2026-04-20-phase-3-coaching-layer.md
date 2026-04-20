# Phase 3 — Coaching Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire all three coaching modes (on_demand / explicit / shadowing) end-to-end — backend routing, trigger detection, and frontend overlay + mode selector.

**Architecture:** `coach.py` detects correction-request trigger phrases and applies per-mode filtering after each `handle_turn()` call. `claude.py` emits mode-aware behavioral instructions in the system prompt. A new `CoachOverlay` component renders filtered corrections; a new `SessionConfig` component lets the user pick the mode before starting a conversation. `useVoice` restarts the session whenever the mode changes.

**Tech Stack:** Python 3.12 / FastAPI / pytest (backend); React + Vite / Vitest / @testing-library/react (frontend).

---

## File Map

**Modify — backend:**
- `backend/ai/claude.py` — replace hardcoded on_demand instruction with mode-aware prompt
- `backend/coach.py` — add `_user_requested_correction()`, `_apply_mode_routing()`, update `handle_turn()`
- `backend/main.py` — `/session/start` accepts optional `coaching_mode` in JSON body

**Modify — tests:**
- `tests/unit/test_ai_providers.py` — add behavioral prompt assertions for all three modes
- `tests/unit/test_coach.py` — add trigger detection tests + mode routing tests
- `tests/integration/test_turn_pipeline.py` — add test for coaching_mode body param

**Create — frontend:**
- `frontend/src/components/CoachOverlay.jsx`
- `frontend/src/components/SessionConfig.jsx`
- `frontend/src/__tests__/CoachOverlay.test.jsx`
- `frontend/src/__tests__/SessionConfig.test.jsx`

**Modify — frontend:**
- `frontend/src/hooks/useVoice.js` — accept `coachingMode` param, restart session on change, return `corrections`
- `frontend/src/App.jsx` — add `SessionConfig` + `CoachOverlay`, pass mode to `useVoice`

**Modify — docs:**
- `docs/manualTestPlan.md` — add Phase 3 procedures

---

## Task 1: Mode-aware system prompt

**Files:**
- Modify: `backend/ai/claude.py`
- Modify: `tests/unit/test_ai_providers.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_ai_providers.py` inside `TestClaudeProviderSystemPrompt` (after the existing tests):

```python
    def test_on_demand_prompt_instructs_no_auto_correction(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
                session = new_session(topic="food", level=5, ai_provider="claude", coaching_mode="on_demand")
                prompt = provider._build_system_prompt(session)
                assert "explicitly" in prompt.lower() or "only if" in prompt.lower()

    def test_explicit_prompt_instructs_always_correct(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
                session = new_session(topic="food", level=5, ai_provider="claude", coaching_mode="explicit")
                prompt = provider._build_system_prompt(session)
                assert "always" in prompt.lower()

    def test_shadowing_prompt_instructs_suppress_overlay(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
                session = new_session(topic="food", level=5, ai_provider="claude", coaching_mode="shadowing")
                prompt = provider._build_system_prompt(session)
                assert "empty corrections list" in prompt.lower() or "return an empty" in prompt.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_ai_providers.py::TestClaudeProviderSystemPrompt -v
```

Expected: 3 new tests FAIL (the hardcoded on_demand text won't match all assertions).

- [ ] **Step 3: Replace hardcoded instruction with mode-aware map in `backend/ai/claude.py`**

Replace the `_LEVEL_SCALE` block and `ClaudeProvider._build_system_prompt` so the file reads:

```python
import os
import anthropic
from typing import Union
from backend.ai.base import AbstractAIProvider
from backend.session import Session, CoachResponse, Correction, TurnError

_TOOL_DEFINITION = {
    "name": "get_coach_response",
    "description": "Return a structured coaching response to the student's Spanish utterance.",
    "input_schema": {
        "type": "object",
        "properties": {
            "coach_text": {
                "type": "string",
                "description": "The coach's Spanish reply to speak aloud.",
            },
            "corrections": {
                "type": "array",
                "description": "Grammar or vocabulary corrections. Empty list if none.",
                "items": {
                    "type": "object",
                    "properties": {
                        "original": {"type": "string"},
                        "corrected": {"type": "string"},
                        "explanation": {"type": "string"},
                        "triggered_by": {
                            "type": "string",
                            "enum": ["auto", "user_request"],
                        },
                    },
                    "required": ["original", "corrected", "explanation", "triggered_by"],
                },
            },
        },
        "required": ["coach_text", "corrections"],
    },
}

_LEVEL_SCALE = (
    "Level scale for reference:\n"
    "- 1–2 (Duolingo 5–30): Greetings, food, basic nouns. Simple present tense only.\n"
    "- 3–4 (Duolingo 30–70): Directions, simple sentences. Introduce past tense.\n"
    "- 5–6 (Duolingo 70–110): Stories, TV, work vocabulary. Full tense range, basic subjunctive.\n"
    "- 7–10 (Duolingo 110+): Near-native fluency, idioms, slang, complex grammar."
)

_MODE_INSTRUCTIONS = {
    "on_demand": (
        "Provide corrections ONLY if the student explicitly asks for feedback "
        "(e.g. 'Corrígeme', 'Was that right?', '¿Lo dije bien?', '¿Cómo se dice…?'). "
        "When correcting, set triggered_by to 'user_request'. "
        "Otherwise return an empty corrections list."
    ),
    "explicit": (
        "Always identify and correct grammar or vocabulary errors in the student's speech. "
        "Set triggered_by to 'auto' for each correction."
    ),
    "shadowing": (
        "When you detect an error, naturally weave the correct Spanish form into your reply "
        "without explicitly labelling it as a correction. "
        "Always return an empty corrections list."
    ),
}


class ClaudeProvider(AbstractAIProvider):
    """Anthropic Claude AI provider using tool use for structured output."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        self._client = anthropic.Anthropic(api_key=api_key)

    def _build_system_prompt(self, session: Session) -> str:
        mode_instruction = _MODE_INSTRUCTIONS.get(
            session.coaching_mode, _MODE_INSTRUCTIONS["on_demand"]
        )
        return (
            f"You are a Spanish conversation coach. "
            f"The student is practicing at level {session.level}/10.\n"
            f"Topic: {session.topic}. Coaching mode: {session.coaching_mode}.\n"
            f"Respond only in Spanish. "
            f"Keep vocabulary and grammar appropriate for level {session.level}.\n"
            f"{mode_instruction}\n\n"
            f"{_LEVEL_SCALE}"
        )

    def _build_messages(self, session: Session, user_text: str) -> list:
        messages = []
        for turn in session.turns:
            if turn.speaker == "user" and turn.transcript_norm:
                messages.append({"role": "user", "content": turn.transcript_norm})
            elif turn.speaker == "coach" and turn.coach_text:
                messages.append({"role": "assistant", "content": turn.coach_text})
        messages.append({"role": "user", "content": user_text})
        return messages

    def chat(self, session: Session, user_text: str) -> Union[CoachResponse, TurnError]:
        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": self._build_system_prompt(session),
                    "cache_control": {"type": "ephemeral"},
                }],
                tools=[_TOOL_DEFINITION],
                tool_choice={"type": "tool", "name": "get_coach_response"},
                messages=self._build_messages(session, user_text),
            )

            tool_block = next(
                (b for b in response.content if b.type == "tool_use"), None
            )
            if tool_block is None:
                return TurnError(
                    stage="ai",
                    message="No tool_use block in Claude response",
                    recoverable=True,
                )

            data = tool_block.input
            corrections = [
                Correction(
                    original=c["original"],
                    corrected=c["corrected"],
                    explanation=c["explanation"],
                    triggered_by=c["triggered_by"],
                )
                for c in data.get("corrections", [])
            ]
            return CoachResponse(coach_text=data["coach_text"], corrections=corrections)

        except Exception as exc:
            return TurnError(
                stage="ai",
                message=f"AI request failed: {exc}",
                recoverable=True,
            )
```

- [ ] **Step 4: Run all AI provider tests**

```bash
uv run pytest tests/unit/test_ai_providers.py -v
```

Expected: All tests pass (existing 8 + 3 new = 11 total).

- [ ] **Step 5: Commit**

```bash
git add backend/ai/claude.py tests/unit/test_ai_providers.py
git commit -m "feat: mode-aware system prompt instructions for on_demand/explicit/shadowing"
```

---

## Task 2: Trigger phrase detection

**Files:**
- Modify: `backend/coach.py`
- Modify: `tests/unit/test_coach.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_coach.py` (after existing imports, before `TestCoachSessionHandleTurn`):

```python
from backend.coach import _user_requested_correction


class TestUserRequestedCorrection:
    def test_corrigeme_triggers(self):
        assert _user_requested_correction("corrígeme") is True

    def test_corrigeme_no_accent_triggers(self):
        assert _user_requested_correction("corrigeme") is True

    def test_como_se_dice_triggers(self):
        assert _user_requested_correction("¿cómo se dice 'butter'?") is True

    def test_was_that_right_triggers(self):
        assert _user_requested_correction("was that right?") is True

    def test_case_insensitive(self):
        assert _user_requested_correction("CORRÍGEME por favor") is True

    def test_lo_dije_bien_triggers(self):
        assert _user_requested_correction("¿lo dije bien?") is True

    def test_normal_sentence_does_not_trigger(self):
        assert _user_requested_correction("quiero comer tacos") is False

    def test_empty_string_does_not_trigger(self):
        assert _user_requested_correction("") is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_coach.py::TestUserRequestedCorrection -v
```

Expected: ImportError — `_user_requested_correction` does not exist yet.

- [ ] **Step 3: Add trigger detection to `backend/coach.py`**

Replace the full contents of `backend/coach.py`:

```python
import re
from datetime import datetime, timezone
from typing import Union
from backend.session import Session, Turn, CoachResponse, TurnError, Correction
from backend.ai.base import AbstractAIProvider

_CORRECTION_REQUEST_PATTERNS = [
    r"corrígeme",
    r"corrigeme",
    r"¿cómo se dice",
    r"como se dice",
    r"was that right",
    r"is that right",
    r"correct me",
    r"¿lo dije bien",
    r"lo dije bien",
    r"¿está bien",
    r"esta bien lo que dije",
]


def _user_requested_correction(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in _CORRECTION_REQUEST_PATTERNS)


def _apply_mode_routing(
    corrections: list[Correction], coaching_mode: str, user_requested: bool
) -> list[Correction]:
    if coaching_mode == "explicit":
        return corrections
    if coaching_mode == "shadowing":
        return []
    # on_demand (default)
    return corrections if user_requested else []


class CoachSession:
    """Manages a coaching session: calls the AI provider and maintains turn history."""

    def __init__(self, session: Session, ai_provider: AbstractAIProvider):
        self.session = session
        self.ai_provider = ai_provider

    def handle_turn(self, user_text: str) -> Union[Turn, TurnError]:
        """Process a user turn: call AI, apply mode routing, append turns, return coach turn.

        Returns TurnError (as a value, not exception) if the AI provider fails.
        """
        now = datetime.now(timezone.utc)

        user_requested = _user_requested_correction(user_text)
        call_text = (
            user_text + "\n[The student is explicitly asking for correction on this turn.]"
            if user_requested
            else user_text
        )

        result = self.ai_provider.chat(self.session, call_text)

        user_turn = Turn(speaker="user", transcript_norm=user_text, timestamp=now)
        self.session.turns.append(user_turn)

        if isinstance(result, TurnError):
            error_turn = Turn(speaker="coach", timestamp=now, error=result)
            self.session.turns.append(error_turn)
            return result

        corrections = _apply_mode_routing(
            result.corrections, self.session.coaching_mode, user_requested
        )

        coach_turn = Turn(
            speaker="coach",
            coach_text=result.coach_text,
            corrections=corrections,
            timestamp=now,
        )
        self.session.turns.append(coach_turn)
        return coach_turn
```

- [ ] **Step 4: Run trigger detection tests**

```bash
uv run pytest tests/unit/test_coach.py::TestUserRequestedCorrection -v
```

Expected: All 8 trigger tests pass.

- [ ] **Step 5: Run full test suite to verify nothing regressed**

```bash
uv run pytest tests/ -q
```

Expected: 37 passing, 2 skipped (same as before — routing tests come in Task 3).

- [ ] **Step 6: Commit**

```bash
git add backend/coach.py tests/unit/test_coach.py
git commit -m "feat: trigger phrase detection and mode routing helpers in coach.py"
```

---

## Task 3: Coaching mode routing tests

**Files:**
- Modify: `tests/unit/test_coach.py`

- [ ] **Step 1: Write the failing routing tests**

Add to `tests/unit/test_coach.py` after `TestUserRequestedCorrection`:

```python
def _correction_fixture() -> Correction:
    return Correction(
        original="yo fui",
        corrected="fui",
        explanation="'yo' is optional in Spanish",
        triggered_by="auto",
    )


class TestCoachingModeRouting:
    def test_explicit_mode_returns_corrections(self):
        session = new_session(
            topic="food", level=5, ai_provider="claude", coaching_mode="explicit"
        )
        coach_response = CoachResponse(
            coach_text="¡Muy bien!", corrections=[_correction_fixture()]
        )
        coach = CoachSession(session, _mock_provider(coach_response))

        result = coach.handle_turn("yo fui al mercado")

        assert isinstance(result, Turn)
        assert len(result.corrections) == 1
        assert result.corrections[0].original == "yo fui"

    def test_explicit_mode_empty_corrections_returns_empty(self):
        session = new_session(
            topic="food", level=5, ai_provider="claude", coaching_mode="explicit"
        )
        coach_response = CoachResponse(coach_text="¡Muy bien!", corrections=[])
        coach = CoachSession(session, _mock_provider(coach_response))

        result = coach.handle_turn("quiero comer tacos")

        assert result.corrections == []

    def test_shadowing_mode_always_suppresses_corrections(self):
        session = new_session(
            topic="food", level=5, ai_provider="claude", coaching_mode="shadowing"
        )
        coach_response = CoachResponse(
            coach_text="Fui al mercado también.",
            corrections=[_correction_fixture()],
        )
        coach = CoachSession(session, _mock_provider(coach_response))

        result = coach.handle_turn("yo fui al mercado")

        assert isinstance(result, Turn)
        assert result.corrections == []

    def test_on_demand_without_trigger_suppresses_corrections(self):
        session = new_session(
            topic="food", level=5, ai_provider="claude", coaching_mode="on_demand"
        )
        coach_response = CoachResponse(
            coach_text="¡Muy bien!",
            corrections=[_correction_fixture()],
        )
        coach = CoachSession(session, _mock_provider(coach_response))

        result = coach.handle_turn("yo fui al mercado")  # no trigger phrase

        assert result.corrections == []

    def test_on_demand_with_trigger_shows_corrections(self):
        session = new_session(
            topic="food", level=5, ai_provider="claude", coaching_mode="on_demand"
        )
        coach_response = CoachResponse(
            coach_text="¡Muy bien! Deberías decir 'fui'.",
            corrections=[_correction_fixture()],
        )
        coach = CoachSession(session, _mock_provider(coach_response))

        result = coach.handle_turn("corrígeme, yo fui al mercado")

        assert len(result.corrections) == 1
        assert result.corrections[0].original == "yo fui"
```

- [ ] **Step 2: Run the routing tests to verify they fail**

```bash
uv run pytest tests/unit/test_coach.py::TestCoachingModeRouting -v
```

Expected: All 5 FAIL (routing logic is in coach.py but tests don't exist yet — they should actually pass since we already wrote the routing code in Task 2. If they do pass, skip Step 3).

- [ ] **Step 3: Run all coach tests to confirm they pass**

```bash
uv run pytest tests/unit/test_coach.py -v
```

Expected: All tests pass (5 existing `TestCoachSessionHandleTurn` + 8 `TestUserRequestedCorrection` + 5 `TestCoachingModeRouting` = 18 total).

Note: `test_session_passed_to_provider_has_correct_fields` asserts `called_text == "hola"`. With the trigger-note logic, "hola" does not match any pattern so `call_text` stays `"hola"`. This test continues to pass.

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest tests/ -q
```

Expected: ~50 passing, 2 skipped.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_coach.py
git commit -m "test: coaching mode routing tests for all three modes"
```

---

## Task 4: `/session/start` accepts coaching_mode

**Files:**
- Modify: `backend/main.py`
- Modify: `tests/integration/test_turn_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/integration/test_turn_pipeline.py` inside `TestSessionStart`:

```python
    def test_accepts_coaching_mode_in_body(self):
        client = make_client()
        response = client.post(
            "/session/start",
            json={"coaching_mode": "explicit"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "session_id" in body
        assert isinstance(body["session_id"], str)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestSessionStart::test_accepts_coaching_mode_in_body -v
```

Expected: FAIL — currently `/session/start` accepts no body; the JSON is ignored and a 200 is returned (this may actually pass as-is). If it passes already, the endpoint already handles unknown JSON gracefully — the important fix is making it *use* the mode. Continue.

- [ ] **Step 3: Update `backend/main.py` to accept `coaching_mode` from request body**

Replace the full contents of `backend/main.py`:

```python
import os
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from pydantic import BaseModel
from backend.session import Session, TurnError, new_session
from backend.stt import WhisperSTT
from backend.coach import CoachSession
from backend.ai.claude import ClaudeProvider

stt_provider = WhisperSTT()
claude_provider = ClaudeProvider()
sessions: dict[str, Session] = {}
app = FastAPI()


class SessionStartRequest(BaseModel):
    coaching_mode: str = "on_demand"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/session/start")
def session_start(body: SessionStartRequest | None = Body(default=None)):
    # TODO Phase 4: accept topic/level/ai_provider from request body
    coaching_mode = body.coaching_mode if body is not None else "on_demand"
    session = new_session(
        topic="general",
        level=5,
        ai_provider="claude",
        coaching_mode=coaching_mode,
    )
    sessions[session.id] = session
    return {"session_id": session.id}


@app.post("/turn")
async def post_turn(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
):
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        stt_result = stt_provider.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)

    if isinstance(stt_result, TurnError):
        return {
            "transcript_raw": None,
            "transcript_norm": None,
            "coach_text": None,
            "corrections": [],
            "error": {
                "stage": stt_result.stage,
                "message": stt_result.message,
                "recoverable": stt_result.recoverable,
            },
        }

    transcript_raw, transcript_norm = stt_result
    # CoachSession is re-instantiated per request; conversation history is
    # preserved via session.turns on the Session object, not on this instance.
    coach = CoachSession(session, claude_provider)
    turn_result = coach.handle_turn(transcript_norm)

    if isinstance(turn_result, TurnError):
        return {
            "transcript_raw": transcript_raw,
            "transcript_norm": transcript_norm,
            "coach_text": None,
            "corrections": [],
            "error": {
                "stage": turn_result.stage,
                "message": turn_result.message,
                "recoverable": turn_result.recoverable,
            },
        }

    return {
        "transcript_raw": transcript_raw,
        "transcript_norm": transcript_norm,
        "coach_text": turn_result.coach_text,
        "corrections": [
            {
                "original": c.original,
                "corrected": c.corrected,
                "explanation": c.explanation,
                "triggered_by": c.triggered_by,
            }
            for c in turn_result.corrections
        ],
        "error": None,
    }
```

- [ ] **Step 4: Run all session/integration tests**

```bash
uv run pytest tests/integration/test_turn_pipeline.py -v
```

Expected: All passing (3 non-skipped tests + the new one = 4 passing, 2 skipped).

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest tests/ -q
```

Expected: ~51 passing, 2 skipped.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/integration/test_turn_pipeline.py
git commit -m "feat: /session/start accepts coaching_mode in JSON body"
```

---

## Task 5: CoachOverlay component

**Files:**
- Create: `frontend/src/components/CoachOverlay.jsx`
- Create: `frontend/src/__tests__/CoachOverlay.test.jsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/__tests__/CoachOverlay.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import CoachOverlay from '../components/CoachOverlay'

describe('CoachOverlay', () => {
  it('renders nothing when corrections list is empty', () => {
    const { container } = render(<CoachOverlay corrections={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when corrections is null', () => {
    const { container } = render(<CoachOverlay corrections={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders original, corrected, and explanation for a single correction', () => {
    const corrections = [{
      original: 'yo fui',
      corrected: 'fui',
      explanation: "'yo' is optional in Spanish",
      triggered_by: 'auto',
    }]
    render(<CoachOverlay corrections={corrections} />)
    expect(screen.getByText('yo fui')).toBeInTheDocument()
    expect(screen.getByText('fui')).toBeInTheDocument()
    expect(screen.getByText(/'yo' is optional in Spanish/)).toBeInTheDocument()
  })

  it('renders multiple corrections', () => {
    const corrections = [
      { original: 'yo fui', corrected: 'fui', explanation: 'Optional pronoun', triggered_by: 'auto' },
      { original: 'el mercado', corrected: 'al mercado', explanation: "Missing 'a' contraction", triggered_by: 'user_request' },
    ]
    render(<CoachOverlay corrections={corrections} />)
    expect(screen.getByText('yo fui')).toBeInTheDocument()
    expect(screen.getByText('el mercado')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npm test -- --run 2>&1 | tail -20
```

Expected: 4 new tests FAIL — `CoachOverlay` module not found.

- [ ] **Step 3: Create `frontend/src/components/CoachOverlay.jsx`**

```jsx
export default function CoachOverlay({ corrections }) {
  if (!corrections || corrections.length === 0) return null
  return (
    <div className="coach-overlay">
      <h3>Corrections</h3>
      {corrections.map((c, i) => (
        <div key={i} className="correction">
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

- [ ] **Step 4: Run CoachOverlay tests**

```bash
cd frontend && npm test -- --run 2>&1 | tail -20
```

Expected: All 4 new tests pass. Existing 12 tests still pass (16 total).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CoachOverlay.jsx frontend/src/__tests__/CoachOverlay.test.jsx
git commit -m "feat: CoachOverlay component renders corrections list"
```

---

## Task 6: SessionConfig component

**Files:**
- Create: `frontend/src/components/SessionConfig.jsx`
- Create: `frontend/src/__tests__/SessionConfig.test.jsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/__tests__/SessionConfig.test.jsx`:

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SessionConfig from '../components/SessionConfig'

describe('SessionConfig', () => {
  it('renders a select with three coaching mode options', () => {
    render(<SessionConfig coachingMode="on_demand" onCoachingModeChange={() => {}} />)
    const select = screen.getByLabelText(/coaching mode/i)
    expect(select).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /on demand/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /explicit/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /shadowing/i })).toBeInTheDocument()
  })

  it('shows the current coaching mode as selected', () => {
    render(<SessionConfig coachingMode="explicit" onCoachingModeChange={() => {}} />)
    expect(screen.getByLabelText(/coaching mode/i).value).toBe('explicit')
  })

  it('calls onCoachingModeChange with the new value when changed', () => {
    const onChange = vi.fn()
    render(<SessionConfig coachingMode="on_demand" onCoachingModeChange={onChange} />)
    fireEvent.change(screen.getByLabelText(/coaching mode/i), { target: { value: 'shadowing' } })
    expect(onChange).toHaveBeenCalledWith('shadowing')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npm test -- --run 2>&1 | tail -20
```

Expected: 3 new tests FAIL — `SessionConfig` module not found.

- [ ] **Step 3: Create `frontend/src/components/SessionConfig.jsx`**

```jsx
export default function SessionConfig({ coachingMode, onCoachingModeChange }) {
  return (
    <div className="session-config">
      <label htmlFor="coaching-mode">Coaching mode</label>
      <select
        id="coaching-mode"
        value={coachingMode}
        onChange={(e) => onCoachingModeChange(e.target.value)}
      >
        <option value="on_demand">On demand</option>
        <option value="explicit">Explicit</option>
        <option value="shadowing">Shadowing</option>
      </select>
    </div>
  )
}
```

- [ ] **Step 4: Run SessionConfig tests**

```bash
cd frontend && npm test -- --run 2>&1 | tail -20
```

Expected: All 3 new tests pass. 19 total frontend tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SessionConfig.jsx frontend/src/__tests__/SessionConfig.test.jsx
git commit -m "feat: SessionConfig component with coaching mode select"
```

---

## Task 7: Wire frontend — useVoice + App

**Files:**
- Modify: `frontend/src/hooks/useVoice.js`
- Modify: `frontend/src/App.jsx`

No new tests for this task — the integration is covered by the component tests above and the manual smoke test. Existing VoiceButton and Transcript tests must continue to pass.

- [ ] **Step 1: Update `frontend/src/hooks/useVoice.js`**

Replace the full file contents:

```js
import { useState, useRef, useEffect } from 'react'

export function useVoice(coachingMode = 'on_demand') {
  const [state, setState] = useState('idle')
  const [turns, setTurns] = useState([])
  const [corrections, setCorrections] = useState([])
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const sessionIdRef = useRef(null)

  useEffect(() => {
    sessionIdRef.current = null
    setTurns([])
    setCorrections([])
    setError(null)
    fetch('/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ coaching_mode: coachingMode }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.session_id) {
          sessionIdRef.current = data.session_id
        } else {
          setError({ stage: 'mic', message: 'Failed to start session', recoverable: false })
        }
      })
      .catch(() => {
        setError({ stage: 'mic', message: 'Failed to start session', recoverable: false })
      })
  }, [coachingMode])

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

  return { state, turns, corrections, error, startRecording, stopRecording }
}
```

- [ ] **Step 2: Update `frontend/src/App.jsx`**

Replace the full file contents:

```jsx
import { useState } from 'react'
import { useVoice } from './hooks/useVoice'
import VoiceButton from './components/VoiceButton'
import Transcript from './components/Transcript'
import CoachOverlay from './components/CoachOverlay'
import SessionConfig from './components/SessionConfig'
import './App.css'

function App() {
  const [coachingMode, setCoachingMode] = useState('on_demand')
  const { state, turns, corrections, error, startRecording, stopRecording } = useVoice(coachingMode)

  return (
    <div className="app">
      <h1>duoVoiceCoach</h1>
      <p className="subtitle">Spanish conversation practice</p>
      <SessionConfig coachingMode={coachingMode} onCoachingModeChange={setCoachingMode} />
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

- [ ] **Step 3: Run all frontend tests**

```bash
cd frontend && npm test -- --run 2>&1 | tail -20
```

Expected: 19 tests pass (12 existing + 4 CoachOverlay + 3 SessionConfig).

- [ ] **Step 4: Run all backend tests**

```bash
uv run pytest tests/ -q
```

Expected: ~51 passing, 2 skipped.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useVoice.js frontend/src/App.jsx
git commit -m "feat: wire CoachOverlay and SessionConfig into App; useVoice restarts session on mode change"
```

---

## Task 8: Manual test plan

**Files:**
- Modify: `docs/manualTestPlan.md`

- [ ] **Step 1: Append Phase 3 procedures to `docs/manualTestPlan.md`**

Add the following to the end of the file (before the final Sign-Off Checklist, or after — update the checklist too):

```markdown
---

## Phase 3 — Coaching Layer

### Prerequisites

- `ANTHROPIC_API_KEY` set in your environment (real key required)
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
ANTHROPIC_API_KEY=test-key uv run pytest -v
cd frontend && npm test -- --run
```

**Pass:** ~51 backend tests pass, 2 skipped; 19 frontend tests pass.
**Fail:** Any failure or error.

---

### MT-3-2: SessionConfig renders correctly

Open `http://localhost:5173`.

**Check:**
- [ ] A "Coaching mode" label and dropdown are visible
- [ ] Dropdown shows three options: "On demand", "Explicit", "Shadowing"
- [ ] Default selected is "On demand"

**Pass:** All checks satisfied.

---

### MT-3-3: on_demand mode — no automatic corrections

1. Ensure dropdown is set to "On demand".
2. Conduct one turn: say "Yo quiero ir al mercado." (deliberate use of optional pronoun).
3. Wait for the coach reply.

**Check:**
- [ ] Coach replies in Spanish
- [ ] No correction overlay appears (CoachOverlay is hidden)
- [ ] Transcript shows user turn and coach reply normally

**Pass:** No correction overlay visible.
**Fail:** Correction overlay appears without the user asking.

---

### MT-3-4: on_demand mode — corrections surface on request

Continuing the same session from MT-3-3:

1. Say "Corrígeme, yo quiero ir al mercado."
2. Wait for the coach reply.

**Check:**
- [ ] A correction overlay appears below the VoiceButton
- [ ] Overlay shows at least one correction with original text, corrected text, and explanation
- [ ] Coach reply is spoken aloud

**Pass:** Overlay visible with correction fields populated.
**Fail:** No overlay, or overlay appears with blank fields.

---

### MT-3-5: explicit mode — automatic corrections appear

1. Change dropdown to "Explicit". Wait 2 seconds for new session to initialise.
2. Say "Yo quiero ir al mercado." (deliberately using optional "yo").
3. Wait for reply.

**Check:**
- [ ] Coach replies in Spanish
- [ ] A correction overlay appears (assuming Claude flags the optional "yo")
- [ ] Correction fields (original, corrected, explanation) are all populated

**Pass:** Overlay visible after turn in explicit mode.
**Fail:** No overlay despite speaking with a known error.

Note: Claude may not always flag "yo quiero" as an error — if no overlay appears, try "Yo soy estudiante muy bien" (mixing languages) or another clear grammar error.

---

### MT-3-6: shadowing mode — no overlay, error woven into reply

1. Change dropdown to "Shadowing". Wait 2 seconds for new session.
2. Say "Yo quiero ir al mercado." (deliberate optional "yo").
3. Wait for reply.

**Check:**
- [ ] No correction overlay appears (CoachOverlay hidden)
- [ ] Coach reply may naturally use "quiero ir" (without "yo") in its response
- [ ] Conversation flows naturally

**Pass:** No overlay. Coach reply is natural Spanish.
**Fail:** Overlay appears in shadowing mode.

---

### MT-3-7: Mode change resets session

1. Set mode to "Explicit", complete one turn, note the transcript content.
2. Change dropdown to "Shadowing".

**Check:**
- [ ] Transcript clears (new session started)
- [ ] CoachOverlay clears
- [ ] New turn works normally in shadowing mode (no overlay)

**Pass:** Session resets on mode change; new turns work in new mode.
**Fail:** Old transcript persists, or new session fails to start.

---

### MT-3-8: Full response structure via curl (explicit mode)

```bash
# Start a session in explicit mode
SESSION=$(curl -s -X POST http://localhost:8001/session/start \
  -H "Content-Type: application/json" \
  -d '{"coaching_mode": "explicit"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

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

**Pass:** All five keys present; `coach_text` is non-empty; `error` is null. (`corrections` may be empty if no errors detected in the fixture phrase.)
**Fail:** Missing keys or non-null error.
```

- [ ] **Step 2: Update the Sign-Off Checklist at the bottom of `docs/manualTestPlan.md`**

Replace the existing checklist with:

```markdown
## Sign-Off Checklist

Before recording sign-off in `manualTestLog.md`, confirm:

- [ ] MT-0-1 through MT-0-4 all passed (Phase 0)
- [ ] MT-1-1 through MT-1-8 all passed (Phase 1)
- [ ] MT-2-1 through MT-2-7 all passed (Phase 2)
- [ ] MT-3-1 through MT-3-8 all passed (Phase 3)
- [ ] No unexpected browser console errors observed during any test
- [ ] No unhandled exceptions in backend terminal output during any test

Record in `docs/manualTestLog.md`:
- Date tested
- Tester name / email
- Any observed issues or deviations (note if a test passed with caveats)
- Whisper model version used (check: `uv run python3 -c "import whisper; print(whisper.__version__)"`)
- Claude model used (currently `claude-sonnet-4-6`)
```

- [ ] **Step 3: Commit**

```bash
git add docs/manualTestPlan.md
git commit -m "docs: add Phase 3 manual test plan (MT-3-1 through MT-3-8)"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|---|---|
| Coaching mode routing (`on_demand`, `explicit`, `shadowing`) | Task 3 |
| User-request trigger detection | Task 2 |
| `/turn` returns filtered `corrections[]` | Task 4 (main.py unchanged; filtering now in coach.py) |
| `CoachOverlay.jsx` displays corrections | Task 5 |
| `SessionConfig.jsx` coaching mode toggle | Task 6 |
| Unit tests for routing, all three modes | Task 3 |
| Vitest for `CoachOverlay` and `SessionConfig` | Tasks 5 & 6 |
| Manual smoke test procedures | Task 8 |
| Phase 3 gate: all tests pass | Verified in each task's step 4 |
| Phase 3 gate: manual smoke test signed off | Documented in Task 8 |
| Phase 3 gate: MVP declared complete | Gate criteria in plan |

**Placeholder scan:** None found — all steps contain complete code.

**Type consistency:**
- `corrections` returned from `handle_turn()` is `list[Correction]` throughout.
- `CoachOverlay` receives a plain array of correction objects from `useVoice` (serialized by `/turn` response).
- `useVoice(coachingMode)` parameter matches `App.jsx` call site.
- `SessionStartRequest.coaching_mode` matches `useVoice` JSON body key `coaching_mode`. ✓
