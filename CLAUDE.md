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

See `docs/projectStatus.md` for the current phase status, test counts, and open items. That file is the authoritative one-stop view of project state; this section intentionally stays brief.

- Phases 0–9, A, B: complete and smoke-test signed off.
- Phase 10 (Cloud Deployment): complete and signed off 2026-05-01; app live at `https://spanishcoach.fly.dev`.
- R1–R6 (code review refactor): all complete and merged 2026-04-28.
- Backend: 180 tests passing, 6 skipped. Frontend: 149 passing. Lint: clean.

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

Use a layered MVP approach:

- Work at the smallest active layer being matured: project, epoch, or feature.
- At that layer, prefer the simplest implementation that satisfies the current goal, while keeping extension seams where future growth is already expected.
- Treat MVP as the default treatment for the active layer until the supported surface of that layer widens.

When a capability grows from one primary path into a broader supported surface, treat that as a shift in rigor for that capability:

- Design review, testing depth, and rollout confidence should follow the current supported surface rather than the earlier narrow path.
- If a change appears to widen the supported surface, surface that transition explicitly, identify the affected design points, and propose the appropriate increase in validation.
- If the intended support level is unclear from repo context, ask before assuming narrow MVP validation is still sufficient.

Follow this order within each phase:

1. Define data contracts and abstract interfaces before writing implementation code.
2. Write failing tests first (TDD); implement only enough to make them pass.
3. Build one capability end-to-end (audio in → response out) before layering features.
4. Gate each phase: all tests pass + manual smoke-test sign-off in `docs/manualTestLog.md` before the next phase begins.
5. Add persistence and session history only after the conversation core is stable (Phase 5+).

Provider abstractions (`AbstractAIProvider`, `AbstractTTSProvider`) must be wired in from Phase 0, before any real provider is implemented. A provider swap must be a config/module change, not a refactor.

## Testing Requirements

Testing should track the support level of the active capability.

- A narrow MVP path may rely mainly on unit and mocked integration coverage.
- When a capability expands into a broader supported or user-selectable surface, strengthen end-to-end validation accordingly, especially when external providers or production-facing paths are involved.
- Distinguish between implemented, exposed, and intended-for-active-use paths; the validation bar should rise as a path moves through those states.
- If support level is ambiguous, surface the transition and ask before assuming lighter MVP validation remains appropriate.

Minimum expectations for all changes:

- Unit tests for all transform, normalization, and session-model logic
- Unit tests for the abstract base plus each concrete AI provider selection path
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

All required keys are documented in `.env.example`. The active keys for the current app are:

- `ANTHROPIC_API_KEY` — required for Phase 2+ (Claude coaching)
- `OPENAI_API_KEY` — required for OpenAI STT mode and OpenAI chat selection
- `GOOGLE_API_KEY` — required when Google Gemini is selected
- `DEEPSEEK_API_KEY` — required when DeepSeek is selected
- `GROQ_API_KEY` — required when Groq is selected
- `DVC_SESSION_SECRET` — required; session cookie signing key

Whisper can still run locally; `OPENAI_API_KEY` is only needed when `STT_PROVIDER=openai` or the OpenAI AI provider is selected.

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

---

## Project Process Rules

### projectStatus.md

`docs/projectStatus.md` is the single-page project dashboard. It is a **pointer document** — it summarizes and references source documents; it does not reproduce their content.

**Update `docs/projectStatus.md` whenever:**
- A phase gate is signed off (update the Phase Status table row and the Test Counts table)
- A phase's status changes (e.g., "Not started" → "In progress", code complete but gate pending)
- The open items list changes (a pending item closes, or a new blocker is identified)
- Test counts change materially (after any phase that adds tests)
- The active layer of work or support-state context changes in a way a later model should not have to rediscover
- This CLAUDE.md "Current Repository State" section is updated (keep both in sync)

**Rules for maintaining it as a pointer:**
- Phase descriptions belong in `claudeSpanishCoachPlan.md`, not here. One-line status only per phase.
- Smoke-test notes belong in `docs/manualTestLog.md`. Record only the gate outcome (signed off / partial / pending) in the status table.
- Task checklists belong in `claudeSpanishCoachPlan.md` or `docs/claudeCodeImplementationPlan.md`. Do not copy tasks into `projectStatus.md`.
- If you find yourself writing more than one sentence of explanation for a phase, move it to the source document and add a reference.
- In addition to phase status, preserve concise support-state context for the active layer of work so a later model can understand project state without re-discovery.
- Keep that context summary-level only: note the active layer (`project`, `epoch`, or `feature`), whether a capability is still in narrow MVP treatment or has widened into a broader supported surface, and any exposed paths whose support level is intentionally limited or still evolving.
- If a capability has shifted from narrow MVP treatment to broader support treatment, note that shift briefly in `Current Focus`, `Phase Status`, or `Open Items`, whichever is clearest.
- If raw test counts could mislead a later model about actual support level, add a short clarifying note rather than expanding the tables.

### Source document sync

- `claudeSpanishCoachPlan.md` is the single source of truth for phase definitions, task checklists, and gate criteria. Update it directly; never reproduce its content elsewhere.
- `docs/manualTestLog.md` is the single source of truth for smoke-test results and sign-off dates. Every gate sign-off lives there.
- `docs/claudeCodeImplementationPlan.md` tracks the R1–R6 refactor work. When a new code-review cycle produces findings, create a new plan document in `docs/` rather than modifying this file.
- When a gate closes, update **both** the source document (`claudeSpanishCoachPlan.md` task checkboxes + gate criteria) **and** `docs/projectStatus.md` (phase row + test counts) in the same commit.
