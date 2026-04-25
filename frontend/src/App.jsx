import { useState, useEffect } from 'react'
import { useVoice } from './hooks/useVoice'
import VoiceButton from './components/VoiceButton'
import Transcript from './components/Transcript'
import CoachOverlay from './components/CoachOverlay'
import SessionConfig from './components/SessionConfig'
import SessionHistory from './components/SessionHistory'
import PronunciationView from './components/PronunciationView'
import './App.css'

const DEFAULT_CONFIG = {
  topic: 'general',
  level: 5,
  ai_provider: 'claude',
  coaching_mode: 'on_demand',
  tts_provider: 'browser',
  tts_voice_id: null,
}

function App() {
  const [topics, setTopics] = useState([])
  const [providers, setProviders] = useState([])
  const [ttsVoices, setTtsVoices] = useState([])
  const [savedSessions, setSavedSessions] = useState([])
  const [selectedSessionId, setSelectedSessionId] = useState(null)
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [mode, setMode] = useState('conversation')
  const [pronunciationTarget, setPronunciationTarget] = useState(null)
  const { state, turns, corrections, error, startRecording, stopRecording, newSession, loadSession } = useVoice()

  function handlePractice(text) {
    if (!text) return
    setPronunciationTarget(text)
    setMode('pronunciation')
  }

  // setMode('conversation') is required here: without it, clearing the target
  // leaves mode === 'pronunciation' and PronunciationView renders with no target.
  function clearPronunciationTarget() {
    setPronunciationTarget(null)
    setMode('conversation')
  }

  function refreshSessions() {
    return fetch('/sessions').then((r) => r.json()).then(setSavedSessions).catch(() => {})
  }

  useEffect(() => {
    fetch('/topics').then((r) => r.json()).then(setTopics).catch(() => {})
    fetch('/providers').then((r) => r.json()).then(setProviders).catch(() => {})
    fetch('/tts-voices').then((r) => r.json()).then(setTtsVoices).catch(() => {})
    newSession(DEFAULT_CONFIG).then((sessionId) => {
      setSelectedSessionId(sessionId)
      refreshSessions()
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function onConfigChange(patch) {
    setConfig((prev) => ({ ...prev, ...patch }))
  }

  function onNewSession() {
    const topic = config.topic.trim() || 'general'
    newSession({ ...config, topic }).then((sessionId) => {
      setSelectedSessionId(sessionId)
      refreshSessions()
    })
  }

  function onSelectSession(sessionId) {
    fetch(`/sessions/${sessionId}`)
      .then((r) => r.json())
      .then((session) => {
        setSelectedSessionId(session.id)
        setConfig({
          topic: session.topic,
          level: session.level,
          ai_provider: session.ai_provider,
          coaching_mode: session.coaching_mode,
          tts_provider: session.tts_provider || 'browser',
          tts_voice_id: session.tts_voice_id || null,
        })
        loadSession(session)
      })
      .catch(() => {})
  }

  return (
    <div className="app">
      <div className="app-left">
        <header className="app-header">
          <span className="app-title">duoVoiceCoach</span>
        </header>
        {mode === 'conversation' && (
          <>
            <Transcript turns={turns} onPractice={handlePractice} />
            <VoiceButton
              state={state}
              onRecord={startRecording}
              onStop={stopRecording}
              error={error}
              coachingMode={config.coaching_mode}
            />
          </>
        )}
        {mode === 'pronunciation' && (
          <PronunciationView
            pronunciationTarget={pronunciationTarget}
            onClearTarget={clearPronunciationTarget}
          />
        )}
      </div>
      <div className={`app-right${drawerOpen ? ' app-right--open' : ''}`}>
        <button
          className="drawer-toggle"
          onClick={() => setDrawerOpen((o) => !o)}
          aria-label={drawerOpen ? 'Close tools panel' : 'Open tools panel'}
        >
          {drawerOpen ? '✕ Close' : '▲ Tools'}
        </button>
        <div className="right-pane-content">
          <SessionConfig
            config={config}
            onConfigChange={onConfigChange}
            topics={topics}
            providers={providers}
            ttsVoices={ttsVoices}
            onNewSession={onNewSession}
            state={state}
          />
          <CoachOverlay corrections={corrections} />
          <SessionHistory
            sessions={savedSessions}
            selectedSessionId={selectedSessionId}
            onSelectSession={onSelectSession}
            onRefresh={refreshSessions}
          />
        </div>
      </div>
    </div>
  )
}

export default App
