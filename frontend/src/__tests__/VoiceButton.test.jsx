import { render, screen, fireEvent, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import VoiceButton from '../components/VoiceButton'

describe('VoiceButton', () => {
  it('renders in idle state initially', () => {
    render(<VoiceButton state="idle" onRecord={() => {}} onStop={() => {}} />)
    expect(screen.getByRole('button')).toHaveTextContent(/record|start|speak/i)
  })

  it('shows recording state when state is recording', () => {
    render(<VoiceButton state="recording" onRecord={() => {}} onStop={() => {}} />)
    expect(screen.getByRole('button')).toHaveTextContent(/stop|recording/i)
  })

  it('shows processing state when state is processing', () => {
    render(<VoiceButton state="processing" onRecord={() => {}} onStop={() => {}} />)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('shows playing state when state is playing', () => {
    render(<VoiceButton state="playing" onRecord={() => {}} onStop={() => {}} />)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })

  it('calls onRecord when clicked in idle state', () => {
    const onRecord = vi.fn()
    render(<VoiceButton state="idle" onRecord={onRecord} onStop={() => {}} />)
    fireEvent.click(screen.getByRole('button'))
    expect(onRecord).toHaveBeenCalledOnce()
  })

  it('calls onStop when clicked in recording state', () => {
    const onStop = vi.fn()
    render(<VoiceButton state="recording" onRecord={() => {}} onStop={onStop} />)
    fireEvent.click(screen.getByRole('button'))
    expect(onStop).toHaveBeenCalledOnce()
  })

  it('shows retry prompt when error is recoverable', () => {
    const error = { stage: 'stt', message: 'Transcription failed', recoverable: true }
    render(<VoiceButton state="idle" onRecord={() => {}} onStop={() => {}} error={error} />)
    expect(screen.getByText(/try again|retry/i)).toBeInTheDocument()
  })

  it('does not show retry prompt when there is no error', () => {
    render(<VoiceButton state="idle" onRecord={() => {}} onStop={() => {}} error={null} />)
    expect(screen.queryByText(/try again|retry/i)).not.toBeInTheDocument()
  })
})
