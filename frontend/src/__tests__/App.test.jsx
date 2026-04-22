import { render } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'

vi.mock('../hooks/useVoice', () => ({
  useVoice: () => ({
    state: 'idle',
    turns: [],
    corrections: [],
    error: null,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    newSession: vi.fn(() => Promise.resolve('session-test')),
    loadSession: vi.fn(),
  }),
}))

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    json: () => Promise.resolve([]),
  }))
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App — two-pane layout', () => {
  it('renders left pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-left')).toBeInTheDocument()
  })

  it('renders right pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-right')).toBeInTheDocument()
  })

  it('renders Transcript inside left pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-left .transcript')).toBeInTheDocument()
  })

  it('renders VoiceButton container inside left pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-left .voice-button-container')).toBeInTheDocument()
  })

  it('renders SessionConfig details inside right pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-right .session-config-details')).toBeInTheDocument()
  })

  it('renders SessionHistory inside right pane', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.app-right .session-history')).toBeInTheDocument()
  })

  it('renders drawer toggle button', () => {
    const { container } = render(<App />)
    expect(container.querySelector('.drawer-toggle')).toBeInTheDocument()
  })
})
