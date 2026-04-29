# duoVoiceCoach — Project Status

**Last updated:** 2026-04-28  
**Branch:** main

---

## Current Focus

Phase 10 cloud deployment is partially live (app at `https://spanishcoach.fly.dev`); two manual gate checks remain (Android session end-to-end + persistence across redeploy). Phase 11 (Windows Docker packaging) and Phase 12 (mobile corrections visibility) are next in queue after Phase 10 gate closes.

---

## Phase Status

| Phase | Name | Status | Gate |
|-------|------|--------|------|
| 0 | Scaffolding & Contracts | Complete | Signed off 2026-04-19 |
| 1 | Voice Pipeline MVP | Complete | Signed off 2026-04-19 |
| 2 | AI Conversation Core | Complete | Signed off 2026-04-20 |
| 3 | Coaching Layer (MVP) | Complete | Signed off 2026-04-21 |
| 4 | Session Config UI | Complete | Signed off 2026-04-21 |
| 5 | Persistence & Session History | Complete | Signed off 2026-04-21 |
| 6 | ElevenLabs TTS | Complete | Signed off 2026-04-22 |
| 7 | Android / PWA | Complete | Signed off 2026-04-28 |
| 8 | Code Review & Refactor | Complete | Signed off 2026-04-22 |
| 9 | GUI Layout Redesign | Complete | Signed off 2026-04-23 |
| A | Flashcards + Translation | Complete | Signed off 2026-04-25 |
| B | Pronunciation Practice | Complete | Signed off 2026-04-25 |
| 10 | Cloud Deployment | Partial | App live; Android session + persistence checks pending |
| 11 | Windows 11 Packaging | Not started | Blocked on Phase 7 gate |
| 12 | Mobile Capability | Not started | Queued |
| 13 | Feature Expansion | Not started | Queued |

### Code Review Plan (R1–R6)

All six findings from `docs/codexCodeReview.md` implemented and merged 2026-04-28. See `docs/claudeCodeImplementationPlan.md` for details.

---

## Test Counts

As of 2026-04-28 (post R1–R6 merge):

| Suite | Passed | Skipped |
|-------|--------|---------|
| Backend (`uv run pytest`) | 175 | 6 |
| Frontend (`npm test -- --run`) | 147 | 0 |
| Lint (`npm run lint`) | clean | — |

---

## Open Items

- Phase 10: Android voice session end-to-end + session persistence across redeploy
- Phase 11: Docker Compose packaging for Windows 11
- Phase 12: CoachOverlay visibility in mobile drawer when drawer is closed

---

## Source Documents

| Document | Purpose |
|----------|---------|
| `SpanishConversationCoachGoals.md` | Goals, motivation, success criteria |
| `claudeSpanishCoachPlan.md` | Full phase plan, data model, gate criteria, task checklists |
| `docs/claudeCodeImplementationPlan.md` | R1–R6 code review refactor plan and phase gates |
| `docs/codexCodeReview.md` | Codex review that originated R1–R6 |
| `docs/manualTestLog.md` | Smoke-test sign-offs per phase |
| `.env.example` | All environment variable documentation |
