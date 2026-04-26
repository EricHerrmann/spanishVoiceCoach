import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ConversationView from '../components/ConversationView'

const defaultProps = {
  state: 'idle',
  turns: [],
  error: null,
  onRecord: vi.fn(),
  onStop: vi.fn(),
  onPractice: vi.fn(),
  coachingMode: 'on_demand',
}

describe('ConversationView — hint', () => {
  it('renders hint text when hint is provided', () => {
    render(<ConversationView {...defaultProps} hint={{ text: 'Hola, ¿cómo estás?', source: 'topic' }} />)
    expect(screen.getByText('Hola, ¿cómo estás?')).toBeInTheDocument()
  })

  it('shows "Try saying" label for topic source', () => {
    render(<ConversationView {...defaultProps} hint={{ text: 'Hola', source: 'topic' }} />)
    expect(screen.getByText('Try saying')).toBeInTheDocument()
  })

  it('shows "You translated" label for translation source', () => {
    render(<ConversationView {...defaultProps} hint={{ text: 'El gato es bonito.', source: 'translation' }} />)
    expect(screen.getByText('You translated')).toBeInTheDocument()
  })

  it('hides hint text after clicking Hide', () => {
    render(<ConversationView {...defaultProps} hint={{ text: 'Hola', source: 'topic' }} />)
    fireEvent.click(screen.getByText('Hide'))
    expect(screen.queryByText('Hola')).not.toBeInTheDocument()
  })

  it('shows hint text again after clicking Show', () => {
    render(<ConversationView {...defaultProps} hint={{ text: 'Hola', source: 'topic' }} />)
    fireEvent.click(screen.getByText('Hide'))
    fireEvent.click(screen.getByText('Show'))
    expect(screen.getByText('Hola')).toBeInTheDocument()
  })

  it('renders nothing hint-related when hint is null', () => {
    render(<ConversationView {...defaultProps} hint={null} />)
    expect(screen.queryByText('Try saying')).not.toBeInTheDocument()
    expect(screen.queryByText('You translated')).not.toBeInTheDocument()
  })
})
