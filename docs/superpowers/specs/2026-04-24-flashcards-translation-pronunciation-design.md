# duoVoiceCoach — Flashcards, Translation & Pronunciation Design Spec

**Date:** 2026-04-24
**Status:** Approved — ready for implementation planning
**Phases:** Phase A (Flashcards + Translation) → Phase B (Pronunciation Practice)

---

## Context

Phases 0–9 delivered a working desktop Spanish voice coach with session config, persistence, ElevenLabs TTS, and a two-pane GUI. Phase 12 (mobile corrections) and Phase 13 (progress tracking, structured lessons) are already planned. This spec adds three new practice modes as two sequential phases that sit after Phase 13 in the roadmap.

All three features are **separate modes** alongside the existing conversation — a top-level `mode` state in `App.jsx` switches between views. This keeps each feature isolated, independently testable, and independently phaseable with no entanglement in the conversation state machine.

---

## Navigation / Mode Switching

### Architecture

`App.jsx` gains a `mode` state:

```js
const [mode, setMode] = useState('conversation')
// 'conversation' | 'flashcards' | 'translation' | 'pronunciation'
```

The existing left-pane content (`<Transcript>` + `<VoiceButton>`) is extracted into `ConversationView.jsx`. The left pane renders whichever view matches `mode`. The right pane (session config, corrections, session history) is unchanged across all modes.

### New Files

| File | Purpose |
|------|---------|
| `frontend/src/components/NavTabs.jsx` | Tab bar: Conversation / Flashcards / Translation / Pronunciation |
| `frontend/src/components/ConversationView.jsx` | Current left-pane content, extracted |
| `frontend/src/components/FlashcardsView.jsx` | Phase A |
| `frontend/src/components/TranslationView.jsx` | Phase A |
| `frontend/src/components/PronunciationView.jsx` | Phase B |

### CSS

`NavTabs` sits inside `.app-header`, below the title. Tab styling added to `App.css` — no grid layout changes.

---

## Phase A — Flashcards

### Data Source

A static JSON file `backend/data/flashcard_deck.json` ships with the codebase. Each card:

```json
{ "id": "str", "english": "str", "spanish": "str", "level": 1-10, "topic": "str" }
```

Claude generates this file offline. Topics match the existing `/topics` endpoint values. Cards span levels 1–10 with sufficient coverage per topic/level combination to make filtering worthwhile.

### Backend

**`GET /flashcards/deck`**
- Query params: `?level=1-10` (optional), `?topic=str` (optional)
- Returns filtered array of card objects
- Reads from `flashcard_deck.json` — no database

**Path to session-derived cards (future enhancement, not Phase A):**
A future `GET /flashcards/session-deck` endpoint extracts `Correction` records from stored sessions, maps them to card format (`original` → error form, `corrected` → correct form, `explanation` → hint). The flashcard UI gains a "Curated / From my sessions" toggle with no structural changes to the endpoint or view.

**Option C — Manual card entry:** Considered and rejected. Requires CRUD UI, new persistence layer, and backend endpoints. High effort relative to value when automatic sources (curated list, session corrections) already exist.

### Frontend — `FlashcardsView`

**State:** `deck` (fetched array), `index` (current card), `flipped` (boolean), `topic` (selector value), `level` (selector value).

**UI:**
- Topic dropdown (populated from `/topics` endpoint — reuse existing data)
- Level selector: four coarse bands — Beginner (1–2), Elementary (3–4), Intermediate (5–6), Advanced (7–10). Not a 10-point slider; flashcards don't need per-point granularity.
- Card display: English on front, Spanish on back. Flip / Previous / Next buttons.
- Progress: cards seen/remaining shown as a count. Tracked in component state — no persistence in Phase A.
- Completion: message + restart button when deck exhausts.

**Re-fetch:** when topic or level selector changes, re-fetch the deck with updated params.

**Reuse:** `/topics` endpoint, existing fetch patterns.

### Testing

- Vitest: card flip logic, deck exhaustion/restart, filter re-fetch on selector change
- Integration: `GET /flashcards/deck` response shape with and without query params

---

## Phase A — Translation ("How do you say this in Spanish")

### Flow

User records English speech → Whisper transcribes → Claude translates → Spanish text displayed → TTS plays Spanish aloud. Linear, stateless — no session, no turns, no coaching mode.

### Backend

**`POST /translate`** — multipart audio file input.

Steps:
1. Whisper transcribes (same STT pipeline, unchanged)
2. Claude called with a direct message prompt: `"Translate this English phrase to natural Spanish. Return only the Spanish translation, no explanation."` — no tool use, single string output
3. TTS synthesizes the Spanish using the session's current TTS provider

Returns: `{english: str, spanish: str, audio_b64: str|null, tts_error: obj|null}`

### Frontend — `TranslationView`

**State:** `recordingState` (idle/recording/processing/playing), `result` (null | `{english, spanish}`).

**UI:**
- Large record button at the bottom (same visual pattern as `VoiceButton`)
- When result exists: English transcription in muted label above, Spanish translation prominent below
- Each new recording replaces the previous result — no history list in Phase A

**Reuse:** mic capture and Whisper path identical to conversation pipeline. TTS playback reuses `playAudioB64` / `speakCoachText` logic from `useVoice`.

### Testing

- Vitest: idle/recording/result render states, result replacement on second recording
- Integration: `POST /translate` using a fixture audio file

---

## Phase B — Pronunciation Practice

### Shared Scoring Pipeline

All three sub-features use the same evaluation flow:

1. User speaks target phrase
2. Whisper transcribes
3. `POST /pronunciation/evaluate` receives `{target: str, transcript: str}`
4. Claude returns structured output via tool use:

```json
{
  "score": 0-100,
  "feedback": "str",
  "issues": [{ "sound": "str", "said": "str", "expected": "str" }]
}
```

5. Score and issue list render below the target phrase

### Sub-feature A — Vocabulary Pronunciation (default tab)

- Pulls cards from `GET /flashcards/deck` — same endpoint and topic/level selectors as the Flashcards mode
- Spanish word/phrase shown as target; user records; scoring pipeline runs
- Next card button advances the deck

### Sub-feature B — Phonetic Challenges (second tab)

- Static JSON `backend/data/pronunciation_challenges.json` — curated list of sounds English speakers consistently struggle with (rr, ñ, vowel purity, b/v distinction, j)
- Each entry: `{id, target, sound_focus, hint}`
- New endpoint `GET /pronunciation/challenges` returns the list
- Same record → evaluate flow as sub-feature A

### Sub-feature C — From Conversation History (third tab / hardest)

Accessed via the right pane session history, not the pronunciation tab directly. Each coach turn bubble in a loaded session gains a small "Practice" button. Clicking it:

1. Sets `mode` to `'pronunciation'`
2. Passes the target phrase as a cross-mode prop
3. `PronunciationView` renders in "single phrase" state — no deck navigation, just the target and the scoring flow

This is the most complex sub-feature. It requires:
- A new "Practice" button on coach turn bubbles in `Transcript.jsx`
- Cross-mode state: a `pronunciationTarget` prop passed from the history browser into `PronunciationView` via `App.jsx`
- A distinct render state in `PronunciationView` for single-phrase vs deck mode

Implemented last within Phase B.

### Backend

| Endpoint | Purpose |
|----------|---------|
| `POST /pronunciation/evaluate` | `{target, transcript}` → Claude score + feedback |
| `GET /pronunciation/challenges` | Returns phonetic challenge list |

### Testing

- Vitest: all three tab states in `PronunciationView`, single-phrase state for sub-feature C, cross-mode prop handoff
- Integration: `POST /pronunciation/evaluate` with fixture input

---

## New Backend Endpoints Summary

| Phase | Endpoint | Method | Purpose |
|-------|----------|--------|---------|
| A | `/flashcards/deck` | GET | Curated deck, filtered by level/topic |
| A | `/translate` | POST | English audio → Spanish text + TTS |
| B | `/pronunciation/challenges` | GET | Phonetic challenge list |
| B | `/pronunciation/evaluate` | POST | User audio + target → score + feedback |

---

## Data Files

| File | Phase | Purpose |
|------|-------|---------|
| `backend/data/flashcard_deck.json` | A | Curated vocabulary cards |
| `backend/data/pronunciation_challenges.json` | B | Phonetically challenging words/phrases |

Both files generated offline by Claude and committed to the repo. No runtime generation.

---

## Phase Gates

### Phase A Gate
- All existing tests pass (no regressions)
- `GET /flashcards/deck` returns correctly filtered cards
- `POST /translate` returns Spanish text and TTS audio
- `FlashcardsView`: topic/level filtering works, card flip and deck navigation work
- `TranslationView`: full voice → translation → TTS playback round-trip works
- Manual smoke test signed off in `docs/manualTestLog.md`

### Phase B Gate
- All existing tests pass
- `POST /pronunciation/evaluate` returns score, feedback, and issues
- All three pronunciation sub-features functional
- Sub-feature C: coach bubble "Practice" button correctly hands off phrase to pronunciation view
- Manual smoke test signed off in `docs/manualTestLog.md`
