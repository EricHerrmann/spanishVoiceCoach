const COACHING_MODE_LABELS = {
  on_demand: 'On demand',
  explicit: 'Explicit',
  shadowing: 'Shadowing',
}

const COACHING_MODE_DESCRIPTIONS = {
  on_demand: 'Corrections hidden — ask anytime to see them.',
  explicit: 'Corrections visible after every turn.',
  shadowing: 'Corrections woven into the conversation.',
}

export default function VoiceButton({ state, onRecord, onStop, error, coachingMode }) {
  const isRecording = state === 'recording'
  const isProcessing = state === 'processing'
  const isPlaying = state === 'playing'
  const disabled = isProcessing || isPlaying

  function handleClick() {
    if (isRecording) onStop()
    else if (!disabled) onRecord()
  }

  return (
    <div className="voice-button-container">
      <button onClick={handleClick} disabled={disabled} className={`voice-btn voice-btn--${state}`}>
        {isRecording ? 'Stop Recording' : isProcessing ? 'Processing...' : isPlaying ? 'Playing...' : 'Start Speaking'}
      </button>
      {coachingMode && (
        <p className="voice-mode-badge">
          {COACHING_MODE_LABELS[coachingMode] ?? coachingMode}
          {COACHING_MODE_DESCRIPTIONS[coachingMode] && (
            <> — {COACHING_MODE_DESCRIPTIONS[coachingMode]}</>
          )}
        </p>
      )}
      {error?.recoverable && (
        <p className="retry-prompt">
          {error.stage === 'mic'
            ? `Microphone error: ${error.message} — check browser permissions`
            : 'Transcription failed — try again'}
        </p>
      )}
    </div>
  )
}
