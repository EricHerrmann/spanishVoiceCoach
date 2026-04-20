import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
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
