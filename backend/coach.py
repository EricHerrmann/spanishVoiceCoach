from datetime import datetime, timezone
from backend.session import Session, Turn
from backend.ai.base import AbstractAIProvider


class CoachSession:
    """Manages a coaching session interaction.

    Phase 0: Stub implementation with no AI provider calls.
    Handles user input and returns coach feedback (placeholder).
    """

    def __init__(self, session: Session, ai_provider: AbstractAIProvider):
        """Initialize a CoachSession.

        Args:
            session: The Session object to manage.
            ai_provider: An AbstractAIProvider instance (not used in Phase 0).
        """
        self.session = session
        self.ai_provider = ai_provider

    def handle_turn(self, user_text: str) -> Turn:
        """Process a user turn and return the coach's response.

        Phase 0: Creates user and coach turns without calling the AI provider.

        Args:
            user_text: The user's input text.

        Returns:
            The coach Turn (with stub response).
        """
        now = datetime.now(timezone.utc)

        # Create user turn
        user_turn = Turn(
            speaker="user",
            transcript_norm=user_text,
            timestamp=now,
        )
        self.session.turns.append(user_turn)

        # Create coach turn (Phase 0 stub - no AI provider call)
        coach_turn = Turn(
            speaker="coach",
            coach_text="[Phase 0 stub — AI not yet connected]",
            timestamp=now,
        )
        self.session.turns.append(coach_turn)

        return coach_turn
