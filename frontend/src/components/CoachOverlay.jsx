export default function CoachOverlay({ corrections }) {
  if (!corrections || corrections.length === 0) return null
  return (
    <div className="coach-overlay">
      <h3>Corrections</h3>
      {corrections.map((c, i) => (
        <div key={i} className="correction">
          <span className="correction-original">{c.original}</span>
          <span className="correction-arrow"> → </span>
          <span className="correction-corrected">{c.corrected}</span>
          <p className="correction-explanation">{c.explanation}</p>
        </div>
      ))}
    </div>
  )
}
