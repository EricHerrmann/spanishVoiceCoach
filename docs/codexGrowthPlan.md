# Codex Growth Plan

Review date: 2026-04-28

## Executive Summary

The project should not jump straight into more feature branches. The right next move is to finish hardening the product that already exists, especially for mobile/cloud use, and then add features that deepen the coaching loop rather than widening the menu.

Recommended order:
1. Stabilize architecture and quality gates
2. Finish mobile/cloud delivery
3. Improve the coaching UI
4. Add progress tracking and lesson structure
5. Package and share more broadly only after the above is solid

## Phase 1: Stabilization And Hardening

Goal:
- Make the existing product easier to maintain and safer to keep extending

Why first:
- The code review found avoidable duplication and an oversized `backend/main.py`
- Frontend lint is currently failing
- The project is feature-rich enough that future work will become slower unless the structure is cleaned up now

Key work:
- Split `backend/main.py` into route wiring plus service/store modules
- Extract shared frontend hooks for recording and playback
- Fix frontend lint errors and adjust ESLint config for test files
- Add one standard validation command set and use it consistently:
  - backend tests
  - frontend tests
  - frontend lint
- Clean repo hygiene around generated artifacts and tracked cache output
- Update the main phase summary so it matches the code and manual log

Exit criteria:
- `uv run pytest` passes
- `npm test -- --run` passes
- `npm run lint` passes
- docs and manual log agree on current phase state

## Phase 2: Finish Mobile And Cloud Delivery

Goal:
- Turn the current desktop-first app into a reliable multi-device app

Why next:
- The original goals include eventual Android use
- Cloud deployment is partially implemented already, so there is an obvious open gate to close

Key work:
- Complete a real Android end-to-end smoke test on the deployed app
- Verify session persistence across redeploy on the Fly volume
- Add latency logging for STT, AI, and TTS so mobile performance can be measured
- Add clearer UI states for recording, processing, playback, and network failure
- Improve microphone permission and retry messaging for Android Chrome
- Review cold-start behavior and decide whether the Fly app should stay warm

UI improvements in this phase:
- Transcript auto-scroll with a visible "jump to latest" affordance
- Stronger loading/progress states during STT and AI waits
- Better mobile drawer behavior for tools and history
- Larger and more obvious record/stop affordances on narrow screens

Exit criteria:
- deployed Android session fully works
- redeploy persistence is verified
- mobile latency is measured and documented

## Phase 3: Coaching UI Improvement Phase

Goal:
- Make the coaching experience feel more intentional and less like a collection of separate tools

Why here:
- The core features exist, but the user experience can do more to guide practice and surface useful feedback

Recommended UI improvements:
- Replace the transient corrections-only overlay with two layers:
  - a short-lived "this turn" correction card
  - a persistent session-side correction list
- Add an end-of-session recap card:
  - strongest phrases
  - corrections worth reviewing
  - suggested next topic or level
- Improve the session setup panel so it reads more like a lesson composer than a settings form
- Show the current topic, level band, and coaching mode more prominently during the conversation
- Add a visible "practice this phrase" or "save this phrase" action for coach turns and corrected user turns
- Make flashcard and pronunciation handoffs feel native to the conversation instead of separate modes

Feature additions worth considering in this phase:
- save favorite phrases
- quick replay of recent coach responses
- one-tap "explain that correction more" follow-up

Exit criteria:
- correction feedback is visible beyond the current turn
- session recap exists
- conversation-to-practice transitions feel coherent

## Phase 4: Progress Tracking And Learning Loop

Goal:
- Help the user see improvement over time, not just practice in the moment

Why this is important:
- The current app helps conversation happen, but it does not yet show whether the learner is improving
- This is the biggest product gap relative to long-term usefulness

Recommended features:
- correction categories on each correction object
- progress dashboard:
  - most frequent correction types
  - phrases or words repeatedly missed
  - sessions per week
  - topic coverage over time
- personalized flashcard queue generated from actual mistakes
- "review before next conversation" list
- session difficulty trend based on topic, level, and correction rate

Implementation note:
- Add structure to correction metadata before building the dashboard

Exit criteria:
- user can answer "what am I improving at?" from the UI
- dashboard uses real stored session data, not placeholder analytics

## Phase 5: Structured Lessons And Guided Paths

Goal:
- Add a second learning mode that complements freeform conversation

Why this should come after progress tracking:
- Once the app knows where the learner struggles, it can guide them more effectively

Recommended features:
- lesson mode beside free conversation mode
- topic-specific guided steps by level band
- completion markers for lesson steps
- recommendation engine for the next lesson based on recent corrections
- reusable challenge packs for travel, food, work, and everyday conversation

UI improvements in this phase:
- step indicator during guided sessions
- clear distinction between free conversation and guided lesson flows
- lightweight progress markers without turning the app into a cluttered course platform

Exit criteria:
- at least a few topics have reusable lesson paths
- lessons and conversation modes share the same session and transcript model cleanly

## Phase 6: Packaging And Broader Sharing

Goal:
- Make the app easier to run outside the current development environment

Consider this phase only after the earlier ones:
- Windows packaging
- simplified local install
- multi-user or household profile separation
- export of corrections or flashcards

Why last:
- Packaging a moving target increases support cost
- It is better to package a stable coaching product than a fast-changing prototype

## Features To Consider, But Not Before Hardening

- additional AI providers
- deeper offline/PWA behavior
- richer export formats
- social or tutor-sharing features
- advanced pronunciation scoring beyond transcript comparison

These are all reasonable later ideas, but none are more important than closing the current mobile/cloud and maintainability gaps.

## Bottom Line

The project already has enough breadth. The best next phases are the ones that make it faster, cleaner, and more useful as a learning tool: stabilize the code, finish mobile/cloud delivery, improve the coaching UI, then add progress tracking and structured lessons.
