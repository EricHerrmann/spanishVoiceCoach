import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import NavTabs from '../components/NavTabs'

describe('NavTabs', () => {
  it('renders all four tabs', () => {
    render(<NavTabs mode="conversation" onModeChange={vi.fn()} />)
    expect(screen.getByText('Conversation')).toBeInTheDocument()
    expect(screen.getByText('Flashcards')).toBeInTheDocument()
    expect(screen.getByText('Translation')).toBeInTheDocument()
    expect(screen.getByText('Pronunciation')).toBeInTheDocument()
  })

  it('active tab has nav-tab--active class', () => {
    render(<NavTabs mode="flashcards" onModeChange={vi.fn()} />)
    expect(screen.getByText('Flashcards')).toHaveClass('nav-tab--active')
    expect(screen.getByText('Conversation')).not.toHaveClass('nav-tab--active')
  })

  it('clicking a tab calls onModeChange with correct id', () => {
    const onModeChange = vi.fn()
    render(<NavTabs mode="conversation" onModeChange={onModeChange} />)
    fireEvent.click(screen.getByText('Translation'))
    expect(onModeChange).toHaveBeenCalledWith('translation')
  })
})
