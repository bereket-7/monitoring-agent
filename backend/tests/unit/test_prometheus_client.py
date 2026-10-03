"""Unit tests for PrometheusClient with mocked HTTP transport."""

from __future__ import annotations

import httpx
import pytest

from app.clients.errors import (
    PrometheusQueryError,
    PrometheusResponseTooLargeError,
    PrometheusTimeoutError,
)
from app.clients.prometheus import PrometheusClient
from app.config import Settings


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "prometheus_url": "http://prometheus.test",
        "prometheus_timeout_seconds": 5.0,
        "prometheus_max_response_bytes": 1024,
        "max_query_length": 100,
        "max_time_range_seconds": 3600,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_instant_query_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/query"
        assert request.url.params["query"] == "up"
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {
                            "metric": {"__name__": "up", "job": "api"},
                            "value": [1710000000, "1"],
                        }
                    ],
                },
            },
        )

    async with PrometheusClient(
        _settings(), transport=httpx.MockTransport(handler)
    ) as client:
        result = await client.instant_query("up")

    assert result.result_type == "vector"
    assert result.result[0].metric["job"] == "api"
    assert result.result[0].value == (1710000000.0, "1")


@pytest.mark.asyncio
async def test_range_query_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/query_range"
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {
                            "metric": {"job": "api"},
                            "values": [[1710000000, "1"], [1710000060, "2"]],
                        }
                    ],
                },
            },
        )

    async with PrometheusClient(
        _settings(), transport=httpx.MockTransport(handler)
    ) as client:
        result = await client.range_query("up", start=1, end=120, step="60s")

    assert result.result_type == "matrix"
    assert len(result.result[0].values) == 2


@pytest.mark.asyncio
async def test_query_error_is_typed() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "error",
                "errorType": "bad_data",
                "error": "invalid query",
            },
        )

    async with PrometheusClient(
        _settings(), transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(PrometheusQueryError, match="invalid query"):
            await client.instant_query("broken(")


@pytest.mark.asyncio
async def test_response_too_large() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        body = b"x" * 2048
        return httpx.Response(200, content=body, headers={"Content-Type": "application/json"})

    async with PrometheusClient(
        _settings(prometheus_max_response_bytes=100),
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(PrometheusResponseTooLargeError):
            await client.instant_query("up")


@pytest.mark.asyncio
async def test_timeout_is_typed() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    async with PrometheusClient(
        _settings(), transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(PrometheusTimeoutError):
            await client.label_names()


@pytest.mark.asyncio
async def test_metadata_labels_and_series() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/metadata":
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "http_requests_total": [
                            {"type": "counter", "help": "HTTP requests", "unit": ""}
                        ]
                    },
                },
            )
        if request.url.path == "/api/v1/labels":
            return httpx.Response(200, json={"status": "success", "data": ["job", "instance"]})
        if request.url.path == "/api/v1/label/job/values":
            return httpx.Response(200, json={"status": "success", "data": ["api", "web"]})
        if request.url.path == "/api/v1/series":
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": [{"__name__": "up", "job": "api"}],
                },
            )
        return httpx.Response(404)

    async with PrometheusClient(
        _settings(), transport=httpx.MockTransport(handler)
    ) as client:
        metadata = await client.metadata("http_requests_total")
        labels = await client.label_names()
        values = await client.label_values("job")
        series = await client.series(['up{job="api"}'])

    assert metadata[0].type == "counter"
    assert labels == ["job", "instance"]
    assert values == ["api", "web"]
    assert series[0].labels["job"] == "api"


@pytest.mark.asyncio
async def test_query_length_limit() -> None:
    async with PrometheusClient(
        _settings(max_query_length=5), transport=httpx.MockTransport(lambda r: httpx.Response(200))
    ) as client:
        with pytest.raises(Exception, match="Query length"):
            await client.instant_query("too-long-query")
