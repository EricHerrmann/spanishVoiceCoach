import { useState, useRef } from 'react'

/**
 * useAudioRecorder({ onStop })
 *
 * Encapsulates MediaRecorder setup, MIME negotiation, and stream teardown.
 * onStop(blob) is called when recording stops.
 *
 * Returns: { isRecording, startRecording, stopRecording, recordingError }
 */
export function useAudioRecorder({ onStop }) {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingError, setRecordingError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  async function startRecording(audioCtxResume) {
    setRecordingError(null)
    // Resume AudioContext synchronously inside user gesture (Android Chrome autoplay policy)
    if (audioCtxResume) {
      audioCtxResume()
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/wav'
      const recorder = new MediaRecorder(stream, { mimeType })
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
        setIsRecording(false)
        onStop(blob)
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setIsRecording(true)
      return true
    } catch (err) {
      setRecordingError(err.message)
      setIsRecording(false)
      return false
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }

  return { isRecording, startRecording, stopRecording, recordingError }
}
