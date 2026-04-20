export default function VoiceButton({ state, onRecord, onStop, error }) {
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
      {error?.recoverable && (
        <p className="retry-prompt">Transcription failed — try again</p>
      )}
    </div>
  )
}
