"""Read-only Prometheus HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

from app.clients._http import enforce_response_size, request_with_retries
from app.clients.errors import (
    PrometheusClientError,
    PrometheusQueryError,
    PrometheusResponseTooLargeError,
    PrometheusTimeoutError,
)
from app.config import Settings, get_settings
from app.schemas.query import (
    MetricMetadata,
    PrometheusQueryResult,
    PrometheusSample,
    SeriesSelector,
)


class PrometheusClient:
    """Typed Prometheus client with timeouts, size limits, and error mapping."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = httpx.AsyncClient(
            base_url=self._settings.prometheus_url.rstrip("/"),
            headers={"Accept": "application/json"},
            timeout=httpx.Timeout(self._settings.prometheus_timeout_seconds),
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> PrometheusClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def instant_query(
        self,
        query: str,
        *,
        time: str | float | None = None,
    ) -> PrometheusQueryResult:
        self._validate_query(query)
        params: dict[str, Any] = {"query": query}
        if time is not None:
            params["time"] = time
        payload = await self._request_json("GET", "/api/v1/query", params=params)
        return self._parse_query_result(payload)

    async def range_query(
        self,
        query: str,
        *,
        start: str | float,
        end: str | float,
        step: str | float = "60s",
    ) -> PrometheusQueryResult:
        self._validate_query(query)
        self._validate_time_range(start, end)
        params: dict[str, Any] = {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        }
        payload = await self._request_json("GET", "/api/v1/query_range", params=params)
        return self._parse_query_result(payload)

    async def metadata(self, metric: str | None = None) -> list[MetricMetadata]:
        params: dict[str, Any] = {}
        if metric:
            params["metric"] = metric
        payload = await self._request_json("GET", "/api/v1/metadata", params=params)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise PrometheusClientError(
                "Prometheus metadata response missing data object",
                status_code=502,
            )
        results: list[MetricMetadata] = []
        for metric_name, entries in data.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                results.append(
                    MetricMetadata(
                        metric=str(metric_name),
                        type=str(entry["type"]) if entry.get("type") is not None else None,
                        help=str(entry["help"]) if entry.get("help") is not None else None,
                        unit=str(entry["unit"]) if entry.get("unit") is not None else None,
                    )
                )
        return results

    async def label_names(self) -> list[str]:
        payload = await self._request_json("GET", "/api/v1/labels")
        data = payload.get("data")
        if not isinstance(data, list):
            raise PrometheusClientError(
                "Prometheus labels response missing data list",
                status_code=502,
            )
        return [str(item) for item in data]

    async def label_values(self, label: str) -> list[str]:
        if not label:
            raise PrometheusClientError("Label name is required", status_code=400)
        payload = await self._request_json("GET", f"/api/v1/label/{label}/values")
        data = payload.get("data")
        if not isinstance(data, list):
            raise PrometheusClientError(
                "Prometheus label values response missing data list",
                status_code=502,
            )
        return [str(item) for item in data]

    async def series(self, matchers: list[str]) -> list[SeriesSelector]:
        if not matchers:
            raise PrometheusClientError("At least one series matcher is required", status_code=400)
        params: list[tuple[str, str]] = [("match[]", matcher) for matcher in matchers]
        response = await request_with_retries(
            self._client,
            "GET",
            "/api/v1/series",
            params=params,
            timeout_error=lambda msg: PrometheusTimeoutError(msg),
            transport_error=lambda msg: PrometheusClientError(msg),
            retry_event="prometheus_retry",
        )
        payload = self._map_response(response, method="GET", path="/api/v1/series")
        data = payload.get("data")
        if not isinstance(data, list):
            raise PrometheusClientError(
                "Prometheus series response missing data list",
                status_code=502,
            )
        series: list[SeriesSelector] = []
        for item in data:
            if isinstance(item, dict):
                series.append(
                    SeriesSelector(labels={str(k): str(v) for k, v in item.items()})
                )
        return series

    def _validate_query(self, query: str) -> None:
        if not query or not query.strip():
            raise PrometheusClientError("Query must not be empty", status_code=400)
        if len(query) > self._settings.max_query_length:
            raise PrometheusClientError(
                f"Query length {len(query)} exceeds limit {self._settings.max_query_length}",
                status_code=400,
            )

    def _validate_time_range(self, start: str | float, end: str | float) -> None:
        try:
            start_f = float(start)
            end_f = float(end)
        except (TypeError, ValueError):
            return
        if end_f < start_f:
            raise PrometheusClientError("Range end must be >= start", status_code=400)
        if (end_f - start_f) > self._settings.max_time_range_seconds:
            raise PrometheusClientError(
                "Requested time range exceeds configured maximum",
                status_code=400,
            )

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await request_with_retries(
            self._client,
            method,
            path,
            params=params,
            timeout_error=lambda msg: PrometheusTimeoutError(msg),
            transport_error=lambda msg: PrometheusClientError(msg),
            retry_event="prometheus_retry",
        )
        return self._map_response(response, method=method, path=path)

    def _map_response(
        self,
        response: httpx.Response,
        *,
        method: str,
        path: str,
    ) -> dict[str, Any]:
        enforce_response_size(
            response,
            max_bytes=self._settings.prometheus_max_response_bytes,
            error_factory=lambda msg: PrometheusResponseTooLargeError(msg, status_code=502),
        )
        if response.status_code >= 400:
            raise PrometheusClientError(
                f"Prometheus error {response.status_code}: {method} {path}",
                status_code=response.status_code,
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise PrometheusClientError(
                f"Prometheus returned non-JSON response: {method} {path}",
                status_code=502,
            ) from exc
        if not isinstance(payload, dict):
            raise PrometheusClientError(
                "Prometheus response was not an object",
                status_code=502,
            )
        if payload.get("status") == "error":
            raise PrometheusQueryError(
                str(payload.get("error") or "Prometheus query failed"),
                status_code=422,
            )
        return payload

    def _parse_query_result(self, payload: dict[str, Any]) -> PrometheusQueryResult:
        data = payload.get("data")
        if not isinstance(data, dict):
            raise PrometheusClientError(
                "Prometheus query response missing data object",
                status_code=502,
            )
        result_type = str(data.get("resultType") or "vector")
        raw_result = data.get("result")
        samples: list[PrometheusSample] = []

        if result_type == "scalar" and isinstance(raw_result, list) and len(raw_result) == 2:
            samples.append(
                PrometheusSample(value=(float(raw_result[0]), str(raw_result[1])))
            )
        elif isinstance(raw_result, list):
            for item in raw_result:
                if not isinstance(item, dict):
                    continue
                metric_obj = item.get("metric")
                metric = (
                    {str(k): str(v) for k, v in metric_obj.items()}
                    if isinstance(metric_obj, dict)
                    else {}
                )
                value = item.get("value")
                values = item.get("values") or []
                parsed_value: tuple[float, str] | None = None
                if isinstance(value, list) and len(value) == 2:
                    parsed_value = (float(value[0]), str(value[1]))
                parsed_values: list[tuple[float, str]] = []
                if isinstance(values, list):
                    for point in values:
                        if isinstance(point, list) and len(point) == 2:
                            parsed_values.append((float(point[0]), str(point[1])))
                samples.append(
                    PrometheusSample(
                        metric=metric,
                        value=parsed_value,
                        values=parsed_values,
                    )
                )

        if result_type not in {"vector", "matrix", "scalar", "string"}:
            result_type = "vector"

        return PrometheusQueryResult(
            result_type=result_type,  # type: ignore[arg-type]
            result=samples,
            raw=payload,
        )
