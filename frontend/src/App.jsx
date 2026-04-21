import { useState, useEffect } from 'react'
import { useVoice } from './hooks/useVoice'
import VoiceButton from './components/VoiceButton'
import Transcript from './components/Transcript'
import CoachOverlay from './components/CoachOverlay'
import SessionConfig from './components/SessionConfig'
import './App.css'

const DEFAULT_CONFIG = {
  topic: 'general',
  level: 5,
  ai_provider: 'claude',
  coaching_mode: 'on_demand',
}

function App() {
  const [topics, setTopics] = useState([])
  const [providers, setProviders] = useState([])
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const { state, turns, corrections, error, startRecording, stopRecording, newSession } = useVoice()

  useEffect(() => {
    fetch('/topics').then((r) => r.json()).then(setTopics).catch(() => {})
    fetch('/providers').then((r) => r.json()).then(setProviders).catch(() => {})
    newSession(DEFAULT_CONFIG)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function onConfigChange(patch) {
    setConfig((prev) => ({ ...prev, ...patch }))
  }

  function onNewSession() {
    const topic = config.topic.trim() || 'general'
    newSession({ ...config, topic })
  }

  return (
    <div className="app">
      <h1>duoVoiceCoach</h1>
      <p className="subtitle">Spanish conversation practice</p>
      <SessionConfig
        config={config}
        onConfigChange={onConfigChange}
        topics={topics}
        providers={providers}
        onNewSession={onNewSession}
        state={state}
      />
      <VoiceButton
        state={state}
        onRecord={startRecording}
        onStop={stopRecording}
        error={error}
      />
      <CoachOverlay corrections={corrections} />
      <Transcript turns={turns} />
    </div>
  )
}

export default App
