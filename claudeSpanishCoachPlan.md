# duoVoiceCoach — Phased Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

---

## Executive Summary

**Last updated:** 2026-04-25 (Phase A implemented, pending manual sign-off; Phase B implemented, pending manual sign-off)

**Current state:** Phases 0–9 complete. Phase A (Flashcards + Translation) and Phase B (Pronunciation Practice) both implemented and awaiting manual sign-off. Phase A must be signed off before Phase B vocabulary tab testing (which depends on the /flashcards/deck endpoint).

| Phase | Name | Status | Tests | Notes |
|-------|------|--------|-------|-------|
| 0 — Scaffolding | Project structure, env, contracts | ✅ Complete | 6 passing | pyproject.toml, Vite setup, abstract interfaces |
| 1 — Voice Pipeline MVP | Mic → Whisper → browser TTS | ✅ Complete | 33 passing | No AI yet; validate full audio round-trip |
| 2 — AI Conversation Core | Claude wired in, freeform chat | ✅ Complete | 36 backend, 2 skipped; 12 frontend | First real Spanish coaching session |
| 3 — Coaching Layer | Hybrid mode, corrections, toggle | ✅ Complete | 56 backend, 2 skipped; 19 frontend | MVP complete |
| 4 — Session Config UI | Topic/level picker, provider selector | ✅ Complete | 67 backend, 2 skipped; 33 frontend | Full session configuration in UI; signed off 2026-04-21 |
| 5 — Persistence | Session history, transcript save | ✅ Complete | 74 backend, 2 skipped; 38 frontend | Session history and local persistence signed off 2026-04-21 |
| 6 — ElevenLabs TTS | Swap browser TTS via tts.py | ✅ Complete | 92 backend, 2 skipped; 46 frontend | Voice quality upgrade; signed off 2026-04-22 |
| 7 — Android / PWA | PWA packaging, mobile UX | ⏳ In progress | — | Local network + ngrok; Phase 10 = cloud |
| 8 — Code Review & Refactor | Systematic review, complexity + efficiency | ✅ Complete | 93 backend; 47 frontend | Discipline checkpoint before cloud/packaging |
| 9 — GUI Layout Redesign | Two-pane desktop layout, mobile drawer | ✅ Complete | 60 frontend | Chat+tools split; responsive at 768px; signed off 2026-04-23 |
| A — Flashcards + Translation | Vocab flashcards, English→Spanish translation | 🔶 Implemented, not signed off | 114 backend (4 skipped), 89 frontend | NavTabs, FlashcardsView, TranslationView, GET /flashcards/deck, POST /translate; 2026-04-25 |
| B — Pronunciation Practice | Vocab/phonetic scoring, cross-mode Practice button | ✅ Complete | 103 backend, 3 skipped; 76 frontend | PronunciationView, evaluate_pronunciation(), Practice button; 2026-04-24 |
| 10 — Cloud Deployment | Cloud hosting, STT evaluation | ⏳ Not started | — | Decision doc required before implementation |
| 11 — Windows 11 Packaging | Docker Compose packaging for Windows 11 | ⏳ Not started | — | Distribute to other laptops |
| 12 — Feature Expansion | Progress tracking, structured lessons, open brainstorm | ⏳ Not started | — | Each workstream gets its own spec first |

**MVP = Phases 0–3.** Phase 4 adds full session configuration and Phase 5 adds local persistence and session history. Phase 6 is the voice quality upgrade. Phases 8–9 refactor and redesign before cloud deployment.

**Phase gate rule:** Each phase ends with a passing test suite and a manual smoke-test sign-off in `docs/manualTestLog.md` before the next phase begins.

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-15 | **React + FastAPI over Streamlit** | Voice state machine (mic/playback/coaching overlay) needs component-level state; Streamlit refresh model is incompatible with real-time audio UX |
| 2026-04-15 | **AI provider abstraction from Phase 0** | Provider swap must be a config change, not a refactor; `ai/base.py` AbstractAIProvider wired in before any AI call is made |
| 2026-04-15 | **TTS abstraction from Phase 0** | ElevenLabs upgrade in Phase 6 is a single module swap; `tts.py` returns `None` in Phase 1–5 (browser handles TTS) |
| 2026-04-15 | **Whisper for STT** | Best Spanish accuracy at MVP cost; local or API mode both supported |
| 2026-04-15 | **Browser `speechSynthesis` for MVP TTS** | Zero dependency; adequate for development and early use |
| 2026-04-15 | **Hybrid coaching mode as default** | Freeform conversation with on-demand corrections matches user's stated preference; avoids over-interrupting natural speech flow |
| 2026-04-15 | **`uv` for Python env management** | Consistent with neuroDb; reproducible pinned dependencies |
| 2026-04-15 | **`transcript_raw` + `transcript_norm` + `TurnError` added in Phase 1** | Whisper output often needs punctuation cleaning before sending to Claude; raw/norm split costs nothing at Phase 1 and prevents a later model change. `TurnError` distinguishes mic vs STT failures without log scraping. Full operational telemetry (latency, provider traces) deferred until needed. |
| 2026-04-15 | **`CoachResponse` typed return from `AbstractAIProvider.chat()` in Phase 2** | LLM free-text parsing is fragile; Claude structured output makes corrections deterministic and testable with fixtures. Schema is minimal (`coach_text` + `corrections` only) — fields added per phase as features require them. |

---

## Goal

Build a voice-first AI Spanish conversation coach that runs in the browser on desktop, conducting natural Spanish conversations at a user-selected topic and level, with configurable coaching feedback. Primary AI: Claude (Anthropic). Voice-provider and AI-provider are both abstracted for future swaps.

**Architecture:** Browser mic captures audio → FastAPI backend runs Whisper STT → AI provider generates coach response → browser TTS (or ElevenLabs) speaks the reply → React UI shows transcript and coaching feedback.

**Tech Stack:** Python 3.12+, `uv`, FastAPI, Whisper, Anthropic Claude, React + Vite, pytest, Vitest.

---

## Project Structure

```
duoVoiceCoach/
├── backend/
│   ├── main.py              ← FastAPI app, routes
│   ├── coach.py             ← conversation + coaching logic (provider-agnostic)
│   ├── stt.py               ← Whisper STT abstraction
│   ├── tts.py               ← TTS provider abstraction
│   ├── session.py           ← session state + optional JSON persistence
│   └── ai/
│       ├── __init__.py
│       ├── base.py          ← AbstractAIProvider interface
│       ├── claude.py        ← Anthropic Claude implementation (default)
│       └── openai.py        ← OpenAI GPT stub (Phase 3+)
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── VoiceButton.jsx     ← idle / recording / processing / playing
│       │   ├── CoachOverlay.jsx    ← correction feedback panel
│       │   ├── SessionConfig.jsx   ← topic, level, AI provider, coaching mode
│       │   └── Transcript.jsx      ← running bilingual conversation display
│       └── hooks/
│           └── useVoice.js         ← mic capture, browser speechSynthesis
├── tests/
│   ├── fixtures/
│   │   └── hola_sample.wav         ← deterministic audio fixture
│   ├── unit/
│   │   ├── test_stt.py
│   │   ├── test_coach.py
│   │   └── test_ai_providers.py
│   └── integration/
│       └── test_turn_pipeline.py
├── docs/
│   ├── claudeSpanishCoachPlan.md   ← this file
│   ├── manualTestLog.md            ← phase smoke-test sign-offs
│   └── superpowers/
│       └── specs/
│           └── 2026-04-15-spanish-coach-design.md
├── pyproject.toml
├── uv.lock
└── package.json
```

---

## Data Model

```python
Session:
  id:            str          # UUID
  started_at:    datetime
  topic:         str          # e.g. "ordering food", freeform text
  level:         int          # 1–10 (see band table below)
  ai_provider:   str          # "claude" | "openai" | ...
  coaching_mode: str          # "on_demand" | "explicit" | "shadowing"
  turns:         list[Turn]

Turn:
  speaker:         str              # "user" | "coach"
  audio_file:      str | None       # path to WAV (user turns, Phase 5+)
  transcript_raw:  str | None       # Whisper output verbatim (user turns); Phase 1+
  transcript_norm: str | None       # cleaned transcript sent to Claude (user turns); Phase 1+
  coach_text:      str | None       # coach response text (coach turns); Phase 2+
  corrections:     list[Correction] # validated corrections from CoachResponse; Phase 2+
  error:           TurnError | None # structured error if a stage failed; Phase 1+
  timestamp:       datetime

Correction:
  original:      str          # what the user said
  corrected:     str          # correct form
  explanation:   str          # grammar rule or vocabulary note
  triggered_by:  str          # "auto" | "user_request"

TurnError:                    # added Phase 1 — distinguishes failure stages without log scraping
  stage:         str          # "mic" | "stt" | "ai" | "tts"
  message:       str          # human-readable description
  recoverable:   bool         # True → prompt user to retry; False → session-ending

CoachResponse:                # typed return from AbstractAIProvider.chat(); added Phase 2
  coach_text:    str          # what the coach says aloud
  corrections:   list[Correction]  # empty list if no errors detected
```

### Level-to-Duolingo Band Mapping

| Level | Duolingo Range | Description |
|-------|---------------|-------------|
| 1–2 | 5–30 | Greetings, food, basic nouns |
| 3–4 | 30–70 | Directions, simple sentences |
| 5–6 | 70–110 | Stories, TV, work vocabulary |
| 7–10 | 110+ | Near-native, idioms, slang |

---

## Phase 0 — Scaffolding & Contracts

**Goal:** Working repo with environment, project structure, abstract interfaces, and test harness — no real functionality yet.

### Tasks

- [x] Initialize Python project: `pyproject.toml` with `uv`, FastAPI, openai-whisper, anthropic dependencies
- [x] Initialize React frontend: `npm create vite@latest frontend -- --template react`
- [x] Create `backend/ai/base.py` — `AbstractAIProvider` with `chat()` signature
- [x] Create `backend/tts.py` — `AbstractTTSProvider` with `synthesize()` returning `None` (passthrough)
- [x] Create `backend/stt.py` — `WhisperSTT` stub returning fixture transcript
- [x] Create `backend/session.py` — `Session`, `Turn`, `Correction` dataclasses
- [x] Create `backend/coach.py` — `CoachSession` stub (accepts messages, returns placeholder)
- [x] Create `backend/main.py` — FastAPI app with `POST /turn` route (wired to stubs)
- [x] Create `tests/fixtures/hola_sample.wav` — short deterministic Spanish audio clip
- [x] Write unit tests for session model serialization/deserialization
- [x] Write unit test asserting `AbstractAIProvider.chat()` raises `NotImplementedError`
- [x] Verify: `uv run pytest` passes; `npm run dev` starts frontend dev server
- [x] Add Phase 0 procedures to `docs/manualTestPlan.md`

### Phase 0 Gate

- [x] All unit tests pass
- [x] `POST /turn` returns a structured JSON response (stub data)
- [x] Manual: frontend dev server loads in browser without errors (signed off 2026-04-19)

---

## Phase 1 — Voice Pipeline MVP

**Goal:** Full audio round-trip working end-to-end — mic capture → Whisper transcription → browser TTS playback. No AI in the loop yet; coach response is a hardcoded echo.

### Tasks

- [x] Implement `backend/stt.py` — real Whisper transcription (local `whisper` package, `base` model); return both `transcript_raw` (verbatim Whisper output) and `transcript_norm` (punctuation-cleaned, lowercased)
- [x] Implement `backend/session.py` — add `TurnError` dataclass; STT failures return `TurnError(stage="stt", recoverable=True)` instead of raising
- [x] Implement `backend/main.py POST /turn` — accept WAV upload, run Whisper, return `{transcript_raw, transcript_norm, error}`
- [x] Implement `frontend/hooks/useVoice.js` — `MediaRecorder` mic capture, WAV blob POST, `speechSynthesis` playback; surface `error` field to UI
- [x] Implement `frontend/components/VoiceButton.jsx` — state machine: idle → recording → processing → playing; show retry prompt on recoverable error
- [x] Implement `frontend/components/Transcript.jsx` — display `transcript_norm` (user) + echo response
- [x] Write unit test: `test_stt.py` — `hola_sample.wav` → expected `transcript_raw` and `transcript_norm` values
- [x] Write unit test: `test_stt.py` — corrupted/empty WAV → `TurnError(stage="stt", recoverable=True)` returned, no exception raised
- [x] Write integration test: WAV fixture → `/turn` → JSON with `transcript_raw`, `transcript_norm`, `error: null`
- [x] Write Vitest: `VoiceButton` state transitions; retry prompt renders on error response
- [x] Manual smoke test: speak "Hola, ¿cómo estás?" → verify `transcript_norm` accuracy → browser speaks echo back
- [x] Add Phase 1 procedures to `docs/manualTestPlan.md`

### Phase 1 Gate

- [x] All tests pass (21 backend, 12 frontend = 33 total)
- [x] Manual smoke test signed off in `docs/manualTestLog.md` (2026-04-19)
- [x] Whisper transcribes spoken Spanish with acceptable accuracy (verified with gTTS fixture)
- [x] `TurnError` test passes: bad audio input returns structured error, no uncaught exception

---

## Phase 2 — AI Conversation Core

**Goal:** Claude wired in as the AI provider. First real Spanish coaching conversation possible.

### Tasks

- [x] Add `CoachResponse` dataclass to `backend/session.py` — `{coach_text: str, corrections: list[Correction]}`
- [x] Update `backend/ai/base.py` — `AbstractAIProvider.chat()` return type is `CoachResponse` (not free text)
- [x] Implement `backend/ai/claude.py` — `ClaudeProvider(AbstractAIProvider)` using `anthropic` SDK with prompt caching; use Claude structured output (tool use / JSON mode) so corrections arrive as structured data, not parsed text; validate response into `CoachResponse` before returning
- [x] Implement `backend/ai/openai.py` — `OpenAIProvider` stub (raises `NotImplementedError`, wires up interface)
- [x] Implement `backend/coach.py` — `CoachSession` builds system prompt (topic, level, coaching mode), maintains message history, calls `ai_provider.chat()`, consumes `CoachResponse`
- [x] Update `backend/main.py` — instantiate `ClaudeProvider` as default, pass to `CoachSession`
- [x] Update `backend/session.py` — wire `ai_provider` field to provider registry; store `coach_text` on coach turns
- [x] Write unit test: `test_ai_providers.py` — `ClaudeProvider` with valid fixture response → `CoachResponse` returned; malformed fixture response → `TurnError(stage="ai", recoverable=True)` returned, no exception raised; `OpenAIProvider` raises `NotImplementedError`
- [x] Write unit test: `test_coach.py` — system prompt construction for topic/level/mode combinations
- [x] Write integration test: full turn → Claude → `CoachResponse` with `coach_text` and empty `corrections`
- [x] Manual smoke test: start session at level 5, topic "ordering food" → conduct 3-turn Spanish conversation → verify responses are contextually appropriate
- [x] Add Phase 2 procedures to `docs/manualTestPlan.md`

### Phase 2 Gate

- [x] All tests pass (36 backend, 2 skipped; 12 frontend — at time of sign-off)
- [x] Manual smoke test signed off in `docs/manualTestLog.md` (2026-04-20)
- [x] Claude responds in Spanish at the requested level

---

## Phase 3 — Coaching Layer (MVP Complete)

**Goal:** Hybrid conversation mode with all three coaching modes working. On-demand corrections triggered by user phrases. MVP is complete.

### Tasks

- [x] Implement coaching mode routing in `backend/coach.py` — consume `CoachResponse.corrections` (already validated); route by mode: `on_demand` (surface corrections only if user asked), `explicit` (always surface non-empty corrections), `shadowing` (pass corrections to prompt so AI weaves correct form into reply, suppress overlay)
- [x] Implement user-request trigger detection in `backend/coach.py` — detect phrases like "¿Cómo se dice...?", "Was that right?", "Corrígeme" in `transcript_norm`; set `triggered_by="user_request"` on resulting corrections
- [x] Update `backend/main.py` — return `corrections[]` from `CoachResponse` in `/turn` response; accept `coaching_mode` in `/session/start` JSON body
- [x] Implement `frontend/components/CoachOverlay.jsx` — display corrections: original → corrected + explanation
- [x] Implement `frontend/components/SessionConfig.jsx` — coaching mode toggle (on_demand / explicit / shadowing)
- [x] Write unit tests: coaching mode routing for all three modes against fixture `CoachResponse` objects (empty corrections, single correction, multiple corrections)
- [x] Write Vitest: `CoachOverlay` renders correction fields; `SessionConfig` emits coaching mode
- [x] Add Phase 3 procedures to `docs/manualTestPlan.md`
- [x] Manual smoke test: speak a sentence with a deliberate verb conjugation error → verify each coaching mode behaves as specified

### Phase 3 Gate

- [x] All tests pass (56 backend, 2 skipped; 19 frontend — 2026-04-21)
- [x] Manual smoke test signed off for all three coaching modes (2026-04-21)
- [x] **MVP declared complete** — desktop Spanish voice coach is usable

---

## Phase 4 — Session Config UI

**Goal:** Full session configuration exposed in the UI — topic selection (list + freeform), level picker, AI provider dropdown.

### Tasks

- [x] Expand `frontend/components/SessionConfig.jsx` — topic picker (preset list + freeform text input), selected preset starter phrase, level slider (1–10 with band labels), AI provider dropdown
- [x] Update `backend/main.py` — accept full config from `POST /session/start`; return `session_id`
- [x] Add `GET /providers` route — returns list of registered AI providers
- [x] Add `GET /topics` route — returns preset topic list with Spanish starter phrases
- [x] Write tests for `/topics`, `/providers`, and `/session/start` config validation
- [x] Write Vitest: `SessionConfig` renders provider list from API, starter phrase behavior, level slider labels, and New Conversation controls
- [x] Manual smoke test: configure sessions with different topics, levels, provider, and coaching modes; verify session reset and config behavior
- [x] Add Phase 4 procedures to `docs/manualTestPlan.md`

### Phase 4 Gate

- [x] All tests pass (67 backend, 2 skipped; 33 frontend — 2026-04-21)
- [x] Manual smoke test signed off in `docs/manualTestLog.md` (2026-04-21)
- [x] Ready to proceed to Phase 5

---

## Phase 5 — Persistence & Session History

**Goal:** Sessions saved to local JSON store. User can review past sessions and corrections.

### Tasks

- [x] Implement local JSON persistence in `backend/session.py` — save/load sessions to `~/.duoVoiceCoach/sessions/` by default, overrideable with `DVC_DATA_DIR`
- [x] Add `GET /sessions` route — list past sessions with metadata
- [x] Add `GET /sessions/{id}` route — full session transcript and corrections
- [x] Save user audio WAV files per turn in `audio_file` field when `DVC_SAVE_AUDIO=true`; default is transcript-only persistence
- [x] Implement session history view in frontend — list past sessions, tap to review transcript + corrections
- [x] Write unit tests: session save → load round-trip; correction retrieval
- [x] Write integration test: full session → save → load → verify turn count and corrections intact
- [x] Manual smoke test: complete a session, close app, reopen, verify session appears in history
- [x] Add Phase 5 procedures to `docs/manualTestPlan.md`

### Phase 5 Gate

- [x] All tests pass (74 backend, 2 skipped; 38 frontend — 2026-04-21)
- [x] Manual smoke test signed off (2026-04-21)

---

## Phase 6 — ElevenLabs TTS

**Goal:** Swap browser `speechSynthesis` to ElevenLabs for high-quality Spanish voice output.

### Tasks

- [x] Implement `ElevenLabsTTSProvider` in `backend/tts.py` — calls ElevenLabs API, returns audio bytes
- [x] Update `backend/main.py` — if `tts_provider` returns bytes, include base64 audio in `/turn` response
- [x] Update `frontend/hooks/useVoice.js` — if response contains audio bytes, play via `AudioContext`; else fall back to `speechSynthesis`
- [x] Add `tts_provider` to session config (browser / elevenlabs)
- [x] Write unit test: `ElevenLabsTTSProvider` with fixture response (no live API in CI)
- [x] Manual smoke test: ElevenLabs voice vs. browser TTS — verify quality improvement
- [x] Add Phase 6 procedures to `docs/manualTestPlan.md`

### Phase 6 Gate

- [x] All tests pass
- [x] Manual smoke test signed off — ElevenLabs voice confirmed working (2026-04-22)

---

## Phase 7 — Android / PWA

**Goal:** Progressive Web App packaging so the coach runs on Android in Chrome with mic and speaker access.

### Tasks

- [x] Add `manifest.json` and service worker to frontend — PWA installable in Chrome
- [x] Audit `useVoice.js` for mobile mic/audio compatibility — fix MIME type detection (`audio/webm;codecs=opus`) and AudioContext eager resume on user gesture
- [x] Tune `VoiceButton` touch targets for mobile screen sizes — 48dp minimum via `.voice-btn` CSS rule
- [x] Serve frontend build output (`frontend/dist`) as static files from FastAPI — single ngrok URL covers both app and API
- [x] Evaluate hosting: local network + ngrok chosen for Phase 7; cloud deployment moved to Phase 10
- [x] Document Android setup in `docs/android-setup.md`
- [ ] Manual smoke test on Android device: full session — mic capture → Whisper → coach response → TTS playback
- [ ] Add Phase 7 procedures to `docs/manualTestPlan.md`

### Phase 7 Gate

- [ ] PWA installable on Android Chrome
- [ ] Full voice session works on Android
- [ ] Manual smoke test signed off in `docs/manualTestLog.md`

---

---

## Phase 8 — Code Review & Refactor

**Goal:** Systematic review of all backend and frontend code after six phases of rapid delivery. Identify and resolve complexity hotspots, efficiency gaps, and test coverage holes. This is a discipline checkpoint, not a response to a specific bug.

### Scope

**Backend**
- `main.py` — verify routes contain no business logic; all logic delegated to `coach.py`, `session.py`, or provider modules
- `coach.py` — review system prompt construction, mode routing, and correction trigger detection for clarity and single responsibility
- `session.py` — review data model, persistence logic, and serialization for correctness and efficiency
- `stt.py` / `tts.py` — verify abstraction boundaries are clean; no provider-specific logic leaking into the base
- `ai/claude.py` — review prompt caching usage, structured output parsing, and error handling path

**Frontend**
- `useVoice.js` — review state machine correctness, AudioContext lifecycle, and error surface
- `App.jsx` — check for state that belongs in the hook vs. component; verify session config flow
- All components — check for unused props, missing test coverage, and CSS not referenced by any component

**Tests**
- Measure backend coverage; identify untested branches in `coach.py` and `session.py`
- Verify integration test still exercises the full WAV → `/turn` → JSON pipeline
- Flag any tests that mock where they should use real implementations (per existing project rule)

### Tasks

- [x] Review all backend modules against scope above; document findings with severity (fix now / defer / accept as-is)
- [x] Review all frontend files against scope above; document findings
- [x] Write refactor report to `docs/superpowers/specs/YYYY-MM-DD-phase8-refactor-report.md`
- [x] Implement all **fix now** findings — no speculative refactors
- [x] Verify all existing tests pass after refactor
- [x] Manual smoke test: full voice session still works end-to-end
- [x] Add Phase 8 procedures to `docs/manualTestPlan.md`

### Phase 8 Gate

- [x] Refactor report written and committed
- [x] All existing tests pass (no regressions)
- [x] Manual smoke test signed off in `docs/manualTestLog.md`

---

## Phase 9 — GUI Layout Redesign

**Goal:** Restructure the app from its current single-column layout into a two-pane desktop layout. Left pane: full-height conversation with voice button pinned to bottom. Right pane: session config (collapsible), corrections, and session history.

### Layout: Chat + Tools Split

```
┌─────────────────────────────┬──────────────────────┐
│                             │  ▸ Session Config    │
│  Transcript                 │  ──────────────────  │
│  (scrollable, full height)  │  Corrections         │
│                             │  ──────────────────  │
│                             │  Session History     │
│  [   🎤 Voice Button   ]   │                      │
└─────────────────────────────┴──────────────────────┘
```

**Left pane (~65% width):** Full-height scrollable transcript (user right / coach left); voice button pinned to bottom center; error state shown inline below voice button.

**Right pane (~35% width):** Session config in collapsible `<details>` (collapsed by default during active session); corrections overlay auto-clears after 8 seconds or on next turn; session history list.

**Responsive:** Below 768px, right pane collapses into a bottom drawer (preserves Android PWA usability).

### Tasks

- [x] Update `App.jsx` — new two-column layout wrapper; right-pane composition
- [x] Update `Transcript.jsx` — full-height flex container; user/coach bubble alignment (user right, coach left)
- [x] Update `VoiceButton.jsx` — pinned bottom position within left pane
- [x] Update `SessionConfig.jsx` — wrap in collapsible `<details>`; collapsed by default
- [x] Update `CoachOverlay.jsx` — move into right pane; add 8-second auto-dismiss timer
- [x] Update `SessionHistory.jsx` — move into right pane; no structural change
- [x] Update `App.css` / `index.css` — new layout grid; responsive breakpoint at 768px
- [x] Add layout-level Vitest snapshots for two-pane structure
- [x] Manual smoke test: full session in new layout on desktop
- [x] Manual smoke test: right pane collapses correctly on Android (browser DevTools viewport resize; device test deferred to Phase 7)
- [x] Add Phase 9 procedures to `docs/manualTestPlan.md`

### Phase 9 Gate

- [x] All existing tests pass
- [x] Two-pane layout renders correctly on desktop
- [x] Right pane collapses to drawer on mobile (browser DevTools viewport resize; device test deferred to Phase 7)
- [x] Manual smoke test signed off in `docs/manualTestLog.md`

---

## Phase 10 — Cloud Deployment

**Goal:** Deploy the backend to a cloud host so the app works on Android anywhere, without needing a laptop running ngrok.

**Before writing any implementation code**, explore and document answers to the following in a decision doc at `docs/superpowers/specs/YYYY-MM-DD-phase8-cloud-decision.md`:

- **STT — local Whisper vs API-based:** Whisper `base` needs ~1 GB RAM, ruling out most free cloud tiers. Candidates to evaluate:
  - OpenAI Whisper API: pay-per-minute, no RAM concern, same model family
  - Deepgram: faster transcription, competitive pricing, strong Spanish accuracy
  - Benchmark: cost-per-session, round-trip latency, Spanish accuracy vs local Whisper `base`
- **Hosting options:** Evaluate RAM requirements vs tier pricing for Fly.io, Railway, Render, plain VPS. Document which tiers support ≥1 GB RAM if staying with local Whisper, and which are adequate for an API-based STT swap.
- **HTTPS:** Handled by the platform — no ngrok required. Document TLS setup expectations per host.
- **Secrets management:** `ANTHROPIC_API_KEY` and `ELEVENLABS_API_KEY` go in the host's secret store, not `.env` files. Document the mechanism per candidate host.
- **Usability delta:** Measure whether cloud latency (STT API round-trip + coach response over internet) feels noticeably worse than local Whisper in a real session.

### Tasks

- [ ] Explore API-based STT options (OpenAI Whisper API, Deepgram) — benchmark cost, latency, Spanish accuracy vs local Whisper `base`
- [ ] Evaluate hosting options — document which platforms support the RAM and pricing requirements
- [ ] Evaluate HTTPS and secrets management per candidate host
- [ ] Run a test session to measure cloud latency vs local — document perceived usability delta
- [ ] Write decision doc to `docs/superpowers/specs/YYYY-MM-DD-phase10-cloud-decision.md`
- [ ] Implement chosen approach based on decision doc

### Phase 10 Gate

- [ ] Decision doc written and committed before implementation begins
- [ ] App accessible on Android without ngrok
- [ ] Manual smoke test signed off

---

## Phase 11 — Windows 11 Packaging

**Goal:** Package duoVoiceCoach so it can be installed and run on other Windows 11 laptops with minimal setup — one command to start the full stack.

**Approach:** Docker Compose. A `docker-compose.yml` bundles the FastAPI backend (with Whisper and all Python deps) and serves the built frontend as static files from the same container. Users need only Docker Desktop for Windows installed; no Python, Node.js, or uv required.

**Key concerns to resolve during implementation:**
- Whisper `base` model download on first run — cache it in the image or volume so it isn't re-downloaded each start
- ffmpeg must be present in the container image (required by Whisper)
- `.env` file handling on Windows — document how to set `ANTHROPIC_API_KEY` etc. in a `.env` file that Docker Compose picks up
- Windows-specific paths and line endings — test `docker compose up` end-to-end on a real Windows 11 machine

### Tasks

- [ ] Write `Dockerfile` — Python 3.12 base, install uv, copy backend, install deps, copy built `frontend/dist/`, expose port 8001
- [ ] Write `docker-compose.yml` — single service, mounts `.env` for secrets, persists `~/.duoVoiceCoach` session data via a named volume
- [ ] Write `.env.example` additions for Docker context (if any new vars needed)
- [ ] Write `docs/windows-setup.md` — install Docker Desktop, clone repo, `npm run build`, `docker compose up`, open `http://localhost:8001`
- [ ] Manual smoke test: full session on Windows 11 via Docker — mic capture → Whisper → coach response → TTS playback
- [ ] Add Phase 9 procedures to `docs/manualTestPlan.md`

### Phase 11 Gate

- [ ] `docker compose up` starts the full stack on Windows 11
- [ ] Full voice session works via Docker
- [ ] Manual smoke test signed off in `docs/manualTestLog.md`

---

## Phase 12 — Mobile Capability

**Issues:**
- `CoachOverlay` renders in the right pane (drawer). On mobile, if the drawer is closed when a correction arrives in Explicit or On-demand mode, the correction is invisible — it auto-dismisses after 8 seconds with the user never seeing it.

### Tasks

- [ ] Write spec for chosen correction notification pattern on mobile
- [ ] Implement chosen approach
- [ ] Verify all three coaching modes (on_demand, explicit, shadowing) surface corrections correctly on mobile
- [ ] Add Phase 12 procedures to `docs/manualTestPlan.md`

### Phase 12 Gate

- [ ] Corrections visible in all three coaching modes without requiring the drawer to be open
- [ ] Manual smoke test on Android PWA signed off in `docs/manualTestLog.md`

---

## Phase 13 — Feature Expansion

**Goal:** Add meaningful depth to the coaching experience across three workstreams. Each workstream gets its own spec before implementation begins.

### Workstream 1: Progress Tracking

The app already stores every `Turn`, `Correction`, and session — progress tracking surfaces what is already captured.

**Features:**
- Correction frequency breakdown by type: article usage, verb conjugation, vocabulary (based on new `category` field on `Correction`)
- "Words I keep getting wrong" list — same `original` corrected across multiple sessions
- Session frequency view — sessions-per-week display

**Data model change:** Add optional `category: str` to `Correction` (`"article"` | `"conjugation"` | `"vocabulary"` | `"other"`). Claude populates via structured output. Existing sessions without it degrade gracefully.

### Workstream 2: Structured Lessons

Guided topic exchanges before opening to freeform conversation.

**Mechanics:**
- New `session_mode: "lesson"` drives the system prompt with an ordered sequence of prompts per topic and level band
- Coach steps through each prompt, confirms completion, then transitions to freeform
- Lesson sequences stored as JSON config in `backend/lessons/` — one file per topic, keyed by level band
- Frontend shows current step indicator in right pane (e.g., "Step 2 of 4: Ask for the menu")

**New backend:** `backend/lessons/` directory; `GET /lessons/{topic}` route; `lesson_step` tracking in session state.

### Workstream 3: Open Brainstorm (candidates, not commitments)

Each item requires its own mini-spec before any implementation:

- **Vocabulary flashcard review** — review logged corrections between sessions (React state only, no new framework)
- **Coach personality modes** — `"formal_tutor"` vs. `"friendly_partner"` system prompt variation
- **Correction export** — download corrections as CSV or Anki-compatible format (`backend/export.py`)

### Tasks

- [ ] Write workstream specs before any workstream implementation begins
- [ ] Progress tracking: add `category` field to `Correction`; update `ClaudeProvider` structured output; implement stats view
- [ ] Structured lessons: create lesson JSON for at least 3 topics at 2 level bands; implement `GET /lessons/{topic}`; add step indicator to frontend
- [ ] Open brainstorm: spec and implement at least one candidate item
- [ ] Add Phase 13 procedures to `docs/manualTestPlan.md`

### Phase 13 Gate

- [ ] All workstream specs written and committed before implementation begins
- [ ] Progress tracking: stats view renders with real session data
- [ ] Structured lessons: end-to-end lesson session works for 3 topics; manual smoke test
- [ ] Open brainstorm: at least one item specced and implemented
- [ ] Manual smoke test signed off in `docs/manualTestLog.md`

---

## Testing Summary

| Layer | Tool | Scope |
|-------|------|-------|
| Backend unit | pytest | STT, TTS, AI providers, coach logic, session model |
| Backend integration | pytest | Full turn pipeline WAV → JSON |
| Frontend unit | Vitest + React Testing Library | Component state, rendering |
| Manual smoke test | `docs/manualTestLog.md` | Real voice session per phase |

**No mocking the AI provider in integration tests** — use real Claude API call with fixed prompt; assert response structure, not exact text.

---

## Working Documentation

Maintain planning and progress docs in this repo:

- `claudeSpanishCoachPlan.md` — this file (update phase status as work progresses)
- `docs/manualTestLog.md` — smoke test sign-offs per phase
- `docs/superpowers/specs/2026-04-15-spanish-coach-design.md` — approved design spec
- `SpanishConversationCoachGoals.md` — original goals document
