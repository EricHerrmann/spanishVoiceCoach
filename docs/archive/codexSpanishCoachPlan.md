# Spanish Coach — Phased Design & Implementation Plan

## Executive Summary

**Last updated:** 2026-04-15

**Current state:** Project is in pre-MVP planning. Goal statements exist in `SpanishConversationCoachGoals.md`; implementation has not started.

**Primary goal:** Build a voice-first AI Spanish conversation coach that helps a single learner improve real conversational ability through guided speaking practice, correction, and review.

**Delivery approach:** Follow a phased implementation model similar to `neuroDb`: make key architecture decisions early, keep MVP narrow, ship in reviewable increments, and use a lightweight Scrum loop to refine prompts, UX, and evaluation criteria over time.

| Phase | Status | Outcome |
|-------|--------|---------|
| 0 — Discovery, contracts, wireframes | ⏳ Not started | Product spec, UX flows, architecture decisions |
| 1 — Voice loop prototype | ⏳ Not started | Desktop/browser mic -> STT -> coach -> TTS |
| 2 — Guided conversation MVP | ⏳ Not started | Topic/level selection, 5-10 turn sessions |
| 3 — Coaching and review layer | ⏳ Not started | Corrections, explanations, transcript review |
| 4 — Personalization and progress tracking | ⏳ Not started | Session history, recurring mistakes, goals |
| 5 — Evaluation and prompt hardening | ⏳ Not started | Quality gates, latency checks, safety rules |
| 6 — Android-ready backend boundary | ⏳ Not started | Stable APIs and auth/session model |
| 7 — Android beta | ⏳ Not started | Mobile client reusing core APIs |
| 8 — Retention and curriculum expansion | ⏳ Not started | Drills, spaced review, richer scenarios |

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-15 | Desktop/browser-first MVP | Fastest way to validate conversation UX before Android work. |
| 2026-04-15 | Voice-first, transcript-backed product | Speaking is the core job; transcript and text aids reduce frustration. |
| 2026-04-15 | Single-user architecture for MVP | This is a personal coach first, not a multi-tenant SaaS product. |
| 2026-04-15 | Managed STT/TTS/LLM services in MVP | Reduces infra risk and shortens time to useful feedback. |
| 2026-04-15 | FastAPI backend + React web client | Clean separation for later Android reuse while keeping initial delivery simple. |
| 2026-04-15 | SQLite for MVP state and session history | Sufficient for single-user local development and easy to inspect/debug. |
| 2026-04-15 | One coach orchestrator, not a complex multi-agent system | The user problem is turn quality and feedback quality, not agent topology. |
| 2026-04-15 | Android deferred until coaching loop is validated on desktop | Avoid paying the mobile complexity tax before core value is proven. |

## Goal

Build a practical AI Spanish coach that improves spoken conversation ability, not just vocabulary recall or scripted quiz performance.

The product should help the learner:
- practice unstructured spoken Spanish at an appropriate difficulty level
- choose a topic or scenario that feels relevant and manageable
- get help during a conversation when blocked on words or phrasing
- receive clear corrections and short explanations without breaking flow
- review mistakes and useful phrases after each session

## Product Principles

- Speaking first: the main loop is verbal conversation, not flashcards.
- Coaching over grading: feedback should help the user continue, not just mark errors.
- Keep momentum: default responses should be short enough to preserve conversational flow.
- Adjustable difficulty: the user should be able to control topic, pace, and challenge level.
- Transcript as support, not as the main experience: text exists to reinforce listening and speaking.
- Reuse across platforms: the desktop MVP should create the API and UX contracts needed for Android later.

## MVP Scope

### In scope

- Start a conversation session with:
  - topic
  - level
  - mode
- Speak into the microphone and receive:
  - transcription
  - Spanish coach response
  - spoken audio reply
- Allow the learner to ask:
  - "How do I say X?"
  - "What is the right word?"
  - "Can you say that slower?"
- Show the current turn transcript and a lightweight correction panel
- End each session with:
  - corrected phrases
  - key vocabulary
  - 2-3 improvement notes

### Out of scope for MVP

- multi-user support
- payments, subscriptions, or account management beyond basic local identity
- phoneme-level pronunciation scoring
- open-ended long-term memory across all conversations
- polished Android native app
- offline speech recognition
- gamification systems, streaks, or social features

## User and Level Model

### Primary user

A motivated learner with decent app-based progress but weak conversational confidence. The user can often recognize words in context, but struggles to respond fluidly in Spanish without text support.

### Initial level bands

| Band | Label | Typical scope |
|------|-------|---------------|
| 1 | Survival basics | greetings, introductions, simple questions |
| 2 | Daily life | food, routines, shopping, directions |
| 3 | Story and media bridge | describing events, opinions, simple narratives |
| 4 | Work and real-world tasks | meetings, scheduling, explaining needs |

These bands should stay coarse in MVP. Fine-grained leveling can be added after real session data exists.

### Initial conversation modes

- Guided chat: coach asks one question at a time within a chosen topic.
- Roleplay: ordering food, asking directions, making plans, travel, work.
- Help me answer: user says what they want to express; coach helps shape it into Spanish.
- Review mode: replay recent mistakes and try improved answers.

## Functional Specification

### Core user flow

1. User opens the app.
2. User chooses topic, level, and mode.
3. Coach explains the scenario in simple Spanish and starts the conversation.
4. User answers by voice.
5. System transcribes the answer and sends it to the coach orchestrator.
6. Coach decides whether to:
   - continue the conversation
   - give a brief correction
   - answer a help request
   - slow down or simplify
7. Coach responds in Spanish by text and audio.
8. User can open turn details to see:
   - transcript
   - corrected version
   - vocabulary notes
   - short explanation in English when needed
9. Session ends with a summary and recommended next topics.

### Required MVP behaviors

- Default to Spanish for conversation.
- Permit limited English for explanations when the learner is blocked.
- Keep coach replies short unless the user explicitly asks for detail.
- Detect likely help requests and switch into coaching mode without derailing the session.
- Preserve all turns in a session transcript.
- Generate a concise session summary with actionable feedback.

## Non-Functional Requirements

- Median end-to-end turn latency target: under 4 seconds in MVP testing.
- Session reliability target: complete a 10-turn session without crash or lost transcript.
- UX target: user can recover from STT mistakes without restarting the session.
- Logging: every turn should capture timestamps, prompt version, transcript, and response metadata for review.
- Privacy: store only the minimum needed for session history and evaluation; make speech retention configurable.

## Architecture

### High-level flow

```text
Browser/Desktop UI
  -> microphone capture / push-to-talk
  -> speech-to-text service
  -> coach orchestrator
  -> response generator + feedback extractor
  -> text-to-speech service
  -> transcript/review UI
  -> local session store
```

### Core services

- `speech` service: microphone handling, STT requests, transcript normalization
- `coach` service: prompt assembly, conversation state, level/topic adaptation
- `feedback` service: extracts corrections, suggested phrases, and summary notes
- `session` service: persists transcripts, settings, mistakes, and metrics
- `ui` layer: session controls, transcript pane, correction cards, audio playback

### Approved architecture direction

- Backend owns session state, prompt templates, and evaluation hooks.
- Frontend owns mic controls, transcript rendering, and interaction flow.
- Speech and LLM providers should be wrapped behind provider interfaces so they can change without rewriting product logic.
- Prompt and policy versions must be explicit so quality regressions can be traced.

## Recommended Tech Stack

| Layer | Recommendation | Reason |
|-------|----------------|--------|
| Backend | Python 3.12 + FastAPI | Strong fit for AI orchestration, testing, and later mobile API reuse |
| Frontend | React + TypeScript + Vite | Fast iteration for desktop/browser MVP |
| Storage | SQLite | Enough for single-user sessions and evaluation logs |
| Real-time/audio | Web Audio APIs + simple HTTP/streaming endpoints | Lowest-friction MVP path |
| Testing | pytest + Playwright | Good balance for API, logic, and UX validation |
| LLM/STT/TTS | Managed providers behind adapters | Keeps MVP focused on learning UX, not infra |

> Native Android code is intentionally deferred. If the web MVP proves valuable, Phase 7 can use React Native or another Android client against the same backend contracts.

## Table of Contents

1. Project Structure
2. Scrum Delivery Model
3. Phase 0 — Discovery, Contracts, Wireframes
4. Phase 1 — Voice Loop Prototype
5. Phase 2 — Guided Conversation MVP
6. Phase 3 — Coaching and Review Layer
7. Phase 4 — Personalization and Progress Tracking
8. Phase 5 — Evaluation and Prompt Hardening
9. Phase 6 — Android-Ready Backend Boundary
10. Phase 7 — Android Beta
11. Phase 8 — Retention and Curriculum Expansion

## Project Structure

```text
duoVoiceCoach/
├── SpanishConversationCoachGoals.md
├── codexSpanishCoachPlan.md
├── docs/
│   ├── specs/
│   │   └── 2026-04-15-mvp-product-spec.md
│   ├── wireframes/
│   ├── reviews/
│   └── testPlans/
├── src/
│   ├── backend/
│   │   ├── app.py
│   │   ├── api/
│   │   ├── coach/
│   │   ├── speech/
│   │   ├── feedback/
│   │   ├── sessions/
│   │   └── prompts/
│   └── frontend/
│       ├── app/
│       ├── components/
│       ├── features/
│       └── lib/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/
│   ├── run_dev.sh
│   └── seed_topics.py
└── README.md
```

## Scrum Delivery Model

### Sprint cadence

- Use 1-2 week sprints.
- Each sprint should end with:
  - a working demo
  - updated acceptance criteria
  - test notes
  - a short review of what changed in prompts, UX, and metrics

### Backlog structure

- Epic 1: Conversation loop
- Epic 2: Coaching and feedback
- Epic 3: Session memory and progress
- Epic 4: Reliability and evaluation
- Epic 5: Mobile readiness

### Definition of done

- Feature has explicit acceptance criteria.
- Automated tests cover the main happy path.
- Manual test notes exist for voice and UX behavior.
- Prompt/version changes are recorded.
- Latency and failure cases were checked at least once during the sprint.

## Phase 0 — Discovery, Contracts, Wireframes

**Goal:** Turn the current goals into concrete UX flows, architecture choices, and implementation contracts before writing production code.

### Deliverables

- MVP product spec
- conversation mode definitions
- level/topic taxonomy
- wireframes for desktop session flow
- provider decision memo for STT/TTS/LLM
- seed backlog for first 2-3 sprints

### Tasks

- [ ] Define 3-5 core user scenarios:
  - daily conversation
  - ordering food
  - asking directions
  - work conversation
  - blocked-word help request
- [ ] Decide whether MVP interaction is push-to-talk, auto-VAD, or both
- [ ] Define session object and turn object contracts
- [ ] Define prompt templates for:
  - system policy
  - conversation mode
  - feedback extraction
  - session summary
- [ ] Create low-fidelity wireframes for:
  - home/setup screen
  - live conversation screen
  - end-of-session review
- [ ] Create initial manual test checklist

### Exit criteria

- A developer can implement the first voice prototype without major product ambiguity.
- Topics, levels, and session outputs are defined well enough to test with real conversations.

## Phase 1 — Voice Loop Prototype

**Goal:** Prove the core interaction loop on desktop: speak, transcribe, generate coach reply, speak reply back.

### Deliverables

- microphone capture in browser
- STT integration
- simple coach response endpoint
- TTS playback
- visible turn transcript

### Tasks

- [ ] Build basic frontend shell with mic controls
- [ ] Implement backend session bootstrap and single-turn endpoint
- [ ] Add STT adapter and transcript normalization
- [ ] Add coach adapter that produces short Spanish replies
- [ ] Add TTS playback for the reply
- [ ] Log each turn with latency and provider metadata

### Exit criteria

- User can complete at least 3 consecutive spoken turns in one session.
- Transcript, text reply, and audio reply all appear reliably.
- Major latency bottlenecks are known and recorded.

## Phase 2 — Guided Conversation MVP

**Goal:** Deliver the first usable product: topic-selected, level-selected guided conversations with a stable multi-turn flow.

### Deliverables

- topic and level selector
- guided conversation state machine
- 5-10 turn sessions
- basic session summary
- initial topic catalog

### Tasks

- [ ] Implement session setup screen
- [ ] Add topic metadata and starter prompts
- [ ] Add level adaptation rules:
  - vocabulary complexity
  - sentence length
  - reply pace
- [ ] Maintain conversation state across turns
- [ ] Generate session summary with strengths and next steps
- [ ] Add integration tests for session start, turn flow, and summary output

### Exit criteria

- The user can choose a topic and level and finish a full practice session.
- The conversation stays on topic and generally respects selected difficulty.
- The end summary is useful enough to guide the next session.

## Phase 3 — Coaching and Review Layer

**Goal:** Make the product feel like a coach, not just a chatbot.

### Deliverables

- in-turn help requests
- correction cards
- "better way to say it" suggestions
- replay/slow-down support
- transcript review screen

### Tasks

- [ ] Detect help-intent utterances and route them correctly
- [ ] Extract corrected phrasing separate from conversational response
- [ ] Add vocabulary note and explanation fields
- [ ] Add slower-repeat behavior for coach replies
- [ ] Build review screen with turn-by-turn corrections
- [ ] Add manual test plan for interruption, clarification, and recovery cases

### Exit criteria

- User can ask for help mid-session without breaking the conversation.
- Each turn can show a corrected version and short explanation when needed.
- Review screen is useful enough to study after the session.

## Phase 4 — Personalization and Progress Tracking

**Goal:** Make repeated use more valuable by tracking mistakes, preferred topics, and challenge level over time.

### Deliverables

- session history
- recurring mistake tags
- saved vocabulary and phrases
- adaptive topic recommendations
- lightweight learner profile

### Tasks

- [ ] Persist sessions and summaries locally
- [ ] Create a mistake taxonomy:
  - vocabulary gap
  - grammar agreement
  - tense choice
  - word order
  - comprehension breakdown
- [ ] Track repeated errors across sessions
- [ ] Recommend next practice topics based on history
- [ ] Add a learner settings profile for pace, help level, and preferred language for explanations

### Exit criteria

- Returning users can review prior sessions.
- The app can identify at least a few recurring patterns in errors.
- Suggested next steps reflect actual session history, not static content only.

## Phase 5 — Evaluation and Prompt Hardening

**Goal:** Create reliable quality gates before broader use or mobile expansion.

### Deliverables

- conversation test fixtures
- prompt regression checks
- latency dashboard or report
- safety and failure policies
- evaluation rubric for session quality

### Tasks

- [ ] Create representative scripted scenarios for each level band
- [ ] Add automated checks for:
  - reply language
  - excessive verbosity
  - off-topic drift
  - missing correction data
- [ ] Create manual evaluation rubric:
  - conversational naturalness
  - usefulness of corrections
  - difficulty fit
  - encouragement vs interruption balance
- [ ] Record baseline latency and reliability metrics
- [ ] Define fallback behavior when provider calls fail

### Exit criteria

- Prompt and UX regressions can be detected before release.
- The app has clear behavior for STT/TTS/LLM failures.
- Session quality can be evaluated with repeatable criteria.

## Phase 6 — Android-Ready Backend Boundary

**Goal:** Separate product logic from desktop-specific UI assumptions so a mobile client can be added without rewriting the coach.

### Deliverables

- stable session APIs
- auth/session identity approach for non-local use
- mobile-safe payload contracts
- streaming or chunked response strategy

### Tasks

- [ ] Clean up API boundaries between frontend and backend
- [ ] Remove desktop-only assumptions from session state and audio flow
- [ ] Decide how mobile authentication will work
- [ ] Review payload sizes and response timing for mobile networks
- [ ] Add API docs and client contract tests

### Exit criteria

- Core conversation and feedback logic can be consumed by a second client.
- API contracts are stable enough for Android beta development.

## Phase 7 — Android Beta

**Goal:** Deliver an Android client that reuses the validated coach experience from desktop.

### Deliverables

- Android mobile UI for session setup, live conversation, and review
- microphone and playback flow tuned for phone use
- beta test checklist

### Tasks

- [ ] Build Android client against Phase 6 APIs
- [ ] Adapt push-to-talk and playback controls for mobile ergonomics
- [ ] Test network interruptions and background/foreground behavior
- [ ] Validate session review readability on small screens

### Exit criteria

- User can complete a practice session on Android with similar quality to desktop.
- Mobile-specific reliability issues are known and triaged.

## Phase 8 — Retention and Curriculum Expansion

**Goal:** Expand beyond conversation MVP into a durable learning product.

### Deliverables

- spaced review drills
- scenario packs by domain
- personalized vocabulary recycling
- richer analytics and progress views

### Tasks

- [ ] Turn high-value mistakes into review drills
- [ ] Add scenario packs for travel, home, media, work, and social conversation
- [ ] Add progress views that show trend lines across sessions
- [ ] Explore more advanced pronunciation or listening support if still needed

### Exit criteria

- The coach supports repeated use beyond novelty.
- New content improves retention without turning the product into a generic flashcard app.

## Risks and Open Questions

- STT accuracy for learner Spanish may be a major source of frustration; this should be tested early with real speech samples.
- Turn latency can break the conversational feel even if model quality is good.
- Over-correction may make the experience feel like a quiz instead of a conversation.
- Topic difficulty may be harder to control than expected; prompt-only level control may need structured scaffolding.
- Android may require a different audio interaction model than desktop; do not assume direct UI reuse.

## Success Metrics for the First MVP

- User completes at least 3 sessions of 5-10 turns each without major failure.
- Median turn latency stays below the agreed MVP threshold in normal use.
- Session summary identifies useful corrections and next steps.
- The learner reports that the app is more helpful for speaking confidence than passive study alone.
