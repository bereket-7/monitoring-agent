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
