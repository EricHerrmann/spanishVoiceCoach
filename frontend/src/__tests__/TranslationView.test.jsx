import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
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
