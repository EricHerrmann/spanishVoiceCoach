import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SessionConfig from '../components/SessionConfig'

describe('SessionConfig', () => {
  it('renders a select with three coaching mode options', () => {
    render(<SessionConfig coachingMode="on_demand" onCoachingModeChange={() => {}} />)
    const select = screen.getByLabelText(/coaching mode/i)
    expect(select).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /on demand/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /explicit/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /shadowing/i })).toBeInTheDocument()
  })

  it('shows the current coaching mode as selected', () => {
    render(<SessionConfig coachingMode="explicit" onCoachingModeChange={() => {}} />)
    expect(screen.getByLabelText(/coaching mode/i).value).toBe('explicit')
  })

  it('calls onCoachingModeChange with the new value when changed', () => {
    const onChange = vi.fn()
    render(<SessionConfig coachingMode="on_demand" onCoachingModeChange={onChange} />)
    fireEvent.change(screen.getByLabelText(/coaching mode/i), { target: { value: 'shadowing' } })
    expect(onChange).toHaveBeenCalledWith('shadowing')
  })
})
