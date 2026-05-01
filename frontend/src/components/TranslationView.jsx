import { useState } from 'react'
import FlashcardButton from './FlashcardButton'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { useSpeechPlayback } from '../hooks/useSpeechPlayback'

export default function TranslationView({ config, onResult, onPractice, onAddFlashcards }) {
  const [recordingState, setRecordingState] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const { play, resumeAudioCtx } = useSpeechPlayback({
    onEnd: () => setRecordingState('idle'),
  })

  const { startRecording, stopRecording, recordingError } = useAudioRecorder({
    onStop: (blob) => {
      setRecordingState('processing')
      submitAudio(blob)
    },
  })

  async function handleStartRecording() {
    setError(null)
    // Pass resumeAudioCtx synchronously inside the user gesture (Android Chrome autoplay policy)
    const ok = await startRecording(resumeAudioCtx)
    if (!ok) {
      setError(recordingError || 'Microphone unavailable')
      return
    }
    setRecordingState('recording')
  }

  async function submitAudio(blob) {
    const form = new FormData()
    form.append('audio', blob, `recording.${blob.type.split('/')[1]?.split(';')[0] || 'wav'}`)
    form.append('tts_provider', config?.tts_provider || 'browser')
    if (config?.tts_voice_id) form.append('tts_voice_id', config.tts_voice_id)
    form.append('ai_provider', config?.ai_provider || 'claude')
    if (config?.ai_model) form.append('ai_model', config.ai_model)
    try {
      const res = await fetch('/translate', { method: 'POST', body: form })
      const data = await res.json()
      if (data.error) { setError(data.error.message); setRecordingState('idle'); return }
      setResult({ english: data.english, spanish: data.spanish })
      onResult?.({ text: data.spanish, source: 'translation' })
      setRecordingState('playing')
      play(data.audio_b64, data.spanish)
    } catch {
      setError('Network error')
      setRecordingState('idle')
    }
  }

  const isRecording = recordingState === 'recording'
  const isProcessing = recordingState === 'processing'
  const isPlaying = recordingState === 'playing'
  const disabled = isProcessing || isPlaying

  return (
    <div className="translation-view">
      {result && (
        <div className="translation-result">
          <p className="translation-english">{result.english}</p>
          <p className="translation-spanish">{result.spanish}</p>
          <button
            className="translation-practice-btn"
            onClick={() => onPractice?.(result.spanish, 'translation')}
          >
            Practice pronunciation
          </button>
          {onAddFlashcards && (
            <FlashcardButton
              label="Add to flashcards"
              onAdd={() => onAddFlashcards(result.spanish, 'translation')}
            />
          )}
        </div>
      )}
      {error && <p className="translation-error">{error}</p>}
      <div className="voice-button-container">
        <button
          className={`voice-btn voice-btn--${recordingState}`}
          onClick={isRecording ? stopRecording : handleStartRecording}
          disabled={disabled}
        >
          {isRecording
            ? 'Stop Recording'
            : isProcessing
            ? 'Processing...'
            : isPlaying
            ? 'Playing...'
            : 'Record English phrase'}
        </button>
      </div>
    </div>
  )
}
