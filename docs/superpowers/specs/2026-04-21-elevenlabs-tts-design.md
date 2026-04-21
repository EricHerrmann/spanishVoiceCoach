# Phase 6 — ElevenLabs TTS Design

**Date:** 2026-04-21
**Status:** Approved

---

## Goal

Swap browser `speechSynthesis` for ElevenLabs high-quality Spanish voice output. TTS provider (browser / elevenlabs) and voice selection are per-session config, following the `ai_provider` model for UI consistency.

---

## Architecture

Audio delivery uses **Option A: base64 audio in the `/turn` JSON response**. The backend calls ElevenLabs, base64-encodes the returned bytes, and includes `audio_b64` in the existing `/turn` response. The frontend decodes and plays via `AudioContext`. When `audio_b64` is absent (browser TTS or TTS error), the frontend falls back to `speechSynthesis`. Single round-trip, no new routes, no temp files.

---

## Components

### `backend/tts.py`

- `AbstractTTSProvider.synthesize(text: str) -> bytes | None` — return type updated from `None` to `bytes | None`
- `BrowserTTSProvider.synthesize()` — keeps returning `None` (passthrough)
- `ElevenLabsTTSProvider(AbstractTTSProvider)`:
  - Reads `ELEVENLABS_API_KEY` from env; raises `RuntimeError` at instantiation if missing (matches `ClaudeProvider` pattern)
  - Takes `voice_id: str` in constructor
  - Calls ElevenLabs `/v1/text-to-speech/{voice_id}` via `httpx`
  - Returns audio `bytes` on success
  - API errors return `TurnError(stage="tts", recoverable=True)` — no exception raised to caller
- `ELEVENLABS_VOICES: list[dict]` — curated static list of Spanish-suitable voices, each with `id`, `label`, and `description`; hardcoded in `tts.py`

### `backend/session.py`

- Add `tts_provider: str = "browser"` to `Session` — valid values: `"browser"`, `"elevenlabs"`
- Add `tts_voice_id: str | None = None` to `Session` — `None` is valid when `tts_provider == "browser"`

### `backend/main.py`

- `GET /tts-voices` — returns `ELEVENLABS_VOICES` from `tts.py`
- `SessionStartRequest` — add `tts_provider: Literal["browser", "elevenlabs"] = "browser"` and `tts_voice_id: str | None = None`
- `POST /session/start` — passes `tts_provider` and `tts_voice_id` through to `new_session()`
- `POST /turn` — after getting `CoachResponse`:
  - If `session.tts_provider == "elevenlabs"`: instantiate `ElevenLabsTTSProvider(session.tts_voice_id)` per request (voice_id is per-session, so no module-level singleton); wrap in try/except — `RuntimeError` (missing key) → `TurnError(stage="tts", recoverable=False)`
  - If `synthesize()` returns `bytes` (MP3): base64-encode, include `audio_b64` in response
  - If result is `TurnError`: include error, omit `audio_b64` (frontend falls back to `speechSynthesis`)
  - If `session.tts_provider == "browser"`: omit `audio_b64`

### `frontend/hooks/useVoice.js`

- `newSession(config)` — pass `tts_provider` and `tts_voice_id` in the `POST /session/start` body
- `submitAudio()` — after receiving `/turn` response:
  - If `data.audio_b64`: decode with `atob`, construct `Uint8Array` of MP3 bytes, play via `AudioContext.decodeAudioData` + `AudioBufferSourceNode`; set state `idle` on playback end
  - Else: call existing `speakCoachText(data.coach_text)` (browser `speechSynthesis`)

### `frontend/components/SessionConfig.jsx`

- Add **TTS provider select** (Browser / ElevenLabs) following the AI provider dropdown pattern
- When ElevenLabs selected: show **voice dropdown** populated from `ttsVoices` prop (fetched in `App.jsx` from `GET /tts-voices`)
- When Browser selected: hide voice dropdown

### `frontend/src/App.jsx`

- Fetch `/tts-voices` on mount (alongside `/topics` and `/providers`)
- Pass `ttsVoices` to `SessionConfig`
- Add `tts_provider` and `tts_voice_id` to config state (defaults: `"browser"`, `null`)

---

## Data Flow

```
User speaks
  → POST /turn (audio)
  → Whisper STT → CoachSession → Claude → CoachResponse
  → If elevenlabs: ElevenLabsTTSProvider.synthesize(coach_text) → bytes
  → Response: { transcript_raw, transcript_norm, coach_text, corrections, audio_b64?, error }
  → Frontend: audio_b64 present → AudioContext playback
              audio_b64 absent  → speechSynthesis fallback
```

---

## Error Handling

- Missing `ELEVENLABS_API_KEY` when ElevenLabs is selected for a turn → `RuntimeError` at `ElevenLabsTTSProvider.__init__` → caught in `/turn` route → `TurnError(stage="tts", recoverable=False)` (config error, not user-retryable)
- ElevenLabs API error during turn → `TurnError(stage="tts", recoverable=True)`; frontend shows retry prompt; `audio_b64` omitted; existing error display handles it
- Invalid `voice_id` → ElevenLabs returns 4xx → caught as API error → `TurnError`

---

## Testing

### Backend unit tests (`tests/unit/test_tts.py`)

- `ElevenLabsTTSProvider` with mocked `httpx` response → verifies `bytes` returned on success
- `ElevenLabsTTSProvider` with mocked HTTP error → verifies `TurnError(stage="tts", recoverable=True)` returned, no exception raised
- `ElevenLabsTTSProvider` with missing `ELEVENLABS_API_KEY` → `RuntimeError` at instantiation
- `BrowserTTSProvider.synthesize()` → returns `None`
- `AbstractTTSProvider.synthesize()` → `NotImplementedError`

### Frontend unit tests (Vitest)

- `SessionConfig` renders TTS provider dropdown
- When ElevenLabs selected, voice dropdown appears with provided options
- When Browser selected, voice dropdown hidden
- `useVoice` plays via `AudioContext` when `audio_b64` present (mock `AudioContext`)
- `useVoice` falls back to `speechSynthesis` when `audio_b64` absent

### Manual smoke test

- Configure session with ElevenLabs + a curated voice; speak → verify high-quality Spanish audio plays
- Switch to Browser TTS; speak → verify `speechSynthesis` fallback works
- Remove `ELEVENLABS_API_KEY` from env; configure ElevenLabs → verify `TurnError` returned, retry prompt shown

---

## Curated Voices (initial list — subject to ElevenLabs availability)

A handful of natural Spanish-accent voices will be hardcoded in `ELEVENLABS_VOICES`. At minimum:
- A neutral Latin American Spanish voice
- A neutral Castilian Spanish voice
- A female and male option each

Exact IDs confirmed from ElevenLabs voice library before implementation.

---

## Out of Scope

- Live voice list from ElevenLabs API (static list is sufficient for MVP)
- Streaming/chunked audio delivery
- Per-voice language filtering in the UI
- ElevenLabs model selection (use `eleven_multilingual_v2` hardcoded)
- Audio format selection (use MP3 — ElevenLabs default output; `audio_b64` is always base64-encoded MP3)
