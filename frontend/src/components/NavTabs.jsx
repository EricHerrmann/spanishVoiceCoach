const TABS = [
  { id: 'conversation', label: 'Conversation' },
  { id: 'flashcards', label: 'Flashcards' },
  { id: 'translation', label: 'Translation' },
  { id: 'pronunciation', label: 'Pronunciation' },
]

export default function NavTabs({ mode, onModeChange }) {
  return (
    <nav className="nav-tabs">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`nav-tab${mode === tab.id ? ' nav-tab--active' : ''}`}
          onClick={() => onModeChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  )
}
