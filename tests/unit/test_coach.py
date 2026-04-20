from unittest.mock import MagicMock
import pytest
from backend.coach import CoachSession
from backend.session import new_session, CoachResponse, TurnError, Turn


def _mock_provider(return_value):
    provider = MagicMock()
    provider.chat.return_value = return_value
    return provider


class TestCoachSessionHandleTurn:
    def test_successful_turn_appends_user_and_coach_turns(self):
        session = new_session(
            topic="travel", level=3, ai_provider="claude", coaching_mode="on_demand"
        )
        coach_response = CoachResponse(
            coach_text="¿A dónde quieres viajar?", corrections=[]
        )
        coach = CoachSession(session, _mock_provider(coach_response))

        coach.handle_turn("quiero viajar a españa")

        assert len(session.turns) == 2
        assert session.turns[0].speaker == "user"
        assert session.turns[0].transcript_norm == "quiero viajar a españa"
        assert session.turns[1].speaker == "coach"
        assert session.turns[1].coach_text == "¿A dónde quieres viajar?"

    def test_successful_turn_returns_coach_turn(self):
        session = new_session(
            topic="food", level=2, ai_provider="claude", coaching_mode="on_demand"
        )
        coach_response = CoachResponse(
            coach_text="¿Qué quieres comer?", corrections=[]
        )
        coach = CoachSession(session, _mock_provider(coach_response))

        result = coach.handle_turn("quiero comer tacos")

        assert isinstance(result, Turn)
        assert result.speaker == "coach"
        assert result.coach_text == "¿Qué quieres comer?"
        assert result.corrections == []

    def test_provider_error_appends_user_and_error_turns(self):
        session = new_session(
            topic="food", level=2, ai_provider="claude", coaching_mode="on_demand"
        )
        turn_error = TurnError(stage="ai", message="API failed", recoverable=True)
        coach = CoachSession(session, _mock_provider(turn_error))

        result = coach.handle_turn("hola")

        assert isinstance(result, TurnError)
        assert len(session.turns) == 2
        assert session.turns[0].speaker == "user"
        assert session.turns[1].speaker == "coach"
        assert session.turns[1].error is not None
        assert session.turns[1].error.stage == "ai"

    def test_session_passed_to_provider_has_correct_fields(self):
        session = new_session(
            topic="ordering food", level=5, ai_provider="claude", coaching_mode="on_demand"
        )
        provider = _mock_provider(CoachResponse(coach_text="Hola", corrections=[]))
        coach = CoachSession(session, provider)

        coach.handle_turn("hola")

        called_session, called_text = provider.chat.call_args[0]
        assert called_session.level == 5
        assert called_session.topic == "ordering food"
        assert called_session.coaching_mode == "on_demand"
        assert called_text == "hola"

    def test_conversation_history_accumulates_across_turns(self):
        session = new_session(
            topic="general", level=5, ai_provider="claude", coaching_mode="on_demand"
        )
        provider = _mock_provider(CoachResponse(coach_text="¡Bien!", corrections=[]))
        coach = CoachSession(session, provider)

        coach.handle_turn("primer turno")
        coach.handle_turn("segundo turno")

        assert len(session.turns) == 4
        assert session.turns[0].transcript_norm == "primer turno"
        assert session.turns[2].transcript_norm == "segundo turno"
