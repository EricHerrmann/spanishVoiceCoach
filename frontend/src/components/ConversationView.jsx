import VoiceButton from './VoiceButton'
import Transcript from './Transcript'

export default function ConversationView({ state, turns, error, onRecord, onStop, onPractice, coachingMode }) {
  return (
    <>
      <Transcript turns={turns} onPractice={onPractice} />
      <VoiceButton state={state} onRecord={onRecord} onStop={onStop} error={error} coachingMode={coachingMode} />
    </>
  )
}
