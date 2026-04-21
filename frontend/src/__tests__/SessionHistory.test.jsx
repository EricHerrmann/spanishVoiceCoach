import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SessionHistory from '../components/SessionHistory'

const SESSIONS = [
  {
    id: 'session-1',
    topic: 'general',
    level: 5,
    coaching_mode: 'on_demand',
    turn_count: 2,
    correction_count: 0,
  },
  {
    id: 'session-2',
    topic: 'ordering_food',
    level: 3,
    coaching_mode: 'explicit',
    turn_count: 4,
    correction_count: 1,
  },
]

function renderHistory(overrides = {}) {
  const props = {
    sessions: SESSIONS,
    selectedSessionId: null,
    onSelectSession: vi.fn(),
    onRefresh: vi.fn(),
    ...overrides,
  }
  render(<SessionHistory {...props} />)
  return props
}

describe('SessionHistory', () => {
  it('renders an empty state when no sessions exist', () => {
    renderHistory({ sessions: [] })
    expect(screen.getByText(/no saved sessions yet/i)).toBeInTheDocument()
  })

  it('renders saved session metadata', () => {
    renderHistory()
    expect(screen.getByText('general')).toBeInTheDocument()
    expect(screen.getByText(/level 5 .* on_demand .* 2 turns .* 0 corrections/i)).toBeInTheDocument()
    expect(screen.getByText('ordering_food')).toBeInTheDocument()
    expect(screen.getByText(/level 3 .* explicit .* 4 turns .* 1 corrections/i)).toBeInTheDocument()
  })

  it('calls onSelectSession with the selected id', () => {
    const { onSelectSession } = renderHistory()
    fireEvent.click(screen.getByRole('button', { name: /ordering_food/i }))
    expect(onSelectSession).toHaveBeenCalledWith('session-2')
  })

  it('calls onRefresh when refresh is clicked', () => {
    const { onRefresh } = renderHistory()
    fireEvent.click(screen.getByRole('button', { name: /refresh/i }))
    expect(onRefresh).toHaveBeenCalledOnce()
  })

  it('marks the selected session', () => {
    renderHistory({ selectedSessionId: 'session-1' })
    expect(screen.getByRole('button', { name: /general/i })).toHaveClass('is-selected')
  })
})
