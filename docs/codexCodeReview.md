# Codex Code Review

Review date: 2026-04-28

Scope reviewed:
- Goals and phase plan in `SpanishConversationCoachGoals.md` and `claudeSpanishCoachPlan.md`
- Backend in `backend/`
- Frontend in `frontend/src/`
- Test suites in `tests/` and `frontend/src/__tests__/`

Validation run during review:
- `uv run pytest`: 155 passed, 6 skipped
- `npm test -- --run`: 126 passed
- `uv run pytest --cov=backend --cov-report=term-missing`: 90% backend coverage
- `npm run lint`: fails with 31 errors and 2 warnings

## Executive Summary

The project is in good functional shape. The core voice pipeline, coaching flow, persistence, flashcards, translation, and pronunciation features are all implemented and covered by a strong test suite.

The main problems are structural, not feature-level:
- `backend/main.py` has grown into a mixed routes/services/storage module.
- frontend audio and recording logic is duplicated across three places.
- AI request cost grows with full conversation replay on every turn.
- static quality gates are weaker than the docs claim, because frontend lint is currently red.

## Strengths

- Provider boundaries are clear enough to support STT/TTS swapping: `backend/stt.py`, `backend/tts.py`, `backend/ai/base.py`
- Session and turn data models are explicit and readable: `backend/session.py`
- Tests are broad and valuable, especially the end-to-end turn pipeline coverage
- The product has moved beyond MVP without collapsing into a large framework or unnecessary abstraction

## Findings

### Fix Now: `backend/main.py` is carrying too much business logic

Evidence:
- The phase plan says `backend/main.py` should contain FastAPI routes only: `claudeSpanishCoachPlan.md:68-72`
- In practice it now also owns auth middleware, session cache access, audio file persistence, user flashcard persistence, pronunciation challenge loading, translation orchestration, flashcard generation orchestration, TTS handling, and static serving: `backend/main.py:47-70`, `backend/main.py:134-154`, `backend/main.py:157-243`, `backend/main.py:250-377`, `backend/main.py:380-448`

Why it matters:
- Route changes and product logic changes now touch the same file
- Reuse is poor, because translation, pronunciation, and turn processing are embedded in handlers
- This file is already the main maintainability hotspot in the repo

Recommended refactor:
- Keep `backend/main.py` as routing and request/response wiring only
- Move turn orchestration into a `backend/turn_service.py`
- Move flashcard deck persistence into a `backend/flashcards_store.py`
- Move translation and pronunciation orchestration into dedicated modules
- Add shared response serializers for `TurnError`, TTS payloads, and correction lists

### Fix Now: the frontend quality gate is not actually clean

Evidence:
- `docs/manualTestLog.md:123-126` says Phase 8 finished with "linting clean"
- Current `npm run lint` fails
- React hook lint issues are present in `frontend/src/App.jsx:95-98`, `frontend/src/components/CoachOverlay.jsx:6-14`, and `frontend/src/components/ConversationView.jsx:11-12`
- Test files fail lint because the config does not define test globals: `frontend/eslint.config.js:7-28`

Why it matters:
- The repo currently passes tests but fails a static maintainability gate
- This makes regressions easier to merge and weakens the usefulness of the earlier refactor phase
- The docs no longer match the actual engineering state

Recommended refactor:
- Fix the current lint errors before adding more UI logic
- Split lint config by app code and test code, with vitest globals enabled for tests
- Ignore generated coverage output in ESLint
- Add lint to the default validation path alongside backend and frontend tests

### Next Sprint: audio capture and playback logic is duplicated across the frontend

Evidence:
- Conversation flow: `frontend/src/hooks/useVoice.js:67-184`
- Translation flow: `frontend/src/components/TranslationView.jsx:17-88`
- Pronunciation flow: `frontend/src/components/PronunciationView.jsx:68-110`

Why it matters:
- Android and browser audio behavior is the highest-risk area in the product
- MIME type handling, `MediaRecorder` setup, stop behavior, base64 playback, and browser speech fallback are being maintained in parallel
- Any bug fix in one flow can easily miss the others

Recommended refactor:
- Extract shared hooks:
  - `useAudioRecorder()`
  - `useSpeechPlayback()`
- Leave each feature responsible only for endpoint-specific submission and response rendering
- Keep MIME negotiation and `AudioContext` behavior in one place

### Next Sprint: Claude turn cost grows linearly with conversation length

Evidence:
- Each chat request rebuilds the message list from every saved turn and resends the whole history: `backend/ai/claude.py:177-199`

Why it matters:
- Latency and token cost will rise as sessions get longer
- The issue is especially relevant now that the app supports longer multi-tool sessions and cloud deployment
- This is the clearest speed bottleneck in the AI layer

Recommended refactor:
- Introduce a context window policy
- Keep the last N user/coach turns verbatim
- Summarize older history into a compact session note
- Make model names and token budgets configurable instead of hard-coded in multiple methods

### Defer Soon: persistence paths are simple but will become a scaling bottleneck

Evidence:
- Every turn persists the full session document: `backend/main.py:192`, `backend/session.py:151-160`
- Session listing reparses every session file on every request: `backend/session.py:171-186`
- Live sessions are also cached in a process-global dict with no eviction: `backend/main.py:41-44`, `backend/main.py:134-143`

Why it matters:
- For current scale this is acceptable
- For longer sessions, more users, or more history, response time and memory growth will trend the wrong way

Recommended refactor:
- Keep JSON persistence for now, but add boundaries
- Cache session summaries separately from full transcripts
- Add a simple session cache size limit or TTL
- Consider append-only turn storage or periodic checkpoints if sessions get materially longer

### Cleanup: repo hygiene around generated frontend artifacts is still loose

Evidence:
- `.gitignore` ignores `frontend/node_modules/` but not root `node_modules/`: `.gitignore:47-51`
- A tracked file exists under root `node_modules/.vite/vitest/.../results.json`

Why it matters:
- Generated artifacts create noisy diffs and accidental churn
- This is a maintainability problem, not a functional one

Recommended refactor:
- Ignore root `node_modules/` and root Vite cache output
- Remove tracked generated artifacts from version control

## Coverage Notes

Backend coverage is strong at 90%, but the main remaining gap is the most operationally important AI module:
- `backend/ai/claude.py`: 70% coverage

That is acceptable for a fast-moving prototype, but it is the wrong place to stay under-tested long-term. The missing lines are concentrated in translation and flashcard-generation branches, which are now user-facing features.

## Priority Refactor Order

1. Make the frontend quality gate real again: fix lint, fix ESLint config, add it to normal validation.
2. Break `backend/main.py` into route wiring plus service/storage modules.
3. Consolidate frontend recording/playback into shared hooks.
4. Add AI context-window management to cap latency and token growth.
5. Tighten persistence and session caching behavior before more cloud/mobile usage.
6. Clean up generated artifact tracking and repo hygiene.

## Bottom Line

The codebase is functionally ahead of the original MVP and test coverage is good. The next engineering win is not more breadth. It is reducing duplication, shrinking the main routing module, and re-establishing clean quality gates so the project can keep growing without getting slower to change.
