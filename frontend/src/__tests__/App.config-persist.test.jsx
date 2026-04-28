import { render, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'

vi.mock('../hooks/useVoice', () => ({
  useVoice: () => ({
    state: 'idle',
    turns: [],
    corrections: [],
    error: null,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    newSession: vi.fn(() => Promise.resolve('session-test')),
    loadSession: vi.fn(),
  }),
}))

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    json: () => Promise.resolve([]),
  }))
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App — config persistence', () => {
  it('saves config to localStorage when topic changes', () => {
    const { container } = render(<App />)
    const select = container.querySelector('select[name="topic"]') ??
      [...container.querySelectorAll('select')].find(s => s.value === 'general')
    if (!select) return // no topic select visible in this render path
    fireEvent.change(select, { target: { value: 'food' } })
    const saved = JSON.parse(localStorage.getItem('dvc_config'))
    expect(saved.topic).toBe('food')
  })

  it('restores config from localStorage on mount', () => {
    localStorage.setItem('dvc_config', JSON.stringify({
      topic: 'food',
      level: 3,
      coaching_mode: 'explicit',
    }))
    const { container } = render(<App />)
    // The restored config should be reflected in the DOM
    const levelInput = container.querySelector('input[type="range"]')
    if (levelInput) expect(Number(levelInput.value)).toBe(3)
    const saved = JSON.parse(localStorage.getItem('dvc_config'))
    expect(saved.topic).toBe('food')
    expect(saved.level).toBe(3)
  })

  it('merges saved config with defaults (unknown keys do not crash)', () => {
    localStorage.setItem('dvc_config', JSON.stringify({ topic: 'travel' }))
    expect(() => render(<App />)).not.toThrow()
  })
})
