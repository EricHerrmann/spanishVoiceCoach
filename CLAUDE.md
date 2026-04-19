# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

duoVoiceCoach is a voice-first AI Spanish conversation coach that runs in the browser on desktop (Android PWA target in a later phase).

Primary goal:
- Build a verbal AI coach/companion that conducts natural Spanish conversations, provides on-demand corrections, and helps bridge the gap between structured language-learning apps and real conversational fluency.

Epoch goal (current execution focus — MVP):
- Deliver a working desktop Spanish voice coach: mic capture → Whisper STT → Claude coaching response → browser TTS playback, with configurable topic, level, and coaching mode. MVP = Phases 0–3.

## Goal-to-Epoch Mapping

### Goal Summary
- Voice-first, unstructured Spanish conversation practice — not drills or fill-in-the-blank.
- User selects topic and proficiency level; coach adapts difficulty and vocabulary.
- On-demand corrections: coach corrects only when asked, or in hybrid mode (auto-correct on clear errors, silent otherwise).
- Bilingual transcript visible during session.
- Eventually runs on Android.

### Epoch (MVP — Phases 0–3)
- Phase 0: Scaffolding — project structure, abstract interfaces, test harness, no real functionality.
- Phase 1: Voice Pipeline — mic capture → Whisper transcription → browser TTS echo. No AI yet.
- Phase 2: AI Conversation Core — Claude wired in; freeform Spanish conversation.
- Phase 3: Coaching Layer — hybrid mode, on-demand corrections, coaching toggle.

Full phase detail, data model, and gate criteria live in `claudeSpanishCoachPlan.md`.

## Current Repository State

- Pre-implementation. Design approved. Phase 0 not yet started.
- Planning artifacts present: `SpanishConversationCoachGoals.md`, `claudeSpanishCoachPlan.md`, `docs/`.
- No backend, frontend, or test code exists yet.

## Recommended Technical Baseline

Use these defaults unless a stronger reason emerges during implementation:

- Python 3.12+ for the backend (`uv` + pinned dependencies via `pyproject.toml`)
- FastAPI for the backend API server
- Local Whisper (`openai-whisper` package, `base` model) for STT — no API key required; swap path via `backend/stt.py` abstraction
- Anthropic Claude as the primary AI provider — abstracted behind `backend/ai/base.py` (`AbstractAIProvider`)
- Browser `speechSynthesis` for TTS in MVP — abstracted behind `backend/tts.py` (`AbstractTTSProvider`); ElevenLabs upgrade in Phase 6
- React + Vite for the frontend (JSX, no TypeScript for MVP)
- pytest for backend tests; Vitest for frontend tests
- Docker for local and deployment packaging

Clear separation of concerns:
- `backend/stt.py` — STT abstraction (Whisper local → API swap later)
- `backend/tts.py` — TTS abstraction (browser passthrough → ElevenLabs swap in Phase 6)
- `backend/ai/` — AI provider abstraction (`AbstractAIProvider`; Claude default)
- `backend/coach.py` — conversation + coaching logic (provider-agnostic)
- `backend/session.py` — session/turn/correction data model
- `backend/main.py` — FastAPI routes only; no business logic
- `frontend/` — React UI, mic capture, browser TTS playback

## Development Process

Follow this order within each phase:

1. Define data contracts and abstract interfaces before writing implementation code.
2. Write failing tests first (TDD); implement only enough to make them pass.
3. Build one capability end-to-end (audio in → response out) before layering features.
4. Gate each phase: all tests pass + manual smoke-test sign-off in `docs/manualTestLog.md` before the next phase begins.
5. Add persistence and session history only after the conversation core is stable (Phase 5+).

Provider abstractions (`AbstractAIProvider`, `AbstractTTSProvider`) must be wired in from Phase 0, before any real provider is implemented. A provider swap must be a config/module change, not a refactor.

## Testing Requirements

Minimum expectations for all changes:

- Unit tests for all transform, normalization, and session-model logic
- Unit tests for every provider stub asserting `NotImplementedError` on the abstract base
- Integration test for the full turn pipeline: WAV fixture → `/turn` → structured JSON response
- Idempotency: re-running an ingest or session-restore must not create duplicate records
- Fixture audio (`tests/fixtures/hola_sample.wav`) used for all STT tests — deterministic, checked in

Document in test files or `docs/manualTestLog.md`:
- Whisper model version and fixture transcript expected output
- Phase gate sign-off date and tester

## Coding Standards

1. Keep implementation simple and explicit; avoid premature abstractions beyond the provider interfaces already planned.
2. Identify root cause before fixing issues; do not guess.
3. Abstract interfaces defined in Phase 0 are the ceiling of abstraction for MVP — do not add new layers.
4. Every session-modifying operation must be traceable through the `Turn` and `TurnError` model.
5. Keep planning and execution artifacts in `docs/` and versioned; update `claudeSpanishCoachPlan.md` as phases complete.

## Environment Variables

All required keys are documented in `.env.example`. The active keys for MVP are:

- `ANTHROPIC_API_KEY` — required for Phase 2+ (Claude coaching)
- `DVC_SESSION_SECRET` — required; session cookie signing key

Whisper runs locally in MVP — no `OPENAI_API_KEY` needed for STT.

Full env var reference: `.env.example`.

## Working Documentation

Maintain planning and progress docs in `docs/`.

Start from:
- `SpanishConversationCoachGoals.md` — user goals and motivation
- `claudeSpanishCoachPlan.md` — full phased plan, data model, gate criteria

When adding implementation, also update:
- `claudeSpanishCoachPlan.md` — check off completed tasks, record gate sign-offs
- `docs/manualTestLog.md` — phase smoke-test results
- `docs/` architecture or runbook notes as needed
