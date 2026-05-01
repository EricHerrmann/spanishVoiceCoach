import { useState } from 'react'

const COACHING_MODE_DESCRIPTIONS = {
  on_demand: 'Corrections hidden — ask anytime to see them.',
  explicit: 'Corrections visible after every turn.',
  shadowing: 'Corrections woven into the conversation.',
}

export default function SessionConfig({ config, onConfigChange, topics, providers, ttsVoices, onNewSession, state }) {
  const isKnownTopic = topics.some((t) => t.id === config.topic)
  const [customSelected, setCustomSelected] = useState(false)
  const showCustomInput = customSelected || (topics.length > 0 && !isKnownTopic && config.topic !== '')
  const selectedTopic = topics.find((t) => t.id === config.topic)
  const selectedProvider = providers.find((p) => p.id === config.ai_provider) ?? providers[0]

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

  function handleTtsProviderChange(e) {
    const newProvider = e.target.value
    onConfigChange({
      tts_provider: newProvider,
      tts_voice_id: newProvider === 'elevenlabs' ? (ttsVoices[0]?.id || null) : null,
    })
  }

  function handleAiProviderChange(e) {
    const nextProvider = providers.find((p) => p.id === e.target.value)
    onConfigChange({
      ai_provider: e.target.value,
      ai_model: nextProvider?.default_model ?? nextProvider?.models?.[0]?.id ?? null,
    })
  }

  return (
    <>
      <details className="session-config-details" open>
        <summary>Coaching Setup</summary>
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
            <p className="mode-description">{COACHING_MODE_DESCRIPTIONS[config.coaching_mode]}</p>
          </div>

          <button
            onClick={onNewSession}
            disabled={state !== 'idle'}
          >
            New Conversation
          </button>
        </div>
      </details>

      <details className="session-config-details">
        <summary>AI Settings</summary>
        <div className="session-config">
          <div className="session-config-field">
            <label htmlFor="ai-provider">AI Provider</label>
            <select
              id="ai-provider"
              value={config.ai_provider}
              onChange={handleAiProviderChange}
            >
              {providers.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </div>

          {selectedProvider?.models?.length > 0 && (
            <div className="session-config-field">
              <label htmlFor="ai-model">AI model</label>
              <select
                id="ai-model"
                value={config.ai_model || selectedProvider.default_model || selectedProvider.models[0].id}
                onChange={(e) => onConfigChange({ ai_model: e.target.value })}
              >
                {selectedProvider.models.map((model) => (
                  <option key={model.id} value={model.id}>{model.label}</option>
                ))}
              </select>
            </div>
          )}

          <div className="session-config-field">
            <label htmlFor="tts-provider">Voice</label>
            <select
              id="tts-provider"
              value={config.tts_provider}
              onChange={handleTtsProviderChange}
            >
              <option value="browser">Browser (built-in)</option>
              <option value="elevenlabs">ElevenLabs</option>
            </select>
          </div>

          {config.tts_provider === 'elevenlabs' && (
            <div className="session-config-field">
              <label htmlFor="tts-voice">ElevenLabs voice</label>
              <select
                id="tts-voice"
                value={config.tts_voice_id || ''}
                onChange={(e) => onConfigChange({ tts_voice_id: e.target.value })}
              >
                {ttsVoices.map((v) => (
                  <option key={v.id} value={v.id}>{v.label}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </details>
    </>
  )
}
