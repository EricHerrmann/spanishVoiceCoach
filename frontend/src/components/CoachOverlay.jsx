import { useState, useEffect } from 'react'

export default function CoachOverlay({ corrections }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!corrections || corrections.length === 0) {
      setVisible(false)
      return
    }
    setVisible(true)
    const timer = setTimeout(() => setVisible(false), 8000)
    return () => clearTimeout(timer)
  }, [corrections])

  if (!visible) return null
  return (
    <div className="coach-overlay">
      <h3>Corrections</h3>
      {corrections.map((c, i) => (
        <div key={`${c.original}-${c.corrected}-${i}`} className="correction">
          <span className="correction-original">{c.original}</span>
          <span className="correction-arrow"> → </span>
          <span className="correction-corrected">{c.corrected}</span>
          <p className="correction-explanation">{c.explanation}</p>
        </div>
      ))}
    </div>
  )
}
