# duoVoiceCoach — Manual Test Log

Each phase gate requires a smoke-test sign-off entry before the next phase begins.

---

## Phase 0 — Scaffolding & Contracts

**Gate criteria:**
- [x] All unit tests pass (`uv run pytest`)
- [x] `POST /turn` returns a structured JSON response (stub data)
- [x] Frontend dev server loads in browser without errors (`npm run dev`)

**Sign-off:**
- Date: 2026-04-19
- Tester: oldhat86@gmail.com
- Notes: All gate criteria met. No issues observed.

---

## Phase 1 — Voice Pipeline MVP

**Gate criteria:**
- [x] All tests pass (21 backend, 12 frontend)
- [x] Whisper transcribes spoken Spanish with acceptable accuracy
- [x] `TurnError` test passes: bad audio returns structured error, no uncaught exception
- [x] Manual smoke: speak "Hola, ¿cómo estás?" → transcript visible → browser speaks echo back

**Sign-off:**
- Date: 2026-04-19
- Tester: oldhat86@gmail.com
- Notes: PASSED. MT-1-1 through MT-1-8 all passed. Known issue: Whisper transcript does not always match intended speech precisely (e.g. accent marks dropped, minor word substitutions). Accuracy is acceptable for MVP pipeline validation.

---

## Phase 2 — AI Conversation Core

**Gate criteria:**
- [x] All required tests pass (36 backend, 12 frontend; live API-key-gated checks excluded from the required gate)
- [x] Claude responds in Spanish at the selected level
- [x] Conversation history is maintained across turns
- [x] Manual smoke: full Spanish conversation exchange completes without error

**Sign-off:**
- Date: 2026-04-20
- Tester: oldhat86@gmail.com
- Notes: PASSED. MT-2-1 through MT-2-7 all passed. Claude responds in Spanish at level 5, conversation context maintained across turns, coach does not spontaneously correct in on_demand mode, and curl structure/error tests passed.

---

## Phase 3 — Coaching Layer

**Gate criteria:**
- [x] All required tests pass (56 backend, 19 frontend — verified 2026-04-21; live API-key-gated checks excluded from the required gate)
- [x] `explicit` mode: auto-corrects clear errors; overlay displays original → corrected + explanation
- [x] `on_demand` mode: corrections surface only when user says "Corrígeme" / trigger phrase
- [x] `shadowing` mode: no overlay; coach naturally weaves correct form into reply
- [x] Coaching mode change starts a new session (transcript and overlay clear)
- [x] Manual smoke: deliberate grammar error → correct overlay per mode; fluent turn → no spurious overlay

**Sign-off:**
- Date: 2026-04-21
- Tester: oldhat86@gmail.com
- Notes: PASSED. MT-3-1 through MT-3-8 all passed. MT-3-8 (curl structure test) requires running from repo root — `tests/fixtures/hola_sample.wav` path is relative to project root, not `frontend/`. All three coaching modes verified. MVP complete.

---

## Phase 4 — Session Config UI

**Gate criteria:**
- [x] All required tests pass (67 backend, 33 frontend — verified 2026-04-21; live API-key-gated checks excluded from the required gate)
- [x] `GET /topics` returns preset topics with `id`, `label`, and Spanish `starter` phrase
- [x] `GET /providers` returns Claude only; OpenAI remains hidden while stubbed
- [x] `POST /session/start` accepts topic, level, AI provider, and coaching mode with validation
- [x] UI exposes topic picker, starter phrase, custom topic input, level slider, provider select, coaching mode, and New Conversation button
- [x] Manual smoke: changing config starts a fresh session and clears transcript/corrections

**Sign-off:**
- Date: 2026-04-21
- Tester: oldhat86@gmail.com
- Notes: PASSED. MT-4-1 through MT-4-8 all passed. Phase 4 session configuration UI verified, including preset starter phrase display and Custom topic behavior. Ready to proceed to Phase 5.

---

## Phase 5 — Persistence & Session History

**Gate criteria:**
- [x] All required tests pass (74 backend, 38 frontend — verified 2026-04-21; live API-key-gated checks excluded from the required gate)
- [x] Session JSON is persisted on `/session/start`
- [x] `GET /sessions` lists saved session summaries
- [x] Full session transcript survives backend restart when using the same `DVC_DATA_DIR`
- [x] Frontend session history can review a saved session
- [x] Audio retention is opt-in with `DVC_SAVE_AUDIO=true`

**Sign-off:**
- Date: 2026-04-21
- Tester: oldhat86@gmail.com
- Notes: PASSED. MT-5-1 through MT-5-6 all passed. Phase 5 persistence and session history verified with explicit manual test `DVC_DATA_DIR`. Ready to proceed to Phase 6.

---

## Phase 6 — ElevenLabs TTS

**Gate criteria:**
- [x] All tests pass (92 backend, 2 skipped; 46 frontend — verified 2026-04-22)
- [x] `/tts-voices` returns 4 curated voice objects
- [x] ElevenLabs TTS produces audibly higher-quality Spanish audio than browser `speechSynthesis`
- [x] Browser TTS fallback still works (no regression)
- [x] TTS failure (missing API key) returns `tts_error`; coach text still displayed; app remains usable
- [x] TTS config (provider + voice) restored correctly when resuming a saved session

**Sign-off:**
- Date: 2026-04-22
- Tester: oldhat86@gmail.com
- Whisper version: 20250625
- Claude model: claude-sonnet-4-6
- Notes: PASSED. MT-6-1 through MT-6-7 all passed. MT-6-4 required fixing the Vite proxy (`/tts-voices` was missing) — voice dropdown was null until proxy was added and dev server restarted. MT-6-6 (missing API key) correctly returns `tts_error` with CUDA/FP16 warnings present but benign (CPU-only machine). Ready to proceed to Phase 7.
