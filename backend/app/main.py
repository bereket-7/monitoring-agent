"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middleware import RequestIdMiddleware
from app.api.routes_agent import router as agent_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_dashboards import router as dashboards_router
from app.api.routes_health import router as health_router
from app.config import get_settings
from app.db import dispose_engine, get_engine
from app.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down process-wide resources."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)
    get_engine(settings)
    logger.info("application_startup", app_env=settings.app_env, app=settings.app_name)
    try:
        yield
    finally:
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
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health_router)
    app.include_router(dashboards_router, prefix=settings.api_prefix)
    app.include_router(analysis_router, prefix=settings.api_prefix)
    app.include_router(agent_router, prefix=settings.api_prefix)

    app.state.settings = settings
    return app


app = create_app()
