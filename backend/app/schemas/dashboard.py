"""Normalized dashboard schemas and API response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NormalizedQuery(BaseModel):
    ref_id: str | None = None
    datasource_uid: str | None = None
    datasource_type: str | None = None
    query_language: str | None = None
    raw_query: str
    expr: str | None = None


class NormalizedPanel(BaseModel):
    grafana_panel_id: int
    title: str
    panel_type: str
    datasource_uid: str | None = None
    queries: list[NormalizedQuery] = Field(default_factory=list)
    transformations: list[dict[str, Any]] = Field(default_factory=list)
    field_config: dict[str, Any] = Field(default_factory=dict)
    raw_definition: dict[str, Any] = Field(default_factory=dict)


class NormalizedVariable(BaseModel):
    name: str
    label: str | None = None
    variable_type: str
    query: str | None = None
    current_value: Any = None
    multi: bool = False
    include_all: bool = False
    raw_definition: dict[str, Any] = Field(default_factory=dict)


class NormalizedDashboard(BaseModel):
    grafana_uid: str
    title: str
    folder: str | None = None
    url: str | None = None
    json_hash: str
    raw_json: dict[str, Any]
    panels: list[NormalizedPanel] = Field(default_factory=list)
    variables: list[NormalizedVariable] = Field(default_factory=list)
    links: list[dict[str, Any]] = Field(default_factory=list)


class PanelResponse(BaseModel):
    id: int
    grafana_panel_id: int
    title: str
    panel_type: str
    datasource_uid: str | None = None


class VariableResponse(BaseModel):
    id: int
    name: str
    label: str | None = None
    variable_type: str
    query: str | None = None
    multi: bool
    include_all: bool


class DashboardSummaryResponse(BaseModel):
    id: int
    grafana_uid: str
    title: str
    folder: str | None = None
    url: str | None = None
    json_hash: str
    updated_at: datetime
    panel_count: int = 0
    variable_count: int = 0


class DashboardDetailResponse(DashboardSummaryResponse):
    panels: list[PanelResponse] = Field(default_factory=list)
    variables: list[VariableResponse] = Field(default_factory=list)


class DashboardSyncResponse(BaseModel):
    dashboard: DashboardDetailResponse
    created: bool
    request_id: str
