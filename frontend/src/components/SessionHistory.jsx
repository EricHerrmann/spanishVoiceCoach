export default function SessionHistory({ sessions, selectedSessionId, onSelectSession, onRefresh }) {
  return (
    <section className="session-history" aria-labelledby="session-history-title">
      <div className="session-history-header">
        <h2 id="session-history-title">Session history</h2>
        <button type="button" onClick={onRefresh}>Refresh</button>
      </div>
      {sessions.length === 0 ? (
        <p className="session-history-empty">No saved sessions yet.</p>
      ) : (
        <ul className="session-history-list">
          {sessions.map((session) => (
            <li key={session.id}>
              <button
                type="button"
                className={session.id === selectedSessionId ? 'session-history-item is-selected' : 'session-history-item'}
                onClick={() => onSelectSession(session.id)}
              >
                <span className="session-history-topic">{session.topic}</span>
                <span className="session-history-meta">
                  Level {session.level} · {session.coaching_mode} · {session.turn_count} turns · {session.correction_count} corrections
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
