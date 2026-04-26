import os
import anthropic
import json
import re
from typing import Union
from backend.ai.base import AbstractAIProvider
from backend.session import Session, CoachResponse, Correction, TurnError, PronunciationEvaluation, PronunciationIssue

_VALID_TOPICS = frozenset({
    "general", "ordering_food", "directions_transport",
    "shopping_markets", "work_daily_routine", "travel_tourism",
})


def _validate_cards(cards: list) -> list[dict]:
    result = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        if not all(k in card for k in ("english", "spanish", "level", "topic")):
            continue
        if not isinstance(card["level"], int) or isinstance(card["level"], bool) or not (1 <= card["level"] <= 10):
            continue
        if card["topic"] not in _VALID_TOPICS:
            continue
        result.append({
            "english": str(card["english"]),
            "spanish": str(card["spanish"]),
            "level": card["level"],
            "topic": card["topic"],
        })
    return result


def parse_flashcard_response(raw_text: str) -> list[dict]:
    """Extract and validate flashcard dicts from Claude's raw text response."""
    text = raw_text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return _validate_cards(parsed)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    return _validate_cards(parsed)


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

_PRONUNCIATION_TOOL = {
    "name": "evaluate_pronunciation",
    "description": "Return a structured pronunciation evaluation for a Spanish phrase.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": "Overall pronunciation score from 0 to 100.",
            },
            "feedback": {
                "type": "string",
                "description": "Brief, encouraging feedback on the pronunciation attempt.",
            },
            "issues": {
                "type": "array",
                "description": "Specific sound issues identified. Empty list if none.",
                "items": {
                    "type": "object",
                    "properties": {
                        "sound": {
                            "type": "string",
                            "description": "The phoneme or sound pattern (e.g. 'rr', 'ñ', 'b/v').",
                        },
                        "said": {
                            "type": "string",
                            "description": "What the learner appears to have pronounced.",
                        },
                        "expected": {
                            "type": "string",
                            "description": "The correct pronunciation.",
                        },
                    },
                    "required": ["sound", "said", "expected"],
                },
            },
        },
        "required": ["score", "feedback", "issues"],
    },
}

_LEVEL_SCALE = (
    "Level scale for reference:\n"
    "- 1–2 (Duolingo 5–30): Greetings, food, basic nouns. Simple present tense only.\n"
    "- 3–4 (Duolingo 30–70): Directions, simple sentences. Introduce past tense.\n"
    "- 5–6 (Duolingo 70–110): Stories, TV, work vocabulary. Full tense range, basic subjunctive.\n"
    "- 7–10 (Duolingo 110+): Near-native fluency, idioms, slang, complex grammar."
)

_MODE_INSTRUCTIONS = {
    "on_demand": (
        "Provide corrections ONLY if the student explicitly asks for feedback "
        "(e.g. 'Corrígeme', 'Was that right?', '¿Lo dije bien?', '¿Cómo se dice…?'). "
        "When correcting, set triggered_by to 'user_request'. "
        "Otherwise return an empty corrections list."
    ),
    "explicit": (
        "Always identify and correct grammar or vocabulary errors in the student's speech. "
        "Set triggered_by to 'auto' for each correction."
    ),
    "shadowing": (
        "When you detect an error, naturally weave the correct Spanish form into your reply "
        "without explicitly labelling it as a correction. "
        "Always return an empty corrections list."
    ),
}


class ClaudeProvider(AbstractAIProvider):
    """Anthropic Claude AI provider using tool use for structured output."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        self._client = anthropic.Anthropic(api_key=api_key)

    def _build_system_prompt(self, session: Session) -> str:
        mode_instruction = _MODE_INSTRUCTIONS.get(
            session.coaching_mode, _MODE_INSTRUCTIONS["on_demand"]
        )
        return (
            f"You are a Spanish conversation coach. "
            f"The student is practicing at level {session.level}/10.\n"
            f"Topic: {session.topic}. Coaching mode: {session.coaching_mode}.\n"
            f"Respond only in Spanish. "
            f"Keep vocabulary and grammar appropriate for level {session.level}.\n"
            f"{mode_instruction}\n\n"
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

    def translate(self, english_text: str) -> Union[str, TurnError]:
        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": (
                        "Translate this English phrase to natural Spanish. "
                        "Return only the Spanish translation, no explanation:\n\n"
                        f"{english_text}"
                    ),
                }],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            return TurnError(
                stage="ai",
                message=f"Translation failed: {exc}",
                recoverable=True,
            )

    def evaluate_pronunciation(self, target: str, transcript: str) -> Union[PronunciationEvaluation, TurnError]:
        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                tools=[_PRONUNCIATION_TOOL],
                tool_choice={"type": "tool", "name": "evaluate_pronunciation"},
                messages=[{
                    "role": "user",
                    "content": (
                        "A Spanish learner attempted to say this phrase:\n\n"
                        f"Target: {target}\n"
                        f"Whisper transcript of their attempt: {transcript}\n\n"
                        "Evaluate their pronunciation by comparing the transcript to the target. "
                        "Give a score of 100 if the transcript matches the target exactly or very closely. "
                        "Identify any specific sounds that differ. Be encouraging."
                    ),
                }],
            )
            for block in response.content:
                if block.type == "tool_use" and block.name == "evaluate_pronunciation":
                    raw = block.input
                    issues = [
                        PronunciationIssue(
                            sound=iss["sound"],
                            said=iss["said"],
                            expected=iss["expected"],
                        )
                        for iss in raw.get("issues", [])
                    ]
                    return PronunciationEvaluation(
                        score=raw["score"],
                        feedback=raw["feedback"],
                        issues=issues,
                    )
            return TurnError(
                stage="ai", message="No evaluation block in Claude response", recoverable=True
            )
        except Exception as exc:
            return TurnError(
                stage="ai", message=f"Pronunciation evaluation failed: {exc}", recoverable=True
            )

    def generate_flashcards(self, text: str, turns: list[dict], source: str) -> Union[list[dict], TurnError]:
        turns_lines = []
        for t in turns:
            speaker = t.get("speaker", "")
            content = t.get("transcript_norm", "") if speaker == "user" else t.get("coach_text", "")
            if content:
                turns_lines.append(f"{speaker}: {content}")
        turns_context = "\n".join(turns_lines)

        if source == "conversation":
            focal = f"Full conversation:\n{turns_context}"
            card_count = "5–15"
        else:
            context_section = f"\n\nConversation context:\n{turns_context}" if turns_context else ""
            focal = f"Text: {text}{context_section}"
            card_count = "3–8"

        prompt = (
            "Extract vocabulary and key phrases suitable for Spanish flashcard study.\n\n"
            f"{focal}\n\n"
            "Assign each card exactly one of these topic IDs:\n"
            "general, ordering_food, directions_transport, shopping_markets, work_daily_routine, travel_tourism\n\n"
            "Assign difficulty levels 1–10 (1=very basic greetings, 10=advanced native-level).\n\n"
            f"Return {card_count} cards as a bare JSON array only — no prose, no markdown fences:\n"
            '[{"english": "...", "spanish": "...", "level": N, "topic": "..."}]'
        )

        try:
            response = self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text
            return parse_flashcard_response(raw)
        except Exception as exc:
            return TurnError(stage="ai", message=f"Flashcard generation failed: {exc}", recoverable=True)
