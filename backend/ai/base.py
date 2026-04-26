from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from backend.session import Session, CoachResponse, TurnError, PronunciationEvaluation


class AbstractAIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def chat(self, session: "Session", user_text: str) -> "Union[CoachResponse, TurnError]":
        """Send a user turn to the AI and return a CoachResponse or TurnError.

        Never raises — errors are returned as TurnError values.
        """
        raise NotImplementedError

    @abstractmethod
    def evaluate_pronunciation(self, target: str, transcript: str) -> "Union[PronunciationEvaluation, TurnError]":
        """Score a pronunciation attempt. Never raises — errors returned as TurnError."""
        raise NotImplementedError

    @abstractmethod
    def translate(self, english_text: str) -> "Union[str, TurnError]":
        """Translate English text to Spanish. Never raises — errors returned as TurnError."""
        raise NotImplementedError

    @abstractmethod
    def generate_flashcards(self, text: str, turns: list[dict], source: str) -> "Union[list[dict], TurnError]":
        """Extract flashcard vocabulary from text. Never raises — errors returned as TurnError."""
        raise NotImplementedError
