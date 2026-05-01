import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import PronunciationView from '../components/PronunciationView'

const MOCK_TOPICS = [{ id: 'general', label: 'General' }]
const MOCK_DECK = [
  { id: 'g001', english: 'hello', spanish: 'hola', level: 1, topic: 'general' },
  { id: 'g002', english: 'goodbye', spanish: 'adiós', level: 1, topic: 'general' },
]
const MOCK_CHALLENGES = [
  { id: 'pc001', target: 'perro', sound_focus: 'rr', hint: 'Roll the rr sound.' },
  { id: 'pc002', target: 'España', sound_focus: 'ñ', hint: 'Nasal palatal sound.' },
]
const DEFAULT_CONFIG = { ai_provider: 'claude', ai_model: 'claude-sonnet-4-6' }

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url.includes('/topics')) {
      return Promise.resolve({ json: () => Promise.resolve(MOCK_TOPICS) })
    }
    if (url.includes('/flashcards/deck')) {
      return Promise.resolve({ json: () => Promise.resolve(MOCK_DECK) })
    }
    if (url.includes('/pronunciation/challenges')) {
      return Promise.resolve({ json: () => Promise.resolve(MOCK_CHALLENGES) })
    }
    return Promise.resolve({ json: () => Promise.resolve([]) })
  }))
})

afterEach(() => { vi.unstubAllGlobals() })

describe('PronunciationView — vocabulary tab (default)', () => {
  it('shows Vocabulary tab as active by default', async () => {
    render(<PronunciationView config={DEFAULT_CONFIG} />)
    await waitFor(() => expect(screen.getByText('Vocabulary')).toBeInTheDocument())
    expect(screen.getByText('Vocabulary').className).toContain('pronunciation-tab--active')
  })

  it('shows Spanish target text from vocab deck', async () => {
    render(<PronunciationView config={DEFAULT_CONFIG} />)
    await waitFor(() => expect(screen.getByText('hola')).toBeInTheDocument())
  })

  it('Record button is present when a target is shown', async () => {
    render(<PronunciationView config={DEFAULT_CONFIG} />)
    await waitFor(() => screen.getByText('hola'))
    expect(screen.getByText('Record')).toBeInTheDocument()
  })

  it('Next card advances to second card', async () => {
    render(<PronunciationView config={DEFAULT_CONFIG} />)
    await waitFor(() => screen.getByText('hola'))
    fireEvent.click(screen.getByText('Next card'))
    expect(screen.getByText('adiós')).toBeInTheDocument()
  })
})

describe('PronunciationView — challenges tab', () => {
  it('switching to Challenges tab shows challenge list', async () => {
    render(<PronunciationView config={DEFAULT_CONFIG} />)
    await waitFor(() => screen.getByText('Challenges'))
    fireEvent.click(screen.getByText('Challenges'))
    await waitFor(() => expect(screen.getByText('perro')).toBeInTheDocument())
  })

  it('clicking a challenge sets it as the target', async () => {
    render(<PronunciationView config={DEFAULT_CONFIG} />)
    await waitFor(() => screen.getByText('Challenges'))
    fireEvent.click(screen.getByText('Challenges'))
    await waitFor(() => screen.getByText('perro'))
    fireEvent.click(screen.getByText('perro'))
    expect(screen.getByText(/Roll the rr sound/)).toBeInTheDocument()
  })
})

describe('PronunciationView — single-phrase mode', () => {
  it('when pronunciationTarget is set, shows that phrase without tabs', () => {
    render(<PronunciationView config={DEFAULT_CONFIG} pronunciationTarget={{ text: 'Muy bien, gracias.', source: 'conversation' }} onClearTarget={vi.fn()} />)
    expect(screen.getByText('Muy bien, gracias.')).toBeInTheDocument()
    expect(screen.queryByText('Vocabulary')).not.toBeInTheDocument()
    expect(screen.queryByText('Challenges')).not.toBeInTheDocument()
  })

  it('shows a back button in single-phrase mode', () => {
    render(<PronunciationView config={DEFAULT_CONFIG} pronunciationTarget={{ text: 'Muy bien.', source: 'conversation' }} onClearTarget={vi.fn()} />)
    expect(screen.getByText('← Back')).toBeInTheDocument()
  })

  it('back button calls onClearTarget', () => {
    const onClearTarget = vi.fn()
    render(<PronunciationView config={DEFAULT_CONFIG} pronunciationTarget={{ text: 'Muy bien.', source: 'conversation' }} onClearTarget={onClearTarget} />)
    fireEvent.click(screen.getByText('← Back'))
    expect(onClearTarget).toHaveBeenCalled()
  })

  it('shows "From conversation" source label when source is conversation', () => {
    render(<PronunciationView config={DEFAULT_CONFIG} pronunciationTarget={{ text: 'Muy bien.', source: 'conversation' }} onClearTarget={vi.fn()} />)
    expect(screen.getByText('From conversation')).toBeInTheDocument()
  })

  it('shows "From translation" source label when source is translation', () => {
    render(<PronunciationView config={DEFAULT_CONFIG} pronunciationTarget={{ text: 'El gato es bonito.', source: 'translation' }} onClearTarget={vi.fn()} />)
    expect(screen.getByText('From translation')).toBeInTheDocument()
  })
})
