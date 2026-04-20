from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
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
    stage: str        # "mic" | "stt" | "ai" | "tts"
    message: str      # human-readable description
    recoverable: bool # True = prompt retry; False = session-ending


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
    ai_provider: str         # "claude" | "openai"
    coaching_mode: str       # "on_demand" | "explicit" | "shadowing"
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

            # Reconstruct Turn object (guard against already-reconstructed)
            if isinstance(turn_data, Turn):
                reconstructed_turns.append(turn_data)
            else:
                reconstructed_turns.append(Turn(**turn_copy))

        data_copy["turns"] = reconstructed_turns

        return cls(**data_copy)


def new_session(
    topic: str, level: int, ai_provider: str, coaching_mode: str
) -> Session:
    """Factory function to create a new Session with a fresh UUID and current timestamp."""
    return Session(
        id=str(uuid4()),
        started_at=datetime.now(timezone.utc),
        topic=topic,
        level=level,
        ai_provider=ai_provider,
        coaching_mode=coaching_mode,
    )
