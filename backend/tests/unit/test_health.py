"""Unit tests for health endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ok(app_client: AsyncClient) -> None:
    response = await app_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "request_id" in body
    assert response.headers["X-Request-ID"] == body["request_id"]


@pytest.mark.asyncio
async def test_health_respects_incoming_request_id(app_client: AsyncClient) -> None:
    response = await app_client.get("/health", headers={"X-Request-ID": "req-123"})
    assert response.status_code == 200
    assert response.json()["request_id"] == "req-123"
    assert response.headers["X-Request-ID"] == "req-123"
