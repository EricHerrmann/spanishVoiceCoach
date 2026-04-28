"""Unit tests for the OrderedDict-backed LRU session cache in backend.main."""
from __future__ import annotations

import importlib
from collections import OrderedDict

import pytest

import backend.main as main_module
from backend.main import _cache_session, sessions, _SESSION_CACHE_MAX
from backend.session import new_session


def _make_session(topic: str = "general") -> object:
    return new_session(
        topic=topic,
        level=5,
        ai_provider="claude",
        coaching_mode="on_demand",
    )


@pytest.fixture(autouse=True)
def clear_sessions():
    """Ensure the module-level sessions dict is empty before and after each test."""
    sessions.clear()
    yield
    sessions.clear()


def test_cache_size_after_50_inserts():
    """After inserting exactly 50 sessions, cache size is 50."""
    for _ in range(_SESSION_CACHE_MAX):
        s = _make_session()
        _cache_session(s.id, s)
    assert len(sessions) == _SESSION_CACHE_MAX


def test_cache_evicts_oldest_on_51st_insert():
    """After inserting 51 sessions, cache size is still 50 and the first entry is evicted."""
    first_session = _make_session()
    _cache_session(first_session.id, first_session)

    for _ in range(_SESSION_CACHE_MAX):
        s = _make_session()
        _cache_session(s.id, s)

    assert len(sessions) == _SESSION_CACHE_MAX
    assert first_session.id not in sessions


def test_accessing_session_promotes_to_mru():
    """Re-inserting an existing session via _cache_session moves it to MRU (not evicted next)."""
    # Fill cache to max
    first_session = _make_session()
    _cache_session(first_session.id, first_session)

    middle_sessions = []
    for _ in range(_SESSION_CACHE_MAX - 1):
        s = _make_session()
        _cache_session(s.id, s)
        middle_sessions.append(s)

    # first_session is at the front (LRU); promote it by re-inserting
    _cache_session(first_session.id, first_session)

    # Now insert one more to trigger eviction — the second-oldest (middle_sessions[0]) should be evicted
    new_s = _make_session()
    _cache_session(new_s.id, new_s)

    assert len(sessions) == _SESSION_CACHE_MAX
    # first_session was promoted to MRU, so it should still be present
    assert first_session.id in sessions
    # The actual LRU (middle_sessions[0]) should have been evicted
    assert middle_sessions[0].id not in sessions
