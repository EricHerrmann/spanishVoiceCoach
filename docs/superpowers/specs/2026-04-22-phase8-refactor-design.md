# Phase 8 — Code Review & Refactor Design

**Date:** 2026-04-22
**Phase:** 8 — Code Review & Refactor
**Status:** Approved

---

## Context

Phases 0–6 are complete. Phase 7 (Android/PWA) is in progress with manual tests explicitly deferred. Phase 8 is a discipline checkpoint before cloud deployment and GUI redesign — not a response to a specific bug.

---

## Approach

**Option B — Review-first, fix-second.**

Full review and coverage run produce a committed report with severity ratings. Only items rated "fix now" are implemented. No opportunistic cleanup beyond the approved list.

### Phase 7 deferral

Phase 7 manual smoke tests (Android device test, `docs/manualTestPlan.md` update) are explicitly deferred. They may run in parallel with Phase 8 or be completed afterward. Phase 8 does not gate on Phase 7 sign-off.

---

## Review Methodology

Each module is reviewed against the scope defined in `claudeSpanishCoachPlan.md` Phase 8.

**Backend modules:**
- `main.py` — routes contain no business logic; all logic delegated to `coach.py`, `session.py`, or provider modules
- `coach.py` — system prompt construction, mode routing, correction trigger detection: clarity and single responsibility
- `session.py` — data model, persistence logic, serialization: correctness and efficiency
- `stt.py` / `tts.py` — abstraction boundaries clean; no provider-specific logic leaking into base
- `ai/claude.py` — prompt caching usage, structured output parsing, error handling path

**Frontend files:**
- `useVoice.js` — state machine correctness, AudioContext lifecycle, error surface
- `App.jsx` — state placement (hook vs. component), session config flow
- All components — unused props, missing test coverage, unreferenced CSS

**Coverage:**
- Run `pytest --cov=backend --cov-report=term-missing` for line coverage with uncovered branches
- Run Vitest coverage for frontend
- Document per-file percentages and uncovered branches in the report

---

## Severity Classification

| Severity | Criteria |
|----------|----------|
| **Fix now** | Correctness bug, silent data corruption, violated abstraction boundary, broken error path |
| **Defer** | Real issue, low risk at MVP scale; revisit Phase 10+ |
| **Accept as-is** | Intentional trade-off; rationale documented |

---

## Report Structure

Report written to `docs/superpowers/specs/2026-04-22-phase8-refactor-report.md` before any code changes.

Sections:
1. **Coverage summary** — backend and frontend percentages; uncovered branches by file
2. **Findings table** — `File | Lines | Finding | Severity | Rationale`
3. **Fix now list** — numbered, each fix described precisely enough to implement without ambiguity
4. **Defer/Accept log** — findings not being fixed, with reason preserved for Phase 10+

---

## Pre-identified Findings

These were identified by reading the codebase before running coverage. Final severities confirmed after the coverage run.

### Likely fix-now

| File | Lines | Finding |
|------|-------|---------|
| `main.py` | 166–168 | `session.turns[-2]` index used to backfill `transcript_raw`/`audio_file` — silently corrupts data if turns are in an unexpected state |
| `main.py` | 93–102 | `get_session` route duplicates session-loading logic already in `_get_session` helper |
| `session.py` | 106 | `isinstance(turn_data, Turn)` guard in `from_dict` is unreachable — data from JSON is never already a `Turn` object |
| `useVoice.js` | 138 | Network errors in `submitAudio` catch labeled `stage: 'stt'` regardless of actual failure point |
| `App.jsx` | 39 | `refreshSessions()` called twice on mount |

### Likely defer

| File | Finding |
|------|---------|
| `session.py` `list_sessions` | Loads full session JSON to build lightweight summaries — inefficient at scale, acceptable at MVP |

### Likely accept as-is

| File | Finding | Rationale |
|------|---------|-----------|
| `ai/claude.py` | Broad `except Exception` in `chat()` | Intentional — converts all AI failures to `TurnError` without raising |
| `coach.py` | `CoachSession` re-instantiated per request | Correct behavior; conversation history lives on `Session.turns`, not on the instance |

---

## Fix Implementation

Fixes are implemented only after the report is committed and the fix-now list is reviewed. Scope is strictly the approved list — no additional cleanup.

**Verification after fixes:**
- `uv run pytest` — full suite, no regressions
- `npm test` — full Vitest suite, no regressions
- Manual smoke test: full voice session end-to-end

---

## Phase 8 Gate

- [ ] Coverage run completed; actuals recorded in report
- [ ] Refactor report written and committed before any code changes
- [ ] All fix-now items implemented
- [ ] All existing tests pass (no regressions)
- [ ] Manual smoke test signed off in `docs/manualTestLog.md`
- [ ] `docs/manualTestPlan.md` updated with Phase 8 procedures
