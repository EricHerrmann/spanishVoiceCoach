import { useState, useRef } from 'react'
import { useAudioRecorder } from './useAudioRecorder'
import { useSpeechPlayback } from './useSpeechPlayback'

export function useVoice() {
  const [state, setState] = useState('idle')
  const [turns, setTurns] = useState([])
  const [corrections, setCorrections] = useState([])
  const [error, setError] = useState(null)
  const sessionIdRef = useRef(null)
  const abortControllerRef = useRef(null)

  const { play, resumeAudioCtx } = useSpeechPlayback({
    onEnd: () => setState('idle'),
  })

  const { startRecording, stopRecording, recordingError } = useAudioRecorder({
    onStop: (blob) => {
      setState('processing')
      submitAudio(blob)
    },
  })

  function newSession(config) {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setState('idle')
    const controller = new AbortController()
    abortControllerRef.current = controller
    sessionIdRef.current = null
    setTurns([])
    setCorrections([])
    setError(null)
    return fetch('/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: config.topic,
        level: config.level,
        ai_provider: config.ai_provider,
        coaching_mode: config.coaching_mode,
        tts_provider: config.tts_provider || 'browser',
        tts_voice_id: config.tts_voice_id || null,
      }),
      signal: controller.signal,
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.session_id) {
          sessionIdRef.current = data.session_id
          return data.session_id
        } else {
          setError({ stage: 'session', message: 'Failed to start session', recoverable: false })
          return null
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError({ stage: 'session', message: 'Failed to start session', recoverable: false })
        }
        return null
      })
  }

  function loadSession(session) {
    sessionIdRef.current = session.id
    setTurns(session.turns || [])
    setCorrections((session.turns || []).flatMap((turn) => turn.corrections || []))
    setError(null)
    setState('idle')
  }

  async function handleStartRecording() {
    if (!sessionIdRef.current) {
      setError({ stage: 'mic', message: 'Session not ready, please try again.', recoverable: true })
      return
    }
    setError(null)
    // Pass resumeAudioCtx so useAudioRecorder can call it synchronously inside the user gesture
    // before the async getUserMedia call (Android Chrome autoplay policy)
    const ok = await startRecording(resumeAudioCtx)
    if (!ok) {
      setError({ stage: 'mic', message: recordingError || 'Microphone unavailable', recoverable: true })
      return
    }
    setState('recording')
  }

  async function submitAudio(blob) {
    const form = new FormData()
    form.append('audio', blob, `recording.${blob.type.split('/')[1]?.split(';')[0] || 'wav'}`)
    form.append('session_id', sessionIdRef.current)
    try {
      const res = await fetch('/turn', { method: 'POST', body: form })
      const data = await res.json()

      if (data.error) {
        setError(data.error)
        setState('idle')
        return
      }

      setTurns((prev) => [
        ...prev,
        { speaker: 'user', transcript_norm: data.transcript_norm, coach_text: null },
        { speaker: 'coach', transcript_norm: null, coach_text: data.coach_text },
      ])
      setCorrections(data.corrections || [])
      setError(null)
      setState('playing')

      play(data.audio_b64, data.coach_text)
    } catch {
      setError({ stage: 'network', message: 'Network error', recoverable: true })
      setState('idle')
    }
  }

  return {
    state,
    turns,
    corrections,
    error,
    startRecording: handleStartRecording,
    stopRecording,
    newSession,
    loadSession,
  }
}
