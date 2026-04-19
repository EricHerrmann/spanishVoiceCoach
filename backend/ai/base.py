from abc import ABC, abstractmethod


class AbstractAIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def chat(self, session: "Session", user_text: str) -> str:
        """
        Chat with the AI provider.

        Args:
            session: The user session object.
            user_text: The user's input text.

        Returns:
            The AI provider's response text.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError
