from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Optional, Any


@dataclass
class Correction:
    original: str        # what the user said
    corrected: str       # correct form
    explanation: str     # grammar rule or vocabulary note
    triggered_by: str    # "auto" | "user_request"


@dataclass
class CoachResponse:
    coach_text: str
    corrections: list[Correction]


@dataclass
class TurnError:
    stage: str        # "mic" | "stt" | "ai" | "tts" | "session"
    message: str      # human-readable description
    recoverable: bool # True = prompt retry; False = session-ending


@dataclass
class PronunciationIssue:
    sound: str      # phoneme or sound pattern (e.g. 'rr', 'ñ')
    said: str       # what the learner pronounced
    expected: str   # correct pronunciation


@dataclass
class PronunciationEvaluation:
    score: int                          # 0–100
    feedback: str                       # encouraging feedback
    issues: list[PronunciationIssue]    # empty list if no issues


@dataclass
class Turn:
    speaker: str                        # "user" | "coach"
    timestamp: datetime
    audio_file: Optional[str] = None    # path to WAV (Phase 5+)
    transcript_raw: Optional[str] = None   # Whisper output verbatim (Phase 1+)
    transcript_norm: Optional[str] = None  # cleaned transcript (Phase 1+)
    coach_text: Optional[str] = None       # coach response text (Phase 2+)
    corrections: list[Correction] = field(default_factory=list)
    error: Optional[TurnError] = None    # Phase 1+


def _convert_datetimes_to_iso(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _convert_datetimes_to_iso(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_datetimes_to_iso(item) for item in obj]
    return obj


@dataclass
class Session:
    id: str                  # UUID
    started_at: datetime
    topic: str               # e.g. "ordering food"
    level: int               # 1–10
    ai_provider: str         # e.g. "claude" | "openai" | "google" | "deepseek" | "groq"
    coaching_mode: str       # "on_demand" | "explicit" | "shadowing"
    ai_model: Optional[str] = None
    tts_provider: str = "browser"        # "browser" | "elevenlabs"
    tts_voice_id: Optional[str] = None   # voice ID when tts_provider == "elevenlabs"
    turns: list[Turn] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize the session to a plain dict (for JSON persistence)."""
        return _convert_datetimes_to_iso(asdict(self))

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        """Reconstruct a Session from a dict (handling nested objects correctly)."""
        data_copy = data.copy()

        # Reconstruct datetime objects
        if isinstance(data_copy.get("started_at"), str):
            data_copy["started_at"] = datetime.fromisoformat(data_copy["started_at"])

        # Reconstruct Turn objects with nested Correction and TurnError objects
        turns_data = data_copy.get("turns", [])
        reconstructed_turns = []
        for turn_data in turns_data:
            turn_copy = turn_data.copy()

            # Reconstruct timestamp
            if isinstance(turn_copy.get("timestamp"), str):
                turn_copy["timestamp"] = datetime.fromisoformat(turn_copy["timestamp"])

            # Reconstruct Correction objects
            corrections_data = turn_copy.get("corrections", [])
            reconstructed_corrections = [
                corr if isinstance(corr, Correction) else Correction(**corr)
                for corr in corrections_data
            ]
            turn_copy["corrections"] = reconstructed_corrections

            # Reconstruct TurnError object
            error_data = turn_copy.get("error")
            if error_data is not None:
                if not isinstance(error_data, TurnError):
                    turn_copy["error"] = TurnError(**error_data)

            reconstructed_turns.append(Turn(**turn_copy))

        data_copy["turns"] = reconstructed_turns

        return cls(**data_copy)


def get_data_dir() -> Path:
    """Return the base local data directory for persisted app state."""
    return Path(os.environ.get("DVC_DATA_DIR", "~/.duoVoiceCoach")).expanduser()


def get_session_store_dir() -> Path:
    """Return the directory containing session JSON documents."""
    return get_data_dir() / "sessions"


def get_audio_store_dir() -> Path:
    """Return the directory containing optional retained user audio files."""
    return get_data_dir() / "audio"


def should_save_audio() -> bool:
    """Whether uploaded user audio should be retained on disk."""
    return os.environ.get("DVC_SAVE_AUDIO", "").lower() in {"1", "true", "yes", "on"}


def session_path(session_id: str, store_dir: Path | None = None) -> Path:
    base_dir = store_dir or get_session_store_dir()
    return base_dir / f"{session_id}.json"


def save_session(session: Session, store_dir: Path | None = None) -> Path:
    """Persist a session JSON document atomically and return its path."""
    path = session_path(session.id, store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(session.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    tmp_path.replace(path)
    return path


def load_session(session_id: str, store_dir: Path | None = None) -> Session:
    """Load a session by id from disk."""
    path = session_path(session_id, store_dir)
    data = json.loads(path.read_text(encoding="utf-8"))
    return Session.from_dict(data)


def list_sessions(store_dir: Path | None = None) -> list[dict]:
    """Return lightweight summaries for persisted sessions, newest first."""
    base_dir = store_dir or get_session_store_dir()
    if not base_dir.exists():
        return []

    summaries = []
    for path in base_dir.glob("*.json"):
        try:
            session = Session.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue

        summaries.append(session_summary(session))

    return sorted(summaries, key=lambda s: s["started_at"], reverse=True)


def session_summary(session: Session) -> dict:
    """Return the list-view representation of a session."""
    correction_count = sum(len(turn.corrections) for turn in session.turns)
    return {
        "id": session.id,
        "started_at": session.started_at.isoformat(),
        "topic": session.topic,
        "level": session.level,
        "ai_provider": session.ai_provider,
        "ai_model": session.ai_model,
        "coaching_mode": session.coaching_mode,
        "turn_count": len(session.turns),
        "correction_count": correction_count,
    }


def new_session(
    topic: str,
    level: int,
    ai_provider: str,
    coaching_mode: str,
    ai_model: Optional[str] = None,
    tts_provider: str = "browser",
    tts_voice_id: Optional[str] = None,
) -> Session:
    """Factory function to create a new Session with a fresh UUID and current timestamp."""
    return Session(
        id=str(uuid4()),
        started_at=datetime.now(timezone.utc),
        topic=topic,
        level=level,
        ai_provider=ai_provider,
        ai_model=ai_model,
        coaching_mode=coaching_mode,
        tts_provider=tts_provider,
        tts_voice_id=tts_voice_id,
    )
