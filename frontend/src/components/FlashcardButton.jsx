import { useState } from 'react'

export default function FlashcardButton({ label, onAdd }) {
  const [status, setStatus] = useState('idle')
  const [count, setCount] = useState(0)

  async function handleClick() {
    if (status !== 'idle') return
    setStatus('loading')
    try {
      const result = await onAdd()
      setCount(result?.added ?? 0)
      setStatus('done')
      setTimeout(() => setStatus('idle'), 2000)
    } catch {
      setStatus('error')
      setTimeout(() => setStatus('idle'), 2000)
    }
  }

  const buttonLabel =
    status === 'loading' ? '...' :
    status === 'done' ? (count === 0 ? '✓ Already in deck' : `✓ ${count} added`) :
    status === 'error' ? 'Error' :
    label

  return (
    <button
      className="flashcard-add-btn"
      onClick={handleClick}
      disabled={status !== 'idle'}
      aria-label={label}
    >
      {buttonLabel}
    </button>
  )
}
