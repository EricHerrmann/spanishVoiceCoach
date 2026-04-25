import { useState } from 'react'

export default function Transcript({ turns, onPractice }) {
  const [collapsed, setCollapsed] = useState(new Set())

  function toggle(i) {
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  return (
    <div className="transcript">
      {turns.map((turn, i) => {
        const isCollapsed = collapsed.has(i)
        const text = turn.speaker === 'user' ? turn.transcript_norm : turn.coach_text
        return (
          <div key={i} className={`turn turn--${turn.speaker}`}>
            <div className="turn-header">
              <span className="turn-label">{turn.speaker === 'user' ? 'You' : 'Coach'}</span>
              <button
                className="turn-toggle"
                onClick={() => toggle(i)}
                aria-label={isCollapsed ? 'Show text' : 'Hide text'}
              >
                {isCollapsed ? 'Show' : 'Hide'}
              </button>
              {turn.speaker === 'coach' && (
                <button
                  className="turn-practice-btn"
                  onClick={() => onPractice?.(text)}
                  aria-label="Practice this phrase"
                >
                  Practice
                </button>
              )}
            </div>
            <span className={`turn-text${isCollapsed ? ' turn-text--hidden' : ''}`}>
              {isCollapsed ? '···' : text}
            </span>
          </div>
        )
      })}
    </div>
  )
}
