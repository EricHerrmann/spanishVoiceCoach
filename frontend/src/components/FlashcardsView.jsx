import { useState, useEffect } from 'react'

const BANDS = [
  { id: 'beginner', label: 'Beginner', min: 1, max: 2 },
  { id: 'elementary', label: 'Elementary', min: 3, max: 4 },
  { id: 'intermediate', label: 'Intermediate', min: 5, max: 6 },
  { id: 'advanced', label: 'Advanced', min: 7, max: 10 },
]

export default function FlashcardsView() {
  const [topics, setTopics] = useState([])
  const [selectedTopic, setSelectedTopic] = useState('general')
  const [selectedBand, setSelectedBand] = useState('intermediate')
  const [deck, setDeck] = useState([])
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)

  useEffect(() => {
    fetch('/topics').then((r) => r.json()).then(setTopics).catch(() => {})
  }, [])

  useEffect(() => {
    const band = BANDS.find((b) => b.id === selectedBand)
    fetch(`/flashcards/deck?topic=${selectedTopic}&level_min=${band.min}&level_max=${band.max}`)
      .then((r) => r.json())
      .then((data) => { setDeck(data); setIndex(0); setFlipped(false) })
      .catch(() => {})
  }, [selectedTopic, selectedBand])

  const card = deck[index]
  const completed = deck.length > 0 && index >= deck.length

  function next() { setIndex((i) => i + 1); setFlipped(false) }
  function prev() { setIndex((i) => Math.max(0, i - 1)); setFlipped(false) }
  function restart() { setIndex(0); setFlipped(false) }

  return (
    <div className="flashcards-view">
      <div className="flashcards-controls">
        <select
          className="flashcards-topic-select"
          value={selectedTopic}
          onChange={(e) => setSelectedTopic(e.target.value)}
        >
          {topics.map((t) => (
            <option key={t.id} value={t.id}>{t.label}</option>
          ))}
        </select>
        <div className="flashcards-bands">
          {BANDS.map((b) => (
            <button
              key={b.id}
              className={`band-btn${selectedBand === b.id ? ' band-btn--active' : ''}`}
              onClick={() => setSelectedBand(b.id)}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>

      {deck.length === 0 && (
        <p className="flashcards-empty">No cards for this topic and level.</p>
      )}

      {completed && (
        <div className="flashcards-complete">
          <p>Deck complete — {deck.length} cards reviewed.</p>
          <button onClick={restart}>Restart</button>
        </div>
      )}

      {!completed && card && (
        <>
          <div className="flashcard" onClick={() => setFlipped((f) => !f)}>
            <span className="flashcard-side-label">{flipped ? 'Spanish' : 'English'}</span>
            <p className="flashcard-text">{flipped ? card.spanish : card.english}</p>
            <span className="flashcard-hint">click to flip</span>
          </div>
          <div className="flashcards-nav">
            <button onClick={prev} disabled={index === 0}>Previous</button>
            <span className="flashcards-progress">{index + 1} / {deck.length}</span>
            <button onClick={next}>Next</button>
          </div>
        </>
      )}
    </div>
  )
}
