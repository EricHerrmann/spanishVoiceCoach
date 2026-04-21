import { useState, useRef } from 'react'

export function useVoice() {
  const [state, setState] = useState('idle')
  const [turns, setTurns] = useState([])
  const [corrections, setCorrections] = useState([])
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const sessionIdRef = useRef(null)
  const abortControllerRef = useRef(null)

  function newSession(config) {
    // Stop any active recording before resetting session state
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
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
    fetch('/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: config.topic,
        level: config.level,
        ai_provider: config.ai_provider,
        coaching_mode: config.coaching_mode,
      }),
      signal: controller.signal,
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.session_id) {
          sessionIdRef.current = data.session_id
        } else {
          setError({ stage: 'session', message: 'Failed to start session', recoverable: false })
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError({ stage: 'session', message: 'Failed to start session', recoverable: false })
        }
      })
  }

  async function startRecording() {
    if (!sessionIdRef.current) {
      setError({ stage: 'mic', message: 'Session not ready, please try again.', recoverable: true })
      return
    }
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setState('processing')
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' })
        await submitAudio(blob)
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setState('recording')
    } catch (err) {
      setError({ stage: 'mic', message: err.message, recoverable: true })
      setState('idle')
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }

  async function submitAudio(blob) {
    const form = new FormData()
    form.append('audio', blob, 'recording.wav')
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
      speakCoachText(data.coach_text)
    } catch (err) {
      setError({ stage: 'stt', message: 'Network error', recoverable: true })
      setState('idle')
    }
  }

  function speakCoachText(text) {
    if (!text || !window.speechSynthesis) {
      setState('idle')
      return
    }
    const utt = new SpeechSynthesisUtterance(text)
    utt.lang = 'es-ES'
    utt.onend = () => setState('idle')
    utt.onerror = () => setState('idle')
    speechSynthesis.speak(utt)
  }

  return { state, turns, corrections, error, startRecording, stopRecording, newSession }
}
