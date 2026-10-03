"""Unit tests for GrafanaClient with mocked HTTP transport."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.clients.errors import GrafanaAuthError, GrafanaNotFoundError
from app.clients.grafana import GrafanaClient
from app.config import Settings

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "sample_grafana_dashboard.json"
)


@pytest.mark.asyncio
async def test_get_dashboard_by_uid_success() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/dashboards/uid/api-overview"
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    settings = Settings(
        grafana_url="http://grafana.test",
        grafana_api_token="token",
    )
    async with GrafanaClient(settings, transport=transport) as client:
        result = await client.get_dashboard_by_uid("api-overview")

    assert result["dashboard"]["uid"] == "api-overview"


@pytest.mark.asyncio
async def test_get_dashboard_not_found() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "not found"})

    transport = httpx.MockTransport(handler)
    settings = Settings(grafana_url="http://grafana.test")
    async with GrafanaClient(settings, transport=transport) as client:
        with pytest.raises(GrafanaNotFoundError):
            await client.get_dashboard_by_uid("missing")


@pytest.mark.asyncio
async def test_get_dashboard_auth_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "unauthorized"})

    transport = httpx.MockTransport(handler)
    settings = Settings(grafana_url="http://grafana.test")
    async with GrafanaClient(settings, transport=transport) as client:
        with pytest.raises(GrafanaAuthError):
            await client.get_dashboard_by_uid("api-overview")
