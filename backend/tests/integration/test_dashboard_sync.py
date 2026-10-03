"""Integration tests for dashboard sync API with mocked Grafana."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.api.deps import get_grafana_client
from app.clients.grafana import GrafanaClient
from app.config import Settings, clear_settings_cache
from app.db import dispose_engine, get_session_factory
from app.main import create_app
from app.models.dashboard import Dashboard

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "sample_grafana_dashboard.json"
)


@pytest.fixture
async def sync_client() -> AsyncIterator[AsyncClient]:
    clear_settings_cache()
    await dispose_engine()

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/dashboards/uid/api-overview":
            return httpx.Response(200, json=payload)
        return httpx.Response(404, json={"message": "not found"})

    settings = Settings(
        grafana_url="http://grafana.test",
        grafana_api_token="test-token",
        database_url=(
            "postgresql+asyncpg://postgres:postgres@localhost:15432/monitoring_agent"
        ),
    )

    app = create_app()

    async def _grafana_override() -> AsyncIterator[GrafanaClient]:
        client = GrafanaClient(settings, transport=httpx.MockTransport(handler))
        try:
            yield client
        finally:
            await client.aclose()

    app.dependency_overrides[get_grafana_client] = _grafana_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await dispose_engine()
    clear_settings_cache()


async def _delete_dashboard(uid: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(delete(Dashboard).where(Dashboard.grafana_uid == uid))
        await session.commit()


@pytest.mark.asyncio
async def test_sync_list_and_get_dashboard(sync_client: AsyncClient) -> None:
    await _delete_dashboard("api-overview")

    sync_response = await sync_client.post("/api/v1/dashboards/api-overview/sync")
    assert sync_response.status_code == 200
    body = sync_response.json()
    assert body["created"] is True
    assert body["dashboard"]["grafana_uid"] == "api-overview"
    assert body["dashboard"]["panel_count"] == 3
    assert body["dashboard"]["variable_count"] == 2
    assert {panel["title"] for panel in body["dashboard"]["panels"]} == {
        "Request Count",
        "Success Rate",
        "Error Logs",
    }

    list_response = await sync_client.get("/api/v1/dashboards")
    assert list_response.status_code == 200
    assert any(item["grafana_uid"] == "api-overview" for item in list_response.json())

    get_response = await sync_client.get("/api/v1/dashboards/api-overview")
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["title"] == "API Overview"
    assert len(detail["panels"]) == 3
    assert len(detail["variables"]) == 2

    resync = await sync_client.post("/api/v1/dashboards/api-overview/sync")
    assert resync.status_code == 200
    assert resync.json()["created"] is False


@pytest.mark.asyncio
async def test_sync_missing_dashboard_returns_404(sync_client: AsyncClient) -> None:
    response = await sync_client.post("/api/v1/dashboards/does-not-exist/sync")
    assert response.status_code == 404
