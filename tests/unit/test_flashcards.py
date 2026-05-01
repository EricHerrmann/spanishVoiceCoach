import json
import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestGetFlashcardDeck:
    def test_returns_list(self):
        response = client.get("/flashcards/deck")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_cards_have_required_fields(self):
        response = client.get("/flashcards/deck")
        for card in response.json():
            assert "id" in card
            assert "english" in card
            assert "spanish" in card
            assert "level" in card
            assert "topic" in card

    def test_topic_filter(self):
        response = client.get("/flashcards/deck?topic=general")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        for card in data:
            assert card["topic"] == "general"

    def test_level_min_filter(self):
        response = client.get("/flashcards/deck?level_min=3")
        assert response.status_code == 200
        for card in response.json():
            assert card["level"] >= 3

    def test_level_max_filter(self):
        response = client.get("/flashcards/deck?level_max=2")
        assert response.status_code == 200
        for card in response.json():
            assert card["level"] <= 2

    def test_combined_filter(self):
        response = client.get("/flashcards/deck?topic=ordering_food&level_min=3&level_max=4")
        assert response.status_code == 200
        for card in response.json():
            assert card["topic"] == "ordering_food"
            assert 3 <= card["level"] <= 4

    def test_unknown_topic_returns_empty_list(self):
        response = client.get("/flashcards/deck?topic=nonexistent_xyz")
        assert response.status_code == 200
        assert response.json() == []


class TestGetFlashcardDeckMerged:
    def test_user_deck_cards_appear_in_results(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        user_card = {
            "id": "u-test-1",
            "english": "test user card",
            "spanish": "__test_user_card__",
            "level": 3,
            "topic": "general",
        }
        deck_file = tmp_path / "user_flashcards.json"
        deck_file.write_text(json.dumps([user_card]))

        response = client.get("/flashcards/deck")
        assert response.status_code == 200
        spanish_phrases = [c["spanish"] for c in response.json()]
        assert "__test_user_card__" in spanish_phrases

    def test_topic_filter_applies_to_user_cards(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        user_card = {
            "id": "u-test-2",
            "english": "to travel",
            "spanish": "__test_viajar__",
            "level": 4,
            "topic": "travel_tourism",
        }
        deck_file = tmp_path / "user_flashcards.json"
        deck_file.write_text(json.dumps([user_card]))

        response = client.get("/flashcards/deck?topic=general")
        assert response.status_code == 200
        spanish_phrases = [c["spanish"] for c in response.json()]
        assert "__test_viajar__" not in spanish_phrases

    def test_level_filter_applies_to_user_cards(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        user_card = {
            "id": "u-test-3",
            "english": "difficult word",
            "spanish": "__test_dificil__",
            "level": 9,
            "topic": "general",
        }
        deck_file = tmp_path / "user_flashcards.json"
        deck_file.write_text(json.dumps([user_card]))

        response = client.get("/flashcards/deck?level_max=5")
        assert response.status_code == 200
        spanish_phrases = [c["spanish"] for c in response.json()]
        assert "__test_dificil__" not in spanish_phrases


class TestPostFlashcardGenerate:
    def test_returns_200_with_list(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "backend.main.get_ai_provider",
            lambda *_args, **_kwargs: type("MockProvider", (), {
                "generate_flashcards": lambda self, text, turns, source: [
                    {"english": "to ask for", "spanish": "__test_pedir__", "level": 3, "topic": "ordering_food"}
                ],
            })(),
        )
        response = client.post("/flashcards/generate", json={
            "text": "Quisiera pedir la cuenta",
            "turns": [],
            "source": "turn",
        })
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_returns_empty_list_for_all_duplicates(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "backend.main.get_ai_provider",
            lambda *_args, **_kwargs: type("MockProvider", (), {
                "generate_flashcards": lambda self, text, turns, source: [
                    {"english": "yes", "spanish": "__test_si_dup__", "level": 1, "topic": "general"}
                ],
            })(),
        )
        # First call saves the card
        client.post("/flashcards/generate", json={"text": "sí", "turns": [], "source": "turn"})
        # Second call should return empty (duplicate)
        response = client.post("/flashcards/generate", json={"text": "sí", "turns": [], "source": "turn"})
        assert response.status_code == 200
        assert response.json() == []

    def test_provider_error_returns_500(self, monkeypatch):
        from backend.session import TurnError
        monkeypatch.setattr(
            "backend.main.get_ai_provider",
            lambda *_args, **_kwargs: type("MockProvider", (), {
                "generate_flashcards": lambda self, text, turns, source: TurnError(
                    stage="ai", message="Claude failed", recoverable=True
                ),
            })(),
        )
        response = client.post("/flashcards/generate", json={
            "text": "test",
            "turns": [],
            "source": "turn",
        })
        assert response.status_code == 500
