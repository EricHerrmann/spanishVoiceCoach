import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, afterEach } from 'vitest'
import FlashcardButton from '../components/FlashcardButton'

afterEach(() => {
  vi.useRealTimers()
})

describe('FlashcardButton', () => {
  it('renders with provided label', () => {
    render(<FlashcardButton label="Add to flashcards" onAdd={vi.fn()} />)
    expect(screen.getByText('Add to flashcards')).toBeInTheDocument()
  })

  it('shows loading state while onAdd is pending', async () => {
    let resolve
    const onAdd = () => new Promise((r) => { resolve = r })
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    expect(screen.getByText('...')).toBeInTheDocument()
    await act(async () => { resolve({ added: 1 }) })
  })

  it('shows count on success with cards added', async () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 2 })
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(screen.getByText('✓ 2 added')).toBeInTheDocument())
  })

  it('shows already in deck when count is 0', async () => {
    const onAdd = vi.fn().mockResolvedValue({ added: 0 })
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(screen.getByText('✓ Already in deck')).toBeInTheDocument())
  })

  it('shows error state on failure', async () => {
    const onAdd = vi.fn().mockRejectedValue(new Error('Network error'))
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(screen.getByText('Error')).toBeInTheDocument())
  })

  it('is disabled while loading', async () => {
    let resolve
    const onAdd = () => new Promise((r) => { resolve = r })
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(screen.getByText('...')).toBeDisabled())
    await act(async () => { resolve({ added: 0 }) })
  })

  it('returns to idle after 2 seconds on success', async () => {
    const setTimeoutSpy = vi.spyOn(global, 'setTimeout')
    const onAdd = vi.fn().mockResolvedValue({ added: 1 })
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(screen.getByText('✓ 1 added')).toBeInTheDocument())
    expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 2000)
    setTimeoutSpy.mockRestore()
  })

  it('returns to idle after 2 seconds on error', async () => {
    const setTimeoutSpy = vi.spyOn(global, 'setTimeout')
    const onAdd = vi.fn().mockRejectedValue(new Error('fail'))
    render(<FlashcardButton label="Add to flashcards" onAdd={onAdd} />)
    fireEvent.click(screen.getByText('Add to flashcards'))
    await waitFor(() => expect(screen.getByText('Error')).toBeInTheDocument())
    expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 2000)
    setTimeoutSpy.mockRestore()
  })
})
