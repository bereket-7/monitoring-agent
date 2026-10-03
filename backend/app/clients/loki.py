"""Read-only Loki HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

from app.clients._http import enforce_response_size, request_with_retries
from app.clients.errors import (
    LokiClientError,
    LokiQueryError,
    LokiResponseTooLargeError,
    LokiTimeoutError,
    LokiUnavailableError,
)
from app.config import Settings, get_settings
from app.schemas.query import LokiQueryResult, LokiStream


class LokiClient:
    """Typed Loki client with timeouts, size limits, and graceful unavailability."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._enabled = bool(self._settings.loki_url)
        base_url = (self._settings.loki_url or "http://localhost").rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Accept": "application/json"},
            timeout=httpx.Timeout(self._settings.loki_timeout_seconds),
            transport=transport,
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> LokiClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def instant_query(
        self,
        query: str,
        *,
        time: str | float | None = None,
        limit: int | None = None,
    ) -> LokiQueryResult:
        self._ensure_enabled()
        self._validate_query(query)
        params: dict[str, Any] = {"query": query}
        if time is not None:
            params["time"] = time
        if limit is not None:
            params["limit"] = limit
        payload = await self._request_json("GET", "/loki/api/v1/query", params=params)
        return self._parse_query_result(payload)

    async def range_query(
        self,
        query: str,
        *,
        start: str | float,
        end: str | float,
        limit: int | None = 1000,
        step: str | float | None = None,
    ) -> LokiQueryResult:
        self._ensure_enabled()
        self._validate_query(query)
        self._validate_time_range(start, end)
        params: dict[str, Any] = {
            "query": query,
            "start": start,
            "end": end,
        }
        if limit is not None:
            params["limit"] = limit
        if step is not None:
            params["step"] = step
        payload = await self._request_json(
            "GET",
            "/loki/api/v1/query_range",
            params=params,
        )
        return self._parse_query_result(payload)

    async def label_names(
        self,
        *,
        start: str | float | None = None,
        end: str | float | None = None,
    ) -> list[str]:
        self._ensure_enabled()
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        payload = await self._request_json("GET", "/loki/api/v1/labels", params=params)
        data = payload.get("data")
        if not isinstance(data, list):
            raise LokiClientError("Loki labels response missing data list", status_code=502)
        return [str(item) for item in data]

    async def label_values(
        self,
        label: str,
        *,
        start: str | float | None = None,
        end: str | float | None = None,
    ) -> list[str]:
        self._ensure_enabled()
        if not label:
            raise LokiClientError("Label name is required", status_code=400)
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        payload = await self._request_json(
            "GET",
            f"/loki/api/v1/label/{label}/values",
            params=params,
        )
        data = payload.get("data")
        if not isinstance(data, list):
            raise LokiClientError(
                "Loki label values response missing data list",
                status_code=502,
            )
        return [str(item) for item in data]

    def _ensure_enabled(self) -> None:
        if not self._enabled:
            raise LokiUnavailableError(
                "Loki is not configured (LOKI_URL is empty)",
                status_code=503,
            )

    def _validate_query(self, query: str) -> None:
        if not query or not query.strip():
            raise LokiClientError("Query must not be empty", status_code=400)
        if len(query) > self._settings.max_query_length:
            raise LokiClientError(
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
            raise LokiClientError("Range end must be >= start", status_code=400)
        if (end_f - start_f) > self._settings.max_time_range_seconds:
            raise LokiClientError(
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
            timeout_error=lambda msg: LokiTimeoutError(msg),
            transport_error=lambda msg: LokiClientError(msg),
            retry_event="loki_retry",
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
            max_bytes=self._settings.loki_max_response_bytes,
            error_factory=lambda msg: LokiResponseTooLargeError(msg, status_code=502),
        )
        if response.status_code >= 400:
            raise LokiClientError(
                f"Loki error {response.status_code}: {method} {path}",
                status_code=response.status_code,
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise LokiClientError(
                f"Loki returned non-JSON response: {method} {path}",
                status_code=502,
            ) from exc
        if not isinstance(payload, dict):
            raise LokiClientError("Loki response was not an object", status_code=502)
        if payload.get("status") == "error":
            raise LokiQueryError(
                str(payload.get("error") or "Loki query failed"),
                status_code=422,
            )
        return payload

    def _parse_query_result(self, payload: dict[str, Any]) -> LokiQueryResult:
        data = payload.get("data")
        if not isinstance(data, dict):
            raise LokiClientError(
                "Loki query response missing data object",
                status_code=502,
            )
        result_type = str(data.get("resultType") or "streams")
        raw_result = data.get("result")
        streams: list[LokiStream] = []
        if isinstance(raw_result, list):
            for item in raw_result:
                if not isinstance(item, dict):
                    continue
                stream_obj = item.get("stream")
                stream_labels: dict[str, Any] = (
                    stream_obj if isinstance(stream_obj, dict) else {}
                )
                values_raw = item.get("values") or []
                values: list[tuple[str, str]] = []
                if isinstance(values_raw, list):
                    for point in values_raw:
                        if isinstance(point, list) and len(point) == 2:
                            values.append((str(point[0]), str(point[1])))
                streams.append(
                    LokiStream(
                        stream={str(k): str(v) for k, v in stream_labels.items()},
                        values=values,
                    )
                )
        return LokiQueryResult(result_type=result_type, result=streams, raw=payload)
