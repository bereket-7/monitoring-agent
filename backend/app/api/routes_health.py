"""Health and readiness routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field

from app.db import check_database_connection
from app.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    request_id: str


class ReadyResponse(BaseModel):
    status: str
    database: str
    request_id: str


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Liveness probe that does not touch external dependencies."""
    return HealthResponse(status="ok", request_id=_request_id(request))


@router.get("/ready", response_model=ReadyResponse)
async def ready(request: Request, response: Response) -> ReadyResponse:
    """Readiness probe that verifies PostgreSQL connectivity."""
    request_id = _request_id(request)
    try:
        await check_database_connection()
    except Exception as exc:
        logger.warning("readiness_check_failed", error=str(exc))
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(
            status="unavailable",
            database="error",
            request_id=request_id,
        )

    return ReadyResponse(status="ok", database="ok", request_id=request_id)
