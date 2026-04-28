import { useState, useEffect } from 'react'
import VoiceButton from './VoiceButton'
import Transcript from './Transcript'

const HINT_SOURCE_LABELS = {
  topic: 'Try saying',
  translation: 'You translated',
}

export default function ConversationView({ state, turns, error, onRecord, onStop, onPractice, onAddFlashcards, coachingMode, hint }) {
  const [hintVisible, setHintVisible] = useState(true)
  // intentional reset: show hint whenever a new hint reference arrives; requires setState in effect
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setHintVisible(true) }, [hint])

  return (
    <>
      <Transcript turns={turns} onPractice={onPractice} onAddFlashcards={onAddFlashcards} />
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
