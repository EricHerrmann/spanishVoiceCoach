import { useVoice } from './hooks/useVoice'
import VoiceButton from './components/VoiceButton'
import Transcript from './components/Transcript'
import './App.css'

function App() {
  const { state, turns, error, startRecording, stopRecording } = useVoice()

  return (
    <div className="app">
      <h1>duoVoiceCoach</h1>
      <p className="subtitle">Spanish conversation practice</p>
      <VoiceButton
        state={state}
        onRecord={startRecording}
        onStop={stopRecording}
        error={error}
      />
      <Transcript turns={turns} />
    </div>
  )
}

export default App
