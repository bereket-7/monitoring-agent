"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.middleware import RequestIdMiddleware, SecurityMiddleware
from app.api.routes_agent import router as agent_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_dashboards import router as dashboards_router
from app.api.routes_health import router as health_router
from app.config import get_settings
from app.db import dispose_engine, get_engine
from app.logging import configure_logging, get_logger
from app.observability.metrics import metrics_response
from app.observability.tracing import setup_tracing, shutdown_tracing
from app.security.auth import auth_required, parse_api_keys, require_api_key


def _parse_cors_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _validate_production_settings() -> None:
    settings = get_settings()
    if settings.app_env != "production":
        return
    if auth_required(settings) and not parse_api_keys(settings.api_keys):
        raise RuntimeError(
            "Production requires API_KEYS when API authentication is enabled"
        )
    if settings.require_readonly_credentials:
        # Operational posture: tokens must be provisioned as read-only externally.
        get_logger(__name__).info(
            "readonly_credentials_required",
            grafana="dashboard/datasource read-only token required",
            prometheus="query API only",
            loki="query API only",
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down process-wide resources."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)
    _validate_production_settings()
    get_engine(settings)
    setup_tracing(settings)

    redis_client: Redis[str] | None = None
    try:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("redis_connected")
    except Exception as exc:
        app.state.redis = None
        if redis_client is not None:
            await redis_client.close()
        logger.warning("redis_unavailable", error=str(exc))

    logger.info("application_startup", app_env=settings.app_env, app=settings.app_name)
    try:
        yield
    finally:
        redis = getattr(app.state, "redis", None)
        if isinstance(redis, Redis):
            await redis.close()
        shutdown_tracing()
        await dispose_engine()
        logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_parse_cors_origins(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # SecurityMiddleware is added without redis initially; it reads get_settings()
    # and uses in-memory limiter until redis is attached via app.state in lifespan.
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health_router)
    protected = [Depends(require_api_key)]
    app.include_router(dashboards_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(analysis_router, prefix=settings.api_prefix, dependencies=protected)
    app.include_router(agent_router, prefix=settings.api_prefix, dependencies=protected)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> object:
        return metrics_response()

    app.state.settings = settings
    app.state.redis = None
    return app


app = create_app()
