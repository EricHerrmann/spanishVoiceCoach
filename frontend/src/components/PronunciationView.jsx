import { useState, useEffect, useRef } from 'react'
import { useAudioRecorder } from '../hooks/useAudioRecorder'

const BANDS = [
  { id: 'beginner', label: 'Beginner', min: 1, max: 2 },
  { id: 'elementary', label: 'Elementary', min: 3, max: 4 },
  { id: 'intermediate', label: 'Intermediate', min: 5, max: 6 },
  { id: 'advanced', label: 'Advanced', min: 7, max: 10 },
]

const SOURCE_LABELS = {
  conversation: 'From conversation',
  translation: 'From translation',
}

export default function PronunciationView({ pronunciationTarget, onClearTarget }) {
  const [tab, setTab] = useState('vocabulary')

  // Vocabulary tab state
  const [topics, setTopics] = useState([])
  const [selectedTopic, setSelectedTopic] = useState('general')
  const [selectedBand, setSelectedBand] = useState('intermediate')
  const [vocabDeck, setVocabDeck] = useState([])
  const [vocabIndex, setVocabIndex] = useState(0)

  // Challenges tab state
  const [challenges, setChallenges] = useState([])
  const [selectedChallenge, setSelectedChallenge] = useState(null)

  // Scoring state
  const [scoringState, setScoringState] = useState('idle') // idle | recording | processing | done
  const [evalResult, setEvalResult] = useState(null)
  const [evalError, setEvalError] = useState(null)

  // Capture the current target at recording-start time so the onStop closure has the right value
  const targetAtStartRef = useRef(null)

  const { startRecording, stopRecording } = useAudioRecorder({
    onStop: (blob) => {
      setScoringState('processing')
      submitAudio(blob, targetAtStartRef.current)
    },
  })

  useEffect(() => {
    fetch('/topics').then((r) => r.json()).then(setTopics).catch(() => {})
    fetch('/pronunciation/challenges').then((r) => r.json()).then(setChallenges).catch(() => {})
  }, [])

  useEffect(() => {
    if (pronunciationTarget) return
    const band = BANDS.find((b) => b.id === selectedBand)
    fetch(`/flashcards/deck?topic=${selectedTopic}&level_min=${band.min}&level_max=${band.max}`)
      .then((r) => r.json())
      .then((data) => { setVocabDeck(data); setVocabIndex(0); resetScoring() })
      .catch(() => {})
  }, [selectedTopic, selectedBand, pronunciationTarget])

  useEffect(() => {
    if (pronunciationTarget) resetScoring()
  }, [pronunciationTarget])

  function resetScoring() {
    setScoringState('idle')
    setEvalResult(null)
    setEvalError(null)
  }

  const target = pronunciationTarget
    ? pronunciationTarget.text
    : tab === 'vocabulary'
    ? vocabDeck[vocabIndex]?.spanish ?? null
    : selectedChallenge?.target ?? null

  const activeHint = tab === 'challenges' && !pronunciationTarget ? selectedChallenge?.hint : null

  async function handleStartRecording() {
    setEvalError(null)
    targetAtStartRef.current = target
    await startRecording()
    setScoringState('recording')
  }

  async function submitAudio(blob, currentTarget) {
    const form = new FormData()
    form.append('audio', blob, `recording.${blob.type.split('/')[1]?.split(';')[0] || 'wav'}`)
    form.append('target', currentTarget)
    try {
      const res = await fetch('/pronunciation/evaluate', { method: 'POST', body: form })
      const data = await res.json()
      if (data.error) { setEvalError(data.error.message); setScoringState('idle'); return }
      setEvalResult(data)
      setScoringState('done')
    } catch {
      setEvalError('Network error')
      setScoringState('idle')
    }
  }

  const isRecording = scoringState === 'recording'
  const isProcessing = scoringState === 'processing'
  const disabled = isProcessing || !target

  return (
    <div className="pronunciation-view">
      {pronunciationTarget ? (
        <div className="pronunciation-external-header">
          <span className="pronunciation-source-label">
            {SOURCE_LABELS[pronunciationTarget.source] ?? 'From session'}
          </span>
          <button
            className="pronunciation-back-btn"
            onClick={onClearTarget}
          >
            ← Back
          </button>
        </div>
      ) : (
        <div className="pronunciation-sub-tabs">
          {['vocabulary', 'challenges'].map((t) => (
            <button
              key={t}
              className={`pronunciation-tab${tab === t ? ' pronunciation-tab--active' : ''}`}
              onClick={() => { setTab(t); resetScoring() }}
            >
              {t === 'vocabulary' ? 'Vocabulary' : 'Challenges'}
            </button>
          ))}
        </div>
      )}

      {!pronunciationTarget && tab === 'vocabulary' && (
        <div className="pronunciation-vocab-controls">
          <select
            value={selectedTopic}
            onChange={(e) => setSelectedTopic(e.target.value)}
          >
            {topics.map((tp) => (
              <option key={tp.id} value={tp.id}>{tp.label}</option>
            ))}
          </select>
          <div className="pronunciation-bands">
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
      )}

      {!pronunciationTarget && tab === 'challenges' && !selectedChallenge && (
        <ul className="pronunciation-challenge-list">
          {challenges.map((ch) => (
            <li key={ch.id}>
              <button
                className="pronunciation-challenge-item"
                onClick={() => { setSelectedChallenge(ch); resetScoring() }}
              >
                <span className="pronunciation-challenge-target">{ch.target}</span>
                <span className="pronunciation-challenge-focus">{ch.sound_focus}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {target && (
        <div className="pronunciation-scoring">
          <p className="pronunciation-target">{target}</p>

          {activeHint && (
            <p className="pronunciation-hint">{activeHint}</p>
          )}

          {evalError && <p className="pronunciation-error">{evalError}</p>}

          {evalResult && (
            <div className="pronunciation-result">
              <span className="pronunciation-score">{evalResult.score}</span>
              <p className="pronunciation-feedback">{evalResult.feedback}</p>
              {evalResult.issues?.length > 0 && (
                <ul className="pronunciation-issues">
                  {evalResult.issues.map((issue, i) => (
                    <li key={i} className="pronunciation-issue">
                      <span className="issue-sound">{issue.sound}</span>
                      {' — said '}
                      <span className="issue-said">{issue.said}</span>
                      {', expected '}
                      <span className="issue-expected">{issue.expected}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <div className="pronunciation-actions">
            {tab === 'challenges' && !pronunciationTarget && selectedChallenge && (
              <button
                className="pronunciation-back-btn"
                onClick={() => { setSelectedChallenge(null); resetScoring() }}
              >
                ← Challenges
              </button>
            )}
            <button
              className={`voice-btn voice-btn--${scoringState === 'done' ? 'idle' : scoringState}`}
              onClick={isRecording ? stopRecording : handleStartRecording}
              disabled={disabled}
            >
              {isRecording ? 'Stop' : isProcessing ? 'Processing…' : 'Record'}
            </button>
            {!pronunciationTarget && tab === 'vocabulary' && vocabDeck.length > 0 && (
              <button
                onClick={() => { setVocabIndex((i) => Math.min(i + 1, vocabDeck.length - 1)); resetScoring() }}
                disabled={vocabIndex >= vocabDeck.length - 1}
              >
                Next card
              </button>
            )}
          </div>
        </div>
      )}

      {!target && tab === 'vocabulary' && vocabDeck.length === 0 && (
        <p className="pronunciation-empty">No cards for this topic and level.</p>
      )}
    </div>
  )
}
