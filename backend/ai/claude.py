import os
import anthropic
from typing import Union
from backend.ai.base import AbstractAIProvider
from backend.session import Session, CoachResponse, Correction, TurnError

_TOOL_DEFINITION = {
    "name": "get_coach_response",
    "description": "Return a structured coaching response to the student's Spanish utterance.",
    "input_schema": {
        "type": "object",
        "properties": {
            "coach_text": {
                "type": "string",
                "description": "The coach's Spanish reply to speak aloud.",
            },
            "corrections": {
                "type": "array",
                "description": "Grammar or vocabulary corrections. Empty list if none.",
                "items": {
                    "type": "object",
                    "properties": {
                        "original": {"type": "string"},
                        "corrected": {"type": "string"},
                        "explanation": {"type": "string"},
                        "triggered_by": {
                            "type": "string",
                            "enum": ["auto", "user_request"],
                        },
                    },
                    "required": ["original", "corrected", "explanation", "triggered_by"],
                },
            },
        },
        "required": ["coach_text", "corrections"],
    },
}

_LEVEL_SCALE = (
    "Level scale for reference:\n"
    "- 1–2 (Duolingo 5–30): Greetings, food, basic nouns. Simple present tense only.\n"
    "- 3–4 (Duolingo 30–70): Directions, simple sentences. Introduce past tense.\n"
    "- 5–6 (Duolingo 70–110): Stories, TV, work vocabulary. Full tense range, basic subjunctive.\n"
    "- 7–10 (Duolingo 110+): Near-native fluency, idioms, slang, complex grammar."
)


class ClaudeProvider(AbstractAIProvider):
    """Anthropic Claude AI provider using tool use for structured output."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        self._client = anthropic.Anthropic(api_key=api_key)

    def _build_system_prompt(self, session: Session) -> str:
        return (
            f"You are a Spanish conversation coach. "
            f"The student is practicing at level {session.level}/10.\n"
            f"Topic: {session.topic}. Coaching mode: {session.coaching_mode}.\n"
            f"Respond only in Spanish. "
            f"Keep vocabulary and grammar appropriate for level {session.level}.\n"
            f"Do not correct the student unless asked (on_demand mode).\n\n"  # Phase 3: replace with coaching_mode-aware instruction
            f"{_LEVEL_SCALE}"
        )

    def _build_messages(self, session: Session, user_text: str) -> list:
        messages = []
        for turn in session.turns:
            if turn.speaker == "user" and turn.transcript_norm:
                messages.append({"role": "user", "content": turn.transcript_norm})
            elif turn.speaker == "coach" and turn.coach_text:
                messages.append({"role": "assistant", "content": turn.coach_text})
        messages.append({"role": "user", "content": user_text})
        return messages

    def chat(self, session: Session, user_text: str) -> Union[CoachResponse, TurnError]:
        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": self._build_system_prompt(session),
                    "cache_control": {"type": "ephemeral"},
                }],
                tools=[_TOOL_DEFINITION],
                tool_choice={"type": "tool", "name": "get_coach_response"},
                messages=self._build_messages(session, user_text),
            )

            tool_block = next(
                (b for b in response.content if b.type == "tool_use"), None
            )
            if tool_block is None:
                return TurnError(
                    stage="ai",
                    message="No tool_use block in Claude response",
                    recoverable=True,
                )

            data = tool_block.input
            corrections = [
                Correction(
                    original=c["original"],
                    corrected=c["corrected"],
                    explanation=c["explanation"],
                    triggered_by=c["triggered_by"],
                )
                for c in data.get("corrections", [])
            ]
            return CoachResponse(coach_text=data["coach_text"], corrections=corrections)

        except Exception as exc:
            return TurnError(
                stage="ai",
                message=f"AI request failed: {exc}",
                recoverable=True,
            )
