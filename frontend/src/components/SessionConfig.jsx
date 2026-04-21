import { useState } from 'react'

export default function SessionConfig({ config, onConfigChange, topics, providers, onNewSession, state }) {
  const isKnownTopic = topics.some((t) => t.id === config.topic)
  const [customSelected, setCustomSelected] = useState(false)
  const showCustomInput = customSelected || (topics.length > 0 && !isKnownTopic && config.topic !== '')
  const selectedTopic = topics.find((t) => t.id === config.topic)

  const topicSelectValue = showCustomInput ? 'custom' : config.topic

  function handleTopicChange(e) {
    if (e.target.value === 'custom') {
      setCustomSelected(true)
      onConfigChange({ topic: '' })
    } else {
      setCustomSelected(false)
      onConfigChange({ topic: e.target.value })
    }
  }

  return (
    <div className="session-config">
      <div className="session-config-field">
        <label htmlFor="topic">Topic</label>
        <select
          id="topic"
          value={topicSelectValue}
          onChange={handleTopicChange}
        >
          {topics.map((t) => (
            <option key={t.id} value={t.id}>{t.label}</option>
          ))}
          <option value="custom">Custom…</option>
        </select>
        {showCustomInput && (
          <input
            type="text"
            placeholder="Enter a topic"
            value={config.topic}
            onChange={(e) => onConfigChange({ topic: e.target.value })}
          />
        )}
        {!showCustomInput && selectedTopic?.starter && (
          <p className="topic-starter">{selectedTopic.starter}</p>
        )}
      </div>

      <div className="session-config-field">
        <label htmlFor="level">Level: {config.level}</label>
        <input
          id="level"
          type="range"
          min="1"
          max="10"
          value={config.level}
          onChange={(e) => onConfigChange({ level: Number(e.target.value) })}
        />
        <div className="level-bands">
          <span>1–2 Beginner</span>
          <span>3–4 Elementary</span>
          <span>5–6 Intermediate</span>
          <span>7–10 Advanced</span>
        </div>
      </div>

      <div className="session-config-field">
        <label htmlFor="ai-provider">Provider</label>
        <select
          id="ai-provider"
          value={config.ai_provider}
          onChange={(e) => onConfigChange({ ai_provider: e.target.value })}
        >
          {providers.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
      </div>

      <div className="session-config-field">
        <label htmlFor="coaching-mode">Coaching mode</label>
        <select
          id="coaching-mode"
          value={config.coaching_mode}
          onChange={(e) => onConfigChange({ coaching_mode: e.target.value })}
        >
          <option value="on_demand">On demand</option>
          <option value="explicit">Explicit</option>
          <option value="shadowing">Shadowing</option>
        </select>
      </div>

      <button
        onClick={onNewSession}
        disabled={state !== 'idle'}
      >
        New Conversation
      </button>
    </div>
  )
}
