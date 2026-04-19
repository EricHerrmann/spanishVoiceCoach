# duoVoiceCoach — Manual Test Log

Each phase gate requires a smoke-test sign-off entry before the next phase begins.

---

## Phase 0 — Scaffolding & Contracts

**Gate criteria:**
- [ ] All unit tests pass (`uv run pytest`)
- [ ] `POST /turn` returns a structured JSON response (stub data)
- [ ] Frontend dev server loads in browser without errors (`npm run dev`)

**Sign-off:**
- Date:
- Tester:
- Notes:

---

## Phase 1 — Voice Pipeline MVP

**Gate criteria:**
- [ ] All tests pass
- [ ] Whisper transcribes spoken Spanish with acceptable accuracy
- [ ] `TurnError` test passes: bad audio returns structured error, no uncaught exception
- [ ] Manual smoke: speak "Hola, ¿cómo estás?" → transcript visible → browser speaks echo back

**Sign-off:**
- Date:
- Tester:
- Notes:

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
