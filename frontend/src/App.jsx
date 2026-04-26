import { useState, useEffect } from 'react'
import { useVoice } from './hooks/useVoice'
import NavTabs from './components/NavTabs'
import ConversationView from './components/ConversationView'
import FlashcardsView from './components/FlashcardsView'
import TranslationView from './components/TranslationView'
import PronunciationView from './components/PronunciationView'
import CoachOverlay from './components/CoachOverlay'
import SessionConfig from './components/SessionConfig'
import SessionHistory from './components/SessionHistory'
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
  const [conversationHint, setConversationHint] = useState(null)
  const { state, turns, corrections, error, startRecording, stopRecording, newSession, loadSession } = useVoice()

  function handlePractice(text, source = 'conversation') {
    if (!text) return
    setPronunciationTarget({ text, source })
    setMode('pronunciation')
  }

  function clearPronunciationTarget() {
    setPronunciationTarget(null)
    setMode('conversation')
  }

  function handleTranslationResult(hint) {
    setConversationHint(hint)
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

  useEffect(() => {
    const topic = topics.find((t) => t.id === config.topic)
    setConversationHint(topic?.starter ? { text: topic.starter, source: 'topic' } : null)
  }, [config.topic, topics])

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
          <NavTabs mode={mode} onModeChange={setMode} />
        </header>
        {mode === 'conversation' && (
          <ConversationView
            state={state}
            turns={turns}
            error={error}
            onRecord={startRecording}
            onStop={stopRecording}
            onPractice={handlePractice}
            coachingMode={config.coaching_mode}
            hint={conversationHint}
          />
        )}
        {mode === 'flashcards' && <FlashcardsView />}
        {mode === 'translation' && (
          <TranslationView
            config={config}
            onResult={handleTranslationResult}
            onPractice={handlePractice}
          />
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
