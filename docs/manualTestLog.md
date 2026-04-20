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
- Notes: PASSED. Known issue: Whisper transcript does not always match intended speech precisely (e.g. accent marks dropped, minor word substitutions). Accuracy is acceptable for MVP pipeline validation. Full transcription quality to be reviewed as development proceeds toward Phase 3.

---

## Phase 2 — AI Conversation Core

**Gate criteria:**
- [ ] All tests pass
- [ ] Claude responds in Spanish at the selected level
- [ ] Conversation history is maintained across turns
- [ ] Manual smoke: full Spanish conversation exchange completes without error

**Sign-off:**
- Date:
- Tester:
- Notes:

---

## Phase 3 — Coaching Layer

**Gate criteria:**
- [ ] All tests pass
- [ ] Hybrid coaching mode active: auto-corrects clear errors, silent otherwise
- [ ] On-demand correction triggered by user request works correctly
- [ ] Coaching toggle switches modes without restarting session
- [ ] Manual smoke: deliberate grammar error → correction appears; fluent turn → no interruption

**Sign-off:**
- Date:
- Tester:
- Notes:
