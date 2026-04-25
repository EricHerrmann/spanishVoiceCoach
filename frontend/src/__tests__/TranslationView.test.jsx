import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
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
})
