"""Persistence layer for user and static flashcard decks."""
import json
import os
import pathlib
import uuid

_FLASHCARD_DECK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "data" / "flashcard_deck.json"


def _get_user_deck_path() -> pathlib.Path:
    data_dir = pathlib.Path(os.environ.get("DVC_DATA_DIR", "~/.duoVoiceCoach")).expanduser()
    return data_dir / "user_flashcards.json"


def load_user_deck() -> list[dict]:
    """Return all cards the user has saved, or [] if none."""
    path = _get_user_deck_path()
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def save_user_deck(new_cards: list[dict]) -> list[dict]:
    """Append new_cards to user deck after deduplication.

    Returns only the cards actually saved (not already present in user or static deck).
    """
    existing = load_user_deck()
    existing_spanish = {c["spanish"].lower().strip() for c in existing}

    try:
        with open(_FLASHCARD_DECK_PATH) as f:
            static = json.load(f)
        existing_spanish.update(c["spanish"].lower().strip() for c in static)
    except (OSError, json.JSONDecodeError):
        pass

    saved = []
    for card in new_cards:
        key = card["spanish"].lower().strip()
        if key in existing_spanish:
            continue
        existing_spanish.add(key)
        card_with_id = {"id": f"u-{uuid.uuid4()}", **card}
        existing.append(card_with_id)
        saved.append(card_with_id)

    if saved:
        path = _get_user_deck_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(existing, f, indent=2)

    return saved
