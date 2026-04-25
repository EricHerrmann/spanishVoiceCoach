import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import FlashcardsView from '../components/FlashcardsView'

const MOCK_TOPICS = [{ id: 'general', label: 'General' }]
const MOCK_DECK = [
  { id: 'f001', english: 'hello', spanish: 'hola', level: 1, topic: 'general' },
  { id: 'f002', english: 'goodbye', spanish: 'adiós', level: 1, topic: 'general' },
]

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url.includes('/topics')) {
      return Promise.resolve({ json: () => Promise.resolve(MOCK_TOPICS) })
    }
    if (url.includes('/flashcards/deck')) {
      return Promise.resolve({ json: () => Promise.resolve(MOCK_DECK) })
    }
    return Promise.resolve({ json: () => Promise.resolve([]) })
  }))
})

afterEach(() => { vi.unstubAllGlobals() })

describe('FlashcardsView', () => {
  it('shows English side of first card by default', async () => {
    render(<FlashcardsView />)
    await waitFor(() => expect(screen.getByText('hello')).toBeInTheDocument())
    expect(screen.queryByText('hola')).not.toBeInTheDocument()
  })

  it('flips to Spanish when card is clicked', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    fireEvent.click(screen.getByText('hello'))
    expect(screen.getByText('hola')).toBeInTheDocument()
  })

  it('Next advances to second card and resets flip state', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    fireEvent.click(screen.getByText('hello'))
    fireEvent.click(screen.getByText('Next'))
    expect(screen.getByText('goodbye')).toBeInTheDocument()
    expect(screen.queryByText('adiós')).not.toBeInTheDocument()
  })

  it('Previous is disabled on first card', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    expect(screen.getByText('Previous')).toBeDisabled()
  })

  it('shows completion message after advancing past last card', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    expect(screen.getByText(/Deck complete/)).toBeInTheDocument()
  })

  it('Restart resets to first card', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Restart'))
    expect(screen.getByText('hello')).toBeInTheDocument()
  })

  it('changing band triggers a new fetch with correct level params', async () => {
    render(<FlashcardsView />)
    await waitFor(() => screen.getByText('hello'))
    fireEvent.click(screen.getByText('Beginner'))
    await waitFor(() => {
      expect(vi.mocked(fetch)).toHaveBeenCalledWith(
        expect.stringContaining('level_min=1'),
      )
    })
  })
})
