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
        response = client.get("/flashcards/deck?topic=food&level_min=3&level_max=4")
        assert response.status_code == 200
        for card in response.json():
            assert card["topic"] == "food"
            assert 3 <= card["level"] <= 4

    def test_unknown_topic_returns_empty_list(self):
        response = client.get("/flashcards/deck?topic=nonexistent_xyz")
        assert response.status_code == 200
        assert response.json() == []
