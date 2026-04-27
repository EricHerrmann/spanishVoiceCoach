import json
import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

_VALID_TOPICS = {"general", "ordering_food", "directions_transport", "shopping_markets", "work_daily_routine", "travel_tourism"}


def _has_real_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return bool(key) and key != "test-key"


@pytest.mark.slow
class TestFlashcardGenerateIntegration:
    def test_generates_cards_from_short_phrase(self, tmp_path, monkeypatch):
        if not _has_real_api_key():
            pytest.skip("ANTHROPIC_API_KEY not set to a real key")
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))

        from backend.ai.claude import ClaudeProvider
        provider = ClaudeProvider()
        result = provider.generate_flashcards(
            "Quisiera pedir la cuenta, por favor",
            [],
            "turn",
        )

        from backend.session import TurnError
        assert not isinstance(result, TurnError), f"Got TurnError: {result.message}"
        assert len(result) > 0

        for card in result:
            assert "english" in card, f"Missing 'english': {card}"
            assert "spanish" in card, f"Missing 'spanish': {card}"
            assert "level" in card, f"Missing 'level': {card}"
            assert "topic" in card, f"Missing 'topic': {card}"
            assert 1 <= card["level"] <= 10, f"Level out of range: {card['level']}"
            assert card["topic"] in _VALID_TOPICS, f"Invalid topic: {card['topic']}"

    def test_generate_endpoint_saves_to_user_deck(self, tmp_path, monkeypatch):
        if not _has_real_api_key():
            pytest.skip("ANTHROPIC_API_KEY not set to a real key")
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))

        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)

        response = client.post("/flashcards/generate", json={
            "text": "Quisiera pedir la cuenta, por favor",
            "turns": [],
            "source": "turn",
        })
        assert response.status_code == 200
        cards = response.json()
        assert isinstance(cards, list)

        if len(cards) > 0:
            deck_path = tmp_path / "user_flashcards.json"
            assert deck_path.exists()
            saved = json.loads(deck_path.read_text())
            assert len(saved) == len(cards)
            for card in saved:
                assert card["id"].startswith("u-")
