"""Shared helpers for read-only HTTP monitoring clients."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from app.logging import get_logger

logger = get_logger(__name__)


def enforce_response_size(response: httpx.Response, *, max_bytes: int, error_factory: Callable[[str], Exception]) -> None:
    """Raise when the response body exceeds the configured byte limit."""
    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        try:
            if int(content_length) > max_bytes:
                raise error_factory(
                    f"Response Content-Length {content_length} exceeds limit {max_bytes}"
                )
        except ValueError:
            pass

    body = response.content
    if len(body) > max_bytes:
        raise error_factory(f"Response body size {len(body)} exceeds limit {max_bytes}")


async def request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | list[tuple[str, str]] | None = None,
    retries: int = 1,
    timeout_error: Callable[[str], Exception],
    transport_error: Callable[[str], Exception],
    retry_event: str,
) -> httpx.Response:
    """Perform an idempotent GET-style request with limited retries."""
    attempt = 0
    while True:
        try:
            response = await client.request(method, path, params=params)  # type: ignore[arg-type]
        except httpx.TimeoutException as exc:
            raise timeout_error(f"Request timed out: {method} {path}") from exc
        except httpx.HTTPError as exc:
            raise transport_error(f"Request failed: {method} {path}: {exc}") from exc

        if response.status_code in {408, 429, 500, 502, 503, 504} and attempt < retries:
            attempt += 1
            logger.warning(
                retry_event,
                method=method,
                path=path,
                status_code=response.status_code,
                attempt=attempt,
            )
            continue
        return response
