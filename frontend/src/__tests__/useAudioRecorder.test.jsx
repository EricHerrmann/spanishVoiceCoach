import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useAudioRecorder } from '../hooks/useAudioRecorder'

describe('useAudioRecorder', () => {
  let fakeStream
  let recorderInstance

  beforeEach(() => {
    fakeStream = {
      getTracks: () => [{ stop: vi.fn() }],
    }

    global.navigator.mediaDevices = {
      getUserMedia: vi.fn(() => Promise.resolve(fakeStream)),
    }

    global.MediaRecorder = vi.fn(function (stream, options) {
      recorderInstance = this
      this.stream = stream
      this.mimeType = options?.mimeType || 'audio/webm'
      this.state = 'inactive'
      this.ondataavailable = null
      this.onstop = null
      this.start = vi.fn(() => {
        this.state = 'recording'
      })
      this.stop = vi.fn(() => {
        this.state = 'inactive'
        if (this.onstop) this.onstop()
      })
    })
    global.MediaRecorder.isTypeSupported = vi.fn(() => false)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    recorderInstance = undefined
  })

  it('startRecording() calls getUserMedia({ audio: true })', async () => {
    const onStop = vi.fn()
    const { result } = renderHook(() => useAudioRecorder({ onStop }))

    await act(async () => {
      await result.current.startRecording()
    })

    expect(global.navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true })
  })

  it('isRecording becomes true after startRecording()', async () => {
    const onStop = vi.fn()
    const { result } = renderHook(() => useAudioRecorder({ onStop }))

    await act(async () => {
      await result.current.startRecording()
    })

    expect(result.current.isRecording).toBe(true)
  })

  it('isRecording becomes false after stopRecording()', async () => {
    const onStop = vi.fn()
    const { result } = renderHook(() => useAudioRecorder({ onStop }))

    await act(async () => {
      await result.current.startRecording()
    })

    expect(result.current.isRecording).toBe(true)

    act(() => {
      result.current.stopRecording()
    })

    expect(result.current.isRecording).toBe(false)
  })

  it('onStop is called with a Blob when recording stops', async () => {
    const onStop = vi.fn()
    const { result } = renderHook(() => useAudioRecorder({ onStop }))

    await act(async () => {
      await result.current.startRecording()
    })

    // Simulate data available event
    act(() => {
      if (recorderInstance.ondataavailable) {
        recorderInstance.ondataavailable({ data: new Blob(['audio-data'], { type: 'audio/webm' }) })
      }
    })

    act(() => {
      result.current.stopRecording()
    })

    expect(onStop).toHaveBeenCalledOnce()
    expect(onStop.mock.calls[0][0]).toBeInstanceOf(Blob)
  })

  it('recordingError is set if getUserMedia rejects', async () => {
    const onStop = vi.fn()
    global.navigator.mediaDevices.getUserMedia = vi.fn(() =>
      Promise.reject(new Error('Permission denied'))
    )

    const { result } = renderHook(() => useAudioRecorder({ onStop }))

    await act(async () => {
      await result.current.startRecording()
    })

    expect(result.current.recordingError).toBe('Permission denied')
    expect(result.current.isRecording).toBe(false)
  })

  it('recordingError is cleared on a new startRecording() call', async () => {
    const onStop = vi.fn()
    // First call fails
    global.navigator.mediaDevices.getUserMedia = vi.fn(() =>
      Promise.reject(new Error('Permission denied'))
    )

    const { result } = renderHook(() => useAudioRecorder({ onStop }))

    await act(async () => {
      await result.current.startRecording()
    })

    expect(result.current.recordingError).toBe('Permission denied')

    // Second call succeeds
    global.navigator.mediaDevices.getUserMedia = vi.fn(() => Promise.resolve(fakeStream))

    await act(async () => {
      await result.current.startRecording()
    })

    expect(result.current.recordingError).toBeNull()
  })

  it('stream tracks are stopped on recorder stop', async () => {
    const onStop = vi.fn()
    const mockStop = vi.fn()
    const trackWithStop = { stop: mockStop }
    fakeStream.getTracks = () => [trackWithStop]

    const { result } = renderHook(() => useAudioRecorder({ onStop }))

    await act(async () => {
      await result.current.startRecording()
    })

    act(() => {
      result.current.stopRecording()
    })

    expect(mockStop).toHaveBeenCalled()
  })

  it('MIME type prefers audio/webm;codecs=opus when supported', async () => {
    global.MediaRecorder.isTypeSupported = vi.fn((type) => type === 'audio/webm;codecs=opus')
    const onStop = vi.fn()
    const { result } = renderHook(() => useAudioRecorder({ onStop }))

    await act(async () => {
      await result.current.startRecording()
    })

    expect(global.MediaRecorder).toHaveBeenCalledWith(
      expect.anything(),
      { mimeType: 'audio/webm;codecs=opus' }
    )
  })

  it('MIME type falls back to audio/wav when webm is not supported', async () => {
    global.MediaRecorder.isTypeSupported = vi.fn(() => false)
    const onStop = vi.fn()
    const { result } = renderHook(() => useAudioRecorder({ onStop }))

    await act(async () => {
      await result.current.startRecording()
    })

    expect(global.MediaRecorder).toHaveBeenCalledWith(
      expect.anything(),
      { mimeType: 'audio/wav' }
    )
  })
})
