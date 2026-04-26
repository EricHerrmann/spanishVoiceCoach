import { render, screen, waitFor } from '@testing-library/react'
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

const MOCK_TOPICS = [
  { id: 'general', label: 'General', starter: 'Hola, ¿cómo estás?' },
  { id: 'food', label: 'Food', starter: '¿Qué quieres comer?' },
]

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url === '/topics') return Promise.resolve({ json: () => Promise.resolve(MOCK_TOPICS) })
    return Promise.resolve({ json: () => Promise.resolve([]) })
  }))
})

afterEach(() => { vi.unstubAllGlobals() })

describe('App — conversation hint from topic starter', () => {
  it('shows topic starter phrase as hint when topics load', async () => {
    render(<App />)
    await waitFor(() => expect(screen.getByText('Hola, ¿cómo estás?')).toBeInTheDocument())
  })

  it('shows "Try saying" label for topic starter hint', async () => {
    render(<App />)
    await waitFor(() => expect(screen.getByText('Try saying')).toBeInTheDocument())
  })
})
