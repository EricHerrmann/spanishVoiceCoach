import os
from typing import Union

import httpx

from backend.ai.base import AbstractAIProvider
from backend.ai.claude import _LEVEL_SCALE, _MODE_INSTRUCTIONS, parse_flashcard_response
from backend.ai.json_utils import extract_json_object
from backend.session import (
    CoachResponse,
    Correction,
    PronunciationEvaluation,
    PronunciationIssue,
    Session,
    TurnError,
)


class GoogleProvider(AbstractAIProvider):
    """Gemini provider using the Google Generative Language REST API."""

    def __init__(self, model: str | None = None):
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY environment variable not set")
        self._api_key = api_key
        self._model = model or os.environ.get("DVC_GOOGLE_MODEL", "gemini-2.5-flash")
        self._context_turns = int(os.environ.get("DVC_CONTEXT_TURNS", "10"))

    def _build_system_prompt(self, session: Session) -> str:
        mode_instruction = _MODE_INSTRUCTIONS.get(
            session.coaching_mode, _MODE_INSTRUCTIONS["on_demand"]
        )
        return (
            "You are a Spanish conversation coach. "
            f"The student is practicing at level {session.level}/10.\n"
            f"Topic: {session.topic}. Coaching mode: {session.coaching_mode}.\n"
            "Respond only in Spanish. "
            f"Keep vocabulary and grammar appropriate for level {session.level}.\n"
            f"{mode_instruction}\n\n"
            f"{_LEVEL_SCALE}"
        )

    def _build_contents(self, session: Session, user_text: str) -> list[dict]:
        all_history = []
        for turn in session.turns:
            if turn.speaker == "user" and turn.transcript_norm:
                all_history.append({"role": "user", "parts": [{"text": turn.transcript_norm}]})
            elif turn.speaker == "coach" and turn.coach_text:
                all_history.append({"role": "model", "parts": [{"text": turn.coach_text}]})
        window_size = self._context_turns * 2
        history = all_history[-window_size:] if window_size > 0 else []
        return history + [{"role": "user", "parts": [{"text": user_text}]}]

    def _generate(self, *, system_instruction: str, contents: list[dict], expect_json: bool = True) -> str:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent",
            params={"key": self._api_key},
            json={
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json" if expect_json else "text/plain",
                },
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def chat(self, session: Session, user_text: str) -> Union[CoachResponse, TurnError]:
        try:
            system_instruction = (
                f"{self._build_system_prompt(session)}\n\n"
                "Return only a JSON object with these exact keys:\n"
                '{"coach_text": "string", "corrections": [{"original": "string", "corrected": "string", "explanation": "string", "triggered_by": "auto|user_request"}]}'
            )
            data = extract_json_object(
                self._generate(
                    system_instruction=system_instruction,
                    contents=self._build_contents(session, user_text),
                )
            )
            corrections = [
                Correction(
                    original=str(c["original"]),
                    corrected=str(c["corrected"]),
                    explanation=str(c["explanation"]),
                    triggered_by=str(c["triggered_by"]),
                )
                for c in data.get("corrections", [])
                if isinstance(c, dict)
                and {"original", "corrected", "explanation", "triggered_by"} <= set(c)
            ]
            return CoachResponse(coach_text=str(data["coach_text"]), corrections=corrections)
        except Exception as exc:
            return TurnError(
                stage="ai",
                message=f"Google request failed: {exc}",
                recoverable=True,
            )

    def translate(self, english_text: str) -> Union[str, TurnError]:
        try:
            data = extract_json_object(
                self._generate(
                    system_instruction=(
                        "Translate English to natural Spanish. "
                        'Return only JSON in the form {"translation": "..."}'
                    ),
                    contents=[{"role": "user", "parts": [{"text": english_text}]}],
                )
            )
            return str(data["translation"]).strip()
        except Exception as exc:
            return TurnError(
                stage="ai",
                message=f"Translation failed: {exc}",
                recoverable=True,
            )

    def evaluate_pronunciation(self, target: str, transcript: str) -> Union[PronunciationEvaluation, TurnError]:
        try:
            data = extract_json_object(
                self._generate(
                    system_instruction=(
                        "Evaluate a Spanish pronunciation attempt. "
                        'Return only JSON in the form {"score": 0-100, "feedback": "string", "issues": [{"sound": "string", "said": "string", "expected": "string"}]}'
                    ),
                    contents=[{
                        "role": "user",
                        "parts": [{
                            "text": (
                                "A Spanish learner attempted to say this phrase:\n\n"
                                f"Target: {target}\n"
                                f"Whisper transcript of their attempt: {transcript}\n\n"
                                "Give a score of 100 if the transcript matches the target exactly or very closely. "
                                "Identify any specific sounds that differ. Be encouraging."
                            )
                        }],
                    }],
                )
            )
            issues = [
                PronunciationIssue(
                    sound=str(issue["sound"]),
                    said=str(issue["said"]),
                    expected=str(issue["expected"]),
                )
                for issue in data.get("issues", [])
                if isinstance(issue, dict) and {"sound", "said", "expected"} <= set(issue)
            ]
            return PronunciationEvaluation(
                score=int(data["score"]),
                feedback=str(data["feedback"]),
                issues=issues,
            )
        except Exception as exc:
            return TurnError(
                stage="ai",
                message=f"Pronunciation evaluation failed: {exc}",
                recoverable=True,
            )

    def generate_flashcards(self, text: str, turns: list[dict], source: str) -> Union[list[dict], TurnError]:
        turns_lines = []
        for turn in turns:
            speaker = turn.get("speaker", "")
            content = turn.get("transcript_norm", "") if speaker == "user" else turn.get("coach_text", "")
            if content:
                turns_lines.append(f"{speaker}: {content}")
        turns_context = "\n".join(turns_lines)

        if source == "conversation":
            focal = f"Full conversation:\n{turns_context}"
            card_count = "5-15"
        else:
            context_section = f"\n\nConversation context:\n{turns_context}" if turns_context else ""
            focal = f"Text: {text}{context_section}"
            card_count = "3-8"

        prompt = (
            "Extract vocabulary and key phrases suitable for Spanish flashcard study.\n\n"
            f"{focal}\n\n"
            "Assign each card exactly one of these topic IDs:\n"
            "general, ordering_food, directions_transport, shopping_markets, work_daily_routine, travel_tourism\n\n"
            f"Assign difficulty levels 1-10 using this scale:\n{_LEVEL_SCALE}\n\n"
            f"Return {card_count} cards as a bare JSON array only with this shape:\n"
            '[{"english": "...", "spanish": "...", "level": 1, "topic": "..."}]'
        )

        try:
            raw = self._generate(
                system_instruction="Return only JSON arrays for flashcard extraction tasks.",
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )
            return parse_flashcard_response(raw)
        except Exception as exc:
            return TurnError(
                stage="ai",
                message=f"Flashcard generation failed: {exc}",
                recoverable=True,
            )
