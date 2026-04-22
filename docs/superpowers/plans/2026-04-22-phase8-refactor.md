# Phase 8 — Code Review & Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run coverage baselines, write a severity-graded refactor report, implement all fix-now items, and verify no regressions.

**Architecture:** Review-first, fix-second. Coverage actuals are collected before any code changes. The refactor report is committed before the first fix. Each fix is a targeted change to a specific file and line range — no opportunistic cleanup.

**Tech Stack:** Python 3.12+, uv, pytest + pytest-cov, FastAPI TestClient, React + Vite, Vitest

---

## Files Modified

| File | Change |
|------|--------|
| `backend/main.py` | Fix duplicate `get_session` route body; fix fragile `turns[-2]` backfill index |
| `backend/session.py` | Remove unreachable `isinstance(turn_data, Turn)` guard in `from_dict` |
| `frontend/src/hooks/useVoice.js` | Fix `submitAudio` catch labeling all network errors as `stage: 'stt'` |
| `frontend/src/App.jsx` | Remove duplicate `refreshSessions()` call on mount |
| `frontend/src/__tests__/useVoice.test.jsx` | New — tests for network error stage in `submitAudio` |
| `docs/superpowers/specs/2026-04-22-phase8-refactor-report.md` | New — coverage actuals + findings table |
| `docs/manualTestPlan.md` | Add Phase 8 smoke-test procedures |

---

## Task 1: Run backend coverage baseline

**Files:**
- Read: `pyproject.toml` (confirm pytest-cov is installed)

- [ ] **Step 1: Install pytest-cov if not present**

```bash
uv add --dev pytest-cov
```

Expected: `pytest-cov` added to dev dependencies (or "already satisfied").

- [ ] **Step 2: Run backend coverage**

```bash
uv run pytest --cov=backend --cov-report=term-missing --cov-branch -q 2>&1 | tee /tmp/backend-coverage.txt
cat /tmp/backend-coverage.txt
```

Expected: Test summary with per-file coverage percentages and missing line numbers. Record the output — you will paste it into the refactor report in Task 2.

- [ ] **Step 3: Run frontend coverage**

```bash
cd frontend && npx vitest run --coverage 2>&1 | tee /tmp/frontend-coverage.txt
cat /tmp/frontend-coverage.txt
```

Expected: Vitest coverage table. Record the output for the report.

---

## Task 2: Write the refactor report

**Files:**
- Create: `docs/superpowers/specs/2026-04-22-phase8-refactor-report.md`

- [ ] **Step 1: Create the report document**

Create `docs/superpowers/specs/2026-04-22-phase8-refactor-report.md` with the following content, substituting real coverage numbers from Task 1:

```markdown
# Phase 8 — Refactor Report

**Date:** 2026-04-22
**Reviewer:** Claude Code
**Status:** Findings complete — fixes pending

---

## 1. Coverage Summary

### Backend (`pytest --cov=backend --cov-branch`)

| File | Coverage | Missing branches / lines |
|------|----------|--------------------------|
| `backend/main.py` | XX% | (paste from coverage output) |
| `backend/coach.py` | XX% | (paste from coverage output) |
| `backend/session.py` | XX% | (paste from coverage output) |
| `backend/stt.py` | XX% | (paste from coverage output) |
| `backend/tts.py` | XX% | (paste from coverage output) |
| `backend/ai/claude.py` | XX% | (paste from coverage output) |
| `backend/ai/base.py` | XX% | (paste from coverage output) |

### Frontend (Vitest)

| File | Coverage | Notes |
|------|----------|-------|
| `src/hooks/useVoice.js` | XX% | (paste from coverage output) |
| `src/App.jsx` | XX% | (paste from coverage output) |
| `src/components/VoiceButton.jsx` | XX% | (paste from coverage output) |
| `src/components/Transcript.jsx` | XX% | (paste from coverage output) |
| `src/components/CoachOverlay.jsx` | XX% | (paste from coverage output) |
| `src/components/SessionConfig.jsx` | XX% | (paste from coverage output) |
| `src/components/SessionHistory.jsx` | XX% | (paste from coverage output) |

---

## 2. Findings

| # | File | Lines | Finding | Severity |
|---|------|-------|---------|----------|
| 1 | `backend/main.py` | 93–102 | `get_session` route duplicates session-loading logic already in `_get_session` helper; route should call the helper directly | **Fix now** |
| 2 | `backend/main.py` | 166–168 | `session.turns[-2]` index used to backfill `transcript_raw`/`audio_file` on the user turn — silently corrupts data if `handle_turn` appends a different number of turns than expected | **Fix now** |
| 3 | `backend/session.py` | 106–107 | `isinstance(turn_data, Turn)` guard in `from_dict` is unreachable — data parsed from JSON is never already a `Turn` object | **Fix now** |
| 4 | `frontend/src/hooks/useVoice.js` | 138 | `submitAudio` catch labels all fetch/network failures as `stage: 'stt'` — incorrect error attribution; should be `stage: 'network'` | **Fix now** |
| 5 | `frontend/src/App.jsx` | 39–40 | `refreshSessions()` called twice on mount — once inside `newSession().then()` and once standalone; the standalone call is redundant | **Fix now** |
| 6 | `backend/session.py` | `list_sessions` | Loads full session JSON for every file to build lightweight summaries — inefficient at scale, acceptable at MVP session counts | **Defer** |
| 7 | `backend/ai/claude.py` | 136–140 | Broad `except Exception` in `chat()` | **Accept as-is** — intentional; converts all AI failures to `TurnError` without raising |
| 8 | `backend/coach.py` | 40–42 | `CoachSession` re-instantiated per request | **Accept as-is** — correct behavior; conversation history lives on `Session.turns` |

---

## 3. Fix Now List

1. **`main.py` duplicate route body** — Replace the `get_session` route body with a single call to `_get_session(session_id).to_dict()`
2. **`main.py` fragile turns index** — Capture `user_turn_index = len(session.turns)` before calling `handle_turn`; use that index to backfill instead of `turns[-2]`
3. **`session.py` unreachable guard** — Remove the `isinstance(turn_data, Turn)` branch in `from_dict`; always call `Turn(**turn_copy)`
4. **`useVoice.js` error stage** — Change `stage: 'stt'` to `stage: 'network'` in `submitAudio` catch block; add a test asserting this
5. **`App.jsx` double refresh** — Remove the standalone `refreshSessions()` call that fires immediately in `useEffect`; the one inside `newSession().then()` is sufficient

---

## 4. Defer / Accept Log

| # | Finding | Reason |
|---|---------|--------|
| 6 | `list_sessions` full-load overhead | Acceptable at MVP scale. At ~hundreds of sessions performance is unnoticeable. Revisit when Phase 10+ adds cloud; at that point server-side pagination would be the right fix, not local optimisation. |
| 7 | Broad `except Exception` in `claude.py` | Deliberate design — any unhandled Claude SDK exception must surface as a recoverable `TurnError`, not a 500. Narrowing the exception type risks letting unexpected exceptions propagate to the HTTP layer. |
| 8 | `CoachSession` per-request instantiation | Correct by design — the session object carries all state; the `CoachSession` wrapper is stateless beyond its constructor args. |
```

- [ ] **Step 2: Commit the report before making any code changes**

```bash
git add docs/superpowers/specs/2026-04-22-phase8-refactor-report.md
git commit -m "docs: add Phase 8 refactor report with coverage actuals and findings"
```

---

## Task 3: Fix `get_session` route duplication (`main.py:93–102`)

**Files:**
- Modify: `backend/main.py:93–103`

- [ ] **Step 1: Verify the existing test covers this route**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestSessionPersistence::test_get_session_loads_persisted_session_after_memory_clear -v
```

Expected: PASS (this test exercises the `GET /sessions/{session_id}` route including the disk-load path).

- [ ] **Step 2: Apply the fix**

In `backend/main.py`, replace lines 93–103:

```python
@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    session = sessions.get(session_id)
    if session is None:
        try:
            session = load_session(session_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Session not found")
        sessions[session.id] = session
    return session.to_dict()
```

With:

```python
@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    return _get_session(session_id).to_dict()
```

- [ ] **Step 3: Run the covering test again to confirm it still passes**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestSessionPersistence -v
```

Expected: All `TestSessionPersistence` tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "refactor: deduplicate get_session route by calling _get_session helper"
```

---

## Task 4: Fix fragile `turns[-2]` backfill (`main.py:163–168`)

**Files:**
- Modify: `backend/main.py:163–169`

The `post_turn` handler calls `coach.handle_turn(transcript_norm)`, which appends a user turn then a coach turn to `session.turns`. The handler then backfills `transcript_raw` and `audio_file` onto the user turn using `session.turns[-2]`. If `handle_turn` ever changes how many turns it appends, this silently writes to the wrong turn.

The fix captures the user turn's future index before `handle_turn` is called.

- [ ] **Step 1: Verify the integration test that covers this path passes**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestSessionPersistence::test_full_turn_updates_persisted_session -v
```

Expected: PASS (this test asserts `turns[0].transcript_raw == "Hola"` and `turns[0].transcript_norm == "hola"` after a full pipeline call).

- [ ] **Step 2: Apply the fix**

In `backend/main.py`, replace:

```python
    coach = CoachSession(session, claude_provider)
    turn_result = coach.handle_turn(transcript_norm)
    if session.turns and session.turns[-2].speaker == "user":
        session.turns[-2].transcript_raw = transcript_raw
        session.turns[-2].audio_file = audio_file
    save_session(session)
```

With:

```python
    user_turn_index = len(session.turns)
    coach = CoachSession(session, claude_provider)
    turn_result = coach.handle_turn(transcript_norm)
    if user_turn_index < len(session.turns) and session.turns[user_turn_index].speaker == "user":
        session.turns[user_turn_index].transcript_raw = transcript_raw
        session.turns[user_turn_index].audio_file = audio_file
    save_session(session)
```

- [ ] **Step 3: Run the covering test to confirm it still passes**

```bash
uv run pytest tests/integration/test_turn_pipeline.py::TestSessionPersistence::test_full_turn_updates_persisted_session tests/integration/test_turn_pipeline.py::TestSessionPersistence::test_audio_file_saved_only_when_opted_in -v
```

Expected: Both PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "fix: use pre-call index to backfill user turn fields instead of turns[-2]"
```

---

## Task 5: Remove unreachable guard in `session.py:from_dict`

**Files:**
- Modify: `backend/session.py:104–110`

The `from_dict` classmethod has a branch `if isinstance(turn_data, Turn): reconstructed_turns.append(turn_data)` that can never be true — the data comes from `json.loads()` which always produces plain dicts, never dataclass instances.

- [ ] **Step 1: Run the session round-trip tests to establish baseline**

```bash
uv run pytest tests/unit/test_session.py -v
```

Expected: All PASS.

- [ ] **Step 2: Apply the fix**

In `backend/session.py`, replace lines 104–109:

```python
            # Reconstruct Turn object (guard against already-reconstructed)
            if isinstance(turn_data, Turn):
                reconstructed_turns.append(turn_data)
            else:
                reconstructed_turns.append(Turn(**turn_copy))
```

With:

```python
            reconstructed_turns.append(Turn(**turn_copy))
```

- [ ] **Step 3: Run session tests to confirm no regressions**

```bash
uv run pytest tests/unit/test_session.py -v
```

Expected: All PASS — identical results to Step 1.

- [ ] **Step 4: Commit**

```bash
git add backend/session.py
git commit -m "refactor: remove unreachable isinstance guard in Session.from_dict"
```

---

## Task 6: Fix `useVoice.js` network error stage mislabel

**Files:**
- Modify: `frontend/src/hooks/useVoice.js:138`
- Create: `frontend/src/__tests__/useVoice.test.jsx`

The `submitAudio` catch block sets `stage: 'stt'` for any fetch failure (network error, server down, JSON parse failure). These aren't STT failures — they're communication failures. The fix changes the stage to `'network'` and adds a test asserting the correct value.

- [ ] **Step 1: Create the test file**

Create `frontend/src/__tests__/useVoice.test.jsx`:

```jsx
import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useVoice } from '../hooks/useVoice'

describe('useVoice — submitAudio error handling', () => {
  let originalFetch

  beforeEach(() => {
    originalFetch = global.fetch
    // Stub /session/start so newSession resolves cleanly
    global.fetch = vi.fn((url) => {
      if (url === '/session/start') {
        return Promise.resolve({
          json: () => Promise.resolve({ session_id: 'test-session-123' }),
        })
      }
      // /turn — simulate network failure
      return Promise.reject(new TypeError('Failed to fetch'))
    })
    // Stub MediaRecorder
    global.MediaRecorder = vi.fn(() => ({
      start: vi.fn(),
      stop: vi.fn(),
      ondataavailable: null,
      onstop: null,
      state: 'inactive',
      mimeType: 'audio/webm',
    }))
    global.MediaRecorder.isTypeSupported = vi.fn(() => false)
    global.navigator.mediaDevices = {
      getUserMedia: vi.fn(() =>
        Promise.resolve({ getTracks: () => [{ stop: vi.fn() }] })
      ),
    }
    global.AudioContext = vi.fn(() => ({ resume: vi.fn(() => Promise.resolve()) }))
  })

  afterEach(() => {
    global.fetch = originalFetch
  })

  it('sets stage to network when /turn fetch throws', async () => {
    const { result } = renderHook(() => useVoice())

    // Initialise session
    await act(async () => {
      await result.current.newSession({
        topic: 'general',
        level: 5,
        ai_provider: 'claude',
        coaching_mode: 'on_demand',
        tts_provider: 'browser',
        tts_voice_id: null,
      })
    })

    // Trigger submitAudio directly with a dummy Blob
    const blob = new Blob(['fake'], { type: 'audio/webm' })
    await act(async () => {
      // Access submitAudio via the recorder onstop path — call startRecording then
      // fire the onstop handler manually with our blob
      await result.current.startRecording()
      const recorder = global.MediaRecorder.mock.results[0].value
      await recorder.onstop()
    })

    // The /turn fetch will reject — error.stage should be 'network', not 'stt'
    expect(result.current.error).not.toBeNull()
    expect(result.current.error.stage).toBe('network')
    expect(result.current.error.recoverable).toBe(true)
  })
})
```

- [ ] **Step 2: Run the new test to confirm it fails (red)**

```bash
cd frontend && npx vitest run src/__tests__/useVoice.test.jsx 2>&1
```

Expected: FAIL — error stage is currently `'stt'`, not `'network'`.

- [ ] **Step 3: Apply the fix**

In `frontend/src/hooks/useVoice.js`, replace line 138:

```js
      setError({ stage: 'stt', message: 'Network error', recoverable: true })
```

With:

```js
      setError({ stage: 'network', message: 'Network error', recoverable: true })
```

- [ ] **Step 4: Run the new test to confirm it passes (green)**

```bash
cd frontend && npx vitest run src/__tests__/useVoice.test.jsx 2>&1
```

Expected: PASS.

- [ ] **Step 5: Run full frontend test suite to check for regressions**

```bash
cd frontend && npx vitest run 2>&1
```

Expected: All tests PASS. `VoiceButton.test.jsx` uses `stage: 'stt'` in its fixture — verify it still passes (it tests display logic, not the stage value itself).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useVoice.js frontend/src/__tests__/useVoice.test.jsx
git commit -m "fix: label submitAudio network errors as stage network instead of stt"
```

---

## Task 7: Fix double `refreshSessions()` on mount (`App.jsx`)

**Files:**
- Modify: `frontend/src/App.jsx:32–41`

On mount, `useEffect` calls `newSession(DEFAULT_CONFIG).then(() => { ...; refreshSessions() })` and also calls `refreshSessions()` directly. The standalone call fires immediately against an empty session store (the new session hasn't been saved yet), producing a redundant request and a brief stale render.

- [ ] **Step 1: Apply the fix**

In `frontend/src/App.jsx`, replace:

```js
  useEffect(() => {
    fetch('/topics').then((r) => r.json()).then(setTopics).catch(() => {})
    fetch('/providers').then((r) => r.json()).then(setProviders).catch(() => {})
    fetch('/tts-voices').then((r) => r.json()).then(setTtsVoices).catch(() => {})
    newSession(DEFAULT_CONFIG).then((sessionId) => {
      setSelectedSessionId(sessionId)
      refreshSessions()
    })
    refreshSessions()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
```

With:

```js
  useEffect(() => {
    fetch('/topics').then((r) => r.json()).then(setTopics).catch(() => {})
    fetch('/providers').then((r) => r.json()).then(setProviders).catch(() => {})
    fetch('/tts-voices').then((r) => r.json()).then(setTtsVoices).catch(() => {})
    newSession(DEFAULT_CONFIG).then((sessionId) => {
      setSelectedSessionId(sessionId)
      refreshSessions()
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
```

- [ ] **Step 2: Run frontend test suite**

```bash
cd frontend && npx vitest run 2>&1
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "fix: remove redundant refreshSessions call on mount in App"
```

---

## Task 8: Verify full test suite — no regressions

**Files:** None modified.

- [ ] **Step 1: Run full backend test suite**

```bash
uv run pytest -v 2>&1
```

Expected: Same number of passing tests as before Phase 8 fixes (92 backend, 2 skipped, per Phase 6 gate). Zero failures.

- [ ] **Step 2: Run full frontend test suite**

```bash
cd frontend && npx vitest run 2>&1
```

Expected: Passes with at least the tests that existed at Phase 6 gate (46 frontend), plus the new `useVoice.test.jsx` test from Task 6. Zero failures.

- [ ] **Step 3: Run backend coverage one more time to record final actuals**

```bash
uv run pytest --cov=backend --cov-report=term-missing --cov-branch -q 2>&1
```

Record the final coverage numbers. If any "fix now" fixes added new branches that are now untested, note them — they become "defer" items in the report update.

- [ ] **Step 4: Commit any report updates**

If coverage numbers changed from the Task 1 baseline, update the Coverage Summary table in `docs/superpowers/specs/2026-04-22-phase8-refactor-report.md` with final actuals, then:

```bash
git add docs/superpowers/specs/2026-04-22-phase8-refactor-report.md
git commit -m "docs: update Phase 8 report with post-fix coverage actuals"
```

---

## Task 9: Manual smoke test and docs update

**Files:**
- Modify: `docs/manualTestPlan.md`
- Modify: `docs/manualTestLog.md`
- Modify: `claudeSpanishCoachPlan.md`

- [ ] **Step 1: Add Phase 8 procedures to `docs/manualTestPlan.md`**

Append the following section to `docs/manualTestPlan.md`:

```markdown
## Phase 8 — Code Review & Refactor

**Goal:** Verify no regressions after refactor fixes.

### Pre-conditions
- Backend running: `uv run uvicorn backend.main:app --reload --port 8001`
- Frontend running: `npm run dev` (or served from FastAPI dist)
- All backend + frontend automated tests pass

### Smoke Test Steps

1. Open the app in Chrome at `http://localhost:5173` (or `http://localhost:8001` if using FastAPI static serve)
2. Verify the page loads with no console errors
3. Start a new session (topic: Ordering food, level 5, coaching mode: On-demand, TTS: Browser)
4. Record: "Hola, quiero ordenar una mesa para dos personas"
5. Verify: transcript appears, coach responds in Spanish, browser TTS plays the reply
6. Record: "¿Corrígeme si digo algo mal?"
7. Verify: coach responds and corrections overlay appears (on-demand trigger phrase detected)
8. Click "New Conversation", select a different topic, verify session resets cleanly
9. Open Session History, verify the previous session appears with the correct turn count
10. Click the previous session to reload it; verify transcript restores correctly

### Pass Criteria
- No console errors throughout
- Voice round-trip works end-to-end (mic → transcription → coach response → TTS playback)
- Corrections overlay appears on step 6
- Session history shows correct entry after new session
- Session reload restores transcript

### Sign-off
Record date, tester, and any deviations in `docs/manualTestLog.md`.
```

- [ ] **Step 2: Run the smoke test manually**

Follow the steps in the procedure added in Step 1. Record pass/fail in `docs/manualTestLog.md`:

```markdown
## Phase 8 — Code Review & Refactor

**Date:** 2026-04-22
**Tester:** [your name]
**Result:** PASS

All smoke test steps passed. No console errors. Voice round-trip confirmed. Corrections trigger confirmed. Session history confirmed.

**Deviations:** None
```

- [ ] **Step 3: Mark Phase 8 complete in `claudeSpanishCoachPlan.md`**

In `claudeSpanishCoachPlan.md`, check off Phase 8 tasks and update the status table. Change the Phase 8 row from `⏳ Not started` to `✅ Complete`.

Also check off the Phase 8 gate items:
```markdown
- [x] Refactor report written and committed
- [x] All existing tests pass (no regressions)
- [x] Manual smoke test signed off in `docs/manualTestLog.md`
```

- [ ] **Step 4: Commit docs**

```bash
git add docs/manualTestPlan.md docs/manualTestLog.md claudeSpanishCoachPlan.md
git commit -m "docs: Phase 8 sign-off — smoke test passed, plan updated"
```
