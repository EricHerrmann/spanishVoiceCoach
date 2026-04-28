import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useSpeechPlayback } from '../hooks/useSpeechPlayback'

// Minimal valid base64 WAV for testing (just needs to be decodable by the mock)
const FAKE_AUDIO_B64 = btoa('fake-audio-bytes')

describe('useSpeechPlayback', () => {
  let mockSpeak
  let savedSpeechSynthesis
  let savedSpeechSynthesisUtterance

  beforeEach(() => {
    savedSpeechSynthesis = global.speechSynthesis
    savedSpeechSynthesisUtterance = global.SpeechSynthesisUtterance

    mockSpeak = vi.fn()
    global.speechSynthesis = { speak: mockSpeak }
    global.SpeechSynthesisUtterance = vi.fn(function (text) {
      this.text = text
      this.lang = ''
      this.onend = null
      this.onerror = null
    })
  })

  afterEach(() => {
    global.speechSynthesis = savedSpeechSynthesis
    global.SpeechSynthesisUtterance = savedSpeechSynthesisUtterance
    vi.restoreAllMocks()
  })

  describe('speechSynthesis path (audio_b64 is null)', () => {
    it('play(null, "hola") uses speechSynthesis.speak', async () => {
      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd }))

      await act(async () => {
        result.current.play(null, 'hola')
      })

      expect(mockSpeak).toHaveBeenCalledOnce()
    })

    it('play(null, "hola") sets lang to es-ES by default', async () => {
      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd }))

      await act(async () => {
        result.current.play(null, 'hola')
      })

      const utt = global.SpeechSynthesisUtterance.mock.results[0].value
      expect(utt.lang).toBe('es-ES')
    })

    it('play(null, "hola") uses the provided lang option', async () => {
      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd, lang: 'fr-FR' }))

      await act(async () => {
        result.current.play(null, 'bonjour')
      })

      const utt = global.SpeechSynthesisUtterance.mock.results[0].value
      expect(utt.lang).toBe('fr-FR')
    })

    it('onEnd is called after speechSynthesis utterance ends', async () => {
      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd }))

      await act(async () => {
        result.current.play(null, 'hola')
      })

      const utt = global.SpeechSynthesisUtterance.mock.results[0].value

      act(() => {
        utt.onend()
      })

      expect(onEnd).toHaveBeenCalledOnce()
    })

    it('onEnd is called when speechSynthesis utterance errors', async () => {
      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd }))

      await act(async () => {
        result.current.play(null, 'hola')
      })

      const utt = global.SpeechSynthesisUtterance.mock.results[0].value

      act(() => {
        utt.onerror()
      })

      expect(onEnd).toHaveBeenCalledOnce()
    })

    it('isPlaying is true while playing, false after onEnd fires', async () => {
      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd }))

      await act(async () => {
        result.current.play(null, 'hola')
      })

      expect(result.current.isPlaying).toBe(true)

      const utt = global.SpeechSynthesisUtterance.mock.results[0].value

      act(() => {
        utt.onend()
      })

      expect(result.current.isPlaying).toBe(false)
    })

    it('if window.speechSynthesis is undefined, play(null, text) calls onEnd immediately', async () => {
      global.speechSynthesis = undefined

      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd }))

      await act(async () => {
        result.current.play(null, 'hola')
      })

      expect(onEnd).toHaveBeenCalledOnce()
      expect(result.current.isPlaying).toBe(false)
    })
  })

  describe('resumeAudioCtx', () => {
    let fakeAudioCtx

    beforeEach(() => {
      fakeAudioCtx = { resume: vi.fn(() => Promise.resolve()) }
      global.AudioContext = function FakeAudioContext() { return fakeAudioCtx }
    })

    afterEach(() => { delete global.AudioContext })

    it('resumeAudioCtx() calls AudioContext.resume()', () => {
      const { result } = renderHook(() => useSpeechPlayback({ onEnd: vi.fn() }))
      result.current.resumeAudioCtx()
      expect(fakeAudioCtx.resume).toHaveBeenCalledOnce()
    })
  })

  describe('AudioContext path (audio_b64 is truthy)', () => {
    let fakeAudioCtx
    let fakeSource

    beforeEach(() => {
      fakeSource = {
        buffer: null,
        connect: vi.fn(),
        start: vi.fn(),
        onended: null,
      }

      fakeAudioCtx = {
        resume: vi.fn(() => Promise.resolve()),
        decodeAudioData: vi.fn((buffer) => Promise.resolve({ duration: 1, buffer })),
        createBufferSource: vi.fn(() => fakeSource),
        destination: {},
      }

      // Must use a constructor function (not arrow) so `new AudioContext()` returns fakeAudioCtx
      global.AudioContext = function FakeAudioContext() {
        return fakeAudioCtx
      }
    })

    afterEach(() => {
      delete global.AudioContext
    })

    it('play(audio_b64, null) calls AudioContext.decodeAudioData', async () => {
      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd }))

      // Start play but don't await — we need to trigger onended manually
      act(() => {
        result.current.play(FAKE_AUDIO_B64, null)
      })

      // Wait for decodeAudioData to be called
      await vi.waitFor(() => {
        expect(fakeAudioCtx.decodeAudioData).toHaveBeenCalled()
      })
    })

    it('play(audio_b64, null) does not use speechSynthesis', async () => {
      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd }))

      act(() => {
        result.current.play(FAKE_AUDIO_B64, null)
      })

      await vi.waitFor(() => {
        expect(fakeAudioCtx.decodeAudioData).toHaveBeenCalled()
      })

      expect(mockSpeak).not.toHaveBeenCalled()
    })

    it('onEnd is called after AudioContext source ends', async () => {
      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd }))

      act(() => {
        result.current.play(FAKE_AUDIO_B64, null)
      })

      // Wait for source.start to be called, then trigger onended
      await vi.waitFor(() => {
        expect(fakeSource.start).toHaveBeenCalled()
      })

      act(() => {
        fakeSource.onended()
      })

      await vi.waitFor(() => {
        expect(onEnd).toHaveBeenCalledOnce()
      })
    })

    it('onEnd is called if decodeAudioData throws', async () => {
      fakeAudioCtx.decodeAudioData = vi.fn(() => Promise.reject(new Error('decode error')))
      const onEnd = vi.fn()
      const { result } = renderHook(() => useSpeechPlayback({ onEnd }))

      await act(async () => {
        await result.current.play(FAKE_AUDIO_B64, null)
      })

      expect(onEnd).toHaveBeenCalledOnce()
    })
  })
})
