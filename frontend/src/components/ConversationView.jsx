import { useState } from 'react'
import VoiceButton from './VoiceButton'
import Transcript from './Transcript'

const HINT_SOURCE_LABELS = {
  topic: 'Try saying',
  translation: 'You translated',
}

export default function ConversationView({ state, turns, error, onRecord, onStop, onPractice, coachingMode, hint }) {
  const [hintVisible, setHintVisible] = useState(true)

  return (
    <>
      <Transcript turns={turns} onPractice={onPractice} />
      <VoiceButton state={state} onRecord={onRecord} onStop={onStop} error={error} coachingMode={coachingMode} />
      {hint && (
        <div className="conversation-hint">
          <div className="conversation-hint-header">
            <span className="conversation-hint-source">{HINT_SOURCE_LABELS[hint.source] ?? 'Hint'}</span>
            <button
              className="conversation-hint-toggle"
              onClick={() => setHintVisible((v) => !v)}
            >
              {hintVisible ? 'Hide' : 'Show'}
            </button>
          </div>
          {hintVisible && (
            <span className="conversation-hint-text">{hint.text}</span>
          )}
        </div>
      )}
    </>
  )
}
