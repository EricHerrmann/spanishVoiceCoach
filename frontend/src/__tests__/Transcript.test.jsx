import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import Transcript from '../components/Transcript'

describe('Transcript', () => {
  it('renders nothing when turns is empty', () => {
    const { container } = render(<Transcript turns={[]} />)
    expect(container.querySelector('.transcript')).toBeInTheDocument()
    expect(screen.queryByRole('listitem')).not.toBeInTheDocument()
  })

  it('renders user turn with transcript_norm', () => {
    const turns = [{ speaker: 'user', transcript_norm: 'hola como estás', echo: null }]
    render(<Transcript turns={turns} />)
    expect(screen.getByText('hola como estás')).toBeInTheDocument()
  })

  it('renders coach echo response', () => {
    const turns = [
      { speaker: 'user', transcript_norm: 'hola', echo: null },
      { speaker: 'coach', transcript_norm: null, echo: 'hola' },
    ]
    render(<Transcript turns={turns} />)
    expect(screen.getAllByText('hola')).toHaveLength(2)
  })

  it('labels user turns distinctly from coach turns', () => {
    const turns = [
      { speaker: 'user', transcript_norm: 'hola', echo: null },
      { speaker: 'coach', transcript_norm: null, echo: 'hola' },
    ]
    render(<Transcript turns={turns} />)
    expect(screen.getByText(/you|user/i)).toBeInTheDocument()
    expect(screen.getByText(/coach/i)).toBeInTheDocument()
  })
})
