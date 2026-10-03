"""Dashboard analysis routes (deterministic, no LLM)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.dashboard import normalize_grafana_dashboard
from app.api.deps import get_db
from app.repositories.dashboard import DashboardRepository
from app.schemas.analysis import DashboardAnalysisReport
from app.services.dashboard_analysis import analyze_normalized_dashboard

router = APIRouter(prefix="/analysis", tags=["analysis"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/dashboards/{uid}", response_model=DashboardAnalysisReport)
async def analyze_dashboard(uid: str, session: DbSession) -> DashboardAnalysisReport:
    """Generate a deterministic analysis report for a synced dashboard."""
    repo = DashboardRepository(session)
    dashboard = await repo.get_by_uid(uid)
    if dashboard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard '{uid}' not found locally. Sync it first.",
        )

    normalized = normalize_grafana_dashboard(
        {
            "dashboard": dashboard.raw_json,
            "meta": {
                "uid": dashboard.grafana_uid,
                "url": dashboard.url,
                "folderTitle": dashboard.folder,
            },
        }
    )
    return analyze_normalized_dashboard(normalized)
