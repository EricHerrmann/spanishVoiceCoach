import { useState, useRef } from 'react'

export function useVoice() {
  const [state, setState] = useState('idle')
  const [turns, setTurns] = useState([])
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  async function startRecording() {
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
        { speaker: 'user', transcript_norm: data.transcript_norm, echo: null },
        { speaker: 'coach', transcript_norm: null, echo: data.echo },
      ])
      setError(null)
      setState('playing')
      speakEcho(data.echo)
    } catch (err) {
      setError({ stage: 'stt', message: 'Network error', recoverable: true })
      setState('idle')
    }
  }

  function speakEcho(text) {
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

  return { state, turns, error, startRecording, stopRecording }
}
