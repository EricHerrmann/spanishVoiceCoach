# duoVoiceCoach — Phased Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

---

## Executive Summary

**Last updated:** 2026-04-21 (Phase 4 signed off; ready for Phase 5)

**Current state:** Phases 0–4 complete. Phase 4 session configuration UI is implemented and signed off; ready to proceed to Phase 5 persistence and session history.

| Phase | Name | Status | Tests | Notes |
|-------|------|--------|-------|-------|
| 0 — Scaffolding | Project structure, env, contracts | ✅ Complete | 6 passing | pyproject.toml, Vite setup, abstract interfaces |
| 1 — Voice Pipeline MVP | Mic → Whisper → browser TTS | ✅ Complete | 33 passing | No AI yet; validate full audio round-trip |
| 2 — AI Conversation Core | Claude wired in, freeform chat | ✅ Complete | 36 backend, 2 skipped; 12 frontend | First real Spanish coaching session |
| 3 — Coaching Layer | Hybrid mode, corrections, toggle | ✅ Complete | 56 backend, 2 skipped; 19 frontend | MVP complete |
| 4 — Session Config UI | Topic/level picker, provider selector | ✅ Complete | 67 backend, 2 skipped; 33 frontend | Full session configuration in UI; signed off 2026-04-21 |
| 5 — Persistence | Session history, transcript save | 🚧 In progress | 74 backend, 2 skipped; 38 frontend | Implementation complete; manual smoke pending |
| 6 — ElevenLabs TTS | Swap browser TTS via tts.py | ⏳ Not started | — | Voice quality upgrade |
| 7 — Android / PWA | PWA packaging, mobile UX | ⏳ Not started | — | Android target |

**MVP = Phases 0–3.** Phase 4 adds full session configuration and is complete. Phase 5 is the next execution focus.

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
- [ ] Manual smoke test: complete a session, close app, reopen, verify session appears in history
- [x] Add Phase 5 procedures to `docs/manualTestPlan.md`

### Phase 5 Gate

- [x] All tests pass (74 backend, 2 skipped; 38 frontend — 2026-04-21)
- [ ] Manual smoke test signed off

---

## Phase 6 — ElevenLabs TTS

**Goal:** Swap browser `speechSynthesis` to ElevenLabs for high-quality Spanish voice output.

### Tasks

- [ ] Implement `ElevenLabsTTSProvider` in `backend/tts.py` — calls ElevenLabs API, returns audio bytes
- [ ] Update `backend/main.py` — if `tts_provider` returns bytes, include base64 audio in `/turn` response
- [ ] Update `frontend/hooks/useVoice.js` — if response contains audio bytes, play via `AudioContext`; else fall back to `speechSynthesis`
- [ ] Add `tts_provider` to session config (browser / elevenlabs)
- [ ] Write unit test: `ElevenLabsTTSProvider` with fixture response (no live API in CI)
- [ ] Manual smoke test: ElevenLabs voice vs. browser TTS — verify quality improvement
- [ ] Add Phase 6 procedures to `docs/manualTestPlan.md`

### Phase 6 Gate

- [ ] All tests pass
- [ ] Manual smoke test signed off — ElevenLabs voice confirmed working

---

## Phase 7 — Android / PWA

**Goal:** Progressive Web App packaging so the coach runs on Android in Chrome with mic and speaker access.

### Tasks

- [ ] Add `manifest.json` and service worker to frontend — PWA installable in Chrome
- [ ] Audit `useVoice.js` for mobile mic/audio compatibility — test `MediaRecorder` on Android Chrome
- [ ] Tune `VoiceButton` touch targets and layout for mobile screen sizes
- [ ] Evaluate hosting options: local network (backend on laptop, phone on same WiFi) vs. cloud deployment
- [ ] Document Android setup in `docs/android-setup.md`
- [ ] Manual smoke test on Android device: full session — mic capture → Whisper → coach response → TTS playback
- [ ] Add Phase 7 procedures to `docs/manualTestPlan.md`

### Phase 7 Gate

- [ ] PWA installable on Android Chrome
- [ ] Full voice session works on Android
- [ ] Manual smoke test signed off

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
