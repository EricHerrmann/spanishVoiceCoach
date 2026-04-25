import base64
import os
import pytest
from fastapi.testclient import TestClient


def _make_auth_header(user: str, pw: str) -> str:
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return f"Basic {token}"


def _client(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DVC_DATA_DIR", "/tmp/duoVoiceCoach-auth-test")
    from backend.main import app
    return TestClient(app)


class TestBasicAuthMiddleware:
    def test_no_env_vars_allows_all_requests(self, monkeypatch):
        monkeypatch.delenv("DVC_BASIC_AUTH_USER", raising=False)
        monkeypatch.delenv("DVC_BASIC_AUTH_PASS", raising=False)
        client = _client(monkeypatch)
        assert client.get("/health").status_code == 200

    def test_valid_credentials_pass_through(self, monkeypatch):
        monkeypatch.setenv("DVC_BASIC_AUTH_USER", "alice")
        monkeypatch.setenv("DVC_BASIC_AUTH_PASS", "s3cret")
        client = _client(monkeypatch)
        response = client.get("/health", headers={"Authorization": _make_auth_header("alice", "s3cret")})
        assert response.status_code == 200

    def test_missing_auth_header_returns_401(self, monkeypatch):
        monkeypatch.setenv("DVC_BASIC_AUTH_USER", "alice")
        monkeypatch.setenv("DVC_BASIC_AUTH_PASS", "s3cret")
        client = _client(monkeypatch)
        response = client.get("/health")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_wrong_password_returns_401(self, monkeypatch):
        monkeypatch.setenv("DVC_BASIC_AUTH_USER", "alice")
        monkeypatch.setenv("DVC_BASIC_AUTH_PASS", "s3cret")
        client = _client(monkeypatch)
        response = client.get("/health", headers={"Authorization": _make_auth_header("alice", "wrong")})
        assert response.status_code == 401
