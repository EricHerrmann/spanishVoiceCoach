from typing import Union
from backend.ai.base import AbstractAIProvider
from backend.session import Session, CoachResponse, TurnError


class OpenAIProvider(AbstractAIProvider):
    """OpenAI GPT provider stub. Wired for Phase 4+ swap."""

    def chat(self, session: Session, user_text: str) -> Union[CoachResponse, TurnError]:
        raise NotImplementedError("OpenAIProvider is not implemented in MVP")
