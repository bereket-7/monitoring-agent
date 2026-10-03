"""Unit tests for LokiClient with mocked HTTP transport."""

from __future__ import annotations

import httpx
import pytest

from app.clients.errors import LokiQueryError, LokiUnavailableError
from app.clients.loki import LokiClient
from app.config import Settings


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "loki_url": "http://loki.test",
        "loki_timeout_seconds": 5.0,
        "loki_max_response_bytes": 2048,
        "max_query_length": 200,
        "max_time_range_seconds": 3600,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_loki_unavailable_when_unconfigured() -> None:
    async with LokiClient(_settings(loki_url=None)) as client:
        assert client.enabled is False
        with pytest.raises(LokiUnavailableError):
            await client.range_query("{app=\"api\"}", start=1, end=2)


@pytest.mark.asyncio
async def test_range_query_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/loki/api/v1/query_range"
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "resultType": "streams",
                    "result": [
                        {
                            "stream": {"service": "payment-api"},
                            "values": [["1710000000000000000", "error boom"]],
                        }
                    ],
                },
            },
        )

    async with LokiClient(
        _settings(), transport=httpx.MockTransport(handler)
    ) as client:
        result = await client.range_query(
            '{service="payment-api"} |= "error"',
            start=1,
            end=100,
            limit=10,
        )

    assert result.result_type == "streams"
    assert result.result[0].stream["service"] == "payment-api"
    assert result.result[0].values[0][1] == "error boom"


@pytest.mark.asyncio
async def test_instant_query_and_labels() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/loki/api/v1/query":
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {"resultType": "streams", "result": []},
                },
            )
        if request.url.path == "/loki/api/v1/labels":
            return httpx.Response(200, json={"status": "success", "data": ["service"]})
        if request.url.path == "/loki/api/v1/label/service/values":
            return httpx.Response(
                200,
                json={"status": "success", "data": ["payment-api"]},
            )
        return httpx.Response(404)

    async with LokiClient(
        _settings(), transport=httpx.MockTransport(handler)
    ) as client:
        instant = await client.instant_query('{app="api"}')
        labels = await client.label_names()
        values = await client.label_values("service")

    assert instant.result_type == "streams"
    assert labels == ["service"]
    assert values == ["payment-api"]


@pytest.mark.asyncio
async def test_loki_query_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "error", "error": "parse error"},
        )

    async with LokiClient(
        _settings(), transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(LokiQueryError, match="parse error"):
            await client.instant_query("{bad")
