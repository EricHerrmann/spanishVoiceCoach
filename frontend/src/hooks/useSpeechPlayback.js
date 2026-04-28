import { useState, useRef } from 'react'

/**
 * useSpeechPlayback({ onEnd, lang })
 *
 * Encapsulates AudioContext base64 playback and speechSynthesis fallback.
 * onEnd() is called when playback finishes or fails.
 * lang defaults to 'es-ES'.
 *
 * Returns: { play, isPlaying }
 * play(audio_b64, text):
 *   - if audio_b64 is truthy: decode + play via AudioContext
 *   - if audio_b64 is null/undefined: use speechSynthesis with text
 */
export function useSpeechPlayback({ onEnd, lang = 'es-ES' }) {
  const [isPlaying, setIsPlaying] = useState(false)
  const audioCtxRef = useRef(null)

  function getAudioCtx() {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new AudioContext()
    }
    return audioCtxRef.current
  }

  async function play(audio_b64, text) {
    setIsPlaying(true)

    if (audio_b64) {
      const binary = atob(audio_b64)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i)
      }
      const audioCtx = getAudioCtx()
      try {
        await audioCtx.resume()
        const buffer = await audioCtx.decodeAudioData(bytes.buffer)
        const source = audioCtx.createBufferSource()
        source.buffer = buffer
        source.connect(audioCtx.destination)
        await new Promise((resolve) => {
          source.onended = resolve
          source.start()
        })
      } catch {
        // decodeAudioData failure — fall through to idle
      } finally {
        setIsPlaying(false)
        onEnd()
      }
      return
    }

    // speechSynthesis fallback
    if (!window.speechSynthesis) {
      setIsPlaying(false)
      onEnd()
      return
    }

    const utt = new SpeechSynthesisUtterance(text)
    utt.lang = lang
    utt.onend = () => {
      setIsPlaying(false)
      onEnd()
    }
    utt.onerror = () => {
      setIsPlaying(false)
      onEnd()
    }
    speechSynthesis.speak(utt)
  }

  function resumeAudioCtx() {
    getAudioCtx().resume()
  }

  return { play, isPlaying, resumeAudioCtx }
}
