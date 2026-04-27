import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'

const MOCK_TURNS = [
  { speaker: 'user', transcript_norm: 'Quisiera una mesa', coach_text: null },
  { speaker: 'coach', transcript_norm: null, coach_text: '¿Para cuántas personas?' },
]

vi.mock('../hooks/useVoice', () => ({
  useVoice: () => ({
    state: 'idle',
    turns: MOCK_TURNS,
    corrections: [],
    error: null,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    newSession: vi.fn(() => Promise.resolve('session-test')),
    loadSession: vi.fn(),
  }),
}))

let fetchMock

beforeEach(() => {
  localStorage.clear()
  fetchMock = vi.fn().mockImplementation((url) => {
    if (url === '/flashcards/generate') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { id: 'u-1', english: 'a table', spanish: 'una mesa', level: 2, topic: 'ordering_food' },
        ]),
      })
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App — handleAddFlashcards', () => {
  it('calls POST /flashcards/generate with turn source and turns array', async () => {
    render(<App />)
    await waitFor(() => screen.getAllByText('Add to flashcards'))
    fireEvent.click(screen.getAllByText('Add to flashcards')[0])

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url === '/flashcards/generate')
      expect(call).toBeDefined()
      const body = JSON.parse(call[1].body)
      expect(body.source).toBe('turn')
      expect(Array.isArray(body.turns)).toBe(true)
      expect(body.turns).toHaveLength(2)
    })

    await waitFor(() => {
      expect(screen.getAllByText('✓ 1 added').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('calls POST /flashcards/generate with conversation source when "Add conversation" clicked', async () => {
    render(<App />)
    await waitFor(() => screen.getByText('Add conversation'))
    fireEvent.click(screen.getByText('Add conversation'))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url === '/flashcards/generate')
      expect(call).toBeDefined()
      const body = JSON.parse(call[1].body)
      expect(body.source).toBe('conversation')
    })
  })
})
