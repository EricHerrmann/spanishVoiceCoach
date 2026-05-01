# duoVoiceCoach — Project Status

**Last updated:** 2026-05-01  
**Branch:** main

---

## Current Focus

Project layer: desktop app stable, cloud deployment signed off, and Phase 11 (Windows Docker packaging) is the active epoch-level focus.

Feature layer: AI model/provider selection has shifted from a narrow single-provider path to a broader selectable surface. The app now exposes `claude`, `openai`, `google`, `deepseek`, and `groq` with provider-specific model choices. Routing, persistence, UI flow, and mocked/provider-path integration coverage were expanded to match that wider surface.

Support-state note: the widened provider surface should no longer be treated as a narrow MVP-only path. Validation expectations have increased accordingly. Live provider-matrix turn validation is still the main remaining confidence gap before treating the newly selectable providers as fully supported at the same level as the original Claude path.

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
| 10 | Cloud Deployment | Complete | Signed off 2026-05-01 |
| 11 | Windows 11 Packaging | In progress | Compose/doc/manual-test path added; Windows smoke test pending |
| 12 | Mobile Capability | Obsolete | Covered by Fly.io deployment and earlier mobile phases; remaining issue moved to Phase 13 |
| 13 | Feature Expansion | Not started | Provider/model selection broadened at feature layer; support-level validation still evolving |

### Code Review Plan (R1–R6)

All six findings from `docs/codexCodeReview.md` implemented and merged 2026-04-28. See `docs/claudeCodeImplementationPlan.md` for details.

---

## Test Counts

As of 2026-05-01:

| Suite | Passed | Skipped |
|-------|--------|---------|
| Backend (`uv run pytest`) | 180 | 6 |
| Frontend (`npm test -- --run`) | 149 | 0 |
| Lint (`npm run lint`) | clean | — |

Clarifying note: current counts cover the expanded multi-provider selection flow through unit, mocked integration, and routing/persistence/UI tests. They do not yet prove live full-turn behavior across the full newly selectable provider matrix.

---

## Open Items

- Phase 11: Windows 11 Docker smoke test and gate sign-off
- Phase 13 feature: Mobile Corrections UX so corrections remain discoverable when the mobile drawer is closed
- AI provider matrix: live full-turn validation still needed for the newly selectable non-Claude providers before they should be treated as fully supported production-equivalent paths

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
