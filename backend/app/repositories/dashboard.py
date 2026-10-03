"""Dashboard persistence repository."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dashboard import Dashboard, DashboardPanel, DashboardVariable
from app.schemas.dashboard import NormalizedDashboard


class DashboardRepository:
    """Store and load synced Grafana dashboards."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_dashboards(self) -> list[Dashboard]:
        result = await self._session.execute(
            select(Dashboard)
            .options(
                selectinload(Dashboard.panels),
                selectinload(Dashboard.variables),
            )
            .order_by(Dashboard.title)
        )
        return list(result.scalars().all())

    async def get_by_uid(self, uid: str) -> Dashboard | None:
        result = await self._session.execute(
            select(Dashboard)
            .where(Dashboard.grafana_uid == uid)
            .options(
                selectinload(Dashboard.panels),
                selectinload(Dashboard.variables),
            )
        )
        return result.scalar_one_or_none()

    async def upsert_normalized(
        self,
        normalized: NormalizedDashboard,
    ) -> tuple[Dashboard, bool]:
        existing = await self.get_by_uid(normalized.grafana_uid)
        created = existing is None

        if existing is None:
            dashboard = Dashboard(
                grafana_uid=normalized.grafana_uid,
                title=normalized.title,
                folder=normalized.folder,
                url=normalized.url,
                json_hash=normalized.json_hash,
                raw_json=normalized.raw_json,
            )
            self._session.add(dashboard)
            await self._session.flush()
        else:
            dashboard = existing
            dashboard.title = normalized.title
            dashboard.folder = normalized.folder
            dashboard.url = normalized.url
            dashboard.json_hash = normalized.json_hash
            dashboard.raw_json = normalized.raw_json
            await self._session.execute(
                delete(DashboardPanel).where(DashboardPanel.dashboard_id == dashboard.id)
            )
            await self._session.execute(
                delete(DashboardVariable).where(
                    DashboardVariable.dashboard_id == dashboard.id
                )
            )
            await self._session.flush()

        for panel in normalized.panels:
            self._session.add(
                DashboardPanel(
                    dashboard_id=dashboard.id,
                    grafana_panel_id=panel.grafana_panel_id,
                    title=panel.title,
                    panel_type=panel.panel_type,
                    datasource_uid=panel.datasource_uid,
                    raw_definition=panel.raw_definition,
                )
            )

        for variable in normalized.variables:
            self._session.add(
                DashboardVariable(
                    dashboard_id=dashboard.id,
                    name=variable.name,
                    label=variable.label,
                    variable_type=variable.variable_type,
                    query=variable.query,
                    current_value=variable.current_value,
                    multi=variable.multi,
                    include_all=variable.include_all,
                    raw_definition=variable.raw_definition,
                )
            )

        await self._session.commit()
        reloaded = await self.get_by_uid(normalized.grafana_uid)
        if reloaded is None:
            raise RuntimeError("Dashboard disappeared after upsert")
        return reloaded, created
