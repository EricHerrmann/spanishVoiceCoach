import re
from datetime import datetime, timezone
from typing import Union
from backend.session import Session, Turn, CoachResponse, TurnError, Correction
from backend.ai.base import AbstractAIProvider

_CORRECTION_REQUEST_PATTERNS = [
    r"corrígeme",
    r"corrigeme",
    r"cómo se dice",
    r"como se dice",
    r"was that right",
    r"is that right",
    r"correct me",
    r"lo dije bien",
    r"está bien",
    r"esta bien lo que dije",
]


def _user_requested_correction(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in _CORRECTION_REQUEST_PATTERNS)


def _apply_mode_routing(
    corrections: list[Correction], coaching_mode: str, user_requested: bool
) -> list[Correction]:
    if coaching_mode == "explicit":
        return corrections
    if coaching_mode == "shadowing":
        return []
    # on_demand (default)
    return corrections if user_requested else []


class CoachSession:
    """Manages a coaching session: calls the AI provider and maintains turn history."""

    def __init__(self, session: Session, ai_provider: AbstractAIProvider):
        self.session = session
        self.ai_provider = ai_provider

    def handle_turn(self, user_text: str) -> Union[Turn, TurnError]:
        """Process a user turn: call AI, apply mode routing, append turns, return coach turn.

        Returns TurnError (as a value, not exception) if the AI provider fails.
        """
        now = datetime.now(timezone.utc)

        user_requested = _user_requested_correction(user_text)
        call_text = (
            user_text + "\n[The student is explicitly asking for correction on this turn.]"
            if user_requested
            else user_text
        )

        result = self.ai_provider.chat(self.session, call_text)

        user_turn = Turn(speaker="user", transcript_norm=user_text, timestamp=now)
        self.session.turns.append(user_turn)

        if isinstance(result, TurnError):
            error_turn = Turn(speaker="coach", timestamp=now, error=result)
            self.session.turns.append(error_turn)
            return result

        corrections = _apply_mode_routing(
            result.corrections, self.session.coaching_mode, user_requested
        )

        coach_turn = Turn(
            speaker="coach",
            coach_text=result.coach_text,
            corrections=corrections,
            timestamp=now,
        )
        self.session.turns.append(coach_turn)
        return coach_turn
