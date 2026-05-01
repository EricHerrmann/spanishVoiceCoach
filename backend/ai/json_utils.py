import json
import re
from typing import Any


def extract_json_payload(raw_text: str) -> Any:
    """Parse a JSON object/array from raw model text, tolerating surrounding prose."""
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Empty response")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for pattern in (r"\{.*\}", r"\[.*\]"):
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            continue
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            continue

    raise ValueError("No JSON payload found")


def extract_json_object(raw_text: str) -> dict:
    payload = extract_json_payload(raw_text)
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object")
    return payload
