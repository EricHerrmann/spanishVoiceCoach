import { render, screen, act } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import CoachOverlay from '../components/CoachOverlay'

describe('CoachOverlay', () => {
  it('renders nothing when corrections list is empty', () => {
    const { container } = render(<CoachOverlay corrections={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when corrections is null', () => {
    const { container } = render(<CoachOverlay corrections={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders original, corrected, and explanation for a single correction', () => {
    const corrections = [{
      original: 'yo fui',
      corrected: 'fui',
      explanation: "'yo' is optional in Spanish",
      triggered_by: 'auto',
    }]
    render(<CoachOverlay corrections={corrections} />)
    expect(screen.getByText('yo fui')).toBeInTheDocument()
    expect(screen.getByText('fui')).toBeInTheDocument()
    expect(screen.getByText(/'yo' is optional in Spanish/)).toBeInTheDocument()
  })

  it('renders multiple corrections', () => {
    const corrections = [
      { original: 'yo fui', corrected: 'fui', explanation: 'Optional pronoun', triggered_by: 'auto' },
      { original: 'el mercado', corrected: 'al mercado', explanation: "Missing 'a' contraction", triggered_by: 'user_request' },
    ]
    render(<CoachOverlay corrections={corrections} />)
    expect(screen.getByText('yo fui')).toBeInTheDocument()
    expect(screen.getByText('el mercado')).toBeInTheDocument()
  })
})

describe('CoachOverlay — auto-dismiss timer', () => {
  it('auto-dismisses after 8 seconds', () => {
    vi.useFakeTimers()
    const corrections = [
      { original: 'yo fui', corrected: 'fui', explanation: 'Optional pronoun', triggered_by: 'auto' },
    ]
    render(<CoachOverlay corrections={corrections} />)
    expect(screen.getByText('yo fui')).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(8000) })
    expect(screen.queryByText('yo fui')).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  it('resets the timer when new corrections arrive', () => {
    vi.useFakeTimers()
    const corrections1 = [
      { original: 'yo fui', corrected: 'fui', explanation: 'Optional pronoun', triggered_by: 'auto' },
    ]
    const corrections2 = [
      { original: 'el mercado', corrected: 'al mercado', explanation: 'Missing contraction', triggered_by: 'user_request' },
    ]
    const { rerender } = render(<CoachOverlay corrections={corrections1} />)
    act(() => { vi.advanceTimersByTime(5000) })
    rerender(<CoachOverlay corrections={corrections2} />)
    expect(screen.getByText('el mercado')).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(5000) })
    expect(screen.getByText('el mercado')).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(3000) })
    expect(screen.queryByText('el mercado')).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  it('hides immediately when corrections become empty', () => {
    vi.useFakeTimers()
    const corrections = [
      { original: 'yo fui', corrected: 'fui', explanation: 'Optional pronoun', triggered_by: 'auto' },
    ]
    const { rerender } = render(<CoachOverlay corrections={corrections} />)
    expect(screen.getByText('yo fui')).toBeInTheDocument()
    rerender(<CoachOverlay corrections={[]} />)
    expect(screen.queryByText('yo fui')).not.toBeInTheDocument()
    vi.useRealTimers()
  })
})
