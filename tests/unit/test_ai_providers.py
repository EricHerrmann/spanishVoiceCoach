"""Unit tests for AI provider abstract base class."""
from __future__ import annotations

import pytest

from backend.ai.base import AbstractAIProvider
from backend.session import CoachResponse, Correction


def test_abstract_ai_provider_raises_not_implemented():
    """Directly calling AbstractAIProvider.chat() raises NotImplementedError."""

    class ConcreteNoOp(AbstractAIProvider):
        """Minimal concrete subclass that does NOT override chat()."""

        def chat(self, session, user_text: str) -> str:
            # Deliberately call super() to trigger the NotImplementedError
            return super().chat(session, user_text)

    provider = ConcreteNoOp()
    with pytest.raises(NotImplementedError):
        provider.chat(session=None, user_text="hola")
