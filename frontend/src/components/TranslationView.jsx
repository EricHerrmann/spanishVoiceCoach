import { useState, useRef } from 'react'

export default function TranslationView({ config, onResult, onPractice, onAddFlashcards }) {
  const [recordingState, setRecordingState] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const audioCtxRef = useRef(null)

  function getAudioCtx() {
    if (!audioCtxRef.current) audioCtxRef.current = new AudioContext()
    return audioCtxRef.current
  }

  async function startRecording() {
    setError(null)
    getAudioCtx().resume()
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/wav'
      const recorder = new MediaRecorder(stream, { mimeType })
      chunksRef.current = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setRecordingState('processing')
        await submitAudio(new Blob(chunksRef.current, { type: recorder.mimeType }))
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setRecordingState('recording')
    } catch (err) {
      setError(err.message)
      setRecordingState('idle')
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop()
  }

  async function submitAudio(blob) {
    const form = new FormData()
    form.append('audio', blob, `recording.${blob.type.split('/')[1]?.split(';')[0] || 'wav'}`)
    form.append('tts_provider', config?.tts_provider || 'browser')
    if (config?.tts_voice_id) form.append('tts_voice_id', config.tts_voice_id)
    try {
      const res = await fetch('/translate', { method: 'POST', body: form })
      const data = await res.json()
      if (data.error) { setError(data.error.message); setRecordingState('idle'); return }
      setResult({ english: data.english, spanish: data.spanish })
      onResult?.({ text: data.spanish, source: 'translation' })
      setRecordingState('playing')
      if (data.audio_b64) await playAudioB64(data.audio_b64)
      else speakText(data.spanish)
    } catch {
      setError('Network error')
      setRecordingState('idle')
    }
  }

  async function playAudioB64(b64) {
    const binary = atob(b64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    const ctx = getAudioCtx()
    try {
      await ctx.resume()
      const buffer = await ctx.decodeAudioData(bytes.buffer)
      const source = ctx.createBufferSource()
      source.buffer = buffer
      source.connect(ctx.destination)
      await new Promise((resolve) => { source.onended = resolve; source.start() })
    } catch { /* fall through */ } finally { setRecordingState('idle') }
  }

  function speakText(text) {
    if (!window.speechSynthesis) { setRecordingState('idle'); return }
    const utt = new SpeechSynthesisUtterance(text)
    utt.lang = 'es-ES'
    utt.onend = () => setRecordingState('idle')
    utt.onerror = () => setRecordingState('idle')
    speechSynthesis.speak(utt)
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
        </div>
      )}
      {error && <p className="translation-error">{error}</p>}
      <div className="voice-button-container">
        <button
          className={`voice-btn voice-btn--${recordingState}`}
          onClick={isRecording ? stopRecording : startRecording}
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
