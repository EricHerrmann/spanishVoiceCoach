export default function SessionConfig({ coachingMode, onCoachingModeChange }) {
  return (
    <div className="session-config">
      <label htmlFor="coaching-mode">Coaching mode</label>
      <select
        id="coaching-mode"
        value={coachingMode}
        onChange={(e) => onCoachingModeChange(e.target.value)}
      >
        <option value="on_demand">On demand</option>
        <option value="explicit">Explicit</option>
        <option value="shadowing">Shadowing</option>
      </select>
    </div>
  )
}
