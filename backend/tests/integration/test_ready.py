"""Integration tests for readiness and database connectivity."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.db import check_database_connection, dispose_engine


@pytest.mark.asyncio
async def test_database_connection() -> None:
    await dispose_engine()
    assert await check_database_connection() is True


@pytest.mark.asyncio
async def test_ready_ok(app_client: AsyncClient) -> None:
    response = await app_client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert "request_id" in body


@pytest.mark.asyncio
async def test_ready_unavailable_when_db_fails(
    app_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fail() -> bool:
        raise SQLAlchemyError("simulated outage")

    monkeypatch.setattr("app.api.routes_health.check_database_connection", _fail)
    response = await app_client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["database"] == "error"
