"""Read-only Grafana HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

from app.clients.errors import (
    GrafanaAuthError,
    GrafanaClientError,
    GrafanaNotFoundError,
    GrafanaTimeoutError,
)
from app.config import Settings, get_settings
from app.logging import get_logger

logger = get_logger(__name__)


class GrafanaClient:
    """Typed, read-only Grafana API client with timeouts and error mapping."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        token = self._settings.grafana_api_token
        headers: dict[str, str] = {"Accept": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token.get_secret_value()}"

        self._client = httpx.AsyncClient(
            base_url=self._settings.grafana_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(self._settings.grafana_timeout_seconds),
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> GrafanaClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def get_dashboard_by_uid(self, uid: str) -> dict[str, Any]:
        """Fetch a dashboard payload by UID (`dashboard` + `meta`)."""
        data = await self._request("GET", f"/api/dashboards/uid/{uid}")
        if not isinstance(data, dict) or "dashboard" not in data:
            raise GrafanaClientError(
                "Grafana dashboard response missing 'dashboard' field",
                status_code=502,
            )
        return data

    async def search_dashboards(self, query: str | None = None) -> list[dict[str, Any]]:
        """Search Grafana dashboards (read-only)."""
        params: dict[str, str] = {"type": "dash-db"}
        if query:
            params["query"] = query
        data = await self._request("GET", "/api/search", params=params)
        if not isinstance(data, list):
            raise GrafanaClientError(
                "Grafana search response was not a list",
                status_code=502,
            )
        return [item for item in data if isinstance(item, dict)]

    async def get_datasource_by_uid(self, uid: str) -> dict[str, Any]:
        """Fetch datasource metadata by UID."""
        data = await self._request("GET", f"/api/datasources/uid/{uid}")
        if not isinstance(data, dict):
            raise GrafanaClientError(
                "Grafana datasource response was not an object",
                status_code=502,
            )
        return data

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        retries: int = 1,
    ) -> Any:
        attempt = 0
        while True:
            try:
                response = await self._client.request(method, path, params=params)
            except httpx.TimeoutException as exc:
                raise GrafanaTimeoutError(
                    f"Grafana request timed out: {method} {path}"
                ) from exc
            except httpx.HTTPError as exc:
                raise GrafanaClientError(
                    f"Grafana request failed: {method} {path}: {exc}"
                ) from exc

            if response.status_code in {408, 429, 500, 502, 503, 504} and attempt < retries:
                attempt += 1
                logger.warning(
                    "grafana_retry",
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    attempt=attempt,
                )
                continue

            return self._map_response(response, method=method, path=path)

    def _map_response(
        self,
        response: httpx.Response,
        *,
        method: str,
        path: str,
    ) -> Any:
        if response.status_code == 404:
            raise GrafanaNotFoundError(
                f"Grafana resource not found: {method} {path}",
                status_code=404,
            )
        if response.status_code in {401, 403}:
            raise GrafanaAuthError(
                f"Grafana authentication/authorization failed: {method} {path}",
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise GrafanaClientError(
                f"Grafana error {response.status_code}: {method} {path}",
                status_code=response.status_code,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise GrafanaClientError(
                f"Grafana returned non-JSON response: {method} {path}",
                status_code=502,
            ) from exc
