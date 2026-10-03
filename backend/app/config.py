"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the monitoring dashboard agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "monitoring-dashboard-agent"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    request_timeout_seconds: float = 30.0

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:15432/monitoring_agent"
    )
    redis_url: str = "redis://localhost:6379/0"

    grafana_url: str = "http://localhost:3000"
    grafana_api_token: SecretStr | None = None
    grafana_timeout_seconds: float = 15.0

    prometheus_url: str = "http://localhost:9090"
    prometheus_timeout_seconds: float = 15.0
    prometheus_max_response_bytes: int = 1_048_576

    loki_url: str | None = None
    loki_timeout_seconds: float = 15.0
    loki_max_response_bytes: int = 1_048_576

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 60.0

    agent_max_tool_calls: int = 20
    agent_max_analysis_seconds: int = 120

    validation_consistency_tolerance: float = Field(default=0.02, ge=0.0)

    max_query_length: int = 4096
    max_time_range_seconds: int = 604_800
    query_concurrency_limit: int = 8


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear settings cache (useful in tests)."""
    get_settings.cache_clear()
