"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.grafana import GrafanaClient
from app.config import Settings, get_settings
from app.db import get_session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


def get_app_settings() -> Settings:
    return get_settings()


async def get_grafana_client() -> AsyncIterator[GrafanaClient]:
    client = GrafanaClient(get_settings())
    try:
        yield client
    finally:
        await client.aclose()
