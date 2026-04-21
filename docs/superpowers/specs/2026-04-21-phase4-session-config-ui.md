# Phase 4 — Session Config UI Design

**Date:** 2026-04-21
**Status:** Approved

## Goal

Expose full session configuration in the UI: topic picker (preset + freeform), level slider, AI provider dropdown, and an explicit "New Conversation" button. Backend gains `/topics` and `/providers` routes and a fully parameterised `/session/start`.

---

## Preset Topics

| ID | Label | Spanish starter phrase |
|----|-------|----------------------|
| `general` | General conversation | Hola, ¿de qué quieres hablar hoy? |
| `ordering_food` | Ordering food | Hola, ¿qué me recomiendas del menú? |
| `directions_transport` | Directions & transport | Disculpe, ¿cómo llego a la estación de metro? |
| `shopping_markets` | Shopping & markets | Buenas, estoy buscando algo de temporada. |
| `work_daily_routine` | Work & daily routine | ¿Cómo fue tu día en el trabajo? |
| `travel_tourism` | Travel & tourism | ¿Qué lugares me recomiendas visitar aquí? |

A "Custom…" option at the end of the topic select reveals a freeform text input. When custom is active, `topic` is whatever the user typed.

---

## Backend

### `GET /topics`

Returns the preset topic list. No auth required.

```json
[
  { "id": "general", "label": "General conversation", "starter": "Hola, ¿de qué quieres hablar hoy?" },
  { "id": "ordering_food", "label": "Ordering food", "starter": "Hola, ¿qué me recomiendas del menú?" },
  ...
]
```

### `GET /providers`

Returns the list of active (fully implemented) AI providers. Hardcoded in `main.py` for now — adding a new provider means adding it here when its implementation is complete.

```json
[{ "id": "claude", "label": "Claude (Anthropic)" }]
```

`OpenAIProvider` is a stub and does **not** appear here.

### `POST /session/start`

Expanded `SessionStartRequest`:

```python
class SessionStartRequest(BaseModel):
    topic: str = "general"
    level: int = Field(default=5, ge=1, le=10)
    ai_provider: Literal["claude"] = "claude"
    coaching_mode: Literal["on_demand", "explicit", "shadowing"] = "on_demand"
```

Removes the existing TODO comment. All fields have validated defaults so existing callers (curl tests without a full body) continue to work.

**All three routes live in `backend/main.py`. No new files.**

---

## Frontend

### `useVoice` refactor

`useVoice` becomes a zero-parameter hook. The `coachingMode` parameter and its `useEffect` dependency are removed. A `newSession(config)` function is exposed:

```js
const { state, turns, corrections, error, startRecording, stopRecording, newSession } = useVoice()
```

`newSession(config)`:
- Cancels any inflight `/session/start` request via `AbortController`
- Resets `turns`, `corrections`, `error` to empty/null
- POSTs to `/session/start` with `{ topic, level, ai_provider, coaching_mode }`
- Stores the returned `session_id` in `sessionIdRef`

---

### `SessionConfig` component

**Props:** `config`, `onConfigChange`, `topics`, `providers`, `onNewSession`, `state`

**Controls (top to bottom):**

1. **Topic select** — options from `topics` prop + a final "Custom…" option (`value="custom"`). Selecting custom reveals a text input beneath the select. `onConfigChange({ topic })` fires on change.
2. **Level slider** — `<input type="range" min="1" max="10">`. Band labels row beneath: *1–2 Beginner · 3–4 Elementary · 5–6 Intermediate · 7–10 Advanced*. `onConfigChange({ level: Number(e.target.value) })` fires on change.
3. **Provider select** — options from `providers` prop (Claude only for now).
4. **Coaching mode select** — existing three options, unchanged.
5. **"New Conversation" button** — calls `onNewSession()`. Disabled when `state !== 'idle'`.

---

### `App.jsx`

```js
const [topics, setTopics] = useState([])
const [providers, setProviders] = useState([])
const [config, setConfig] = useState({
  topic: 'general', level: 5, ai_provider: 'claude', coaching_mode: 'on_demand'
})
const { state, turns, corrections, error, startRecording, stopRecording, newSession } = useVoice()
```

- Two fetch `useEffect`s on mount: one for `/topics`, one for `/providers`.
- One `useEffect([], [])` calls `newSession(config)` to start the initial session.
- `onConfigChange = (patch) => setConfig(prev => ({ ...prev, ...patch }))`
- `onNewSession = () => newSession(config)`

`VoiceButton`, `CoachOverlay`, and `Transcript` are unchanged.

---

## Testing

### Backend (pytest)

- `TestGetTopics` — response is a list; each item has `id`, `label`, `starter`; `general` is present.
- `TestGetProviders` — response is a list; `claude` entry present; `openai` not present.
- `TestSessionStart` (existing class) — add cases: full body accepted; `level` out of range (0, 11) returns 422; unknown `ai_provider` returns 422.

### Frontend (Vitest)

New `SessionConfig` tests:
- Topic select renders all preset options plus "Custom…".
- Selecting "Custom…" reveals a text input.
- Level slider renders with `min="1"` and `max="10"`.
- Provider select renders with Claude option.
- "New Conversation" button calls `onNewSession`.
- Button is disabled when `state` is not `'idle'`.

Existing `SessionConfig` tests (coaching mode) remain valid — coaching mode select is unchanged.

---

## What Is Not In Scope

- Saving config preferences across page reloads (Phase 5+)
- Level recommendations per topic
- OpenAI provider appearing in UI
- Any changes to `VoiceButton`, `CoachOverlay`, or `Transcript`
