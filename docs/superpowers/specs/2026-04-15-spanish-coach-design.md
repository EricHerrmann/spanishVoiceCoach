# duoVoiceCoach — Design Specification

**Date:** 2026-04-15
**Status:** Approved
**Author:** Claude Code (brainstorming session)

---

## 1. Problem Statement

The user has 600+ days of Duolingo at level ~98 but cannot hold a natural Spanish conversation and catches only 10–20% of spoken TV Spanish. Duolingo's structured, text-heavy format does not build the verbal fluency needed. A voice-first AI coach that conducts real Spanish conversations, at a chosen topic and level, with configurable coaching feedback, addresses this gap.

---

## 2. User Context

- Duolingo score ~98 (between "watching TV" and "communicating at work" bands)
- Reads Spanish reasonably well with transcript support; verbal production is the weak point
- Primary device: desktop (Linux/WSL2); future target: Android phone
- Prefers conversation about topics they choose, at a level they can succeed with

---

## 3. Architecture

### 3.1 High-Level

```
Browser (React)
  │
  │  WAV audio (mic capture)
  ▼
FastAPI Backend (Python)
  ├── stt.py       ← Whisper STT → transcript text
  ├── ai/          ← AI provider abstraction
  │   ├── base.py       AbstractAIProvider
  │   ├── claude.py     Anthropic Claude (default)
  │   └── openai.py     OpenAI GPT (stub, Phase 3+)
  ├── tts.py       ← TTS provider abstraction
  │   (Phase 1: passthrough — browser handles TTS)
  │   (Phase 6: ElevenLabs implementation)
  ├── coach.py     ← conversation logic, correction detection
  └── session.py   ← session state, config, persistence (Phase 5+)
  │
  │  JSON response (transcript + coach reply + corrections)
  ▼
Browser (React)
  ├── useVoice.js hook    ← mic capture, browser speechSynthesis
  ├── VoiceButton         ← idle / recording / processing / playing states
  ├── Transcript          ← running bilingual conversation display
  ├── CoachOverlay        ← correction feedback panel
  └── SessionConfig       ← topic, level, AI provider, coaching mode
```

### 3.2 Per-Turn Data Flow

1. User presses mic → browser captures audio via `MediaRecorder`
2. Frontend POSTs WAV blob to `POST /turn`
3. Backend: Whisper transcribes audio → transcript text
4. Backend: `coach.py` builds message history + system prompt → calls `ai_provider.chat(messages)`
5. AI provider returns coach response text + optional correction metadata
6. Backend returns JSON: `{transcript, coach_text, corrections[], session_id}`
7. Frontend: browser `speechSynthesis` speaks `coach_text`; `Transcript` and `CoachOverlay` update

### 3.3 Provider Abstraction Points

**AI Provider (`ai/base.py`):**
```python
class AbstractAIProvider:
    def chat(self, messages: list[Message], system: str) -> CoachResponse:
        raise NotImplementedError
```
`coach.py` only calls `ai_provider.chat()`. Provider is set per-session via `session.ai_provider`.

**TTS Provider (`tts.py`):**
```python
class AbstractTTSProvider:
    def synthesize(self, text: str, lang: str = "es") -> bytes | None:
        raise NotImplementedError
```
Phase 1–5: returns `None` (browser handles TTS). Phase 6: ElevenLabs returns audio bytes.

---

## 4. Conversation Model

### 4.1 Session Modes

**Hybrid mode (default):** Session opens with a guided prompt (topic + level set by user). AI conducts natural freeform conversation. Coaching is triggered by explicit user request ("¿Cómo se dice...?" / "Was that right?") or by session coaching mode toggle.

### 4.2 Coaching Modes (configurable per session)

| Mode | Behavior |
|------|----------|
| `on_demand` | AI never interrupts; corrections only when user asks (default) |
| `explicit` | AI pauses after errors: "You said X — the correct form is Y because Z" |
| `shadowing` | AI naturally reuses the correct form in its next sentence without commentary |

Mode is stored in session config and surfaced as a toggle in `SessionConfig.jsx`.

---

## 5. Data Model

```python
Session:
  id:            str          # UUID
  started_at:    datetime
  topic:         str          # e.g. "ordering food", freeform text
  level:         int          # 1–10
  ai_provider:   str          # "claude" | "openai" | ...
  coaching_mode: str          # "on_demand" | "explicit" | "shadowing"
  turns:         list[Turn]

Turn:
  speaker:       str          # "user" | "coach"
  audio_file:    str | None   # path to WAV (user turns, Phase 5+)
  transcript:    str
  corrections:   list[Correction] | None
  timestamp:     datetime

Correction:
  original:      str          # what the user said
  corrected:     str          # correct form
  explanation:   str          # grammar rule or vocabulary note
  triggered_by:  str          # "auto" | "user_request"
```

### 5.1 Level-to-Duolingo Band Mapping

| Level | Duolingo Range | Description |
|-------|---------------|-------------|
| 1–2 | 5–30 | Greetings, food, basic nouns |
| 3–4 | 30–70 | Directions, simple sentences |
| 5–6 | 70–110 | Stories, TV, work vocabulary |
| 7–10 | 110+ | Near-native, idioms, slang |

---

## 6. Project Structure

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
│       ├── base.py          ← AbstractAIProvider
│       ├── claude.py        ← Anthropic Claude implementation
│       └── openai.py        ← OpenAI GPT stub
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── VoiceButton.jsx
│       │   ├── CoachOverlay.jsx
│       │   ├── SessionConfig.jsx
│       │   └── Transcript.jsx
│       └── hooks/
│           └── useVoice.js
├── tests/
│   ├── fixtures/
│   │   └── hola_sample.wav  ← deterministic audio fixture
│   ├── unit/
│   │   ├── test_stt.py
│   │   ├── test_coach.py
│   │   └── test_ai_providers.py
│   └── integration/
│       └── test_turn_pipeline.py
├── docs/
│   ├── claudeSpanishCoachPlan.md
│   ├── manualTestLog.md
│   └── superpowers/
│       └── specs/
│           └── 2026-04-15-spanish-coach-design.md
├── pyproject.toml
├── uv.lock
└── package.json
```

---

## 7. Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Backend language | Python 3.12+ | Consistent with neuroDb |
| Backend framework | FastAPI | Async, clean REST, easy WebSocket upgrade path |
| Environment | `uv` + pinned deps | Consistent with neuroDb |
| STT | OpenAI Whisper (local or API) | Strong Spanish accuracy |
| TTS Phase 1–5 | Browser `speechSynthesis` | Zero dependency |
| TTS Phase 6+ | ElevenLabs | High-quality Spanish voice |
| AI Provider default | Anthropic Claude | Pluggable via `ai/` abstraction |
| Frontend framework | React + Vite | Component model fits voice state; React Native path to Android |
| Frontend testing | Vitest + React Testing Library | Standard React test stack |
| Backend testing | pytest | Consistent with neuroDb |

---

## 8. Testing Strategy

**Backend (pytest):**
- Unit: each AI provider with fixture responses (no live API calls in CI)
- Unit: `stt.py` with `hola_sample.wav` deterministic fixture
- Unit: `tts.py` provider abstraction switching
- Unit: `coach.py` correction detection logic
- Integration: full turn pipeline — WAV in → Whisper → Claude → JSON out
- Integration: session serialization/deserialization round-trip

**Frontend (Vitest + React Testing Library):**
- `VoiceButton` state machine: idle → recording → processing → playing
- `CoachOverlay` renders correction fields correctly
- `SessionConfig` emits correct provider/mode on change

**Manual smoke test (logged in `docs/manualTestLog.md`):**
- Record a Spanish sentence with a deliberate grammar error
- Verify transcript accuracy, coach response quality, correction trigger
- Sign off per phase before next phase begins

**Gate rule:** No phase begins until the previous phase's tests pass and manual smoke test is signed off.

---

## 9. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| React over Streamlit | Voice state (mic/playback/overlay) needs component-level state management; Streamlit's refresh model is incompatible with real-time audio UX |
| AI provider abstraction from Phase 0 | Swapping providers is a configuration change, not a refactor |
| TTS abstraction from Phase 0 | ElevenLabs upgrade is a module swap, not a rewrite |
| Browser TTS for MVP | Zero dependency, good enough for development; quality upgrade deferred to Phase 6 |
| Whisper for STT | Best Spanish accuracy in class at MVP cost point |
| Local-first | No cloud hosting required for MVP; aligns with desktop-first then Android target |
