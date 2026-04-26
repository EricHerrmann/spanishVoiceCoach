# Flashcard Generation from Conversation & Translation — Design

**Date:** 2026-04-26
**Status:** Approved

---

## Goal

Allow users to generate flashcards from any conversation turn, the full conversation, or a translation result. Claude extracts key vocabulary and phrases, infers the appropriate topic, and saves cards to a persistent user deck that merges seamlessly with the built-in deck.

---

## Data Layer

### User deck file

User-generated cards are stored separately from the static built-in deck:

- **Static deck:** `backend/data/flashcard_deck.json` — shipped with the app, reset on redeploy, read-only at runtime
- **User deck:** `$DVC_DATA_DIR/user_flashcards.json` — on the Fly.io persistent volume (`/data/`), survives redeploy, append-only at runtime

Both files share the same card schema:

```json
{
  "id": "u-<uuid4>",
  "english": "I would like to order",
  "spanish": "Quisiera pedir",
  "level": 4,
  "topic": "ordering_food"
}
```

User card IDs are prefixed `u-` to distinguish origin. The user deck file is created automatically on first write.

### Merged deck

`GET /flashcards/deck` loads and concatenates both decks before applying topic and level filters. Order: static cards first, then user cards. No changes to the response schema — user cards are indistinguishable from built-in cards in the API response.

### Valid topics

Claude must assign one of these six topic IDs:

| ID | Label |
|----|-------|
| `general` | General conversation |
| `ordering_food` | Ordering food |
| `directions_transport` | Directions & transport |
| `shopping_markets` | Shopping & markets |
| `work_daily_routine` | Work & daily routine |
| `travel_tourism` | Travel & tourism |

Any topic not in this list returned by Claude is dropped before saving.

### Deduplication

Before saving, the backend loads the merged deck and compares each generated card's `spanish` field (lowercased, stripped) against all existing cards. Exact matches are silently dropped. Near-matches are kept.

---

## Backend API

### New endpoint: `POST /flashcards/generate`

**Request body (JSON):**

```json
{
  "text": "the specific text to generate cards from",
  "turns": [
    {"speaker": "user", "text": "Quisiera una mesa para dos."},
    {"speaker": "coach", "text": "Por supuesto, ¿tiene reserva?"}
  ],
  "source": "turn" | "conversation" | "translation"
}
```

- `text` — the focal content: a single turn's text, all turns concatenated, or the Spanish translation result
- `turns` — full conversation history for context (helps Claude infer topic and calibrate level); always sent even for single-turn requests; empty list for `translation` source
- `source` — shapes the Claude prompt: `turn`/`translation` ask for vocabulary and key phrases from a short text; `conversation` asks for the most teachable phrases across the whole exchange

**Response:**

```json
[
  {"english": "a table for two", "spanish": "una mesa para dos", "level": 3, "topic": "ordering_food"},
  {"english": "do you have a reservation?", "spanish": "¿tiene reserva?", "level": 4, "topic": "ordering_food"}
]
```

Returns only the cards actually saved (after deduplication). Empty array if all were duplicates.

**Implementation location:**
- Route handler: `backend/main.py`
- Claude method: `backend/ai/claude.py` → `ClaudeProvider.generate_flashcards(text, turns, source) -> list[dict] | TurnError`
- Response parser: `backend/ai/claude.py` → `parse_flashcard_response(raw_text) -> list[dict]` (standalone function, independently testable)
- Persistence helpers: `backend/main.py` → `load_user_deck()`, `save_user_deck(cards)`

### Updated endpoint: `GET /flashcards/deck`

Merges static deck + user deck before filtering. No change to query parameters or response schema.

---

## Claude Prompt Design

The `generate_flashcards` method sends a single user message to Claude (no conversation history / system prompt from the session). The prompt:

1. States the task: extract vocabulary and key phrases suitable for flashcard study
2. Provides the focal `text`
3. For `conversation` source: also provides the full turn list for broader extraction
4. Lists the 6 valid topic IDs and instructs Claude to assign exactly one per card
5. Instructs Claude to assign difficulty levels 1–10 (1 = very basic, 10 = advanced native)
6. Requests output as a **bare JSON array only** — no prose, no markdown fences
7. Asks for 3–8 cards for a single turn or translation; 5–15 for a full conversation

---

## Frontend

### New callback in `App.jsx`

The prop exposed to child components is `(text, source)` — two arguments only. App.jsx owns `turns` state (from `useVoice`) and always appends it to the API call internally. For `source: "conversation"`, App.jsx also builds `text` from the `turns` state directly, so the child just calls `onAddFlashcards(null, 'conversation')`.

```
handleAddFlashcards(text, source) -> Promise<{added: number}>
```

Internally, App.jsx constructs the full API body:
- `source: "turn"` or `"translation"` → `{ text, turns: voiceTurns, source }`
- `source: "conversation"` → `{ text: voiceTurns.map(t => `${t.speaker}: ${t.speaker === 'user' ? t.transcript_norm : t.coach_text}`).join('\n'), turns: voiceTurns, source }`

Lives alongside `handlePractice` and `handleTranslationResult`.

### Button placement — three locations

**1. Per-turn in `Transcript.jsx`**
- "Add to flashcards" button in the turn header for every turn (user and coach)
- Calls: `onAddFlashcards(turn.text, 'turn')`

**2. Whole conversation in `Transcript.jsx`**
- "Add conversation" button rendered below all turns, visible only when `turns.length >= 2`
- Calls: `onAddFlashcards(null, 'conversation')`

**3. Translation result in `TranslationView.jsx`**
- "Add to flashcards" button in the result block alongside "Practice pronunciation"
- Calls: `onAddFlashcards(result.spanish, 'translation')`

### Inline feedback

Each button manages local state: `idle | loading | done(n) | error`. On success it shows "✓ N cards added" (or "✓ Already in deck" if N = 0). Message fades after 2 seconds, button returns to idle. No modals, no navigation.

`Transcript.jsx` receives `onAddFlashcards` as a prop from `App.jsx` (same pattern as `onPractice`).

---

## Testing

### Backend unit tests

**Deduplication & persistence** (`tests/unit/test_flashcard_store.py`):
- `load_user_deck()` returns empty list when file does not exist
- `save_user_deck()` creates the file on first write
- `save_user_deck()` appends to existing cards without duplicating
- Dedup: exact Spanish match (lowercased/stripped) is dropped
- Dedup: near-match (different word) is kept
- Dedup: all-duplicate input returns empty saved list
- Idempotency: saving the same card twice results in one card in the file

**Response parser** (`tests/unit/test_flashcard_parser.py`):
- Valid bare JSON array → returns list of card dicts
- JSON embedded in prose / markdown fences → extracted and parsed correctly
- Card with topic not in allowed list → dropped
- Card with level outside 1–10 → dropped
- Card missing required field (`english`, `spanish`, `level`, `topic`) → dropped
- Completely malformed response → returns empty list

**`GET /flashcards/deck` integration** (added to existing integration tests):
- With user deck present, merged results include both static and user cards
- Topic filter applies to both decks
- Level filter applies to both decks

**`POST /flashcards/generate` slow integration test** (`tests/integration/test_flashcard_generate.py`, `@pytest.mark.slow`):
- Calls real Claude with a short Spanish phrase ("Quisiera pedir la cuenta, por favor")
- Response is a non-empty list
- Each card has `english`, `spanish`, `level` (1–10), `topic` (in allowed list)
- Cards are written to a temp user deck path (monkeypatched)

### Frontend unit tests

**`Transcript.jsx`:**
- "Add to flashcards" button present on user turns
- "Add to flashcards" button present on coach turns
- "Add conversation" button absent when `turns.length < 2`
- "Add conversation" button present when `turns.length >= 2`
- Clicking "Add to flashcards" on a turn calls `onAddFlashcards` with correct `source: "turn"`
- Clicking "Add conversation" calls `onAddFlashcards` with `source: "conversation"`

**`TranslationView.jsx`:**
- "Add to flashcards" button present in result block
- Clicking calls `onAddFlashcards` with `source: "translation"` and `text = result.spanish`
- Button absent before result

**`App.jsx`:**
- `handleAddFlashcards` calls `POST /flashcards/generate` with correct body shape

---

## File Map

| File | Change |
|------|--------|
| `backend/main.py` | Add `POST /flashcards/generate` route; update `GET /flashcards/deck` to merge user deck; add `load_user_deck()`, `save_user_deck()` helpers |
| `backend/ai/claude.py` | Add `generate_flashcards(text, turns, source)` method; add `parse_flashcard_response(raw)` function |
| `backend/ai/base.py` | Add `generate_flashcards` abstract method |
| `tests/unit/test_flashcard_store.py` | New — dedup and persistence unit tests |
| `tests/unit/test_flashcard_parser.py` | New — response parser unit tests |
| `tests/integration/test_flashcard_generate.py` | New — slow integration test with real Claude |
| `frontend/src/App.jsx` | Add `handleAddFlashcards`; pass `onAddFlashcards` to `Transcript` and `TranslationView` |
| `frontend/src/components/Transcript.jsx` | Add per-turn "Add to flashcards" button and whole-conversation "Add conversation" button |
| `frontend/src/components/TranslationView.jsx` | Add "Add to flashcards" button to result block |
| `frontend/src/__tests__/Transcript.test.jsx` | Add button presence and callback tests |
| `frontend/src/__tests__/TranslationView.test.jsx` | Add "Add to flashcards" button tests |
| `frontend/src/__tests__/App.flashcard.test.jsx` | New — `handleAddFlashcards` wiring tests |
