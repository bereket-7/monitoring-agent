"""Unit tests for Phase 10 security hardening."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, clear_settings_cache
from app.main import create_app
from app.security.auth import extract_api_key, verify_api_key
from app.security.rate_limit import allow_request, reset_memory_limiter
from app.security.redaction import REDACTED, redact_object, redact_text


def test_redact_text_removes_secrets_and_emails() -> None:
    text = "Authorization: Bearer supersecrettoken123 email user@example.com api_key=abcd1234"
    redacted = redact_text(text)
    assert "supersecrettoken123" not in redacted
    assert "user@example.com" not in redacted
    assert "abcd1234" not in redacted
    assert REDACTED in redacted


def test_redact_object_masks_sensitive_keys() -> None:
    payload = {
        "authorization": "Bearer abc",
        "nested": {"token": "xyz", "query": "sum(up)"},
    }
    redacted = redact_object(payload)
    assert redacted["authorization"] == REDACTED
    assert redacted["nested"]["token"] == REDACTED
    assert redacted["nested"]["query"] == "sum(up)"


def test_api_key_verification() -> None:
    assert extract_api_key("Bearer good-key-value", None) == "good-key-value"
    assert extract_api_key(None, "header-key") == "header-key"
    assert verify_api_key("good-key-value", {"good-key-value"})
    assert not verify_api_key("bad", {"good-key-value"})


@pytest.mark.asyncio
async def test_memory_rate_limiter() -> None:
    reset_memory_limiter()
    settings = Settings(rate_limit_requests_per_minute=2)
    assert await allow_request(key="test", settings=settings, redis_client=None)
    assert await allow_request(key="test", settings=settings, redis_client=None)
    assert not await allow_request(key="test", settings=settings, redis_client=None)


@pytest.mark.asyncio
async def test_auth_required_rejects_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "test-secret-key-1234")
    clear_settings_cache()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.get("/api/v1/dashboards")
        assert denied.status_code == 401

        allowed = await client.get(
            "/api/v1/dashboards",
            headers={"Authorization": "Bearer test-secret-key-1234"},
        )
        # May be 200 (empty list) depending on DB; must not be auth failure.
        assert allowed.status_code != 401

        health = await client.get("/health")
        assert health.status_code == 200

    clear_settings_cache()


@pytest.mark.asyncio
async def test_metrics_endpoint_public() -> None:
    clear_settings_cache()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "http_requests_total" in response.text or response.text.startswith("#")
