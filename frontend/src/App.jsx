import { useState } from 'react'
import { useVoice } from './hooks/useVoice'
import VoiceButton from './components/VoiceButton'
import Transcript from './components/Transcript'
import CoachOverlay from './components/CoachOverlay'
import SessionConfig from './components/SessionConfig'
import './App.css'

function App() {
  const [coachingMode, setCoachingMode] = useState('on_demand')
  const { state, turns, corrections, error, startRecording, stopRecording } = useVoice(coachingMode)

  return (
    <div className="app">
      <h1>duoVoiceCoach</h1>
      <p className="subtitle">Spanish conversation practice</p>
      <SessionConfig coachingMode={coachingMode} onCoachingModeChange={setCoachingMode} />
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
