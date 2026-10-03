"""API key authentication for production hardening."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from app.config import Settings, get_settings

PUBLIC_PATH_PREFIXES = ("/health", "/ready", "/metrics", "/docs", "/openapi.json", "/redoc")


def parse_api_keys(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}


def auth_required(settings: Settings) -> bool:
    if settings.api_auth_enabled is not None:
        return settings.api_auth_enabled
    return settings.app_env == "production"


def extract_api_key(
    authorization: str | None,
    x_api_key: str | None,
) -> str | None:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        return token or None
    return None


def verify_api_key(provided: str | None, configured: set[str]) -> bool:
    if not provided or not configured:
        return False
    for candidate in configured:
        if hmac.compare_digest(provided, candidate):
            return True
    return False


def is_public_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in PUBLIC_PATH_PREFIXES)


def identity_from_key(provided: str) -> str:
    if len(provided) >= 8:
        return f"api-key:{provided[:4]}...{provided[-4:]}"
    return "api-key"


async def require_api_key(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str | None:
    """FastAPI dependency: enforce API key when auth is enabled."""
    settings = get_settings()
    if not auth_required(settings):
        identity = extract_api_key(authorization, x_api_key)
        request.state.user_identity = identity_from_key(identity) if identity else "anonymous"
        return identity

    keys = parse_api_keys(settings.api_keys)
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is enabled but API_KEYS is not configured",
        )

    provided = extract_api_key(authorization, x_api_key)
    if not verify_api_key(provided, keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    assert provided is not None
    identity = identity_from_key(provided)
    request.state.user_identity = identity
    return identity
