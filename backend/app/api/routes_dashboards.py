"""Dashboard sync and read routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_grafana_client
from app.clients.errors import (
    GrafanaAuthError,
    GrafanaClientError,
    GrafanaNotFoundError,
    GrafanaTimeoutError,
)
from app.clients.grafana import GrafanaClient
from app.models.dashboard import Dashboard
from app.repositories.dashboard import DashboardRepository
from app.schemas.dashboard import (
    DashboardDetailResponse,
    DashboardSummaryResponse,
    DashboardSyncResponse,
    PanelResponse,
    VariableResponse,
)
from app.services.dashboard_sync import DashboardSyncService

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
Grafana = Annotated[GrafanaClient, Depends(get_grafana_client)]


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def _to_summary(dashboard: Dashboard) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(
        id=dashboard.id,
        grafana_uid=dashboard.grafana_uid,
        title=dashboard.title,
        folder=dashboard.folder,
        url=dashboard.url,
        json_hash=dashboard.json_hash,
        updated_at=dashboard.updated_at,
        panel_count=len(dashboard.panels),
        variable_count=len(dashboard.variables),
    )


def _to_detail(dashboard: Dashboard) -> DashboardDetailResponse:
    summary = _to_summary(dashboard)
    return DashboardDetailResponse(
        **summary.model_dump(),
        panels=[
            PanelResponse(
                id=panel.id,
                grafana_panel_id=panel.grafana_panel_id,
                title=panel.title,
                panel_type=panel.panel_type,
                datasource_uid=panel.datasource_uid,
            )
            for panel in dashboard.panels
        ],
        variables=[
            VariableResponse(
                id=variable.id,
                name=variable.name,
                label=variable.label,
                variable_type=variable.variable_type,
                query=variable.query,
                multi=variable.multi,
                include_all=variable.include_all,
            )
            for variable in dashboard.variables
        ],
    )


@router.get("", response_model=list[DashboardSummaryResponse])
async def list_dashboards(session: DbSession) -> list[DashboardSummaryResponse]:
    repo = DashboardRepository(session)
    dashboards = await repo.list_dashboards()
    return [_to_summary(item) for item in dashboards]


@router.get("/{uid}", response_model=DashboardDetailResponse)
async def get_dashboard(uid: str, session: DbSession) -> DashboardDetailResponse:
    repo = DashboardRepository(session)
    dashboard = await repo.get_by_uid(uid)
    if dashboard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard '{uid}' not found locally. Sync it first.",
        )
    return _to_detail(dashboard)


@router.post("/{uid}/sync", response_model=DashboardSyncResponse)
async def sync_dashboard(
    uid: str,
    request: Request,
    session: DbSession,
    grafana: Grafana,
) -> DashboardSyncResponse:
    service = DashboardSyncService(session, grafana)
    try:
        dashboard, created = await service.sync_by_uid(uid)
    except GrafanaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GrafanaAuthError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except GrafanaTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except GrafanaClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return DashboardSyncResponse(
        dashboard=_to_detail(dashboard),
        created=created,
        request_id=_request_id(request),
    )
