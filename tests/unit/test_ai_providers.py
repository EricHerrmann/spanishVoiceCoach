"""Unit tests for AI provider abstract base class."""
from __future__ import annotations

import pytest

from backend.ai.base import AbstractAIProvider
from backend.session import CoachResponse, Correction, PronunciationEvaluation


def test_abstract_ai_provider_raises_not_implemented():
    """Directly calling AbstractAIProvider.chat() raises NotImplementedError."""

    class ConcreteNoOp(AbstractAIProvider):
        """Minimal concrete subclass that does NOT override chat(), evaluate_pronunciation(), translate(), or generate_flashcards()."""

        def chat(self, session, user_text: str) -> str:
            return super().chat(session, user_text)

        def evaluate_pronunciation(self, target: str, transcript: str):
            return super().evaluate_pronunciation(target, transcript)

        def translate(self, english_text: str):
            return super().translate(english_text)

        def generate_flashcards(self, text: str, turns: list[dict], source: str):
            return super().generate_flashcards(text, turns, source)

    provider = ConcreteNoOp()
    with pytest.raises(NotImplementedError):
        provider.chat(session=None, user_text="hola")
    with pytest.raises(NotImplementedError):
        provider.evaluate_pronunciation(target="hola", transcript="hola")
    with pytest.raises(NotImplementedError):
        provider.translate(english_text="hello")
    with pytest.raises(NotImplementedError):
        provider.generate_flashcards(text="hello", turns=[], source="turn")


from backend.session import new_session
from backend.ai.openai import OpenAIProvider


class TestOpenAIProvider:
    def test_chat_raises_not_implemented(self):
        provider = OpenAIProvider()
        session = new_session(
            topic="ordering food", level=5,
            ai_provider="openai", coaching_mode="on_demand"
        )
        with pytest.raises(NotImplementedError):
            provider.chat(session, "hola")

    def test_evaluate_pronunciation_raises_not_implemented(self):
        provider = OpenAIProvider()
        with pytest.raises(NotImplementedError):
            provider.evaluate_pronunciation(target="hola", transcript="hola")

    def test_translate_raises_not_implemented(self):
        provider = OpenAIProvider()
        with pytest.raises(NotImplementedError):
            provider.translate(english_text="hello")

    def test_generate_flashcards_raises_not_implemented(self):
        provider = OpenAIProvider()
        with pytest.raises(NotImplementedError):
            provider.generate_flashcards(text="hello", turns=[], source="turn")


from unittest.mock import MagicMock, patch
from backend.ai.claude import ClaudeProvider
from backend.session import TurnError


def _make_session():
    return new_session(
        topic="ordering food", level=5,
        ai_provider="claude", coaching_mode="on_demand"
    )


def _mock_tool_response(coach_text, corrections=None):
    """Build a fake anthropic response containing a tool_use block."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {"coach_text": coach_text, "corrections": corrections or []}
    response = MagicMock()
    response.content = [tool_block]
    return response


class TestClaudeProvider:
    def test_valid_response_returns_coach_response(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.messages.create.return_value = _mock_tool_response(
                    "¡Hola! ¿Qué quieres pedir hoy?"
                )

                provider = ClaudeProvider()
                result = provider.chat(_make_session(), "hola quiero ordenar")

                assert isinstance(result, CoachResponse)
                assert result.coach_text == "¡Hola! ¿Qué quieres pedir hoy?"
                assert result.corrections == []

    def test_response_with_corrections_parses_them(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.messages.create.return_value = _mock_tool_response(
                    "¡Muy bien!",
                    corrections=[{
                        "original": "yo quiero ir",
                        "corrected": "quiero ir",
                        "explanation": "Subject pronoun 'yo' is optional in Spanish and sounds unnatural here.",
                        "triggered_by": "auto",
                    }],
                )

                provider = ClaudeProvider()
                result = provider.chat(_make_session(), "yo quiero ir al mercado")

                assert isinstance(result, CoachResponse)
                assert len(result.corrections) == 1
                assert result.corrections[0].original == "yo quiero ir"
                assert result.corrections[0].triggered_by == "auto"

    def test_response_with_no_tool_use_block_returns_turn_error(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                empty_response = MagicMock()
                empty_response.content = []
                mock_client.messages.create.return_value = empty_response

                provider = ClaudeProvider()
                result = provider.chat(_make_session(), "hola")

                assert isinstance(result, TurnError)
                assert result.stage == "ai"
                assert result.recoverable is True

    def test_api_error_returns_turn_error(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.messages.create.side_effect = Exception("connection refused")

                provider = ClaudeProvider()
                result = provider.chat(_make_session(), "hola")

                assert isinstance(result, TurnError)
                assert result.stage == "ai"
                assert result.recoverable is True

    def test_missing_api_key_raises_runtime_error_at_instantiation(self):
        import os
        clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict("os.environ", clean_env, clear=True):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                ClaudeProvider()


class TestClaudeProviderSystemPrompt:
    def test_system_prompt_includes_level(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
                session = new_session(topic="ordering food", level=7, ai_provider="claude", coaching_mode="on_demand")
                prompt = provider._build_system_prompt(session)
                assert "7/10" in prompt

    def test_system_prompt_includes_topic(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
                session = new_session(topic="ordering food", level=5, ai_provider="claude", coaching_mode="on_demand")
                prompt = provider._build_system_prompt(session)
                assert "ordering food" in prompt

    def test_system_prompt_includes_level_band_table(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
                session = new_session(topic="travel", level=3, ai_provider="claude", coaching_mode="on_demand")
                prompt = provider._build_system_prompt(session)
                assert "1–2" in prompt
                assert "7–10" in prompt

    def test_system_prompt_includes_coaching_mode(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
                for mode in ("on_demand", "explicit", "shadowing"):
                    session = new_session(topic="travel", level=5, ai_provider="claude", coaching_mode=mode)
                    prompt = provider._build_system_prompt(session)
                    assert mode in prompt

    def test_on_demand_prompt_instructs_no_auto_correction(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
                session = new_session(topic="food", level=5, ai_provider="claude", coaching_mode="on_demand")
                prompt = provider._build_system_prompt(session)
                assert "explicitly" in prompt.lower() or "only if" in prompt.lower()

    def test_explicit_prompt_instructs_always_correct(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
                session = new_session(topic="food", level=5, ai_provider="claude", coaching_mode="explicit")
                prompt = provider._build_system_prompt(session)
                assert "always" in prompt.lower()

    def test_shadowing_prompt_instructs_suppress_overlay(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
                session = new_session(topic="food", level=5, ai_provider="claude", coaching_mode="shadowing")
                prompt = provider._build_system_prompt(session)
                assert "empty corrections list" in prompt.lower() or "return an empty" in prompt.lower()


def _mock_pronunciation_response(score, feedback, issues=None):
    """Build a fake anthropic response containing an evaluate_pronunciation tool_use block."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "evaluate_pronunciation"
    tool_block.input = {"score": score, "feedback": feedback, "issues": issues or []}
    response = MagicMock()
    response.content = [tool_block]
    return response


class TestClaudeProviderEvaluatePronunciation:
    def test_valid_tool_response_returns_pronunciation_evaluation(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.messages.create.return_value = _mock_pronunciation_response(
                    score=90, feedback="Great!", issues=[]
                )

                provider = ClaudeProvider()
                result = provider.evaluate_pronunciation("hola", "hola")

                assert isinstance(result, PronunciationEvaluation)
                assert result.score == 90
                assert result.feedback == "Great!"
                assert result.issues == []

    def test_missing_tool_block_returns_turn_error(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                empty_response = MagicMock()
                empty_response.content = []
                mock_client.messages.create.return_value = empty_response

                provider = ClaudeProvider()
                result = provider.evaluate_pronunciation("hola", "ola")

                assert isinstance(result, TurnError)
                assert result.stage == "ai"
                assert result.recoverable is True

    def test_api_exception_returns_turn_error(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.messages.create.side_effect = Exception("connection refused")

                provider = ClaudeProvider()
                result = provider.evaluate_pronunciation("hola", "hola")

                assert isinstance(result, TurnError)
                assert result.stage == "ai"
                assert result.recoverable is True


def test_abstract_provider_generate_flashcards_raises():
    """AbstractAIProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AbstractAIProvider()


# ---------------------------------------------------------------------------
# ClaudeProvider._build_messages — sliding-window context tests
# ---------------------------------------------------------------------------

from datetime import datetime, timezone
from backend.session import Turn


def _make_turn(speaker: str, content: str) -> Turn:
    """Build a minimal Turn fixture with the given speaker and content."""
    ts = datetime.now(timezone.utc)
    if speaker == "user":
        return Turn(speaker="user", timestamp=ts, transcript_norm=content)
    else:
        return Turn(speaker="coach", timestamp=ts, coach_text=content)


class TestClaudeProviderBuildMessages:
    """Unit tests for _build_messages() sliding-window context truncation."""

    def _make_provider(self, context_turns: int | None = None) -> "ClaudeProvider":
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("backend.ai.claude.anthropic.Anthropic"):
                provider = ClaudeProvider()
        if context_turns is not None:
            provider._context_turns = context_turns
        return provider

    def test_empty_session_returns_only_new_user_message(self):
        """0 turns in session → only the new user message (length 1)."""
        provider = self._make_provider()
        session = _make_session()
        # session.turns is empty by default
        messages = provider._build_messages(session, "hola")
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "hola"}

    def test_three_pairs_no_truncation(self):
        """3 user/coach pairs + new message → 7 total (context_turns=10, no truncation)."""
        provider = self._make_provider(context_turns=10)
        session = _make_session()
        for i in range(3):
            session.turns.append(_make_turn("user", f"user message {i}"))
            session.turns.append(_make_turn("coach", f"coach reply {i}"))
        messages = provider._build_messages(session, "new message")
        assert len(messages) == 7  # 6 historical + 1 new
        assert messages[-1] == {"role": "user", "content": "new message"}

    def test_fifteen_pairs_truncated_to_ten(self):
        """15 user/coach pairs with context_turns=10 → last 10 pairs (20 msgs) + new = 21 total."""
        provider = self._make_provider(context_turns=10)
        session = _make_session()
        for i in range(15):
            session.turns.append(_make_turn("user", f"user message {i}"))
            session.turns.append(_make_turn("coach", f"coach reply {i}"))
        messages = provider._build_messages(session, "new message")
        assert len(messages) == 21  # 20 historical + 1 new
        assert messages[-1] == {"role": "user", "content": "new message"}

    def test_context_turns_zero_returns_only_new_message(self):
        """context_turns=0 → no historical messages, only the new user message."""
        provider = self._make_provider(context_turns=0)
        session = _make_session()
        session.turns.append(_make_turn("user", "old message"))
        session.turns.append(_make_turn("coach", "old reply"))
        messages = provider._build_messages(session, "new message")
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "new message"}

    def test_most_recent_turns_are_preserved(self):
        """When truncation occurs, the MOST RECENT turns are kept (not the oldest)."""
        provider = self._make_provider(context_turns=2)
        session = _make_session()
        # Add 5 pairs; with context_turns=2 only last 2 pairs should survive
        for i in range(5):
            session.turns.append(_make_turn("user", f"user message {i}"))
            session.turns.append(_make_turn("coach", f"coach reply {i}"))
        messages = provider._build_messages(session, "new message")
        # Should have 4 historical + 1 new = 5
        assert len(messages) == 5
        # First historical message should be from pair 3 (0-indexed), not pair 0
        assert messages[0] == {"role": "user", "content": "user message 3"}
        assert messages[1] == {"role": "assistant", "content": "coach reply 3"}
        assert messages[2] == {"role": "user", "content": "user message 4"}
        assert messages[3] == {"role": "assistant", "content": "coach reply 4"}
        assert messages[4] == {"role": "user", "content": "new message"}
