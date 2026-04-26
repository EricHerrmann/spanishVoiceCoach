import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

from backend.ai.claude import parse_flashcard_response


class TestParseFlashcardResponse:
    def test_valid_bare_json_array(self):
        raw = '[{"english": "to order", "spanish": "pedir", "level": 3, "topic": "ordering_food"}]'
        result = parse_flashcard_response(raw)
        assert len(result) == 1
        assert result[0]["spanish"] == "pedir"
        assert result[0]["topic"] == "ordering_food"

    def test_json_in_markdown_fences(self):
        raw = '```json\n[{"english": "yes", "spanish": "sí", "level": 1, "topic": "general"}]\n```'
        result = parse_flashcard_response(raw)
        assert len(result) == 1
        assert result[0]["spanish"] == "sí"

    def test_json_embedded_in_prose(self):
        raw = 'Here are flashcards:\n[{"english": "table", "spanish": "mesa", "level": 2, "topic": "ordering_food"}]\nDone.'
        result = parse_flashcard_response(raw)
        assert len(result) == 1

    def test_invalid_topic_dropped(self):
        raw = '[{"english": "hello", "spanish": "hola", "level": 2, "topic": "BOGUS_TOPIC"}]'
        assert parse_flashcard_response(raw) == []

    def test_level_zero_dropped(self):
        raw = '[{"english": "hello", "spanish": "hola", "level": 0, "topic": "general"}]'
        assert parse_flashcard_response(raw) == []

    def test_level_eleven_dropped(self):
        raw = '[{"english": "hello", "spanish": "hola", "level": 11, "topic": "general"}]'
        assert parse_flashcard_response(raw) == []

    def test_missing_spanish_field_dropped(self):
        raw = '[{"english": "hello", "level": 2, "topic": "general"}]'
        assert parse_flashcard_response(raw) == []

    def test_missing_english_field_dropped(self):
        raw = '[{"spanish": "hola", "level": 2, "topic": "general"}]'
        assert parse_flashcard_response(raw) == []

    def test_completely_malformed_returns_empty(self):
        assert parse_flashcard_response("this is not json") == []
        assert parse_flashcard_response("") == []

    def test_mixed_valid_and_invalid_cards(self):
        raw = (
            '[{"english": "yes", "spanish": "sí", "level": 1, "topic": "general"},'
            '{"english": "bad", "spanish": "malo", "level": 0, "topic": "general"}]'
        )
        result = parse_flashcard_response(raw)
        assert len(result) == 1
        assert result[0]["spanish"] == "sí"

    def test_all_six_valid_topics_accepted(self):
        topics = [
            "general", "ordering_food", "directions_transport",
            "shopping_markets", "work_daily_routine", "travel_tourism",
        ]
        for topic in topics:
            raw = f'[{{"english": "x", "spanish": "y", "level": 5, "topic": "{topic}"}}]'
            result = parse_flashcard_response(raw)
            assert len(result) == 1, f"Topic {topic} should be valid"
