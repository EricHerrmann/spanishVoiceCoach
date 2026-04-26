from typing import Union
from backend.ai.base import AbstractAIProvider
from backend.session import Session, CoachResponse, TurnError, PronunciationEvaluation


class OpenAIProvider(AbstractAIProvider):
    """OpenAI GPT provider stub. Wired for Phase 4+ swap."""

    def chat(self, session: Session, user_text: str) -> Union[CoachResponse, TurnError]:
        raise NotImplementedError("OpenAIProvider is not implemented in MVP")

    def evaluate_pronunciation(self, target: str, transcript: str) -> Union[PronunciationEvaluation, TurnError]:
        raise NotImplementedError("OpenAIProvider is not implemented in MVP")

    def translate(self, english_text: str) -> Union[str, TurnError]:
        raise NotImplementedError("OpenAIProvider is not implemented in MVP")

    def generate_flashcards(self, text: str, turns: list[dict], source: str) -> Union[list[dict], TurnError]:
        raise NotImplementedError("OpenAIProvider is not implemented in MVP")
