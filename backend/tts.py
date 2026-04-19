from abc import ABC, abstractmethod


class AbstractTTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @abstractmethod
    def synthesize(self, text: str) -> None:
        """
        Synthesize speech from text.

        Args:
            text: The text to synthesize.

        Returns:
            None. In MVP, browser handles TTS.
        """
        raise NotImplementedError


class BrowserTTSProvider(AbstractTTSProvider):
    """Concrete TTS provider that delegates to browser.

    In Phase 0 MVP, TTS is handled client-side in the browser.
    This provider is a passthrough stub.
    """

    def synthesize(self, text: str) -> None:
        """
        Passthrough synthesize method.

        Args:
            text: The text to synthesize (handled by browser).

        Returns:
            None.
        """
        return None
