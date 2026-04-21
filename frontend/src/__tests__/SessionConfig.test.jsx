import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SessionConfig from '../components/SessionConfig'

const TOPICS = [
  { id: 'general', label: 'General conversation', starter: 'Hola' },
  { id: 'ordering_food', label: 'Ordering food', starter: 'Hola menú' },
]
const PROVIDERS = [{ id: 'claude', label: 'Claude (Anthropic)' }]
const DEFAULT_CONFIG = {
  topic: 'general',
  level: 5,
  ai_provider: 'claude',
  coaching_mode: 'on_demand',
}

function renderConfig(overrides = {}) {
  const props = {
    config: DEFAULT_CONFIG,
    onConfigChange: vi.fn(),
    topics: TOPICS,
    providers: PROVIDERS,
    onNewSession: vi.fn(),
    state: 'idle',
    ...overrides,
  }
  render(<SessionConfig {...props} />)
  return props
}

describe('SessionConfig — coaching mode', () => {
  it('renders coaching mode select with three options', () => {
    renderConfig()
    const select = screen.getByLabelText(/coaching mode/i)
    expect(select).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /on demand/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /explicit/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /shadowing/i })).toBeInTheDocument()
  })

  it('shows current coaching mode as selected', () => {
    renderConfig({ config: { ...DEFAULT_CONFIG, coaching_mode: 'explicit' } })
    expect(screen.getByLabelText(/coaching mode/i).value).toBe('explicit')
  })

  it('calls onConfigChange when coaching mode changes', () => {
    const { onConfigChange } = renderConfig()
    fireEvent.change(screen.getByLabelText(/coaching mode/i), { target: { value: 'shadowing' } })
    expect(onConfigChange).toHaveBeenCalledWith({ coaching_mode: 'shadowing' })
  })
})

describe('SessionConfig — topic picker', () => {
  it('renders topic select with preset options plus Custom', () => {
    renderConfig()
    expect(screen.getByRole('option', { name: /general conversation/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /ordering food/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /custom/i })).toBeInTheDocument()
  })

  it('selecting Custom reveals a text input', () => {
    renderConfig()
    fireEvent.change(screen.getByLabelText(/topic/i), { target: { value: 'custom' } })
    expect(screen.getByPlaceholderText(/enter a topic/i)).toBeInTheDocument()
  })

  it('calls onConfigChange when a preset topic is selected', () => {
    const { onConfigChange } = renderConfig()
    fireEvent.change(screen.getByLabelText(/topic/i), { target: { value: 'ordering_food' } })
    expect(onConfigChange).toHaveBeenCalledWith({ topic: 'ordering_food' })
  })
})

describe('SessionConfig — level slider', () => {
  it('renders level slider with min 1 and max 10', () => {
    renderConfig()
    const slider = screen.getByLabelText(/level/i)
    expect(slider).toHaveAttribute('type', 'range')
    expect(slider).toHaveAttribute('min', '1')
    expect(slider).toHaveAttribute('max', '10')
  })

  it('calls onConfigChange with a numeric level when slider changes', () => {
    const { onConfigChange } = renderConfig()
    fireEvent.change(screen.getByLabelText(/level/i), { target: { value: '7' } })
    expect(onConfigChange).toHaveBeenCalledWith({ level: 7 })
  })
})

describe('SessionConfig — provider select', () => {
  it('renders provider select with Claude option', () => {
    renderConfig()
    expect(screen.getByRole('option', { name: /claude \(anthropic\)/i })).toBeInTheDocument()
  })

  it('calls onConfigChange when provider changes', () => {
    const { onConfigChange } = renderConfig()
    fireEvent.change(screen.getByLabelText(/provider/i), { target: { value: 'claude' } })
    expect(onConfigChange).toHaveBeenCalledWith({ ai_provider: 'claude' })
  })
})

describe('SessionConfig — New Conversation button', () => {
  it('calls onNewSession when clicked', () => {
    const { onNewSession } = renderConfig()
    fireEvent.click(screen.getByRole('button', { name: /new conversation/i }))
    expect(onNewSession).toHaveBeenCalled()
  })

  it('is disabled when state is not idle', () => {
    renderConfig({ state: 'recording' })
    expect(screen.getByRole('button', { name: /new conversation/i })).toBeDisabled()
  })

  it('is enabled when state is idle', () => {
    renderConfig({ state: 'idle' })
    expect(screen.getByRole('button', { name: /new conversation/i })).not.toBeDisabled()
  })
})
