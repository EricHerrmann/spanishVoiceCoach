from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from backend.session import Session, CoachResponse, TurnError


class AbstractAIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def chat(self, session: "Session", user_text: str) -> "Union[CoachResponse, TurnError]":
        """Send a user turn to the AI and return a CoachResponse or TurnError.

        Never raises — errors are returned as TurnError values.
        """
        raise NotImplementedError
