# Initial Plan Review

## Scope Reviewed

- `SpanishConversationCoachGoals.md`
- `codexSpanishCoachPlan.md`
- `claudeSpanishCoachPlan.md`
- `docs/specs/2026-04-15-phase0-sprint-backlog.md`
- `docs/superpowers/specs/2026-04-15-spanish-coach-design.md`

## Findings

### 1. Critical: the plan set does not converge on a single baseline architecture

The biggest issue is not lack of detail. It is conflicting detail.

- `codexSpanishCoachPlan.md:29-36` chooses a desktop/browser MVP, managed STT/TTS/LLM services, SQLite, and a `src/backend` + `src/frontend` structure.
- `claudeSpanishCoachPlan.md:34-40` and `docs/superpowers/specs/2026-04-15-spanish-coach-design.md:33-43` choose local Whisper, browser TTS, Anthropic-first AI, and a root-level `backend/` + `frontend/` layout.
- `claudeSpanishCoachPlan.md:262-273` chooses local JSON persistence, which conflicts with the SQLite direction in `codexSpanishCoachPlan.md:34` and `codexSpanishCoachPlan.md:189`.

Why this matters:
- Repo scaffolding will diverge immediately depending on which document is treated as authoritative.
- Provider interfaces, persistence shape, and even test setup will be different from day one.
- Phase 0 cannot be "done" until one baseline is selected.

Recommendation:
- Choose one canonical architecture document before any scaffolding starts.
- Keep the other plan as a reference, not as an equally valid implementation path.

### 2. High: the Claude plan delays core user-facing configuration too long

The user explicitly wants topic and level control early. The Codex plan reflects that in MVP scope and core flow.

- `codexSpanishCoachPlan.md:62-78` includes topic, level, and mode in MVP scope.
- `codexSpanishCoachPlan.md:118-143` makes topic/level selection part of the primary session flow.
- `claudeSpanishCoachPlan.md:239-251` postpones full session configuration UI to Phase 4, after MVP is already declared complete in `claudeSpanishCoachPlan.md:233-235`.

This creates a product mismatch:
- the implementation plan reaches "MVP complete" before exposing one of the user's key requested controls
- Phase 2 smoke tests already assume topic and level exist in practice at `claudeSpanishCoachPlan.md:205`, so the phase order is internally inconsistent

Recommendation:
- Move topic, level, and coaching mode selection into Phase 1 or 2, not Phase 4.
- Treat session setup as part of the first usable MVP, not post-MVP polish.

### 3. High: the session and turn contracts are too thin in the Claude plan and design spec

The detailed design has a clean high-level model, but it is missing fields needed for observability, evaluation, and prompt regression analysis.

- `claudeSpanishCoachPlan.md:103-127` and `docs/superpowers/specs/2026-04-15-spanish-coach-design.md:103-127` define `Session`, `Turn`, and `Correction`.
- `docs/specs/2026-04-15-phase0-sprint-backlog.md:122-159` correctly requires normalized transcript, audio metadata, prompt/policy version, coaching metadata, and error state.
- `codexSpanishCoachPlan.md:147-151` also requires timestamps, prompt version, transcript, response metadata, and privacy controls.

Current gap:
- no raw transcript vs normalized transcript distinction
- no latency fields
- no provider metadata
- no prompt version
- no turn error state
- no explicit session summary object

Why this matters:
- you will not be able to diagnose STT failures, prompt drift, or latency regressions cleanly
- later personalization and evaluation features will need schema changes that could have been avoided in Phase 0

Recommendation:
- Promote the backlog contract requirements into the canonical design spec before implementation.

### 4. High: AI output structure and correction extraction are under-specified

The design assumes the AI can return coach text plus correction metadata, but it never defines a strict output contract.

- `docs/superpowers/specs/2026-04-15-spanish-coach-design.md:57-63` describes a JSON response from the backend, but not a required structured response from the model.
- `claudeSpanishCoachPlan.md:221-224` says correction metadata will be parsed from Claude output.
- `docs/specs/2026-04-15-phase0-sprint-backlog.md:143-159` explicitly calls for prompt responsibilities, expected outputs, constraints, and failure handling.

Risk:
- correction parsing will be brittle if the model output format is informal
- support for multiple coaching modes will become prompt-coupled rather than contract-driven
- test fixtures will be hard to stabilize

Recommendation:
- Define a model output schema in Phase 0.
- Separate:
  - conversational reply text
  - correction objects
  - explanation text
  - session summary output

### 5. Medium: speech provider choices are plausible, but the risk profile is not resolved

The Claude plan and design spec pick local Whisper plus browser `speechSynthesis`. That is concrete, but not yet justified against the desktop Linux/WSL2 context and later Android goal.

- `docs/superpowers/specs/2026-04-15-spanish-coach-design.md:17-20` notes desktop Linux/WSL2 as the primary environment.
- `claudeSpanishCoachPlan.md:37-38` and `docs/superpowers/specs/2026-04-15-spanish-coach-design.md:196-199` choose Whisper and browser TTS.
- `codexSpanishCoachPlan.md:32` and `codexSpanishCoachPlan.md:190-192` prefer managed providers behind adapters specifically to reduce infra and speech-quality risk.
- `docs/specs/2026-04-15-phase0-sprint-backlog.md:179-193` correctly calls for a provider decision memo, which has not yet been written.

Pros of the Claude/design choice:
- concrete and immediately buildable
- low cash cost for the first prototype
- good local control

Cons:
- browser TTS quality on Linux can be weak or inconsistent
- local Whisper may be slower than expected on the target machine
- the Android path may force a provider rethink later

Recommendation:
- do not lock this in as "approved" until a provider memo and latency test exist
- keep adapter boundaries, but treat the speech stack as a pending decision

### 6. Medium: the testing strategy is strong in spirit, but inconsistent in execution

The documents are right to require tests plus manual smoke sign-off. The problem is determinism.

- `claudeSpanishCoachPlan.md:26` requires a passing test suite and manual sign-off at every phase gate.
- `docs/superpowers/specs/2026-04-15-spanish-coach-design.md:209-214` leans on fixture-based tests and integration coverage.
- `claudeSpanishCoachPlan.md:332` says not to mock the AI provider in integration tests and to use the real Claude API.

Problems with that choice:
- network/API flakiness will make phase gates noisy
- test cost becomes variable
- provider output drift can fail tests without any code regression

Recommendation:
- required integration tests should use deterministic fixtures or recorded responses
- real-provider tests should be smoke tests or optional gated checks, not mandatory CI blockers

### 7. Medium: all plans still underspecify learning efficacy measurement

The plans define product behavior well enough to build, but not well enough to know if the coach is genuinely improving conversational skill.

Strengths already present:
- `codexSpanishCoachPlan.md:147-151` sets latency, reliability, and logging expectations
- `codexSpanishCoachPlan.md:422-426` adds initial success metrics
- `claudeSpanishCoachPlan.md:26` and `docs/superpowers/specs/2026-04-15-spanish-coach-design.md:221-226` require manual sign-off

Remaining gap:
- no explicit rubric for "difficulty fit"
- no measure of conversation continuity versus over-correction
- no criterion for whether the learner understood the coach's spoken Spanish
- no early benchmark tasks that can be repeated across sprints

Recommendation:
- define 3-5 repeatable benchmark scenarios and a manual rubric before building too far past Phase 2

## Plan-by-Plan Pros and Cons

### `codexSpanishCoachPlan.md`

Pros:
- strongest product framing and user alignment
- clearly separates MVP scope from later expansion
- includes privacy, observability, and evaluation concerns early
- phases for prompt hardening and Android-ready API boundaries are well judged

Cons:
- less executable as an implementation checklist
- repo structure conflicts with the Claude/design documents
- provider strategy is prudent but still abstract

Best use:
- primary product and architecture direction document

### `docs/specs/2026-04-15-phase0-sprint-backlog.md`

Pros:
- best operational artifact in the repo right now
- turns ambiguity into acceptance criteria
- correctly identifies session/turn contracts and prompt contracts as Phase 0 blockers
- strong sequencing from discovery into Sprint 1

Cons:
- inherits unresolved architecture conflicts from the parent plans
- depends on documents that do not yet exist

Best use:
- working backlog for Phase 0 after a canonical architecture is selected

### `claudeSpanishCoachPlan.md`

Pros:
- most implementation-ready phased checklist
- strong phase gates and testing discipline
- good instinct to abstract AI and TTS providers early
- realistic emphasis on voice UX rather than a generic chat UI

Cons:
- phase order conflicts with the user's need for early topic/level control
- overcommits to local Whisper + browser TTS before the provider decision is actually closed
- JSON persistence conflicts with SQLite direction
- integration testing strategy is likely to be flaky and expensive
- data contracts are too thin for later evaluation and debugging

Best use:
- secondary implementation reference after its sequencing and contract gaps are corrected

### `docs/superpowers/specs/2026-04-15-spanish-coach-design.md`

Pros:
- concise and readable
- good high-level architecture and per-turn flow
- aligned with the Claude implementation concept
- useful as a short design handoff document

Cons:
- too many major decisions are marked as settled even though cross-plan conflicts remain
- duplicates the Claude plan more than it resolves open questions
- lacks the strict schema, fallback, privacy, and evaluation detail needed to be the final source of truth

Best use:
- design brief, not final implementation authority

## Gap Analysis

### Shared gaps across the current document set

- No single canonical source of truth.
- No final provider memo for STT, TTS, and LLM.
- No final session/turn/API contract document.
- No strict model output schema for corrections and summaries.
- No agreed persistence baseline.
- No benchmark evaluation rubric for conversational improvement.

### Gaps specifically between product intent and implementation detail

- Topic and level control are central in the goals, but not early enough in the Claude phase plan.
- Transcript support is central in the goals, but transcript quality, normalization, and correction display contracts are not yet locked down.
- Android is a future goal, but the current plan set does not yet define which parts must stay mobile-safe from day one.

## Recommended Synthesis

Use `codexSpanishCoachPlan.md` as the primary product and architecture plan, and use `docs/specs/2026-04-15-phase0-sprint-backlog.md` as the execution backlog.

Before implementation starts, revise the Claude plan and the superpowers design so they conform to that baseline:

1. Pick one project structure and one persistence approach.
2. Move session setup and topic/level/mode selection into the actual MVP path.
3. Add the missing session/turn fields required for logging and evaluation.
4. Define a strict structured output contract for coach replies, corrections, and summaries.
5. Replace required live-provider integration tests with deterministic tests plus optional smoke checks.
6. Write the missing provider decision memo before locking Whisper/browser TTS as approved.

## Bottom Line

The planning work is good enough to proceed, but not good enough to scaffold against without rework.

The Codex plan is the best product-level foundation. The sprint backlog is the best execution artifact. The Claude plan and superpowers design are useful, but they should be treated as a candidate implementation path that still needs normalization against the product plan before Phase 0 begins.
