import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SessionConfig from '../components/SessionConfig'

const TOPICS = [
  { id: 'general', label: 'General conversation', starter: 'Hola' },
  { id: 'ordering_food', label: 'Ordering food', starter: 'Hola menú' },
]
const PROVIDERS = [{ id: 'claude', label: 'Claude (Anthropic)' }]
const TTS_VOICES = [
  { id: '21m00Tcm4TlvDq8ikWAM', label: 'Rachel — Female, clear (multilingual)' },
  { id: 'ErXwobaYiN019PkySvjV', label: 'Antoni — Male, natural (multilingual)' },
]
const DEFAULT_CONFIG = {
  topic: 'general',
  level: 5,
  ai_provider: 'claude',
  coaching_mode: 'on_demand',
  tts_provider: 'browser',
  tts_voice_id: null,
}

function renderConfig(overrides = {}) {
  const props = {
    config: DEFAULT_CONFIG,
    onConfigChange: vi.fn(),
    topics: TOPICS,
    providers: PROVIDERS,
    ttsVoices: TTS_VOICES,
    onNewSession: vi.fn(),
    state: 'idle',
    ...overrides,
  }
  const { container } = render(<SessionConfig {...props} />)
  return { ...props, container }
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

  it('shows the selected preset starter phrase', () => {
    renderConfig()
    expect(screen.getByText('Hola')).toBeInTheDocument()
  })

  it('updates the starter phrase when a different preset topic is selected', () => {
    renderConfig({ config: { ...DEFAULT_CONFIG, topic: 'ordering_food' } })
    expect(screen.getByText('Hola menú')).toBeInTheDocument()
  })

  it('selecting Custom reveals a text input', () => {
    const props = renderConfig()
    fireEvent.change(screen.getByLabelText(/topic/i), { target: { value: 'custom' } })
    expect(screen.getByPlaceholderText(/enter a topic/i)).toBeInTheDocument()
    expect(props.onConfigChange).toHaveBeenCalledWith({ topic: '' })
  })

  it('selecting Custom hides the preset starter phrase', () => {
    renderConfig()
    fireEvent.change(screen.getByLabelText(/topic/i), { target: { value: 'custom' } })
    expect(screen.queryByText('Hola')).not.toBeInTheDocument()
  })

  it('does not treat the default topic as custom while topics are loading', () => {
    renderConfig({ topics: [] })
    expect(screen.queryByPlaceholderText(/enter a topic/i)).not.toBeInTheDocument()
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
    fireEvent.change(screen.getByLabelText(/ai provider/i), { target: { value: 'claude' } })
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

describe('SessionConfig — TTS provider', () => {
  it('renders voice select with browser and elevenlabs options', () => {
    renderConfig()
    expect(screen.getByRole('option', { name: /browser/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /elevenlabs/i })).toBeInTheDocument()
  })

  it('shows browser as default selected voice provider', () => {
    renderConfig()
    expect(screen.getByLabelText(/^voice$/i).value).toBe('browser')
  })

  it('hides voice dropdown when browser is selected', () => {
    renderConfig()
    expect(screen.queryByLabelText(/elevenlabs voice/i)).not.toBeInTheDocument()
  })

  it('shows voice dropdown when elevenlabs is selected', () => {
    renderConfig({
      config: { ...DEFAULT_CONFIG, tts_provider: 'elevenlabs', tts_voice_id: TTS_VOICES[0].id },
    })
    expect(screen.getByLabelText(/elevenlabs voice/i)).toBeInTheDocument()
  })

  it('voice dropdown lists all curated voices', () => {
    renderConfig({
      config: { ...DEFAULT_CONFIG, tts_provider: 'elevenlabs', tts_voice_id: TTS_VOICES[0].id },
    })
    expect(screen.getByRole('option', { name: /rachel/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /antoni/i })).toBeInTheDocument()
  })

  it('calls onConfigChange with tts_provider and first voice when switching to elevenlabs', () => {
    const { onConfigChange } = renderConfig()
    fireEvent.change(screen.getByLabelText(/^voice$/i), { target: { value: 'elevenlabs' } })
    expect(onConfigChange).toHaveBeenCalledWith({
      tts_provider: 'elevenlabs',
      tts_voice_id: TTS_VOICES[0].id,
    })
  })

  it('calls onConfigChange with null voice_id when switching back to browser', () => {
    const { onConfigChange } = renderConfig({
      config: { ...DEFAULT_CONFIG, tts_provider: 'elevenlabs', tts_voice_id: TTS_VOICES[0].id },
    })
    fireEvent.change(screen.getByLabelText(/^voice$/i), { target: { value: 'browser' } })
    expect(onConfigChange).toHaveBeenCalledWith({
      tts_provider: 'browser',
      tts_voice_id: null,
    })
  })

  it('calls onConfigChange with tts_voice_id when voice changes', () => {
    const { onConfigChange } = renderConfig({
      config: { ...DEFAULT_CONFIG, tts_provider: 'elevenlabs', tts_voice_id: TTS_VOICES[0].id },
    })
    fireEvent.change(screen.getByLabelText(/elevenlabs voice/i), {
      target: { value: TTS_VOICES[1].id },
    })
    expect(onConfigChange).toHaveBeenCalledWith({ tts_voice_id: TTS_VOICES[1].id })
  })
})

describe('SessionConfig — collapsible wrapper', () => {
  it('renders inside a details element', () => {
    const { container } = renderConfig()
    expect(container.querySelector('details')).toBeInTheDocument()
  })

  it('details element is collapsed by default', () => {
    const { container } = renderConfig()
    expect(container.querySelector('details')).not.toHaveAttribute('open')
  })

  it('details element has a summary with text matching Session Config', () => {
    const { container } = renderConfig()
    const summary = container.querySelector('details > summary')
    expect(summary).toBeInTheDocument()
    expect(summary.textContent).toMatch(/session config/i)
  })
})
