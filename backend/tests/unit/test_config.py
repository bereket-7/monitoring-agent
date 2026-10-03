"""Unit tests for application settings."""

import pytest

from app.config import Settings, clear_settings_cache, get_settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.app_name == "monitoring-dashboard-agent"
    assert settings.api_prefix == "/api/v1"
    assert settings.agent_max_tool_calls == 20
    assert "postgresql+asyncpg://" in settings.database_url


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("APP_NAME", "cached-app")
    first = get_settings()
    monkeypatch.setenv("APP_NAME", "other-app")
    second = get_settings()
    assert first is second
    assert first.app_name == "cached-app"
