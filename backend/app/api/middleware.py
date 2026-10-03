"""HTTP middleware for correlation, auth, and rate limiting."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings
from app.observability.metrics import HTTP_REQUESTS
from app.security.auth import (
    auth_required,
    extract_api_key,
    identity_from_key,
    is_public_path,
    parse_api_keys,
    verify_api_key,
)
from app.security.rate_limit import allow_request

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to logs and response headers."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class SecurityMiddleware(BaseHTTPMiddleware):
    """Enforce API auth (when enabled) and per-identity rate limits."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        path = request.url.path
        started = time.monotonic()

        if not is_public_path(path):
            authorization = request.headers.get("authorization")
            x_api_key = request.headers.get("x-api-key")
            provided = extract_api_key(authorization, x_api_key)

            if auth_required(settings):
                keys = parse_api_keys(settings.api_keys)
                if not keys:
                    return JSONResponse(
                        status_code=503,
                        content={
                            "detail": "API authentication is enabled but API_KEYS is not configured"
                        },
                    )
                if not verify_api_key(provided, keys):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid or missing API key"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                assert provided is not None
                identity = identity_from_key(provided)
            else:
                identity = identity_from_key(provided) if provided else "anonymous"

            request.state.user_identity = identity

            client_host = request.client.host if request.client else "unknown"
            rate_key = f"{identity}:{client_host}"
            redis_client = getattr(request.app.state, "redis", None)
            redis = redis_client if isinstance(redis_client, Redis) else None
            allowed = await allow_request(
                key=rate_key,
                settings=settings,
                redis_client=redis,
            )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )
        else:
            request.state.user_identity = "public"

        response = await call_next(request)
        HTTP_REQUESTS.labels(
            method=request.method,
            path=path,
            status=str(response.status_code),
        ).inc()
        response.headers["X-Response-Time-Ms"] = f"{(time.monotonic() - started) * 1000:.1f}"
        return response
