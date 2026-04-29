# Code Review Implementation Plan

**Review source:** `docs/codexCodeReview.md` (2026-04-28)  
**Author:** Eric Herrmann  
**Status:** Draft — pending context-window strategy confirmation (see R4 note)

---

## Priority Order

Six findings from the review, executed in this sequence:

| Phase | Finding | Urgency | Risk |
|-------|---------|---------|------|
| R1 | Frontend lint quality gate broken | Fix Now | Low |
| R2 | `backend/main.py` carries business logic | Fix Now | Medium |
| R3 | Audio capture/playback duplicated across frontend | Next Sprint | Medium |
| R4 | Claude turn cost grows linearly | Next Sprint | Low |
| R5 | Persistence paths will become a bottleneck | Defer Soon | Low |
| R6 | Repo hygiene (generated artifacts tracked) | Cleanup | Trivial |

**Rationale for this order:**
- R1 first because a red lint gate invalidates the "clean" phase sign-offs and masks regressions going forward. Low-risk, high-trust payoff.
- R2 second because `main.py` is the highest-churn file and will keep accumulating logic if not broken up before R3–R4 add more.
- R3 before R4 because the Android audio path is a higher-risk area than AI token cost, and consolidating it first simplifies any future hook changes.
- R4 is real cost/latency pressure but acceptable at current session lengths; after R3 the codebase is in better shape to add it cleanly.
- R5 and R6 are low-urgency housekeeping with no functional risk; defer until after the higher-value work lands.

---

## Pros/Cons Summary

**R1 — Lint:** Pure upside. The ESLint config needs a vitest globals block for test files and the hook-rules violations in App.jsx, CoachOverlay.jsx, and ConversationView.jsx need fixing. Risk of behavior change is negligible since lint errors rarely indicate runtime bugs — but fixing them prevents real ones from hiding.

**R2 — Backend decomposition:** Significant maintenance gain; aligns with the stated architecture contract in CLAUDE.md (routes only in main.py). Moderate risk from import refactors. Mitigation: all existing tests pass at phase gate — no new behavior, only reorganization. The proposed module split (turn_service, flashcards_store, translation_service, pronunciation_service) is appropriate; do not over-decompose beyond what the review names.

**R3 — Frontend audio hooks:** High value for Android robustness — MIME type handling, AudioContext resume, and MediaRecorder stop behavior are the riskiest parts of the frontend for cross-browser/cross-platform support. Modest risk that the abstraction doesn't fit all three call sites cleanly (conversation flow has a full state machine; translation and pronunciation are simpler record-submit flows). Mitigation: keep the hook interface narrow and let each feature control its own state machine.

**R4 — Context window:** Confirmed approach is **sliding-window truncation** (keep last N turns verbatim, drop older turns). Summarization is more capable but adds a synchronous Claude call per turn once the window fills — too much added latency and complexity for the current session length profile. Summarization can be added later as a config-selectable strategy. The truncation window, model name, and max_tokens should all become configurable via env vars rather than hard-coded.

> **Open question (confirm before implementing R4):** Is sliding-window truncation acceptable, or do you want the summarization path now? If truncation is fine, R4 is straightforward; if you want summarization, R4 scope roughly doubles.

**R5 — Persistence:** Acceptable at current scale. The review is correct that append-only turns and a cache TTL will matter eventually. Implementing a simple LRU cap on the in-process session dict (e.g., 50 sessions) is the highest-value change with minimal complexity.

**R6 — Hygiene:** No tradeoffs. Remove tracked generated artifacts, update .gitignore, done.

---

## Phase R1 — Restore Frontend Lint Gate

**Goal:** `npm run lint` exits 0. Lint added to the standard validation path alongside `pytest` and `npm test`.

### What's broken

- Test files fail lint because vitest globals (`describe`, `it`, `expect`, `vi`, `beforeEach`, `afterEach`) are not declared in the ESLint config.
- React hook rule violations in at least `frontend/src/App.jsx`, `frontend/src/components/CoachOverlay.jsx`, and `frontend/src/components/ConversationView.jsx`.
- Coverage output (`coverage/`) is not ignored by ESLint.

### Tasks

- [ ] Add a second config block in `frontend/eslint.config.js` scoped to `**/__tests__/**` and `**/*.test.{js,jsx}` files — set `globals` to `globals.browser` merged with vitest globals (`describe`, `it`, `test`, `expect`, `vi`, `beforeEach`, `afterEach`, `afterAll`, `beforeAll`).
- [ ] Add `coverage` to `globalIgnores` in `frontend/eslint.config.js`.
- [ ] Fix React hook violations in `App.jsx` — audit `useEffect` and `useCallback` dependency arrays; move any hook calls that are inside conditionals or callbacks to top-level.
- [ ] Fix React hook violations in `CoachOverlay.jsx` — same audit.
- [ ] Fix React hook violations in `ConversationView.jsx` — same audit.
- [ ] Verify `npm run lint` exits 0.
- [ ] Verify `npm test -- --run` still passes (no regressions from hook fixes).
- [ ] Add `npm run lint` to the project validation note in `docs/manualTestLog.md`.

### Phase R1 Gate

- [ ] `npm run lint` exits 0 with no errors or warnings.
- [ ] `npm test -- --run` passes (all existing tests, no regressions).
- [ ] `uv run pytest` still passes.

---

## Phase R2 — Decompose `backend/main.py`

**Goal:** `backend/main.py` contains only FastAPI app setup, middleware wiring, route definitions, and request/response serialization. All orchestration and storage logic extracted into dedicated modules.

### What moves where

| Logic currently in `main.py` | Destination |
|------------------------------|-------------|
| Turn orchestration (STT → coach → TTS) | `backend/turn_service.py` |
| Audio file persistence (`_save_audio_file`) | `backend/turn_service.py` |
| User flashcard deck load/save/dedup | `backend/flashcards_store.py` |
| Pronunciation challenge file reading | `backend/pronunciation_service.py` |
| Pronunciation evaluation orchestration (STT → evaluate) | `backend/pronunciation_service.py` |
| Translation orchestration (STT → translate → TTS) | `backend/translation_service.py` |
| TTS result serialization (base64 encode + error shape) | `backend/tts_helpers.py` (shared by turn and translate) |
| `_get_session()` cache helper | Stays in `main.py` (app-level state) |
| `BasicAuthMiddleware` | Stays in `main.py` (middleware config is wiring, not logic) |
| `_TOPICS`, `_PROVIDERS` data | Stays in `main.py` (route data) |

### New module contracts

**`backend/turn_service.py`**
```python
def process_turn(session, audio_bytes, filename, stt_provider, ai_provider) -> dict
def save_audio_file(session_id, audio_bytes, turn_index) -> str | None
```

**`backend/flashcards_store.py`**
```python
def load_user_deck() -> list[dict]
def save_user_deck(new_cards: list[dict]) -> list[dict]  # returns only newly saved cards
def get_user_deck_path() -> Path
```

**`backend/translation_service.py`**
```python
def process_translation(audio_bytes, filename, tts_provider_id, tts_voice_id, stt_provider, ai_provider) -> dict
```

**`backend/pronunciation_service.py`**
```python
def load_challenges() -> list[dict]
def process_pronunciation_eval(audio_bytes, filename, target, stt_provider, ai_provider) -> dict
```

**`backend/tts_helpers.py`**
```python
def synthesize_tts(text, tts_provider_id, tts_voice_id) -> tuple[str | None, dict | None]
# returns (audio_b64, tts_error_dict)
```

### Tasks

- [ ] Create `backend/tts_helpers.py` with `synthesize_tts()` — extract duplicated ElevenLabs call + base64 encode + error shape from `/turn` and `/translate` handlers.
- [ ] Create `backend/flashcards_store.py` — move `load_user_deck`, `save_user_deck`, `_get_user_deck_path` from `main.py`; update `_FLASHCARD_DECK_PATH` to live here.
- [ ] Create `backend/turn_service.py` — move `_save_audio_file` and the turn orchestration logic from `post_turn()`; route handler becomes a thin call into `process_turn()`.
- [ ] Create `backend/translation_service.py` — move translation orchestration from `translate()`.
- [ ] Create `backend/pronunciation_service.py` — move `_PRONUNCIATION_CHALLENGES_PATH`, `load_challenges()`, and pronunciation evaluation orchestration from `pronunciation_evaluate()`.
- [ ] Update `backend/main.py` route handlers to call the new service functions and return their results directly.
- [ ] Write unit tests for `flashcards_store.py` — load from empty path, load existing deck, save with dedup, save with deck + static overlap.
- [ ] Write unit tests for `tts_helpers.py` — browser provider returns `(None, None)`, elevenlabs with fixture bytes returns `(b64_str, None)`, elevenlabs error returns `(None, error_dict)`.
- [ ] Verify `uv run pytest` passes (no regressions).
- [ ] Verify `npm run lint` still passes.
- [ ] Verify `npm test -- --run` still passes.

### Phase R2 Gate

- [ ] `backend/main.py` is ≤200 lines and contains no business logic beyond request parsing and response construction.
- [ ] All service modules have at least basic unit tests covering their new logic.
- [ ] All existing tests pass (155+ backend, 126 frontend).

---

## Phase R3 — Consolidate Frontend Audio Hooks

**Goal:** MIME type handling, `MediaRecorder` setup, stream teardown, base64 playback, and `speechSynthesis` fallback live in exactly one place.

### What's duplicated

The recording start/stop/chunk pattern is near-identical in:
- `frontend/src/hooks/useVoice.js:67-184`
- `frontend/src/components/TranslationView.jsx:17-88`
- `frontend/src/components/PronunciationView.jsx:68-110`

The base64 → AudioContext playback + speechSynthesis fallback is duplicated between `useVoice.js` and `TranslationView.jsx`.

### New hooks

**`frontend/src/hooks/useAudioRecorder.js`**

```js
// Returns: { isRecording, startRecording, stopRecording, recordingError }
// Calls onStop(blob) when recorder stops; handles MIME negotiation and stream teardown.
useAudioRecorder({ onStop })
```

**`frontend/src/hooks/useSpeechPlayback.js`**

```js
// Returns: { play, isPlaying }
// play(audio_b64 | null, text, lang) — prefers AudioContext for b64, falls back to speechSynthesis.
// Calls onEnd when playback finishes.
useSpeechPlayback({ onEnd })
```

### Refactor plan per call site

- `useVoice.js`: Replace internal `MediaRecorder` setup with `useAudioRecorder`; replace base64 playback + speechSynthesis with `useSpeechPlayback`. State machine (`idle/recording/processing/playing`) stays in `useVoice`.
- `TranslationView.jsx`: Replace recording block with `useAudioRecorder`; replace `playAudioB64` + `speakText` with `useSpeechPlayback`.
- `PronunciationView.jsx`: Replace recording block with `useAudioRecorder`. No playback hook needed here (pronunciation returns a score, not audio).

### Tasks

- [ ] Create `frontend/src/hooks/useAudioRecorder.js` — MIME negotiation (`audio/webm;codecs=opus` with WAV fallback), `MediaRecorder` setup, chunk accumulation, stream teardown on stop, calls `onStop(blob)`.
- [ ] Create `frontend/src/hooks/useSpeechPlayback.js` — `AudioContext` base64 decode + play, `speechSynthesis` fallback for text, `onEnd` callback, `isPlaying` state.
- [ ] Write Vitest for `useAudioRecorder` — mock `navigator.mediaDevices.getUserMedia` and `MediaRecorder`; assert `onStop` called with blob, stream tracks stopped.
- [ ] Write Vitest for `useSpeechPlayback` — mock `AudioContext` and `speechSynthesis`; assert b64 path uses AudioContext, text-only path uses speechSynthesis, `onEnd` fires in both cases.
- [ ] Refactor `useVoice.js` to use both new hooks — verify all existing `useVoice` tests pass.
- [ ] Refactor `TranslationView.jsx` to use both new hooks — verify all existing `TranslationView` tests pass.
- [ ] Refactor `PronunciationView.jsx` to use `useAudioRecorder` — verify all existing `PronunciationView` tests pass.
- [ ] Verify `npm run lint` passes.
- [ ] Manual smoke test: full voice conversation, translation tab, pronunciation tab all function correctly.

### Phase R3 Gate

- [ ] `useAudioRecorder` and `useSpeechPlayback` have their own Vitest coverage.
- [ ] All existing frontend tests pass.
- [ ] Manual smoke test signed off in `docs/manualTestLog.md`.

---

## Phase R4 — AI Context Window Management

**Goal:** Cap per-turn token cost and latency by limiting how much conversation history is sent to Claude. Make model name and token budget configurable.

### Approach: sliding-window truncation

Keep the last `CONTEXT_TURNS` user+coach turn pairs verbatim (default: 10 pairs = 20 messages). Older turns are dropped. No summarization in this phase — add that as a future strategy if sessions grow longer than the window regularly.

> **Blocked on confirmation:** Proceed only after user confirms sliding-window truncation is acceptable (see open question above).

### Env vars introduced

| Variable | Default | Description |
|----------|---------|-------------|
| `DVC_CONTEXT_TURNS` | `10` | Number of recent turn pairs to include in each Claude request |
| `DVC_CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude model ID |
| `DVC_CLAUDE_MAX_TOKENS` | `1024` | Max tokens per chat response |

### Tasks

- [ ] Add `DVC_CONTEXT_TURNS` env var reading to `backend/ai/claude.py`; default 10.
- [ ] Update `_build_messages()` in `ClaudeProvider` — collect all speaker-tagged turns, take the last `CONTEXT_TURNS * 2` messages (pairs of user + coach), then append the new user message. Do not truncate the system prompt.
- [ ] Add `DVC_CLAUDE_MODEL` env var; replace hard-coded `"claude-sonnet-4-6"` in `ClaudeProvider.__init__`.
- [ ] Add `DVC_CLAUDE_MAX_TOKENS` env var; replace hard-coded `1024` in all `messages.create` calls within `claude.py`.
- [ ] Write unit tests for the truncation: session with 20 turns → `_build_messages` → assert message list length ≤ `(CONTEXT_TURNS * 2) + 1`; assert the last user message is always present; assert the most recent turns are preserved.
- [ ] Write unit test: `CONTEXT_TURNS=0` edge case — only the new user message is sent (minimal context).
- [ ] Verify `uv run pytest` passes.

### Phase R4 Gate

- [ ] `_build_messages` enforces the window; unit tests confirm.
- [ ] Model name and token budget are env-configurable with safe defaults.
- [ ] All existing tests pass.

---

## Phase R5 — Persistence Hardening

**Goal:** Prevent unbounded memory growth in the in-process session cache and reduce per-request I/O at session list time.

### Scope (minimal, per "defer soon" classification)

- Cap the in-process `sessions` dict at 50 entries (LRU eviction — drop the least-recently-used session when limit is reached).
- Do not change JSON persistence format or turn write behavior in this phase.
- Do not add session summary caching — that belongs in a later phase if session list performance degrades in practice.

### Tasks

- [ ] Replace the plain `dict` `sessions` in `main.py` with a simple `OrderedDict`-backed LRU cache limited to 50 entries; evict LRU entry when limit is reached.
- [ ] Write unit test: add 51 sessions → assert only 50 in cache; assert the first session is evicted.
- [ ] Write unit test: accessing a cached session moves it to most-recently-used position.
- [ ] Verify `uv run pytest` passes.

### Phase R5 Gate

- [ ] Session cache bounded at 50; unit tests pass.
- [ ] All existing tests pass.

---

## Phase R6 — Repo Hygiene

**Goal:** No generated artifacts tracked in version control.

### Tasks

- [ ] Add `node_modules/` (root-level) to `.gitignore`.
- [ ] Add `.vite/` (root-level) to `.gitignore`.
- [ ] Run `git rm -r --cached node_modules/.vite/` to untrack the existing `results.json` artifact.
- [ ] Verify `git status` shows no unintended tracked files under `node_modules/`.
- [ ] Commit `.gitignore` update and the removal.

### Phase R6 Gate

- [ ] `git status` is clean after removal.
- [ ] `npm test -- --run` and `uv run pytest` still pass.

---

## Validation Baseline

At the start of this work, the baseline is:
- `uv run pytest`: 155 passed, 6 skipped
- `npm test -- --run`: 126 passed
- `npm run lint`: **FAILS** (31 errors, 2 warnings) — this is the first thing fixed
- Backend coverage: 90% (`backend/ai/claude.py` at 70%)

Each phase gate requires all prior tests to continue passing. No phase introduces new behavior — only reorganization, extraction, and configuration.

---

## Implementation Notes

- Follow TDD: write or adjust tests before changing implementation code.
- Each phase should be a standalone commit (or small PR if preferred) — phases are not batched.
- `docs/manualTestLog.md` gets a sign-off entry for any phase that touches audio or AI behavior (R1 does not require one; R3 does).
- Phase 7 (Android manual smoke test) remains a separate open item — this plan does not address it.
