"""Unit tests for Session serialization round-trips."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from backend.session import Correction, Session, Turn, TurnError, new_session
from backend.session import load_session, list_sessions, save_session, session_summary


def _make_session(**kwargs) -> Session:
    defaults = dict(
        topic="ordering food",
        level=3,
        ai_provider="claude",
        coaching_mode="on_demand",
    )
    defaults.update(kwargs)
    return new_session(**defaults)


def test_session_roundtrip_empty_turns():
    """New session serializes and deserializes with no data loss."""
    original = _make_session()
    restored = Session.from_dict(original.to_dict())

    assert restored.id == original.id
    assert restored.topic == original.topic
    assert restored.level == original.level
    assert restored.ai_provider == original.ai_provider
    assert restored.coaching_mode == original.coaching_mode
    assert restored.started_at == original.started_at
    assert restored.turns == []


def test_session_roundtrip_with_turn():
    """Session with a Turn serializes and deserializes correctly."""
    original = _make_session()
    ts = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
    turn = Turn(
        speaker="user",
        timestamp=ts,
        transcript_raw="Hola, ¿cómo estás?",
        transcript_norm="hola como estas",
    )
    original.turns.append(turn)

    restored = Session.from_dict(original.to_dict())

    assert len(restored.turns) == 1
    rt = restored.turns[0]
    assert rt.speaker == "user"
    assert rt.timestamp == ts
    assert rt.transcript_raw == "Hola, ¿cómo estás?"
    assert rt.transcript_norm == "hola como estas"
    assert rt.corrections == []
    assert rt.error is None


def test_session_roundtrip_with_correction():
    """Session with Turn containing Correction round-trips correctly."""
    original = _make_session()
    ts = datetime(2026, 4, 19, 12, 1, 0, tzinfo=timezone.utc)
    correction = Correction(
        original="Yo soy tiene hambre",
        corrected="Yo tengo hambre",
        explanation="Use tener for hunger, not ser/estar.",
        triggered_by="auto",
    )
    turn = Turn(
        speaker="coach",
        timestamp=ts,
        coach_text="Casi perfecto! Pequeña corrección:",
        corrections=[correction],
    )
    original.turns.append(turn)

    restored = Session.from_dict(original.to_dict())

    assert len(restored.turns) == 1
    rt = restored.turns[0]
    assert len(rt.corrections) == 1
    rc = rt.corrections[0]
    assert rc.original == correction.original
    assert rc.corrected == correction.corrected
    assert rc.explanation == correction.explanation
    assert rc.triggered_by == correction.triggered_by


def test_to_dict_is_json_serializable():
    """Session.to_dict() output can be passed to json.dumps() without error."""
    original = _make_session()
    ts = datetime(2026, 4, 19, 9, 30, 0, tzinfo=timezone.utc)
    turn = Turn(
        speaker="user",
        timestamp=ts,
        transcript_raw="Buenos días",
        error=TurnError(stage="stt", message="Low confidence", recoverable=True),
    )
    original.turns.append(turn)

    d = original.to_dict()
    # Must not raise
    serialized = json.dumps(d)
    assert isinstance(serialized, str)
    assert original.id in serialized


def test_from_dict_preserves_datetime():
    """from_dict() correctly reconstructs datetime fields from ISO strings."""
    original = _make_session()
    ts = datetime(2026, 4, 19, 15, 45, 30, tzinfo=timezone.utc)
    original.turns.append(Turn(speaker="coach", timestamp=ts, coach_text="¡Muy bien!"))

    as_dict = original.to_dict()

    # Verify the dict stored datetimes as strings
    assert isinstance(as_dict["started_at"], str)
    assert isinstance(as_dict["turns"][0]["timestamp"], str)

    restored = Session.from_dict(as_dict)

    assert isinstance(restored.started_at, datetime)
    assert isinstance(restored.turns[0].timestamp, datetime)
    assert restored.started_at == original.started_at
    assert restored.turns[0].timestamp == ts


def test_save_and_load_session_roundtrip(tmp_path):
    """Persisting and loading a session preserves nested turns and corrections."""
    original = _make_session(topic="travel", level=6)
    ts = datetime(2026, 4, 21, 10, 0, 0, tzinfo=timezone.utc)
    original.turns.append(Turn(speaker="user", timestamp=ts, transcript_norm="hola"))
    original.turns.append(
        Turn(
            speaker="coach",
            timestamp=ts,
            coach_text="¡Hola!",
            corrections=[
                Correction(
                    original="yo soy hambre",
                    corrected="tengo hambre",
                    explanation="Use tener with hunger.",
                    triggered_by="auto",
                )
            ],
        )
    )

    save_session(original, store_dir=tmp_path)
    restored = load_session(original.id, store_dir=tmp_path)

    assert restored.id == original.id
    assert restored.topic == "travel"
    assert restored.level == 6
    assert len(restored.turns) == 2
    assert restored.turns[1].corrections[0].corrected == "tengo hambre"


def test_list_sessions_returns_newest_first(tmp_path):
    older = _make_session(topic="older")
    newer = _make_session(topic="newer")
    older.started_at = datetime(2026, 4, 20, 10, 0, 0, tzinfo=timezone.utc)
    newer.started_at = datetime(2026, 4, 21, 10, 0, 0, tzinfo=timezone.utc)
    save_session(older, store_dir=tmp_path)
    save_session(newer, store_dir=tmp_path)

    summaries = list_sessions(store_dir=tmp_path)

    assert [s["id"] for s in summaries] == [newer.id, older.id]


def test_session_summary_counts_turns_and_corrections():
    session = _make_session(topic="food")
    ts = datetime(2026, 4, 21, 11, 0, 0, tzinfo=timezone.utc)
    session.turns.append(Turn(speaker="user", timestamp=ts, transcript_norm="hola"))
    session.turns.append(
        Turn(
            speaker="coach",
            timestamp=ts,
            coach_text="Bien",
            corrections=[
                Correction(
                    original="mal",
                    corrected="bien",
                    explanation="Example correction.",
                    triggered_by="auto",
                )
            ],
        )
    )

    summary = session_summary(session)

    assert summary["id"] == session.id
    assert summary["topic"] == "food"
    assert summary["turn_count"] == 2
    assert summary["correction_count"] == 1
