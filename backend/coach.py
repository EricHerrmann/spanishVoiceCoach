from datetime import datetime, timezone
from typing import Union
from backend.session import Session, Turn, CoachResponse, TurnError
from backend.ai.base import AbstractAIProvider


class CoachSession:
    """Manages a coaching session: calls the AI provider and maintains turn history."""

    def __init__(self, session: Session, ai_provider: AbstractAIProvider):
        self.session = session
        self.ai_provider = ai_provider

    def handle_turn(self, user_text: str) -> Union[Turn, TurnError]:
        """Process a user turn: call AI, append both turns to session, return coach turn.

        Returns TurnError (as a value, not exception) if the AI provider fails.
        """
        now = datetime.now(timezone.utc)

        result = self.ai_provider.chat(self.session, user_text)

        user_turn = Turn(speaker="user", transcript_norm=user_text, timestamp=now)
        self.session.turns.append(user_turn)

        if isinstance(result, TurnError):
            error_turn = Turn(speaker="coach", timestamp=now, error=result)
            self.session.turns.append(error_turn)
            return result

        coach_turn = Turn(
            speaker="coach",
            coach_text=result.coach_text,
            corrections=result.corrections,
            timestamp=now,
        )
        self.session.turns.append(coach_turn)
        return coach_turn
