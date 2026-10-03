"""Dashboard synchronization from Grafana into local storage."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.dashboard import normalize_grafana_dashboard
from app.clients.grafana import GrafanaClient
from app.models.dashboard import Dashboard
from app.repositories.dashboard import DashboardRepository


class DashboardSyncService:
    """Fetch a Grafana dashboard, normalize it, and persist it."""

    def __init__(
        self,
        session: AsyncSession,
        grafana: GrafanaClient,
    ) -> None:
        self._repo = DashboardRepository(session)
        self._grafana = grafana

    async def sync_by_uid(self, uid: str) -> tuple[Dashboard, bool]:
        payload = await self._grafana.get_dashboard_by_uid(uid)
        meta_obj = payload.get("meta")
        meta: dict[str, Any] = meta_obj if isinstance(meta_obj, dict) else {}
        folder_title = meta.get("folderTitle")
        folder = str(folder_title) if folder_title else None
        meta_url = meta.get("url")
        url = str(meta_url) if meta_url else None
        normalized = normalize_grafana_dashboard(payload, folder=folder, url=url)
        return await self._repo.upsert_normalized(normalized)
