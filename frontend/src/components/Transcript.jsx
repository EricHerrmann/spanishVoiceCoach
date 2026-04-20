export default function Transcript({ turns }) {
  return (
    <div className="transcript">
      {turns.map((turn, i) => (
        <div key={i} className={`turn turn--${turn.speaker}`}>
          <span className="turn-label">{turn.speaker === 'user' ? 'You' : 'Coach'}</span>
          <span className="turn-text">
            {turn.speaker === 'user' ? turn.transcript_norm : turn.coach_text}
          </span>
        </div>
      ))}
    </div>
  )
}
