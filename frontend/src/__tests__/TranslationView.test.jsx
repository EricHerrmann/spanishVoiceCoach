import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import TranslationView from '../components/TranslationView'

const DEFAULT_CONFIG = { tts_provider: 'browser', tts_voice_id: null }

describe('TranslationView', () => {
  it('renders record button in idle state', () => {
    render(<TranslationView config={DEFAULT_CONFIG} />)
    expect(screen.getByText('Record English phrase')).toBeInTheDocument()
  })

  it('record button is enabled in idle state', () => {
    render(<TranslationView config={DEFAULT_CONFIG} />)
    expect(screen.getByText('Record English phrase')).not.toBeDisabled()
  })

  it('does not show a result panel initially', () => {
    render(<TranslationView config={DEFAULT_CONFIG} />)
    expect(screen.queryByRole('paragraph')).not.toBeInTheDocument()
  })

  it('accepts onResult and onPractice props without crashing', () => {
    render(<TranslationView config={DEFAULT_CONFIG} onResult={vi.fn()} onPractice={vi.fn()} />)
    expect(screen.getByText('Record English phrase')).toBeInTheDocument()
  })

  it('does not show Practice button when there is no result', () => {
    render(<TranslationView config={DEFAULT_CONFIG} onResult={vi.fn()} onPractice={vi.fn()} />)
    expect(screen.queryByText(/practice/i)).not.toBeInTheDocument()
  })
})

describe('TranslationView — flashcard button', () => {
  it('"Add to flashcards" button absent when there is no result', () => {
    render(<TranslationView config={DEFAULT_CONFIG} onAddFlashcards={vi.fn()} />)
    expect(screen.queryByText('Add to flashcards')).not.toBeInTheDocument()
  })

  it('"Add to flashcards" button absent when onAddFlashcards prop is not provided', () => {
    render(<TranslationView config={DEFAULT_CONFIG} />)
    expect(screen.queryByText('Add to flashcards')).not.toBeInTheDocument()
  })

  describe('happy path — button appears and fires callback after translation', () => {
    let savedFetch
    let savedGetUserMedia
    let savedMediaRecorder
    let savedAudioContext

    beforeEach(() => {
      savedFetch = global.fetch
      savedGetUserMedia = navigator.mediaDevices?.getUserMedia
      savedMediaRecorder = global.MediaRecorder
      savedAudioContext = global.AudioContext

      // Minimal AudioContext stub — must be a real constructor
      function FakeAudioContext() {
        this.resume = vi.fn().mockResolvedValue(undefined)
        this.decodeAudioData = vi.fn()
        this.createBufferSource = vi.fn()
        this.destination = {}
      }
      global.AudioContext = FakeAudioContext

      // Mock fetch to return a translation result immediately
      global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve({
          english: 'Hello world',
          spanish: 'Hola mundo',
          audio_b64: null,
        }),
      })

      // Mock getUserMedia to return a minimal stream
      const fakeStream = { getTracks: () => [{ stop: vi.fn() }] }
      const mockGetUserMedia = vi.fn().mockResolvedValue(fakeStream)
      Object.defineProperty(navigator, 'mediaDevices', {
        value: { getUserMedia: mockGetUserMedia },
        configurable: true,
        writable: true,
      })

      // Mock speechSynthesis so speakText() doesn't throw
      global.speechSynthesis = { speak: vi.fn() }
      global.SpeechSynthesisUtterance = vi.fn(() => ({}))

      // Mock MediaRecorder with a real constructor function
      let recorderInstance
      function FakeMediaRecorder() {
        recorderInstance = this
        this.state = 'recording'
        this.mimeType = 'audio/wav'
        this.ondataavailable = null
        this.onstop = null
        this.start = vi.fn()
        this.stop = vi.fn(async () => {
          this.state = 'inactive'
          if (this.onstop) await this.onstop()
        })
      }
      FakeMediaRecorder.isTypeSupported = vi.fn().mockReturnValue(false)
      global.MediaRecorder = FakeMediaRecorder

      // Expose the recorder instance for tests to call stop
      global.__getRecorder = () => recorderInstance
    })

    afterEach(() => {
      global.fetch = savedFetch
      global.MediaRecorder = savedMediaRecorder
      global.AudioContext = savedAudioContext
      if (savedGetUserMedia !== undefined) {
        navigator.mediaDevices.getUserMedia = savedGetUserMedia
      }
      delete global.__getRecorder
      delete global.speechSynthesis
      delete global.SpeechSynthesisUtterance
    })

    it('"Add to flashcards" appears after translation and calls onAddFlashcards(spanish, "translation")', async () => {
      const onAddFlashcards = vi.fn().mockResolvedValue({ added: 1 })

      render(<TranslationView config={DEFAULT_CONFIG} onAddFlashcards={onAddFlashcards} />)

      // Start recording
      fireEvent.click(screen.getByText('Record English phrase'))

      // Wait until recording is active
      await waitFor(() => screen.getByText('Stop Recording'))

      // Stop recording — this triggers onstop → submitAudio → fetch → setResult
      await act(async () => {
        fireEvent.click(screen.getByText('Stop Recording'))
        // Allow the MediaRecorder.stop mock and fetch to resolve
        await new Promise((r) => setTimeout(r, 0))
      })

      // Wait for the "Add to flashcards" button to appear
      const addBtn = await waitFor(() => screen.getByText('Add to flashcards'))

      // Click the button
      fireEvent.click(addBtn)

      // Assert onAddFlashcards was called with the Spanish text and source
      await waitFor(() => {
        expect(onAddFlashcards).toHaveBeenCalledWith('Hola mundo', 'translation')
      })
    })
  })
})
