"""Typed errors for external monitoring clients."""

from __future__ import annotations


class ExternalClientError(Exception):
    """Base error for outbound monitoring API calls."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GrafanaClientError(ExternalClientError):
    """Grafana request failed."""


class GrafanaNotFoundError(GrafanaClientError):
    """Requested Grafana resource was not found."""


class GrafanaAuthError(GrafanaClientError):
    """Grafana rejected credentials."""


class GrafanaTimeoutError(GrafanaClientError):
    """Grafana request timed out."""


class PrometheusClientError(ExternalClientError):
    """Prometheus request failed."""


class PrometheusQueryError(PrometheusClientError):
    """Prometheus returned a query execution error."""


class PrometheusTimeoutError(PrometheusClientError):
    """Prometheus request timed out."""


class PrometheusResponseTooLargeError(PrometheusClientError):
    """Prometheus response exceeded configured size limit."""


class LokiClientError(ExternalClientError):
    """Loki request failed."""


class LokiQueryError(LokiClientError):
    """Loki returned a query execution error."""


class LokiTimeoutError(LokiClientError):
    """Loki request timed out."""


class LokiResponseTooLargeError(LokiClientError):
    """Loki response exceeded configured size limit."""


class LokiUnavailableError(LokiClientError):
    """Loki is not configured; degrade gracefully."""
