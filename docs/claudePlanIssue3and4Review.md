# Claude Plan Follow-Up Review: Issues 3 and 4

## Scope

This note assumes `claudeSpanishCoachPlan.md` is the chosen baseline plan.

The goal here is not to compare it against the Codex plan again. The goal is to take issue 3 and issue 4 from `docs/initPlanReviewCodex.md` and translate them into concrete changes that make the Claude plan implementable with less rework.

Relevant source documents:
- `claudeSpanishCoachPlan.md`
- `docs/initPlanReviewCodex.md`
- `docs/superpowers/specs/2026-04-15-spanish-coach-design.md`

## Focus Issue 3

### Problem

Issue 3 in `docs/initPlanReviewCodex.md` is correct: the session and turn contracts in the Claude plan are too thin.

Current Claude plan data model:
- `Session` has only identity, topic/level/provider/mode, and turns
- `Turn` has only speaker, optional audio file, transcript, corrections, and timestamp
- `Correction` has only original, corrected, explanation, and trigger source

This is too minimal for:
- diagnosing STT failures
- distinguishing raw transcript from cleaned transcript
- tracing which prompt/policy produced a response
- tracking latency across STT, LLM, and TTS
- recording recoverable turn errors cleanly
- storing end-of-session summary output without reshaping the model later

### What to change in the Claude plan

The Claude plan should keep its current structure, but its Phase 0 contract work needs to expand.

#### 1. Replace the current Data Model section with a richer contract

Suggested replacement shape:

```python
Session:
  id:                  str
  started_at:          datetime
  completed_at:        datetime | None
  topic:               str
  level:               int
  ai_provider:         str
  coaching_mode:       str
  prompt_version:      str
  policy_version:      str
  turns:               list[Turn]
  latest_summary:      SessionSummary | None
  metadata:            dict | None

Turn:
  id:                  str
  session_id:          str
  index:               int
  speaker:             str                  # "user" | "coach"
  recorded_at:         datetime
  transcript_raw:      str | None
  transcript_norm:     str | None
  coach_text:          str | None
  corrections:         list[Correction]
  help_request:        HelpRequest | None
  provider_trace:      ProviderTrace | None
  latency_ms:          TurnLatency | None
  audio_input:         AudioRef | None
  audio_output:        AudioRef | None
  error:               TurnError | None

Correction:
  source_span:         str | None
  original:            str
  corrected:           str
  explanation:         str
  severity:            str | None
  triggered_by:        str                  # "auto" | "user_request"

SessionSummary:
  strengths:           list[str]
  recurring_issues:    list[str]
  suggested_phrases:   list[str]
  next_steps:          list[str]

ProviderTrace:
  stt_provider:        str
  ai_provider:         str
  tts_provider:        str | None
  model_id:            str | None

TurnLatency:
  stt_ms:              int | None
  ai_ms:               int | None
  tts_ms:              int | None
  total_ms:            int | None

TurnError:
  stage:               str                  # "mic" | "stt" | "ai" | "tts" | "ui"
  code:                str
  message:             str
  recoverable:         bool

AudioRef:
  format:              str | None
  duration_ms:         int | None
  path:                str | None
```

This is still lightweight enough for MVP, but it covers the missing operational fields.

#### 2. Add explicit API contracts in Phase 0

`claudeSpanishCoachPlan.md` currently says `POST /turn` will return structured JSON, but it does not define the payload shape.

Phase 0 should add tasks like:

- [ ] Define `POST /session/start` request/response schema
- [ ] Define `POST /turn` request/response schema
- [ ] Define `GET /sessions/{id}` response schema
- [ ] Define a contract for turn errors and recoverable failures
- [ ] Add serialization tests for the full session and turn schema

#### 3. Move contract coverage into Phase 0 gate criteria

Current Phase 0 gate:
- unit tests pass
- `POST /turn` returns structured JSON
- frontend dev server loads

This is too weak.

Add:
- [ ] Session, turn, correction, and summary schemas are written and tested
- [ ] `POST /turn` response includes provider trace and latency placeholders
- [ ] Turn error contract exists and is exercised by at least one test fixture

### Why this improves the Claude plan

It preserves the current implementation approach while preventing predictable schema churn in Phases 2–5.

Without this change, the Claude plan will likely:
- add ad hoc fields later
- couple debugging to log scraping instead of structured data
- make phase-gate testing harder because failures are not represented consistently

## Focus Issue 4

### Problem

Issue 4 in `docs/initPlanReviewCodex.md` is also correct: the Claude plan assumes structured correction behavior without defining a strict model output contract.

Current Claude plan wording:
- Phase 2 says `CoachSession` will call `ai_provider.chat()`
- Phase 3 says correction metadata will be parsed from Claude output
- the design spec says the backend returns JSON with transcript, coach text, and corrections

The weak point is in the middle:
- what exact structure is Claude expected to return?
- what happens if Claude returns plain text, partial JSON, or mixed formatting?
- how are coaching modes enforced without brittle string parsing?

### What to change in the Claude plan

The Claude plan should explicitly define a typed model-response contract in Phase 0, then wire Phase 2 and 3 around that contract.

#### 1. Define a canonical AI response schema

Suggested Claude output contract:

```python
CoachResponse:
  coach_text: str
  detected_intent: str | None               # "conversation" | "help" | "clarify" | "repeat"
  corrections: list[Correction]
  vocabulary_notes: list[str]
  explanation_text: str | None
  should_end_session: bool
  summary_update: str | None
```

If you want even stricter separation, split it into two model tasks:

- `ConversationResponse`
  - `coach_text`
  - `detected_intent`
  - `should_end_session`

- `FeedbackResponse`
  - `corrections`
  - `vocabulary_notes`
  - `explanation_text`

For MVP, a single `CoachResponse` object is acceptable as long as it is validated before use.

#### 2. Change `AbstractAIProvider.chat()` to return a typed object, not free text

Current plan:
- `backend/ai/base.py` defines `chat()` but does not commit to a validated return type

Recommended change:

```python
class AbstractAIProvider:
    def chat(self, messages: list[Message], system: str) -> CoachResponse:
        raise NotImplementedError
```

The important point is not the Python type annotation itself. The important point is that:
- `claude.py` must parse/validate model output
- `coach.py` should consume a typed response, not parse raw LLM text
- parse failure should become a `TurnError`, not a silent bad turn

#### 3. Rewrite Phase 2 tasks around structured output

Current Phase 2 tasks are too loose. Replace or expand them with:

- [ ] Define `CoachResponse` schema and validation rules
- [ ] Implement `ClaudeProvider` to request structured output and validate it
- [ ] Add fixture tests for valid, partial, and invalid provider responses
- [ ] Make `CoachSession` consume `CoachResponse`, not provider raw text
- [ ] Return a stable backend turn payload even when model validation fails

#### 4. Rewrite Phase 3 tasks to use the validated response schema

Current Phase 3 says:
- parse Claude response for correction metadata

That should become:
- [ ] map validated `CoachResponse.corrections` into UI payloads
- [ ] route `detected_intent` into coaching mode logic
- [ ] support `on_demand`, `explicit`, and `shadowing` using explicit response fields, not text heuristics alone
- [ ] add tests for empty corrections, malformed corrections, and correction-overflow cases

#### 5. Add fallback rules for invalid model output

The Claude plan should define expected backend behavior if the model response is malformed.

Recommended fallback policy:
- if `coach_text` is valid but correction fields fail validation:
  - use `coach_text`
  - drop invalid correction payload
  - record a recoverable parse error
- if the whole response fails validation:
  - return a friendly retry message
  - log a recoverable AI-stage error
  - do not corrupt session history

### Why this improves the Claude plan

This preserves the Claude-first architecture, but removes the most fragile part of the current approach: implicit parsing.

Without this change, Phase 3 is likely to become:
- prompt-tuned string matching
- correction parsing bugs that only appear in live use
- unstable tests because output format drifts over time

With this change:
- provider behavior is explicit
- tests can use deterministic response fixtures
- coaching-mode logic becomes easier to reason about

## Specific Claude Plan Edits Recommended

### Edit 1: expand the Data Model section

Revise `claudeSpanishCoachPlan.md` around the current `## Data Model` section to include:
- `transcript_raw`
- `transcript_norm`
- `coach_text`
- `provider_trace`
- `latency_ms`
- `error`
- `latest_summary`

### Edit 2: strengthen Phase 0

Add these Phase 0 tasks:
- [ ] Define session, turn, error, and summary schemas
- [ ] Define `CoachResponse` schema
- [ ] Add serialization/validation tests for all schemas
- [ ] Define `POST /turn` request/response contract

Add these Phase 0 gate checks:
- [ ] Contract tests pass for valid and invalid turn payloads
- [ ] `POST /turn` stub returns a contract-compliant response

### Edit 3: revise Phase 2

Replace "calls `ai_provider.chat()`" with:
- `CoachSession` builds request context and consumes a validated `CoachResponse`

Add:
- [ ] tests for malformed model output
- [ ] tests for missing corrections
- [ ] tests for mode-specific structured fields

### Edit 4: revise Phase 3

Replace:
- "parse Claude response for correction metadata"

With:
- "map validated `CoachResponse` fields into correction and coaching-mode behavior"

Add:
- [ ] UI tests for empty and multi-correction payloads
- [ ] backend tests for recoverable parse failures

## Bottom Line

If the Claude plan is the chosen implementation path, issue 3 and issue 4 do not require abandoning it. They require tightening it.

The right fix is:
- make the contracts richer in Phase 0
- make the AI response typed and validated in Phase 2
- make Phase 3 consume structured correction data instead of parsing informal LLM output

That keeps the existing Claude plan shape, but removes two of its highest-risk failure points before implementation starts.
