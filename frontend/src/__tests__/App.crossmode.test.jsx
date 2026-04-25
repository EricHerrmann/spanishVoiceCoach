import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'

vi.mock('../hooks/useVoice', () => ({
  useVoice: () => ({
    state: 'idle',
    turns: [{ speaker: 'coach', coach_text: 'Muy bien, practiquemos.' }],
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

afterEach(() => { vi.unstubAllGlobals() })

describe('App — Practice button cross-mode handoff', () => {
  it('clicking Practice on a coach turn switches to PronunciationView', () => {
    const { container } = render(<App />)
    fireEvent.click(screen.getByText('Practice'))
    expect(container.querySelector('.pronunciation-view')).toBeInTheDocument()
    expect(container.querySelector('.transcript')).not.toBeInTheDocument()
  })

  it('Back button in PronunciationView returns to conversation', () => {
    const { container } = render(<App />)
    fireEvent.click(screen.getByText('Practice'))
    fireEvent.click(screen.getByText('← Back'))
    expect(container.querySelector('.transcript')).toBeInTheDocument()
    expect(container.querySelector('.pronunciation-view')).not.toBeInTheDocument()
  })
})
