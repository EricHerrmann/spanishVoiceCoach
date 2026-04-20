# Phase 2 — AI Conversation Core: Design Spec

**Date:** 2026-04-20
**Status:** Approved
**Phase:** 2 of MVP (Phases 0–3)

---

## Goal

Wire Claude in as the AI provider. Replace the Phase 1 echo response with real Spanish conversation. First real coaching session is possible after this phase.

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Tool use for structured output | Forces parseable `{coach_text, corrections}` JSON — no regex, deterministic in Phase 3 |
| Full message history per turn | Claude sees the real back-and-forth; correction quality depends on context |
| Errors as return values (not exceptions) | Consistent with `WhisperSTT.transcribe()` pattern established in Phase 1 |
| Minimal `POST /session/start` now | Phase 4 expands request body; Phase 5 adds persistence — both are additive, no redesign |
| `ClaudeProvider` instantiated once at module level | Reuses HTTP client across requests |

---

## Data Model Changes

**Add to `backend/session.py`:**

```python
@dataclass
class CoachResponse:
    coach_text: str
    corrections: list[Correction]  # always empty list in Phase 2
```

**Update `backend/ai/base.py`:**

```python
from typing import Union

class AbstractAIProvider(ABC):
    @abstractmethod
    def chat(self, session: Session, user_text: str) -> Union[CoachResponse, TurnError]:
        raise NotImplementedError
```

Errors are values, not exceptions — same pattern as `WhisperSTT.transcribe()`.

---

## Backend Components

### `backend/ai/claude.py` — ClaudeProvider

- Inherits `AbstractAIProvider`
- **Tool use**: defines tool `get_coach_response` with schema `{coach_text: string, corrections: array}`. Claude is required to call this tool, guaranteeing structured JSON output.
- **Prompt caching**: system prompt tagged with `cache_control: {type: "ephemeral"}`. Hits cache on turn 2+ within a session.
- **Message history**: builds `messages[]` from `session.turns`:
  - User turns → `{role: "user", content: transcript_norm}`
  - Coach turns → `{role: "assistant", content: coach_text}`
- **Error handling**: any `anthropic.APIError` or missing/malformed tool call → `TurnError(stage="ai", recoverable=True)`. No exceptions escape.
- **API key**: read from `ANTHROPIC_API_KEY` at instantiation. `RuntimeError` at startup if missing.

### `backend/ai/openai.py` — OpenAIProvider (stub)

- Inherits `AbstractAIProvider`
- `chat()` raises `NotImplementedError`
- Confirms the abstraction holds; wired for Phase 4+ swap

### `backend/coach.py` — CoachSession.handle_turn()

System prompt template (built from session fields):

```
You are a Spanish conversation coach. The student is practicing at level {level}/10.
Topic: {topic}. Coaching mode: {coaching_mode}.
Respond only in Spanish. Keep vocabulary and grammar appropriate for level {level}.
Do not correct the student unless asked (on_demand mode).
```

Call flow:
1. Append user `Turn` (with `transcript_norm`) to `session.turns`
2. Call `ai_provider.chat(session, user_text)`
3. If `TurnError` returned → append error turn, return `TurnError`
4. If `CoachResponse` → append coach `Turn` with `coach_text` and `corrections`, return the turn

Message history assembly lives inside `ClaudeProvider`, not `coach.py`. Coach owns session state; provider owns API shape.

### `backend/main.py` — Routes

**New route: `POST /session/start`**
- Creates `Session` with Phase 2 defaults: `topic="general", level=5, ai_provider="claude", coaching_mode="on_demand"`
- Stores in module-level `sessions: dict[str, Session] = {}`
- Returns `{session_id: str}`

**Updated route: `POST /turn`**
- Accepts `session_id` form field alongside `audio`
- Returns 404 if session not found
- Runs Whisper (unchanged)
- Creates `CoachSession(session, claude_provider)` and calls `handle_turn(transcript_norm)`
- Response shape:
  ```json
  {
    "transcript_raw": "...",
    "transcript_norm": "...",
    "coach_text": "...",
    "corrections": [],
    "error": null
  }
  ```

`ClaudeProvider` instantiated once at module level (reuses HTTP client).

---

## Frontend Changes

No new components. Three targeted changes:

**`frontend/src/hooks/useVoice.js`**
- On mount: call `POST /session/start`, store returned `session_id` in a ref
- Each `/turn` request: include `session_id` as a form field
- Replace `echo` with `coach_text` in turn state: `{speaker, transcript_norm, coach_text}`
- Speak `coach_text` via `speechSynthesis` instead of `echo`

**`frontend/src/components/Transcript.jsx`**
- Render `coach_text` for coach turns instead of `echo`

**`frontend/src/App.jsx`**
- No changes needed — session init is handled inside `useVoice`

---

## Tests

### Backend Unit Tests

**`tests/unit/test_ai_providers.py`**
- Mock `anthropic` client; valid tool-use fixture → `CoachResponse` returned
- Mock client; malformed response (no tool call) → `TurnError(stage="ai", recoverable=True)`
- `OpenAIProvider.chat()` → `NotImplementedError`

**`tests/unit/test_coach.py`**
- System prompt construction for topic/level/mode combinations (mock provider, no API call)
- `handle_turn()` with mock provider returning fixture `CoachResponse` → coach turn appended to session

### Backend Integration Test

**`tests/integration/test_turn_pipeline.py`**
- `POST /session/start` → valid `session_id`
- `POST /turn` with fixture WAV + `session_id` → real Claude API call
- Assert: `coach_text` non-empty string, `corrections` is list, `error` is null
- Assert structure, not exact text

### Frontend Tests (Vitest)

- Update existing tests: `echo` → `coach_text` throughout
- New test: `useVoice` calls `POST /session/start` on mount and attaches `session_id` to subsequent `/turn` requests

---

## What Phase 2 Does NOT Include

- Session config UI (topic/level/mode picker) — Phase 4
- Corrections populated in `CoachResponse` — Phase 3
- Persistence — Phase 5
- Multiple provider selection in UI — Phase 4

---

## Phase 2 Gate Criteria

- All tests pass (backend unit + integration; frontend Vitest)
- Claude responds in Spanish at the requested level
- Conversation history is maintained across turns
- Manual smoke test signed off in `docs/manualTestLog.md`
