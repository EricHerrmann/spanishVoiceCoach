import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Transcript from '../components/Transcript'

describe('Transcript', () => {
  it('renders nothing when turns is empty', () => {
    const { container } = render(<Transcript turns={[]} />)
    expect(container.querySelector('.transcript')).toBeInTheDocument()
    expect(screen.queryByRole('listitem')).not.toBeInTheDocument()
  })

  it('renders user turn with transcript_norm', () => {
    const turns = [{ speaker: 'user', transcript_norm: 'hola como estás', coach_text: null }]
    render(<Transcript turns={turns} />)
    expect(screen.getByText('hola como estás')).toBeInTheDocument()
  })

  it('renders coach turn with coach_text', () => {
    const turns = [
      { speaker: 'user', transcript_norm: 'hola', coach_text: null },
      { speaker: 'coach', transcript_norm: null, coach_text: '¡Hola! ¿Cómo estás?' },
    ]
    render(<Transcript turns={turns} />)
    expect(screen.getByText('hola')).toBeInTheDocument()
    expect(screen.getByText('¡Hola! ¿Cómo estás?')).toBeInTheDocument()
  })

  it('labels user turns distinctly from coach turns', () => {
    const turns = [
      { speaker: 'user', transcript_norm: 'hola', coach_text: null },
      { speaker: 'coach', transcript_norm: null, coach_text: '¡Hola!' },
    ]
    render(<Transcript turns={turns} />)
    expect(screen.getByText(/you|user/i)).toBeInTheDocument()
    expect(screen.getByText(/coach/i)).toBeInTheDocument()
  })
})

describe('Transcript — Practice button', () => {
  it('coach turns have a Practice button', () => {
    const turns = [
      { speaker: 'coach', coach_text: 'Muy bien, sigamos practicando.' },
    ]
    render(<Transcript turns={turns} onPractice={vi.fn()} />)
    expect(screen.getByText('Practice')).toBeInTheDocument()
  })

  it('user turns do not have a Practice button', () => {
    const turns = [
      { speaker: 'user', transcript_norm: 'Quiero hablar más.' },
    ]
    render(<Transcript turns={turns} onPractice={vi.fn()} />)
    expect(screen.queryByText('Practice')).not.toBeInTheDocument()
  })

  it('clicking Practice calls onPractice with the coach text', () => {
    const onPractice = vi.fn()
    const turns = [
      { speaker: 'coach', coach_text: 'Muy bien, sigamos practicando.' },
    ]
    render(<Transcript turns={turns} onPractice={onPractice} />)
    fireEvent.click(screen.getByText('Practice'))
    expect(onPractice).toHaveBeenCalledWith('Muy bien, sigamos practicando.', 'conversation')
  })

  it('works without onPractice prop (no crash)', () => {
    const turns = [{ speaker: 'coach', coach_text: 'Hola.' }]
    render(<Transcript turns={turns} />)
    fireEvent.click(screen.getByText('Practice'))
    // No error thrown
  })
})

describe('Transcript — flashcard buttons', () => {
  const twoTurns = [
    { speaker: 'user', transcript_norm: 'Hola', coach_text: null },
    { speaker: 'coach', transcript_norm: null, coach_text: '¡Hola!' },
  ]

  it('"Add to flashcards" button present on user turns', () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<Transcript turns={twoTurns} onAddFlashcards={onAdd} />)
    const addButtons = screen.getAllByText('Add to flashcards')
    expect(addButtons.length).toBeGreaterThanOrEqual(1)
  })

  it('"Add to flashcards" button present on coach turns', () => {
    const turns = [{ speaker: 'coach', transcript_norm: null, coach_text: '¡Hola!' }]
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<Transcript turns={turns} onAddFlashcards={onAdd} />)
    expect(screen.getByText('Add to flashcards')).toBeInTheDocument()
  })

  it('"Add conversation" button absent when turns.length < 2', () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<Transcript turns={[twoTurns[0]]} onAddFlashcards={onAdd} />)
    expect(screen.queryByText('Add conversation')).not.toBeInTheDocument()
  })

  it('"Add conversation" button present when turns.length >= 2', () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<Transcript turns={twoTurns} onAddFlashcards={onAdd} />)
    expect(screen.getByText('Add conversation')).toBeInTheDocument()
  })

  it('clicking "Add to flashcards" on a turn calls onAddFlashcards with source "turn"', async () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<Transcript turns={[twoTurns[0]]} onAddFlashcards={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(onAdd).toHaveBeenCalledWith('Hola', 'turn'))
  })

  it('clicking "Add conversation" calls onAddFlashcards with source "conversation"', async () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 2 })
    render(<Transcript turns={twoTurns} onAddFlashcards={onAdd} />)
    fireEvent.click(screen.getByText('Add conversation'))
    await waitFor(() => expect(onAdd).toHaveBeenCalledWith(null, 'conversation'))
  })

  it('flashcard buttons absent when onAddFlashcards prop is not provided', () => {
    render(<Transcript turns={twoTurns} />)
    expect(screen.queryByText('Add to flashcards')).not.toBeInTheDocument()
    expect(screen.queryByText('Add conversation')).not.toBeInTheDocument()
  })
})
