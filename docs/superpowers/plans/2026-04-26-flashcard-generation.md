# Flashcard Generation from Conversation & Translation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to generate flashcards from conversation turns, the full conversation, or a translation result — Claude extracts vocabulary, assigns topics, and saves cards to a persistent user deck that merges with the built-in deck.

**Architecture:** A standalone `parse_flashcard_response` function handles Claude output parsing; `load_user_deck` / `save_user_deck` in `main.py` manage JSON persistence on the Fly.io volume; `ClaudeProvider.generate_flashcards` calls Haiku with a bare-JSON prompt; `POST /flashcards/generate` wires it together; a shared `FlashcardButton` React component handles per-button idle/loading/done/error state in the UI.

**Tech Stack:** Python 3.12, FastAPI, Anthropic SDK (Haiku), pytest, React 18, Vitest, React Testing Library

---

## File Map

| File | Change |
|------|--------|
| `backend/ai/claude.py` | Add `_VALID_TOPICS`, `_validate_cards`, `parse_flashcard_response`; add `generate_flashcards` method |
| `backend/ai/base.py` | Add `generate_flashcards` abstract method |
| `backend/main.py` | Add `import uuid`; add `load_user_deck`, `save_user_deck`, `_get_user_deck_path`; add `POST /flashcards/generate`; update `GET /flashcards/deck` to merge user deck |
| `pyproject.toml` | Register `slow` marker |
| `tests/unit/test_flashcard_parser.py` | New — parser unit tests |
| `tests/unit/test_flashcard_store.py` | New — store dedup/persistence unit tests |
| `tests/unit/test_flashcards.py` | Add deck-merge tests for `GET /flashcards/deck` |
| `tests/integration/test_flashcard_generate.py` | New — slow real-Claude integration test |
| `frontend/src/components/FlashcardButton.jsx` | New — shared button component with idle/loading/done/error state |
| `frontend/src/App.jsx` | Add `handleAddFlashcards`; pass `onAddFlashcards` to `ConversationView` and `TranslationView` |
| `frontend/src/components/ConversationView.jsx` | Accept and pass `onAddFlashcards` to `Transcript` |
| `frontend/src/components/Transcript.jsx` | Add per-turn "Add to flashcards" button and whole-conversation "Add conversation" button |
| `frontend/src/components/TranslationView.jsx` | Add "Add to flashcards" button in result block |
| `frontend/src/App.css` | Add `.flashcard-add-btn` styles |
| `frontend/src/__tests__/App.flashcard.test.jsx` | New — `handleAddFlashcards` wiring tests |
| `frontend/src/__tests__/Transcript.test.jsx` | Add flashcard button presence and callback tests |
| `frontend/src/__tests__/TranslationView.test.jsx` | Add flashcard button tests |

---

### Task 1: `parse_flashcard_response` + parser unit tests

**Files:**
- Modify: `backend/ai/claude.py`
- Create: `tests/unit/test_flashcard_parser.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_flashcard_parser.py`:

```python
import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

from backend.ai.claude import parse_flashcard_response


class TestParseFlashcardResponse:
    def test_valid_bare_json_array(self):
        raw = '[{"english": "to order", "spanish": "pedir", "level": 3, "topic": "ordering_food"}]'
        result = parse_flashcard_response(raw)
        assert len(result) == 1
        assert result[0]["spanish"] == "pedir"
        assert result[0]["topic"] == "ordering_food"

    def test_json_in_markdown_fences(self):
        raw = '```json\n[{"english": "yes", "spanish": "sí", "level": 1, "topic": "general"}]\n```'
        result = parse_flashcard_response(raw)
        assert len(result) == 1
        assert result[0]["spanish"] == "sí"

    def test_json_embedded_in_prose(self):
        raw = 'Here are flashcards:\n[{"english": "table", "spanish": "mesa", "level": 2, "topic": "ordering_food"}]\nDone.'
        result = parse_flashcard_response(raw)
        assert len(result) == 1

    def test_invalid_topic_dropped(self):
        raw = '[{"english": "hello", "spanish": "hola", "level": 2, "topic": "BOGUS_TOPIC"}]'
        assert parse_flashcard_response(raw) == []

    def test_level_zero_dropped(self):
        raw = '[{"english": "hello", "spanish": "hola", "level": 0, "topic": "general"}]'
        assert parse_flashcard_response(raw) == []

    def test_level_eleven_dropped(self):
        raw = '[{"english": "hello", "spanish": "hola", "level": 11, "topic": "general"}]'
        assert parse_flashcard_response(raw) == []

    def test_missing_spanish_field_dropped(self):
        raw = '[{"english": "hello", "level": 2, "topic": "general"}]'
        assert parse_flashcard_response(raw) == []

    def test_missing_english_field_dropped(self):
        raw = '[{"spanish": "hola", "level": 2, "topic": "general"}]'
        assert parse_flashcard_response(raw) == []

    def test_completely_malformed_returns_empty(self):
        assert parse_flashcard_response("this is not json") == []
        assert parse_flashcard_response("") == []

    def test_mixed_valid_and_invalid_cards(self):
        raw = (
            '[{"english": "yes", "spanish": "sí", "level": 1, "topic": "general"},'
            '{"english": "bad", "spanish": "malo", "level": 0, "topic": "general"}]'
        )
        result = parse_flashcard_response(raw)
        assert len(result) == 1
        assert result[0]["spanish"] == "sí"

    def test_all_six_valid_topics_accepted(self):
        topics = [
            "general", "ordering_food", "directions_transport",
            "shopping_markets", "work_daily_routine", "travel_tourism",
        ]
        for topic in topics:
            raw = f'[{{"english": "x", "spanish": "y", "level": 5, "topic": "{topic}"}}]'
            result = parse_flashcard_response(raw)
            assert len(result) == 1, f"Topic {topic} should be valid"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/oldha/projects/duoVoiceCoach
python -m pytest tests/unit/test_flashcard_parser.py -v 2>&1 | head -30
```

Expected: `ImportError` or `AttributeError` — `parse_flashcard_response` does not exist yet.

- [ ] **Step 3: Add `parse_flashcard_response` to `backend/ai/claude.py`**

Add after the existing imports at the top of `backend/ai/claude.py` (after `import os`):

```python
import json
import re
```

Then add these three items as module-level definitions, inserted before the `_TOOL_DEFINITION` dict:

```python
_VALID_TOPICS = frozenset({
    "general", "ordering_food", "directions_transport",
    "shopping_markets", "work_daily_routine", "travel_tourism",
})


def _validate_cards(cards: list) -> list[dict]:
    result = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        if not all(k in card for k in ("english", "spanish", "level", "topic")):
            continue
        if not isinstance(card["level"], int) or not (1 <= card["level"] <= 10):
            continue
        if card["topic"] not in _VALID_TOPICS:
            continue
        result.append({
            "english": str(card["english"]),
            "spanish": str(card["spanish"]),
            "level": card["level"],
            "topic": card["topic"],
        })
    return result


def parse_flashcard_response(raw_text: str) -> list[dict]:
    """Extract and validate flashcard dicts from Claude's raw text response."""
    text = raw_text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return _validate_cards(parsed)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    return _validate_cards(parsed)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/unit/test_flashcard_parser.py -v
```

Expected: 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/ai/claude.py tests/unit/test_flashcard_parser.py
git commit -m "feat: add parse_flashcard_response with topic/level validation"
```

---

### Task 2: Flashcard store (`load_user_deck`, `save_user_deck`) + unit tests

**Files:**
- Modify: `backend/main.py`
- Create: `tests/unit/test_flashcard_store.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_flashcard_store.py`:

```python
import json
import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

from backend.main import load_user_deck, save_user_deck


def _unique_card(spanish_suffix: str) -> dict:
    """Create a card with a unique Spanish phrase that won't clash with the static deck."""
    return {
        "english": "test phrase",
        "spanish": f"__test_frase_{spanish_suffix}__",
        "level": 3,
        "topic": "general",
    }


class TestLoadUserDeck:
    def test_returns_empty_list_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        assert load_user_deck() == []

    def test_returns_cards_from_existing_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = {"id": "u-abc", "english": "hi", "spanish": "__test_hi__", "level": 1, "topic": "general"}
        deck_file = tmp_path / "user_flashcards.json"
        deck_file.write_text(json.dumps([card]))
        result = load_user_deck()
        assert len(result) == 1
        assert result[0]["spanish"] == "__test_hi__"


class TestSaveUserDeck:
    def test_creates_file_on_first_write(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = _unique_card("create_test")
        saved = save_user_deck([card])
        assert len(saved) == 1
        assert (tmp_path / "user_flashcards.json").exists()

    def test_saved_card_has_u_prefixed_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        saved = save_user_deck([_unique_card("id_prefix")])
        assert saved[0]["id"].startswith("u-")

    def test_appends_to_existing_cards(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        save_user_deck([_unique_card("first")])
        save_user_deck([_unique_card("second")])
        result = load_user_deck()
        assert len(result) == 2

    def test_exact_spanish_match_is_deduped(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = _unique_card("dedup_exact")
        save_user_deck([card])
        saved = save_user_deck([card])
        assert saved == []
        assert len(load_user_deck()) == 1

    def test_dedup_is_case_insensitive(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = {"english": "x", "spanish": "__TEST_CASE__", "level": 1, "topic": "general"}
        save_user_deck([card])
        card_lower = {"english": "x", "spanish": "__test_case__", "level": 1, "topic": "general"}
        saved = save_user_deck([card_lower])
        assert saved == []

    def test_near_match_different_word_is_kept(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        save_user_deck([_unique_card("near_a")])
        saved = save_user_deck([_unique_card("near_b")])
        assert len(saved) == 1

    def test_all_duplicate_input_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = _unique_card("all_dup")
        save_user_deck([card])
        result = save_user_deck([card, card])
        assert result == []

    def test_idempotency_same_card_twice_stored_once(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = _unique_card("idempotent")
        save_user_deck([card])
        save_user_deck([card])
        assert len(load_user_deck()) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/test_flashcard_store.py -v 2>&1 | head -20
```

Expected: `ImportError` — `load_user_deck` and `save_user_deck` not defined yet.

- [ ] **Step 3: Add `import uuid` to `backend/main.py`**

In `backend/main.py`, find the existing imports block and add `uuid`:

```python
import uuid
```

Add it alongside the other stdlib imports (`base64`, `json`, `os`, `pathlib`, `secrets`).

- [ ] **Step 4: Add store helpers to `backend/main.py`**

Add these three functions directly after the `_FLASHCARD_DECK_PATH` definition (currently at line 241):

```python
def _get_user_deck_path() -> pathlib.Path:
    data_dir = pathlib.Path(os.environ.get("DVC_DATA_DIR", "~/.duoVoiceCoach")).expanduser()
    return data_dir / "user_flashcards.json"


def load_user_deck() -> list[dict]:
    path = _get_user_deck_path()
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def save_user_deck(new_cards: list[dict]) -> list[dict]:
    """Append new_cards to user deck after deduplication. Returns only the cards actually saved."""
    existing = load_user_deck()
    existing_spanish = {c["spanish"].lower().strip() for c in existing}
    try:
        with open(_FLASHCARD_DECK_PATH) as f:
            static = json.load(f)
        existing_spanish.update(c["spanish"].lower().strip() for c in static)
    except (OSError, json.JSONDecodeError):
        pass

    saved = []
    for card in new_cards:
        key = card["spanish"].lower().strip()
        if key in existing_spanish:
            continue
        existing_spanish.add(key)
        card_with_id = {"id": f"u-{uuid.uuid4()}", **card}
        existing.append(card_with_id)
        saved.append(card_with_id)

    if saved:
        path = _get_user_deck_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(existing, f, indent=2)

    return saved
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/unit/test_flashcard_store.py -v
```

Expected: 10 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/unit/test_flashcard_store.py
git commit -m "feat: add load_user_deck and save_user_deck with deduplication"
```

---

### Task 3: `generate_flashcards` method + abstract base update

**Files:**
- Modify: `backend/ai/base.py`
- Modify: `backend/ai/claude.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_ai_providers.py`. First check the file to understand the existing pattern, then append:

```python
def test_abstract_provider_generate_flashcards_raises():
    from backend.ai.base import AbstractAIProvider
    # AbstractAIProvider cannot be instantiated directly
    with pytest.raises(TypeError):
        AbstractAIProvider()
```

Also add an import at the top of that file if `pytest` isn't already imported.

- [ ] **Step 2: Run to verify current state**

```bash
python -m pytest tests/unit/test_ai_providers.py -v 2>&1 | tail -10
```

Note the current pass/fail count before changes.

- [ ] **Step 3: Add `generate_flashcards` to `backend/ai/base.py`**

Replace the entire file:

```python
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from backend.session import Session, CoachResponse, TurnError, PronunciationEvaluation


class AbstractAIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def chat(self, session: "Session", user_text: str) -> "Union[CoachResponse, TurnError]":
        """Send a user turn to the AI and return a CoachResponse or TurnError.

        Never raises — errors are returned as TurnError values.
        """
        raise NotImplementedError

    @abstractmethod
    def evaluate_pronunciation(self, target: str, transcript: str) -> "Union[PronunciationEvaluation, TurnError]":
        """Score a pronunciation attempt. Never raises — errors returned as TurnError."""
        raise NotImplementedError

    @abstractmethod
    def translate(self, english_text: str) -> "Union[str, TurnError]":
        """Translate English text to Spanish. Never raises — errors returned as TurnError."""
        raise NotImplementedError

    @abstractmethod
    def generate_flashcards(self, text: str, turns: list[dict], source: str) -> "Union[list[dict], TurnError]":
        """Extract flashcard vocabulary from text. Never raises — errors returned as TurnError."""
        raise NotImplementedError
```

- [ ] **Step 4: Add `generate_flashcards` to `ClaudeProvider` in `backend/ai/claude.py`**

Add this method to `ClaudeProvider`, after the `evaluate_pronunciation` method:

```python
def generate_flashcards(self, text: str, turns: list[dict], source: str) -> Union[list[dict], TurnError]:
    turns_lines = []
    for t in turns:
        speaker = t.get("speaker", "")
        content = t.get("transcript_norm", "") if speaker == "user" else t.get("coach_text", "")
        if content:
            turns_lines.append(f"{speaker}: {content}")
    turns_context = "\n".join(turns_lines)

    if source == "conversation":
        focal = f"Full conversation:\n{turns_context}"
        card_count = "5–15"
    else:
        context_section = f"\n\nConversation context:\n{turns_context}" if turns_context else ""
        focal = f"Text: {text}{context_section}"
        card_count = "3–8"

    prompt = (
        "Extract vocabulary and key phrases suitable for Spanish flashcard study.\n\n"
        f"{focal}\n\n"
        "Assign each card exactly one of these topic IDs:\n"
        "general, ordering_food, directions_transport, shopping_markets, work_daily_routine, travel_tourism\n\n"
        "Assign difficulty levels 1–10 (1=very basic greetings, 10=advanced native-level).\n\n"
        f"Return {card_count} cards as a bare JSON array only — no prose, no markdown fences:\n"
        '[{"english": "...", "spanish": "...", "level": N, "topic": "..."}]'
    )

    try:
        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        return parse_flashcard_response(raw)
    except Exception as exc:
        return TurnError(stage="ai", message=f"Flashcard generation failed: {exc}", recoverable=True)
```

- [ ] **Step 5: Run all unit tests to verify no regressions**

```bash
python -m pytest tests/unit/ -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/ai/base.py backend/ai/claude.py tests/unit/test_ai_providers.py
git commit -m "feat: add generate_flashcards to ClaudeProvider and abstract base"
```

---

### Task 4: `POST /flashcards/generate` route + update `GET /flashcards/deck` + deck merge tests

**Files:**
- Modify: `backend/main.py`
- Modify: `tests/unit/test_flashcards.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_flashcards.py`:

```python
import json
import pathlib


class TestGetFlashcardDeckMerged:
    def test_user_deck_cards_appear_in_results(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        user_card = {
            "id": "u-test-1",
            "english": "test user card",
            "spanish": "__test_user_card__",
            "level": 3,
            "topic": "general",
        }
        deck_file = tmp_path / "user_flashcards.json"
        deck_file.write_text(json.dumps([user_card]))

        response = client.get("/flashcards/deck")
        assert response.status_code == 200
        spanish_phrases = [c["spanish"] for c in response.json()]
        assert "__test_user_card__" in spanish_phrases

    def test_topic_filter_applies_to_user_cards(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        user_card = {
            "id": "u-test-2",
            "english": "to travel",
            "spanish": "__test_viajar__",
            "level": 4,
            "topic": "travel_tourism",
        }
        deck_file = tmp_path / "user_flashcards.json"
        deck_file.write_text(json.dumps([user_card]))

        response = client.get("/flashcards/deck?topic=general")
        assert response.status_code == 200
        spanish_phrases = [c["spanish"] for c in response.json()]
        assert "__test_viajar__" not in spanish_phrases

    def test_level_filter_applies_to_user_cards(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        user_card = {
            "id": "u-test-3",
            "english": "difficult word",
            "spanish": "__test_dificil__",
            "level": 9,
            "topic": "general",
        }
        deck_file = tmp_path / "user_flashcards.json"
        deck_file.write_text(json.dumps([user_card]))

        response = client.get("/flashcards/deck?level_max=5")
        assert response.status_code == 200
        spanish_phrases = [c["spanish"] for c in response.json()]
        assert "__test_dificil__" not in spanish_phrases


class TestPostFlashcardGenerate:
    def test_returns_200_with_list(self, monkeypatch):
        monkeypatch.setattr(
            "backend.main.claude_provider",
            type("MockProvider", (), {
                "generate_flashcards": lambda self, text, turns, source: [
                    {"english": "to ask for", "spanish": "__test_pedir__", "level": 3, "topic": "ordering_food"}
                ],
            })(),
        )
        response = client.post("/flashcards/generate", json={
            "text": "Quisiera pedir la cuenta",
            "turns": [],
            "source": "turn",
        })
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_returns_empty_list_for_all_duplicates(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "backend.main.claude_provider",
            type("MockProvider", (), {
                "generate_flashcards": lambda self, text, turns, source: [
                    {"english": "yes", "spanish": "__test_si_dup__", "level": 1, "topic": "general"}
                ],
            })(),
        )
        # First call saves the card
        client.post("/flashcards/generate", json={"text": "sí", "turns": [], "source": "turn"})
        # Second call should return empty (duplicate)
        response = client.post("/flashcards/generate", json={"text": "sí", "turns": [], "source": "turn"})
        assert response.status_code == 200
        assert response.json() == []

    def test_provider_error_returns_500(self, monkeypatch):
        from backend.session import TurnError
        monkeypatch.setattr(
            "backend.main.claude_provider",
            type("MockProvider", (), {
                "generate_flashcards": lambda self, text, turns, source: TurnError(
                    stage="ai", message="Claude failed", recoverable=True
                ),
            })(),
        )
        response = client.post("/flashcards/generate", json={
            "text": "test",
            "turns": [],
            "source": "turn",
        })
        assert response.status_code == 500
```

- [ ] **Step 2: Run to verify they fail**

```bash
python -m pytest tests/unit/test_flashcards.py -v 2>&1 | tail -20
```

Expected: `TestGetFlashcardDeckMerged` and `TestPostFlashcardGenerate` fail — route and merge not implemented yet.

- [ ] **Step 3: Add `FlashcardGenerateRequest` model and route to `backend/main.py`**

Add the Pydantic model after `SessionStartRequest`:

```python
class FlashcardGenerateRequest(BaseModel):
    text: str | None = None
    turns: list[dict] = []
    source: Literal["turn", "conversation", "translation"] = "turn"
```

Add the route after the existing `GET /flashcards/deck` handler:

```python
@app.post("/flashcards/generate")
def post_flashcard_generate(body: FlashcardGenerateRequest):
    result = claude_provider.generate_flashcards(body.text or "", body.turns, body.source)
    if isinstance(result, TurnError):
        raise HTTPException(status_code=500, detail=result.message)
    return save_user_deck(result)
```

- [ ] **Step 4: Update `GET /flashcards/deck` to merge user deck**

Replace the existing `get_flashcard_deck` function:

```python
@app.get("/flashcards/deck")
def get_flashcard_deck(
    level_min: int = None,
    level_max: int = None,
    topic: str = None,
):
    try:
        with open(_FLASHCARD_DECK_PATH) as f:
            deck = json.load(f)
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Flashcard deck data not found")
    deck = deck + load_user_deck()
    if topic is not None:
        deck = [c for c in deck if c["topic"] == topic]
    if level_min is not None:
        deck = [c for c in deck if c["level"] >= level_min]
    if level_max is not None:
        deck = [c for c in deck if c["level"] <= level_max]
    return deck
```

- [ ] **Step 5: Run all unit tests**

```bash
python -m pytest tests/unit/ -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/unit/test_flashcards.py
git commit -m "feat: add POST /flashcards/generate route and merge user deck into GET /flashcards/deck"
```

---

### Task 5: `FlashcardButton` shared component + CSS

**Files:**
- Create: `frontend/src/components/FlashcardButton.jsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/__tests__/FlashcardButton.test.jsx`:

```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import FlashcardButton from '../components/FlashcardButton'

describe('FlashcardButton', () => {
  it('renders with provided label', () => {
    render(<FlashcardButton label="Add to flashcards" onAdd={vi.fn()} />)
    expect(screen.getByText('Add to flashcards')).toBeInTheDocument()
  })

  it('shows loading state while onAdd is pending', async () => {
    let resolve
    const onAdd = () => new Promise((r) => { resolve = r })
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    expect(screen.getByText('...')).toBeInTheDocument()
    resolve({ added: 1 })
  })

  it('shows count on success with cards added', async () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 2 })
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(screen.getByText('✓ 2 added')).toBeInTheDocument())
  })

  it('shows already in deck when count is 0', async () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 0 })
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(screen.getByText('✓ Already in deck')).toBeInTheDocument())
  })

  it('shows error state on failure', async () => {
    const onAdd = vi.fn().mockRejectedValue(new Error('Network error'))
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(screen.getByText('Error')).toBeInTheDocument())
  })

  it('is disabled while loading', async () => {
    let resolve
    const onAdd = () => new Promise((r) => { resolve = r })
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(screen.getByText('...')).toBeDisabled())
    resolve({ added: 0 })
  })
})
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /home/oldha/projects/duoVoiceCoach/frontend
npx vitest run src/__tests__/FlashcardButton.test.jsx 2>&1 | tail -15
```

Expected: FAIL — `FlashcardButton` does not exist.

- [ ] **Step 3: Create `frontend/src/components/FlashcardButton.jsx`**

```jsx
import { useState } from 'react'

export default function FlashcardButton({ label, onAdd }) {
  const [status, setStatus] = useState('idle')
  const [count, setCount] = useState(0)

  async function handleClick() {
    if (status !== 'idle') return
    setStatus('loading')
    try {
      const result = await onAdd()
      setCount(result?.added ?? 0)
      setStatus('done')
      setTimeout(() => setStatus('idle'), 2000)
    } catch {
      setStatus('error')
      setTimeout(() => setStatus('idle'), 2000)
    }
  }

  const buttonLabel =
    status === 'loading' ? '...' :
    status === 'done' ? (count === 0 ? '✓ Already in deck' : `✓ ${count} added`) :
    status === 'error' ? 'Error' :
    label

  return (
    <button
      className="flashcard-add-btn"
      onClick={handleClick}
      disabled={status !== 'idle'}
      aria-label={label}
    >
      {buttonLabel}
    </button>
  )
}
```

- [ ] **Step 4: Add CSS for `.flashcard-add-btn` to `frontend/src/App.css`**

Append to the end of `frontend/src/App.css`:

```css
/* ── Flashcard add button ───────────────────────────── */
.flashcard-add-btn {
  padding: 2px 8px;
  font-size: 0.7rem;
  background: transparent;
  color: var(--accent, #6c63ff);
  border: 1px solid var(--accent, #6c63ff);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
}

.flashcard-add-btn:hover:not(:disabled) {
  background: var(--accent, #6c63ff);
  color: #fff;
}

.flashcard-add-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npx vitest run src/__tests__/FlashcardButton.test.jsx
```

Expected: 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/FlashcardButton.jsx frontend/src/App.css frontend/src/__tests__/FlashcardButton.test.jsx
git commit -m "feat: add FlashcardButton shared component with idle/loading/done/error state"
```

---

### Task 6: `App.jsx` `handleAddFlashcards` + `ConversationView` pass-through + App test

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/ConversationView.jsx`
- Create: `frontend/src/__tests__/App.flashcard.test.jsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/__tests__/App.flashcard.test.jsx`:

```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'

const MOCK_TURNS = [
  { speaker: 'user', transcript_norm: 'Quisiera una mesa', coach_text: null },
  { speaker: 'coach', transcript_norm: null, coach_text: '¿Para cuántas personas?' },
]

vi.mock('../hooks/useVoice', () => ({
  useVoice: () => ({
    state: 'idle',
    turns: MOCK_TURNS,
    corrections: [],
    error: null,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    newSession: vi.fn(() => Promise.resolve('session-test')),
    loadSession: vi.fn(),
  }),
}))

let fetchMock

beforeEach(() => {
  fetchMock = vi.fn().mockImplementation((url) => {
    if (url === '/flashcards/generate') {
      return Promise.resolve({
        json: () => Promise.resolve([
          { id: 'u-1', english: 'a table', spanish: 'una mesa', level: 2, topic: 'ordering_food' },
        ]),
      })
    }
    return Promise.resolve({ json: () => Promise.resolve([]) })
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App — handleAddFlashcards', () => {
  it('calls POST /flashcards/generate with turn source and turns array', async () => {
    render(<App />)
    await waitFor(() => screen.getAllByText('Add to flashcards'))
    fireEvent.click(screen.getAllByText('Add to flashcards')[0])

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url === '/flashcards/generate')
      expect(call).toBeDefined()
      const body = JSON.parse(call[1].body)
      expect(body.source).toBe('turn')
      expect(Array.isArray(body.turns)).toBe(true)
      expect(body.turns).toHaveLength(2)
    })
  })

  it('calls POST /flashcards/generate with conversation source when "Add conversation" clicked', async () => {
    render(<App />)
    await waitFor(() => screen.getByText('Add conversation'))
    fireEvent.click(screen.getByText('Add conversation'))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url === '/flashcards/generate')
      expect(call).toBeDefined()
      const body = JSON.parse(call[1].body)
      expect(body.source).toBe('conversation')
    })
  })
})
```

- [ ] **Step 2: Run to verify they fail**

```bash
npx vitest run src/__tests__/App.flashcard.test.jsx 2>&1 | tail -15
```

Expected: FAIL — `handleAddFlashcards` and "Add to flashcards" buttons don't exist yet.

- [ ] **Step 3: Add `handleAddFlashcards` to `frontend/src/App.jsx`**

Add this function alongside `handlePractice` and `handleTranslationResult`:

```jsx
async function handleAddFlashcards(text, source) {
  let body
  if (source === 'conversation') {
    const conversationText = turns
      .map((t) => `${t.speaker}: ${t.speaker === 'user' ? t.transcript_norm : t.coach_text}`)
      .join('\n')
    body = { text: conversationText, turns, source }
  } else {
    body = { text, turns, source }
  }
  const res = await fetch('/flashcards/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  return { added: Array.isArray(data) ? data.length : 0 }
}
```

- [ ] **Step 4: Pass `onAddFlashcards` to `ConversationView` and `TranslationView` in `frontend/src/App.jsx`**

Update the `ConversationView` JSX to include the new prop:

```jsx
{mode === 'conversation' && (
  <ConversationView
    state={state}
    turns={turns}
    error={error}
    onRecord={startRecording}
    onStop={stopRecording}
    onPractice={handlePractice}
    onAddFlashcards={handleAddFlashcards}
    coachingMode={config.coaching_mode}
    hint={conversationHint}
  />
)}
```

Update the `TranslationView` JSX:

```jsx
{mode === 'translation' && (
  <TranslationView
    config={config}
    onResult={handleTranslationResult}
    onPractice={handlePractice}
    onAddFlashcards={handleAddFlashcards}
  />
)}
```

- [ ] **Step 5: Update `frontend/src/components/ConversationView.jsx` to accept and pass the prop**

Replace the function signature and `Transcript` usage:

```jsx
export default function ConversationView({ state, turns, error, onRecord, onStop, onPractice, onAddFlashcards, coachingMode, hint }) {
```

And update the `Transcript` line to include `onAddFlashcards`:

```jsx
<Transcript turns={turns} onPractice={onPractice} onAddFlashcards={onAddFlashcards} />
```

- [ ] **Step 6: Run tests**

```bash
npx vitest run src/__tests__/App.flashcard.test.jsx
```

Expected: FAIL still — Transcript doesn't render the buttons yet. This is expected; the buttons are added in Task 7.

Note: Once Task 7 is complete, re-run this test to confirm it passes.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.jsx frontend/src/components/ConversationView.jsx frontend/src/__tests__/App.flashcard.test.jsx
git commit -m "feat: add handleAddFlashcards to App and wire onAddFlashcards through ConversationView"
```

---

### Task 7: `Transcript.jsx` flashcard buttons + tests

**Files:**
- Modify: `frontend/src/components/Transcript.jsx`
- Modify: `frontend/src/__tests__/Transcript.test.jsx`

- [ ] **Step 1: Write the failing tests**

First update the import line at the top of `frontend/src/__tests__/Transcript.test.jsx` to add `waitFor`:

```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
```

Then append to `frontend/src/__tests__/Transcript.test.jsx`:

```jsx
describe('Transcript — flashcard buttons', () => {
  const twoTurns = [
    { speaker: 'user', transcript_norm: 'Hola', coach_text: null },
    { speaker: 'coach', transcript_norm: null, coach_text: '¡Hola!' },
  ]

  it('"Add to flashcards" button present on user turns', () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<Transcript turns={twoTurns} onAddFlashcards={onAdd} />)
    const addButtons = screen.getAllByText('Add to flashcards')
    expect(addButtons.length).toBeGreaterThanOrEqual(1)
  })

  it('"Add to flashcards" button present on coach turns', () => {
    const turns = [{ speaker: 'coach', transcript_norm: null, coach_text: '¡Hola!' }]
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<Transcript turns={turns} onAddFlashcards={onAdd} />)
    expect(screen.getByText('Add to flashcards')).toBeInTheDocument()
  })

  it('"Add conversation" button absent when turns.length < 2', () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<Transcript turns={[twoTurns[0]]} onAddFlashcards={onAdd} />)
    expect(screen.queryByText('Add conversation')).not.toBeInTheDocument()
  })

  it('"Add conversation" button present when turns.length >= 2', () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<Transcript turns={twoTurns} onAddFlashcards={onAdd} />)
    expect(screen.getByText('Add conversation')).toBeInTheDocument()
  })

  it('clicking "Add to flashcards" on a turn calls onAddFlashcards with source "turn"', async () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<Transcript turns={[twoTurns[0]]} onAddFlashcards={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(onAdd).toHaveBeenCalledWith('Hola', 'turn'))
  })

  it('clicking "Add conversation" calls onAddFlashcards with source "conversation"', async () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 2 })
    render(<Transcript turns={twoTurns} onAddFlashcards={onAdd} />)
    fireEvent.click(screen.getByText('Add conversation'))
    await waitFor(() => expect(onAdd).toHaveBeenCalledWith(null, 'conversation'))
  })

  it('flashcard buttons absent when onAddFlashcards prop is not provided', () => {
    render(<Transcript turns={twoTurns} />)
    expect(screen.queryByText('Add to flashcards')).not.toBeInTheDocument()
    expect(screen.queryByText('Add conversation')).not.toBeInTheDocument()
  })
})
```

Add `waitFor` to the existing import at the top of the test file if not already there:

```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
```

- [ ] **Step 2: Run to verify they fail**

```bash
npx vitest run src/__tests__/Transcript.test.jsx 2>&1 | tail -20
```

Expected: the new `flashcard buttons` describe block fails.

- [ ] **Step 3: Rewrite `frontend/src/components/Transcript.jsx`**

```jsx
import { useState } from 'react'
import FlashcardButton from './FlashcardButton'

export default function Transcript({ turns, onPractice, onAddFlashcards }) {
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
                  onClick={() => onPractice?.(text, 'conversation')}
                  aria-label="Practice this phrase"
                >
                  Practice
                </button>
              )}
              {onAddFlashcards && (
                <FlashcardButton
                  label="Add to flashcards"
                  onAdd={() => onAddFlashcards(text, 'turn')}
                />
              )}
            </div>
            <span className={`turn-text${isCollapsed ? ' turn-text--hidden' : ''}`}>
              {isCollapsed ? '···' : text}
            </span>
          </div>
        )
      })}
      {turns.length >= 2 && onAddFlashcards && (
        <div className="transcript-footer">
          <FlashcardButton
            label="Add conversation"
            onAdd={() => onAddFlashcards(null, 'conversation')}
          />
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run all Transcript tests**

```bash
npx vitest run src/__tests__/Transcript.test.jsx
```

Expected: all tests PASS (both existing and new).

- [ ] **Step 5: Run App.flashcard tests (now the buttons exist)**

```bash
npx vitest run src/__tests__/App.flashcard.test.jsx
```

Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Transcript.jsx frontend/src/__tests__/Transcript.test.jsx
git commit -m "feat: add per-turn and whole-conversation flashcard buttons to Transcript"
```

---

### Task 8: `TranslationView.jsx` flashcard button + tests

**Files:**
- Modify: `frontend/src/components/TranslationView.jsx`
- Modify: `frontend/src/__tests__/TranslationView.test.jsx`

- [ ] **Step 1: Write the failing tests**

Append to `frontend/src/__tests__/TranslationView.test.jsx`:

```jsx
import { fireEvent, waitFor } from '@testing-library/react'

describe('TranslationView — flashcard button', () => {
  it('"Add to flashcards" button absent when there is no result', () => {
    render(<TranslationView config={DEFAULT_CONFIG} onAddFlashcards={vi.fn()} />)
    expect(screen.queryByText('Add to flashcards')).not.toBeInTheDocument()
  })

  it('"Add to flashcards" button absent when onAddFlashcards prop is not provided', () => {
    render(<TranslationView config={DEFAULT_CONFIG} />)
    expect(screen.queryByText('Add to flashcards')).not.toBeInTheDocument()
  })
})
```

Note: testing the button appearing after a result requires mocking `fetch` and the MediaRecorder — that interaction is already covered by App.flashcard.test.jsx. The unit tests here confirm the conditional rendering contract.

- [ ] **Step 2: Run to verify they fail**

```bash
npx vitest run src/__tests__/TranslationView.test.jsx 2>&1 | tail -15
```

Expected: the new tests PASS immediately (no result = no button is already true). This is fine — the next step adds the button; re-running confirms it doesn't appear without a result.

- [ ] **Step 3: Update `frontend/src/components/TranslationView.jsx`**

Add `FlashcardButton` import at the top:

```jsx
import FlashcardButton from './FlashcardButton'
```

Update the function signature to accept `onAddFlashcards`:

```jsx
export default function TranslationView({ config, onResult, onPractice, onAddFlashcards }) {
```

Update the result block to include the flashcard button (after the Practice pronunciation button):

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
    {onAddFlashcards && (
      <FlashcardButton
        label="Add to flashcards"
        onAdd={() => onAddFlashcards(result.spanish, 'translation')}
      />
    )}
  </div>
)}
```

- [ ] **Step 4: Run all TranslationView tests**

```bash
npx vitest run src/__tests__/TranslationView.test.jsx
```

Expected: all tests PASS.

- [ ] **Step 5: Run full frontend test suite to check for regressions**

```bash
npx vitest run
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/TranslationView.jsx frontend/src/__tests__/TranslationView.test.jsx
git commit -m "feat: add Add to flashcards button to TranslationView result block"
```

---

### Task 9: `slow` marker registration + slow integration test

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/integration/test_flashcard_generate.py`

- [ ] **Step 1: Register the `slow` marker in `pyproject.toml`**

Replace the `[tool.pytest.ini_options]` section:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow — require real API keys, deselect with '-m \"not slow\"'",
]
```

- [ ] **Step 2: Verify the marker is registered (no warning)**

```bash
python -m pytest --markers 2>&1 | grep slow
```

Expected: line containing `slow: marks tests as slow`.

- [ ] **Step 3: Write the slow integration test**

Create `tests/integration/test_flashcard_generate.py`:

```python
import json
import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

_VALID_TOPICS = {"general", "ordering_food", "directions_transport", "shopping_markets", "work_daily_routine", "travel_tourism"}


def _has_real_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return bool(key) and key != "test-key"


@pytest.mark.slow
class TestFlashcardGenerateIntegration:
    def test_generates_cards_from_short_phrase(self, tmp_path, monkeypatch):
        if not _has_real_api_key():
            pytest.skip("ANTHROPIC_API_KEY not set to a real key")
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))

        from backend.ai.claude import ClaudeProvider
        provider = ClaudeProvider()
        result = provider.generate_flashcards(
            "Quisiera pedir la cuenta, por favor",
            [],
            "turn",
        )

        from backend.session import TurnError
        assert not isinstance(result, TurnError), f"Got TurnError: {result.message}"
        assert len(result) > 0

        for card in result:
            assert "english" in card, f"Missing 'english': {card}"
            assert "spanish" in card, f"Missing 'spanish': {card}"
            assert "level" in card, f"Missing 'level': {card}"
            assert "topic" in card, f"Missing 'topic': {card}"
            assert 1 <= card["level"] <= 10, f"Level out of range: {card['level']}"
            assert card["topic"] in _VALID_TOPICS, f"Invalid topic: {card['topic']}"

    def test_generate_endpoint_saves_to_user_deck(self, tmp_path, monkeypatch):
        if not _has_real_api_key():
            pytest.skip("ANTHROPIC_API_KEY not set to a real key")
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))

        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)

        response = client.post("/flashcards/generate", json={
            "text": "Quisiera pedir la cuenta, por favor",
            "turns": [],
            "source": "turn",
        })
        assert response.status_code == 200
        cards = response.json()
        assert isinstance(cards, list)

        if len(cards) > 0:
            deck_path = tmp_path / "user_flashcards.json"
            assert deck_path.exists()
            saved = json.loads(deck_path.read_text())
            assert len(saved) == len(cards)
            for card in saved:
                assert card["id"].startswith("u-")
```

- [ ] **Step 4: Run the slow test to verify it works (requires real ANTHROPIC_API_KEY)**

```bash
python -m pytest tests/integration/test_flashcard_generate.py -v -m slow
```

Expected: 2 tests PASS (or SKIP if key not set).

- [ ] **Step 5: Verify fast tests still skip the slow marker**

```bash
python -m pytest tests/ -v -m "not slow" 2>&1 | tail -5
```

Expected: integration flashcard tests are deselected; all other tests pass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tests/integration/test_flashcard_generate.py
git commit -m "feat: add slow integration test for flashcard generation and register slow marker"
```

---

## Running the full test suite

After all tasks are complete:

```bash
# Fast tests only (CI-safe)
python -m pytest tests/ -m "not slow" -v

# Frontend tests
cd frontend && npx vitest run

# Slow tests (requires real ANTHROPIC_API_KEY)
python -m pytest tests/ -m slow -v
```
