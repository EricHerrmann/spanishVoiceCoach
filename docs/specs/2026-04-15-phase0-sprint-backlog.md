# Spanish Coach — Phase 0 Sprint Backlog

## Purpose

Translate Phase 0 of `codexSpanishCoachPlan.md` into sprint-ready work with explicit user stories, acceptance criteria, and sequencing.

This backlog assumes:
- the product starts as a desktop/browser MVP
- Phase 0 is a design-and-contract sprint, not a production feature sprint
- Sprint 1 begins implementation of the voice loop immediately after Phase 0 exit criteria are met

## Planning Assumptions

- Sprint length: 1 week for Sprint 0, 1-2 weeks for Sprint 1
- Team shape: one primary builder, AI-assisted development, lightweight review process
- Delivery standard:
  - every story has acceptance criteria
  - design decisions are written down
  - unresolved provider choices are narrowed before implementation starts

## Sprint Structure

| Sprint | Goal | Primary output |
|--------|------|----------------|
| Sprint 0 | Remove product and architecture ambiguity | product spec, contracts, wireframes, test checklist |
| Sprint 1 | Prove the first end-to-end voice loop | mic -> STT -> coach -> TTS -> transcript |

## Phase 0 Exit Gate

Phase 0 is complete only when all of the following are true:

- MVP setup flow is defined clearly enough to build without inventing UX mid-implementation.
- Session and turn contracts are written and stable enough for backend and frontend work.
- Prompt responsibilities are separated into conversation, coaching, and summary concerns.
- A provider strategy exists for STT, TTS, and LLM, even if final vendors may change later.
- Manual test coverage exists for the first real spoken sessions.

## Sprint 0 — Discovery, Contracts, Wireframes

### Sprint goal

Produce the minimum set of decisions and artifacts needed to start Sprint 1 without major product ambiguity.

### Sprint deliverables

- MVP product spec
- initial scenario catalog
- level/topic taxonomy
- session and turn data contracts
- prompt contract outline
- low-fidelity wireframes
- provider decision memo
- manual test checklist

### Sprint 0 backlog summary

| ID | Story | Priority | Estimate |
|----|-------|----------|----------|
| SC-001 | Define the core practice scenarios | Must | S |
| SC-002 | Define level bands and topic taxonomy | Must | S |
| SC-003 | Decide the MVP interaction model | Must | S |
| SC-004 | Define session and turn contracts | Must | M |
| SC-005 | Define prompt responsibilities and outputs | Must | M |
| SC-006 | Produce low-fidelity wireframes | Must | M |
| SC-007 | Choose the MVP provider strategy | Must | M |
| SC-008 | Create a manual test checklist for first spoken sessions | Must | S |
| SC-009 | Build Sprint 1 implementation backlog | Should | S |

### Stories

#### SC-001 — Define the core practice scenarios

**User story:** As the learner, I want the coach to support realistic conversation scenarios so practice feels useful and appropriately scoped.

**Acceptance criteria:**
- 5 initial scenarios are documented.
- Each scenario includes:
  - user goal
  - conversation mode
  - target level band
  - example prompts
  - failure cases to watch for
- The scenario list includes at least:
  - introductions
  - ordering food
  - asking directions
  - daily conversation
  - work conversation

**Notes:** This story anchors prompt design and the first topic catalog.

#### SC-002 — Define level bands and topic taxonomy

**User story:** As the learner, I want the app to speak at a level I can handle so I stay challenged without being overwhelmed.

**Acceptance criteria:**
- 4 initial level bands are defined.
- Each level band includes:
  - vocabulary complexity guidance
  - expected sentence length
  - coach pacing rule
  - acceptable English support rule
- Topics are grouped into a first-pass taxonomy usable by the setup screen.

**Notes:** Keep the level model coarse. Do not overfit before real sessions exist.

#### SC-003 — Decide the MVP interaction model

**User story:** As the learner, I want a clear speaking interaction model so I know when to talk and how the app listens.

**Acceptance criteria:**
- The MVP decision between `push-to-talk`, `auto-VAD`, or `hybrid` is documented.
- The chosen model includes:
  - why it was chosen
  - expected UX tradeoffs
  - how interruptions are handled
  - what fallback is available if detection is unreliable
- The decision is reflected in the Sprint 1 backlog.

**Recommended default:** `push-to-talk` for MVP, with auto-VAD explicitly deferred unless testing proves it reliable enough.

#### SC-004 — Define session and turn contracts

**User story:** As a developer, I want stable session and turn contracts so frontend and backend work can proceed without guesswork.

**Acceptance criteria:**
- A `session` object is documented with required fields.
- A `turn` object is documented with required fields.
- The contract includes:
  - identifiers
  - timestamps
  - user transcript
  - normalized transcript
  - coach response text
  - coaching metadata
  - audio metadata
  - prompt/policy version
  - error state
- The contract distinguishes between live-turn fields and post-session summary fields.

**Notes:** This is a blocker for Sprint 1 API work.

#### SC-005 — Define prompt responsibilities and outputs

**User story:** As a developer, I want prompt responsibilities separated by job so prompt changes are easier to test and reason about.

**Acceptance criteria:**
- Prompt responsibilities are split into at least:
  - coach conversation prompt
  - correction/feedback extractor
  - end-of-session summary prompt
- For each prompt type, the doc defines:
  - required inputs
  - expected outputs
  - constraints
  - failure handling rules
- Prompt versioning expectations are documented.

**Notes:** Do not collapse all behavior into one opaque prompt if the outputs need different structure.

#### SC-006 — Produce low-fidelity wireframes

**User story:** As the learner, I want a simple and predictable interface so I can focus on speaking rather than figuring out the UI.

**Acceptance criteria:**
- Three wireframes exist:
  - setup screen
  - live conversation screen
  - session review screen
- Each wireframe identifies:
  - primary user action
  - visible transcript behavior
  - correction panel behavior
  - session controls
- Wireframes are simple and implementation-oriented, not polished design comps.

**Notes:** This should resolve layout uncertainty before frontend coding begins.

#### SC-007 — Choose the MVP provider strategy

**User story:** As a builder, I want a clear provider strategy so Sprint 1 can integrate speech and model services without re-deciding the stack mid-build.

**Acceptance criteria:**
- STT, TTS, and LLM provider options are listed with a preferred MVP choice.
- The memo includes:
  - selection criteria
  - expected latency concerns
  - cost sensitivity
  - adapter boundary requirements
  - swap risk if a provider underperforms
- The outcome is enough to define provider interfaces in Sprint 1.

**Notes:** The memo does not need procurement-level depth; it needs implementation clarity.

#### SC-008 — Create a manual test checklist for first spoken sessions

**User story:** As a tester, I want a structured manual checklist so early voice-loop defects are caught quickly and repeatably.

**Acceptance criteria:**
- The checklist covers at least:
  - mic permission flow
  - normal spoken answer
  - help request
  - repeated playback
  - misunderstood transcript
  - provider failure
  - session summary generation
- Each test item has an expected result.
- The checklist can be used during Sprint 1 demos.

#### SC-009 — Build Sprint 1 implementation backlog

**User story:** As the builder, I want Sprint 1 broken into executable stories so coding can start immediately after Phase 0 review.

**Acceptance criteria:**
- Sprint 1 stories are written with clear dependencies.
- Each Sprint 1 story maps to an agreed contract or decision from Sprint 0.
- No Sprint 1 story depends on undefined UX or undefined API shape.

## Sprint 1 — Voice Loop Prototype

### Sprint goal

Deliver the first working browser-based voice loop with visible transcript and spoken coach reply.

### Sprint deliverables

- frontend shell
- session bootstrap endpoint
- single-turn conversation endpoint
- STT adapter
- coach adapter
- TTS adapter
- transcript rendering
- latency/error logging

### Sprint 1 backlog summary

| ID | Story | Priority | Estimate | Depends on |
|----|-------|----------|----------|------------|
| SC-101 | Scaffold frontend and backend app shells | Must | M | SC-004 |
| SC-102 | Implement session bootstrap contract | Must | S | SC-004 |
| SC-103 | Add browser microphone capture with push-to-talk | Must | M | SC-003, SC-006 |
| SC-104 | Implement STT adapter and transcript normalization | Must | M | SC-007 |
| SC-105 | Implement coach response endpoint | Must | M | SC-004, SC-005, SC-007 |
| SC-106 | Implement TTS playback path | Must | M | SC-007 |
| SC-107 | Render live transcript and coach response | Must | S | SC-006 |
| SC-108 | Add turn logging and basic error handling | Must | S | SC-004 |
| SC-109 | Run manual voice-loop test pass and capture issues | Must | S | SC-008 |

### Stories

#### SC-101 — Scaffold frontend and backend app shells

**User story:** As a developer, I want a clean app skeleton so voice-loop implementation can proceed without setup churn.

**Acceptance criteria:**
- Backend app starts locally.
- Frontend app starts locally.
- The project structure follows the direction in `codexSpanishCoachPlan.md`.
- A developer can run both services with a short documented command flow.

#### SC-102 — Implement session bootstrap contract

**User story:** As the app, I want to create a session before the first spoken turn so all conversation state is tied to a stable session record.

**Acceptance criteria:**
- The backend can create a session with:
  - topic
  - level
  - mode
  - created timestamp
- The frontend can start a session and receive a session identifier.
- Invalid setup input returns a clear error.

#### SC-103 — Add browser microphone capture with push-to-talk

**User story:** As the learner, I want a clear talk button so I know when the app is listening and can control turn boundaries.

**Acceptance criteria:**
- The user can start and stop recording intentionally.
- Mic permission denial is handled visibly.
- The UI reflects listening, processing, and response states.
- Audio capture is wired into the turn submission flow.

#### SC-104 — Implement STT adapter and transcript normalization

**User story:** As the learner, I want my spoken answer turned into usable text so the coach can respond accurately.

**Acceptance criteria:**
- Recorded audio is sent to the STT adapter.
- A transcript is returned and stored on the turn.
- Basic normalization is applied consistently.
- Provider failure returns a recoverable error to the UI.

#### SC-105 — Implement coach response endpoint

**User story:** As the learner, I want a short Spanish reply that continues the conversation at my chosen level.

**Acceptance criteria:**
- The backend receives the current turn and session context.
- The coach returns:
  - response text
  - lightweight coaching metadata
  - prompt version
- The reply generally respects topic and level rules from Sprint 0.
- The system can distinguish a help request from a normal reply if that behavior was defined in Sprint 0.

#### SC-106 — Implement TTS playback path

**User story:** As the learner, I want to hear the coach reply spoken aloud so I can practice listening as well as reading.

**Acceptance criteria:**
- Coach response text can be converted to speech.
- The frontend can play the returned audio.
- A TTS failure does not destroy the transcript or session state.

#### SC-107 — Render live transcript and coach response

**User story:** As the learner, I want to see what I said and what the coach answered so I can recover from misunderstandings quickly.

**Acceptance criteria:**
- The screen shows:
  - user transcript
  - coach reply text
  - turn status
- The transcript updates after each completed turn.
- The UI supports at least 3 consecutive turns without losing prior context.

#### SC-108 — Add turn logging and basic error handling

**User story:** As the builder, I want turn-level logs so latency and quality issues can be debugged quickly.

**Acceptance criteria:**
- Each turn records:
  - timestamps
  - provider path
  - error status
  - latency fields
  - prompt version
- Error states are visible enough to diagnose failed turns.
- Logging works without exposing unnecessary sensitive content beyond MVP needs.

#### SC-109 — Run manual voice-loop test pass and capture issues

**User story:** As the team, I want a manual validation pass so the first working loop is judged by actual user experience, not just code completion.

**Acceptance criteria:**
- The Sprint 0 manual checklist is run against the prototype.
- Findings are written down.
- The output separates:
  - blockers
  - rough edges
  - later improvements

## Recommended Sprint Ordering

1. Finish SC-001 through SC-005 first. These are the hard blockers for implementation.
2. Run SC-006 and SC-007 in parallel once the product scope is stable.
3. Close Sprint 0 with SC-008 and SC-009 so Sprint 1 starts with both test coverage and implementation clarity.
4. In Sprint 1, build the thin end-to-end loop before refining quality.

## Immediate Next Documents to Create

- `docs/specs/2026-04-15-mvp-product-spec.md`
- `docs/wireframes/2026-04-15-desktop-mvp-wireframes.md`
- `docs/specs/2026-04-15-provider-decision-memo.md`
- `docs/testPlans/2026-04-15-manual-voice-loop-checklist.md`

## Risks if Sprint 0 Is Skipped or Compressed Too Far

- Sprint 1 will stall on unresolved UX questions around turn-taking and help requests.
- Prompt design will become tangled if output contracts are not separated early.
- Provider-specific behavior may leak into product logic.
- The first prototype may technically work but still fail the learning experience because scenarios and level rules were underdefined.
