import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useVoice } from '../hooks/useVoice'

describe('useVoice — submitAudio error handling', () => {
  let originalFetch

  beforeEach(() => {
    originalFetch = global.fetch
    // Stub /session/start so newSession resolves cleanly
    global.fetch = vi.fn((url) => {
      if (url === '/session/start') {
        return Promise.resolve({
          json: () => Promise.resolve({ session_id: 'test-session-123' }),
        })
      }
      // /turn — simulate network failure
      return Promise.reject(new TypeError('Failed to fetch'))
    })
    // Stub MediaRecorder
    global.MediaRecorder = vi.fn(function () {
      this.start = vi.fn()
      this.stop = vi.fn()
      this.ondataavailable = null
      this.onstop = null
      this.state = 'inactive'
      this.mimeType = 'audio/webm'
    })
    global.MediaRecorder.isTypeSupported = vi.fn(() => false)
    global.navigator.mediaDevices = {
      getUserMedia: vi.fn(() =>
        Promise.resolve({ getTracks: () => [{ stop: vi.fn() }] })
      ),
    }
    global.AudioContext = vi.fn(function () {
      this.resume = vi.fn(() => Promise.resolve())
    })
  })

  afterEach(() => {
    global.fetch = originalFetch
  })

  it('sets stage to network when /turn fetch throws', async () => {
    const { result } = renderHook(() => useVoice())

    // Initialise session
    await act(async () => {
      await result.current.newSession({
        topic: 'general',
        level: 5,
        ai_provider: 'claude',
        ai_model: 'claude-sonnet-4-6',
        coaching_mode: 'on_demand',
        tts_provider: 'browser',
        tts_voice_id: null,
      })
    })

    // Start recording to set up the recorder with its onstop handler
    await act(async () => {
      await result.current.startRecording()
    })

    // Fire onstop to trigger submitAudio — this calls /turn which will reject
    const recorder = global.MediaRecorder.mock.results[0].value
    await act(async () => {
      await recorder.onstop()
    })

    // The /turn fetch will reject — error.stage should be 'network', not 'stt'
    expect(result.current.error).not.toBeNull()
    expect(result.current.error.stage).toBe('network')
    expect(result.current.error.recoverable).toBe(true)
  })
})
