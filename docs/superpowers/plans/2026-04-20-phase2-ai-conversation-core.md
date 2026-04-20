# Phase 2 — AI Conversation Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Claude in as the AI provider so the app conducts real Spanish conversations, replacing the Phase 1 echo response.

**Architecture:** Add `CoachResponse` dataclass and update the abstract provider interface. Implement `ClaudeProvider` using tool use for structured output and prompt caching on the system prompt. Add an in-memory session store with `POST /session/start`. Update `POST /turn` to look up a session, run Whisper, call `CoachSession.handle_turn()`, and return `coach_text`. Update frontend to initialize a session on mount and render coach replies.

**Tech Stack:** Python 3.12+, FastAPI, `anthropic` SDK, `openai-whisper`, React + Vite, pytest, Vitest.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/session.py` | Modify | Add `CoachResponse` dataclass |
| `backend/ai/base.py` | Modify | Update `chat()` return type to `CoachResponse \| TurnError` |
| `backend/ai/openai.py` | **Create** | `OpenAIProvider` stub (raises `NotImplementedError`) |
| `backend/ai/claude.py` | **Create** | `ClaudeProvider` — tool use, prompt caching, message history |
| `backend/coach.py` | Modify | `handle_turn()` calls real AI provider |
| `backend/main.py` | Modify | Add `POST /session/start`; update `POST /turn` |
| `tests/unit/test_ai_providers.py` | **Create** | Unit tests for `ClaudeProvider` and `OpenAIProvider` |
| `tests/unit/test_coach.py` | **Create** | Unit tests for `CoachSession.handle_turn()` |
| `tests/integration/test_turn_pipeline.py` | Modify | Update for Phase 2 API shape; add real-Claude integration test |
| `frontend/src/hooks/useVoice.js` | Modify | Session init on mount; pass `session_id`; use `coach_text` |
| `frontend/src/components/Transcript.jsx` | Modify | Render `coach_text` instead of `echo` |
| `frontend/src/__tests__/Transcript.test.jsx` | Modify | Update fixture data and assertions for `coach_text` |

---

## Task 1: Add CoachResponse dataclass and update AbstractAIProvider return type

**Files:**
- Modify: `backend/session.py`
- Modify: `backend/ai/base.py`

- [ ] **Step 1: Write the failing import test**

Create `tests/unit/test_ai_providers.py`:

```python
from backend.session import CoachResponse, Correction
from backend.ai.base import AbstractAIProvider
```

Run: `uv run pytest tests/unit/test_ai_providers.py -v`
Expected: `ImportError: cannot import name 'CoachResponse'`

- [ ] **Step 2: Add CoachResponse to session.py**

In `backend/session.py`, after the `Correction` dataclass (around line 14), add:

```python
@dataclass
class CoachResponse:
    coach_text: str
    corrections: list[Correction]
```

- [ ] **Step 3: Update AbstractAIProvider.chat() return type**

Replace the entire contents of `backend/ai/base.py` with:

```python
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from backend.session import Session, CoachResponse, TurnError


class AbstractAIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def chat(self, session: "Session", user_text: str) -> "Union[CoachResponse, TurnError]":
        """Send a user turn to the AI and return a CoachResponse or TurnError.

        Never raises — errors are returned as TurnError values.
        """
        raise NotImplementedError
```

- [ ] **Step 4: Run the import test to verify it passes**

Run: `uv run pytest tests/unit/test_ai_providers.py -v`
Expected: PASS (both imports resolve)

- [ ] **Step 5: Run the full test suite to confirm no regressions**

Run: `uv run pytest -v`
Expected: all previously passing tests still pass

- [ ] **Step 6: Commit**

```bash
git add backend/session.py backend/ai/base.py tests/unit/test_ai_providers.py
git commit -m "feat: add CoachResponse dataclass and update AbstractAIProvider return type"
```

---

## Task 2: OpenAIProvider stub

**Files:**
- Create: `backend/ai/openai.py`
- Modify: `tests/unit/test_ai_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_ai_providers.py`:

```python
import pytest
from backend.ai.openai import OpenAIProvider
from backend.session import new_session


class TestOpenAIProvider:
    def test_chat_raises_not_implemented(self):
        provider = OpenAIProvider()
        session = new_session(
            topic="ordering food", level=5,
            ai_provider="openai", coaching_mode="on_demand"
        )
        with pytest.raises(NotImplementedError):
            provider.chat(session, "hola")
```

Run: `uv run pytest tests/unit/test_ai_providers.py::TestOpenAIProvider -v`
Expected: `ModuleNotFoundError: No module named 'backend.ai.openai'`

- [ ] **Step 2: Create the stub**

Create `backend/ai/openai.py`:

```python
from typing import Union
from backend.ai.base import AbstractAIProvider
from backend.session import Session, CoachResponse, TurnError


class OpenAIProvider(AbstractAIProvider):
    """OpenAI GPT provider stub. Wired for Phase 4+ swap."""

    def chat(self, session: Session, user_text: str) -> Union[CoachResponse, TurnError]:
        raise NotImplementedError("OpenAIProvider is not implemented in MVP")
```

- [ ] **Step 3: Run the test to verify it passes**

Run: `uv run pytest tests/unit/test_ai_providers.py::TestOpenAIProvider -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/ai/openai.py tests/unit/test_ai_providers.py
git commit -m "feat: add OpenAIProvider stub and unit test"
```

---

## Task 3: ClaudeProvider

**Files:**
- Create: `backend/ai/claude.py`
- Modify: `tests/unit/test_ai_providers.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_ai_providers.py`:

```python
from unittest.mock import MagicMock, patch
from backend.ai.claude import ClaudeProvider


def _make_session():
    return new_session(
        topic="ordering food", level=5,
        ai_provider="claude", coaching_mode="on_demand"
    )


def _mock_tool_response(coach_text, corrections=None):
    """Build a fake anthropic response containing a tool_use block."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {"coach_text": coach_text, "corrections": corrections or []}
    response = MagicMock()
    response.content = [tool_block]
    return response


class TestClaudeProvider:
    def test_valid_response_returns_coach_response(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.messages.create.return_value = _mock_tool_response(
                    "¡Hola! ¿Qué quieres pedir hoy?"
                )

                provider = ClaudeProvider()
                result = provider.chat(_make_session(), "hola quiero ordenar")

                assert isinstance(result, CoachResponse)
                assert result.coach_text == "¡Hola! ¿Qué quieres pedir hoy?"
                assert result.corrections == []

    def test_response_with_corrections_parses_them(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.messages.create.return_value = _mock_tool_response(
                    "¡Muy bien!",
                    corrections=[{
                        "original": "yo quiero ir",
                        "corrected": "quiero ir",
                        "explanation": "Subject pronoun 'yo' is optional in Spanish and sounds unnatural here.",
                        "triggered_by": "auto",
                    }],
                )

                provider = ClaudeProvider()
                result = provider.chat(_make_session(), "yo quiero ir al mercado")

                assert isinstance(result, CoachResponse)
                assert len(result.corrections) == 1
                assert result.corrections[0].original == "yo quiero ir"
                assert result.corrections[0].triggered_by == "auto"

    def test_response_with_no_tool_use_block_returns_turn_error(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                empty_response = MagicMock()
                empty_response.content = []
                mock_client.messages.create.return_value = empty_response

                provider = ClaudeProvider()
                result = provider.chat(_make_session(), "hola")

                assert isinstance(result, TurnError)
                assert result.stage == "ai"
                assert result.recoverable is True

    def test_api_error_returns_turn_error(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.messages.create.side_effect = Exception("connection refused")

                provider = ClaudeProvider()
                result = provider.chat(_make_session(), "hola")

                assert isinstance(result, TurnError)
                assert result.stage == "ai"
                assert result.recoverable is True

    def test_missing_api_key_raises_runtime_error_at_instantiation(self):
        import os
        clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict("os.environ", clean_env, clear=True):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                ClaudeProvider()
```

Run: `uv run pytest tests/unit/test_ai_providers.py::TestClaudeProvider -v`
Expected: `ModuleNotFoundError: No module named 'backend.ai.claude'`

- [ ] **Step 2: Create ClaudeProvider**

Create `backend/ai/claude.py`:

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


class ClaudeProvider(AbstractAIProvider):
    """Anthropic Claude AI provider using tool use for structured output."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        self._client = anthropic.Anthropic(api_key=api_key)

    def _build_system_prompt(self, session: Session) -> str:
        return (
            f"You are a Spanish conversation coach. "
            f"The student is practicing at level {session.level}/10.\n"
            f"Topic: {session.topic}. Coaching mode: {session.coaching_mode}.\n"
            f"Respond only in Spanish. "
            f"Keep vocabulary and grammar appropriate for level {session.level}.\n"
            f"Do not correct the student unless asked (on_demand mode).\n\n"
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

- [ ] **Step 3: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_ai_providers.py -v`
Expected: all 8 tests PASS

- [ ] **Step 4: Run the full test suite**

Run: `uv run pytest -v`
Expected: all previously passing tests still pass

- [ ] **Step 5: Commit**

```bash
git add backend/ai/claude.py tests/unit/test_ai_providers.py
git commit -m "feat: implement ClaudeProvider with tool use and prompt caching"
```

---

## Task 4: Update CoachSession.handle_turn()

**Files:**
- Modify: `backend/coach.py`
- Create: `tests/unit/test_coach.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_coach.py`:

```python
from unittest.mock import MagicMock
import pytest
from backend.coach import CoachSession
from backend.session import new_session, CoachResponse, TurnError, Turn


def _mock_provider(return_value):
    provider = MagicMock()
    provider.chat.return_value = return_value
    return provider


class TestCoachSessionHandleTurn:
    def test_successful_turn_appends_user_and_coach_turns(self):
        session = new_session(
            topic="travel", level=3, ai_provider="claude", coaching_mode="on_demand"
        )
        coach_response = CoachResponse(
            coach_text="¿A dónde quieres viajar?", corrections=[]
        )
        coach = CoachSession(session, _mock_provider(coach_response))

        coach.handle_turn("quiero viajar a españa")

        assert len(session.turns) == 2
        assert session.turns[0].speaker == "user"
        assert session.turns[0].transcript_norm == "quiero viajar a españa"
        assert session.turns[1].speaker == "coach"
        assert session.turns[1].coach_text == "¿A dónde quieres viajar?"

    def test_successful_turn_returns_coach_turn(self):
        session = new_session(
            topic="food", level=2, ai_provider="claude", coaching_mode="on_demand"
        )
        coach_response = CoachResponse(
            coach_text="¿Qué quieres comer?", corrections=[]
        )
        coach = CoachSession(session, _mock_provider(coach_response))

        result = coach.handle_turn("quiero comer tacos")

        assert isinstance(result, Turn)
        assert result.speaker == "coach"
        assert result.coach_text == "¿Qué quieres comer?"
        assert result.corrections == []

    def test_provider_error_appends_user_and_error_turns(self):
        session = new_session(
            topic="food", level=2, ai_provider="claude", coaching_mode="on_demand"
        )
        turn_error = TurnError(stage="ai", message="API failed", recoverable=True)
        coach = CoachSession(session, _mock_provider(turn_error))

        result = coach.handle_turn("hola")

        assert isinstance(result, TurnError)
        assert len(session.turns) == 2
        assert session.turns[0].speaker == "user"
        assert session.turns[1].speaker == "coach"
        assert session.turns[1].error is not None
        assert session.turns[1].error.stage == "ai"

    def test_session_passed_to_provider_has_correct_fields(self):
        session = new_session(
            topic="ordering food", level=5, ai_provider="claude", coaching_mode="on_demand"
        )
        provider = _mock_provider(CoachResponse(coach_text="Hola", corrections=[]))
        coach = CoachSession(session, provider)

        coach.handle_turn("hola")

        called_session, called_text = provider.chat.call_args[0]
        assert called_session.level == 5
        assert called_session.topic == "ordering food"
        assert called_session.coaching_mode == "on_demand"
        assert called_text == "hola"

    def test_conversation_history_accumulates_across_turns(self):
        session = new_session(
            topic="general", level=5, ai_provider="claude", coaching_mode="on_demand"
        )
        provider = _mock_provider(CoachResponse(coach_text="¡Bien!", corrections=[]))
        coach = CoachSession(session, provider)

        coach.handle_turn("primer turno")
        coach.handle_turn("segundo turno")

        assert len(session.turns) == 4
        assert session.turns[0].transcript_norm == "primer turno"
        assert session.turns[2].transcript_norm == "segundo turno"
```

Run: `uv run pytest tests/unit/test_coach.py -v`
Expected: `AttributeError` or assertion failures — Phase 0 stub returns hardcoded text, not a `CoachResponse`.

- [ ] **Step 2: Update CoachSession.handle_turn()**

Replace the entire contents of `backend/coach.py` with:

```python
from datetime import datetime, timezone
from typing import Union
from backend.session import Session, Turn, CoachResponse, TurnError
from backend.ai.base import AbstractAIProvider


class CoachSession:
    """Manages a coaching session: calls the AI provider and maintains turn history."""

    def __init__(self, session: Session, ai_provider: AbstractAIProvider):
        self.session = session
        self.ai_provider = ai_provider

    def handle_turn(self, user_text: str) -> Union[Turn, TurnError]:
        """Process a user turn: call AI, append both turns to session, return coach turn.

        Returns TurnError (as a value, not exception) if the AI provider fails.
        """
        now = datetime.now(timezone.utc)

        result = self.ai_provider.chat(self.session, user_text)

        user_turn = Turn(speaker="user", transcript_norm=user_text, timestamp=now)
        self.session.turns.append(user_turn)

        if isinstance(result, TurnError):
            error_turn = Turn(speaker="coach", timestamp=now, error=result)
            self.session.turns.append(error_turn)
            return result

        coach_turn = Turn(
            speaker="coach",
            coach_text=result.coach_text,
            corrections=result.corrections,
            timestamp=now,
        )
        self.session.turns.append(coach_turn)
        return coach_turn
```

- [ ] **Step 3: Run the coach tests**

Run: `uv run pytest tests/unit/test_coach.py -v`
Expected: all 5 tests PASS

- [ ] **Step 4: Run the full test suite**

Run: `uv run pytest -v`
Expected: all previously passing tests still pass

- [ ] **Step 5: Commit**

```bash
git add backend/coach.py tests/unit/test_coach.py
git commit -m "feat: implement CoachSession.handle_turn() with real AI provider call"
```

---

## Task 5: Update main.py routes

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Replace main.py**

Replace the entire contents of `backend/main.py` with:

```python
import os
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from backend.session import Session, TurnError, new_session
from backend.stt import WhisperSTT
from backend.coach import CoachSession
from backend.ai.claude import ClaudeProvider

stt_provider = WhisperSTT()
claude_provider = ClaudeProvider()
sessions: dict[str, Session] = {}
app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/session/start")
def session_start():
    session = new_session(
        topic="general",
        level=5,
        ai_provider="claude",
        coaching_mode="on_demand",
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

- [ ] **Step 2: Run the full backend test suite**

Run: `uv run pytest -v`

At this point the old integration tests (`test_turn_response_includes_echo`, `test_turn_with_valid_wav_returns_transcript`) will fail because `/turn` now requires `session_id`. That is expected — they will be replaced in the next task.

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: add POST /session/start and update POST /turn for Phase 2"
```

---

## Task 6: Update integration tests

**Files:**
- Modify: `tests/integration/test_turn_pipeline.py`

- [ ] **Step 1: Replace the integration test file**

Replace the entire contents of `tests/integration/test_turn_pipeline.py` with:

```python
import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
FIXTURE_WAV = os.path.join(os.path.dirname(__file__), "..", "fixtures", "hola_sample.wav")

# Real Claude API call tests require ANTHROPIC_API_KEY.
# Run with: ANTHROPIC_API_KEY=sk-... uv run pytest tests/integration/ -v
requires_api_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


class TestSessionStart:
    def test_returns_session_id(self):
        response = client.post("/session/start")
        assert response.status_code == 200
        body = response.json()
        assert "session_id" in body
        assert isinstance(body["session_id"], str)
        assert len(body["session_id"]) > 0

    def test_each_call_returns_unique_session_id(self):
        r1 = client.post("/session/start").json()
        r2 = client.post("/session/start").json()
        assert r1["session_id"] != r2["session_id"]


class TestTurnRoute:
    def test_unknown_session_id_returns_404(self):
        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/turn",
                files={"audio": ("hola_sample.wav", f, "audio/wav")},
                data={"session_id": "nonexistent-id"},
            )
        assert response.status_code == 404

    def test_corrupted_wav_returns_structured_stt_error(self, tmp_path):
        session_id = client.post("/session/start").json()["session_id"]
        bad_wav = tmp_path / "bad.wav"
        bad_wav.write_bytes(b"not a valid wav")
        with open(bad_wav, "rb") as f:
            response = client.post(
                "/turn",
                files={"audio": ("bad.wav", f, "audio/wav")},
                data={"session_id": session_id},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["error"] is not None
        assert body["error"]["stage"] == "stt"
        assert body["error"]["recoverable"] is True
        assert body["transcript_raw"] is None
        assert body["transcript_norm"] is None

    @requires_api_key
    def test_valid_wav_returns_coach_text(self):
        session_id = client.post("/session/start").json()["session_id"]
        with open(FIXTURE_WAV, "rb") as f:
            response = client.post(
                "/turn",
                files={"audio": ("hola_sample.wav", f, "audio/wav")},
                data={"session_id": session_id},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["error"] is None
        assert body["transcript_raw"] == "Hola, como estás?"
        assert body["transcript_norm"] == "hola como estás"
        assert isinstance(body["coach_text"], str)
        assert len(body["coach_text"]) > 0
        assert isinstance(body["corrections"], list)

    @requires_api_key
    def test_conversation_history_maintained_across_turns(self):
        session_id = client.post("/session/start").json()["session_id"]
        for _ in range(2):
            with open(FIXTURE_WAV, "rb") as f:
                response = client.post(
                    "/turn",
                    files={"audio": ("hola_sample.wav", f, "audio/wav")},
                    data={"session_id": session_id},
                )
            body = response.json()
            assert body["error"] is None
            assert isinstance(body["coach_text"], str)
```

- [ ] **Step 2: Run integration tests without API key (should skip API tests, pass structure tests)**

Run: `uv run pytest tests/integration/ -v`
Expected: `TestSessionStart` and structure tests PASS; API-key tests SKIPPED

- [ ] **Step 3: Run full backend suite**

Run: `uv run pytest -v`
Expected: all tests PASS (API-key tests skipped if key not set)

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_turn_pipeline.py
git commit -m "test: update integration tests for Phase 2 API shape"
```

---

## Task 7: Update frontend

**Files:**
- Modify: `frontend/src/hooks/useVoice.js`
- Modify: `frontend/src/components/Transcript.jsx`
- Modify: `frontend/src/__tests__/Transcript.test.jsx`

- [ ] **Step 1: Update Transcript.test.jsx first (failing tests)**

Replace the entire contents of `frontend/src/__tests__/Transcript.test.jsx` with:

```jsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import Transcript from '../components/Transcript'

describe('Transcript', () => {
  it('renders nothing when turns is empty', () => {
    const { container } = render(<Transcript turns={[]} />)
    expect(container.querySelector('.transcript')).toBeInTheDocument()
    expect(screen.queryByRole('listitem')).not.toBeInTheDocument()
  })

  it('renders user turn with transcript_norm', () => {
    const turns = [{ speaker: 'user', transcript_norm: 'hola como estás', coach_text: null }]
    render(<Transcript turns={turns} />)
    expect(screen.getByText('hola como estás')).toBeInTheDocument()
  })

  it('renders coach turn with coach_text', () => {
    const turns = [
      { speaker: 'user', transcript_norm: 'hola', coach_text: null },
      { speaker: 'coach', transcript_norm: null, coach_text: '¡Hola! ¿Cómo estás?' },
    ]
    render(<Transcript turns={turns} />)
    expect(screen.getByText('hola')).toBeInTheDocument()
    expect(screen.getByText('¡Hola! ¿Cómo estás?')).toBeInTheDocument()
  })

  it('labels user turns distinctly from coach turns', () => {
    const turns = [
      { speaker: 'user', transcript_norm: 'hola', coach_text: null },
      { speaker: 'coach', transcript_norm: null, coach_text: '¡Hola!' },
    ]
    render(<Transcript turns={turns} />)
    expect(screen.getByText(/you|user/i)).toBeInTheDocument()
    expect(screen.getByText(/coach/i)).toBeInTheDocument()
  })
})
```

Run: `cd frontend && npm test -- --run`
Expected: `renders coach turn with coach_text` FAILS (Transcript still uses `echo`)

- [ ] **Step 2: Update Transcript.jsx**

Replace the entire contents of `frontend/src/components/Transcript.jsx` with:

```jsx
export default function Transcript({ turns }) {
  return (
    <div className="transcript">
      {turns.map((turn, i) => (
        <div key={i} className={`turn turn--${turn.speaker}`}>
          <span className="turn-label">{turn.speaker === 'user' ? 'You' : 'Coach'}</span>
          <span className="turn-text">
            {turn.speaker === 'user' ? turn.transcript_norm : turn.coach_text}
          </span>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Run frontend tests — Transcript tests should now pass**

Run: `cd frontend && npm test -- --run`
Expected: all Transcript tests PASS; VoiceButton tests unaffected

- [ ] **Step 4: Update useVoice.js**

Replace the entire contents of `frontend/src/hooks/useVoice.js` with:

```javascript
import { useState, useRef, useEffect } from 'react'

export function useVoice() {
  const [state, setState] = useState('idle')
  const [turns, setTurns] = useState([])
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const sessionIdRef = useRef(null)

  useEffect(() => {
    fetch('/session/start', { method: 'POST' })
      .then((res) => res.json())
      .then((data) => { sessionIdRef.current = data.session_id })
      .catch(() => {
        setError({ stage: 'mic', message: 'Failed to start session', recoverable: false })
      })
  }, [])

  async function startRecording() {
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

  return { state, turns, error, startRecording, stopRecording }
}
```

- [ ] **Step 5: Run the full frontend test suite**

Run: `cd frontend && npm test -- --run`
Expected: all tests PASS

- [ ] **Step 6: Run the full backend test suite**

Run: `uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/hooks/useVoice.js frontend/src/components/Transcript.jsx frontend/src/__tests__/Transcript.test.jsx
git commit -m "feat: update frontend for Phase 2 — session init, coach_text rendering"
```

---

## Task 8: Integration smoke test with real Claude API

This task requires `ANTHROPIC_API_KEY` to be set in your environment.

- [ ] **Step 1: Start the backend**

```bash
uv run uvicorn backend.main:app --reload
```

Expected output includes: `Application startup complete.`

- [ ] **Step 2: Run the API-key-gated integration tests**

In a separate terminal:

```bash
uv run pytest tests/integration/ -v
```

Expected: all tests PASS (API-key tests now run, not skipped)

- [ ] **Step 3: Start the frontend dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 4: Manual smoke test**

Open `http://localhost:5173` in a browser.

1. Click Record and say "Hola, ¿cómo estás?" in Spanish
2. Stop recording
3. Verify: transcript appears in the conversation panel
4. Verify: coach replies in Spanish (visible in transcript and spoken via browser TTS)
5. Speak a second turn and verify the coach reply references the prior exchange

- [ ] **Step 5: Sign off in manualTestLog.md**

In `docs/manualTestLog.md`, under the Phase 2 section, update:

```markdown
**Sign-off:**
- Date: 2026-04-20
- Tester: oldhat86@gmail.com
- Notes: PASSED. Claude responds in Spanish at level 5. Conversation history maintained across turns. Browser TTS speaks coach replies.
```

- [ ] **Step 6: Update claudeSpanishCoachPlan.md**

In `claudeSpanishCoachPlan.md`, mark Phase 2 tasks complete and update the phase status table:

```markdown
| 2 — AI Conversation Core | Claude wired in, freeform chat | ✅ Complete | N tests passing | ...
```

- [ ] **Step 7: Final commit**

```bash
git add docs/manualTestLog.md claudeSpanishCoachPlan.md
git commit -m "docs: Phase 2 gate sign-off — AI Conversation Core complete"
```

---

## Self-Review Checklist

- [x] `CoachResponse` dataclass added — Task 1
- [x] `AbstractAIProvider.chat()` return type updated — Task 1
- [x] `OpenAIProvider` stub + test — Task 2
- [x] `ClaudeProvider` with tool use, prompt caching, message history — Task 3
- [x] `CoachSession.handle_turn()` calls real provider — Task 4
- [x] `POST /session/start` route — Task 5
- [x] `POST /turn` accepts `session_id`, returns `coach_text` + `corrections` — Task 5
- [x] Integration tests updated for Phase 2 API shape — Task 6
- [x] Frontend: session init on mount — Task 7
- [x] Frontend: `session_id` sent with each turn — Task 7
- [x] Frontend: `coach_text` rendered in transcript — Task 7
- [x] Manual smoke test + gate sign-off — Task 8
- [x] `claudeSpanishCoachPlan.md` updated — Task 8
