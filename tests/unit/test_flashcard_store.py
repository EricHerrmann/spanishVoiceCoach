import json
import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DVC_DATA_DIR", "/tmp/duoVoiceCoach-test-data")

from backend.main import load_user_deck, save_user_deck


def _unique_card(spanish_suffix: str) -> dict:
    """Create a card with a unique Spanish phrase that won't clash with the static deck."""
    return {
        "english": "test phrase",
        "spanish": f"__test_frase_{spanish_suffix}__",
        "level": 3,
        "topic": "general",
    }


class TestLoadUserDeck:
    def test_returns_empty_list_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        assert load_user_deck() == []

    def test_returns_cards_from_existing_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = {"id": "u-abc", "english": "hi", "spanish": "__test_hi__", "level": 1, "topic": "general"}
        deck_file = tmp_path / "user_flashcards.json"
        deck_file.write_text(json.dumps([card]))
        result = load_user_deck()
        assert len(result) == 1
        assert result[0]["spanish"] == "__test_hi__"


class TestSaveUserDeck:
    def test_creates_file_on_first_write(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = _unique_card("create_test")
        saved = save_user_deck([card])
        assert len(saved) == 1
        assert (tmp_path / "user_flashcards.json").exists()

    def test_saved_card_has_u_prefixed_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        saved = save_user_deck([_unique_card("id_prefix")])
        assert saved[0]["id"].startswith("u-")

    def test_appends_to_existing_cards(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        save_user_deck([_unique_card("first")])
        save_user_deck([_unique_card("second")])
        result = load_user_deck()
        assert len(result) == 2

    def test_exact_spanish_match_is_deduped(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = _unique_card("dedup_exact")
        save_user_deck([card])
        saved = save_user_deck([card])
        assert saved == []
        assert len(load_user_deck()) == 1

    def test_dedup_is_case_insensitive(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = {"english": "x", "spanish": "__TEST_CASE__", "level": 1, "topic": "general"}
        save_user_deck([card])
        card_lower = {"english": "x", "spanish": "__test_case__", "level": 1, "topic": "general"}
        saved = save_user_deck([card_lower])
        assert saved == []

    def test_near_match_different_word_is_kept(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        save_user_deck([_unique_card("near_a")])
        saved = save_user_deck([_unique_card("near_b")])
        assert len(saved) == 1

    def test_all_duplicate_input_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = _unique_card("all_dup")
        save_user_deck([card])
        result = save_user_deck([card, card])
        assert result == []

    def test_idempotency_same_card_twice_stored_once(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DVC_DATA_DIR", str(tmp_path))
        card = _unique_card("idempotent")
        save_user_deck([card])
        save_user_deck([card])
        assert len(load_user_deck()) == 1
