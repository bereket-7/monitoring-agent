"""Deterministic dashboard/query analysis report schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.filters import FilterIntelligenceReport

FindingSeverity = Literal["info", "warning", "error", "critical"]


class AnalyzedQuery(BaseModel):
    panel_id: int
    panel_title: str
    ref_id: str | None = None
    datasource_uid: str | None = None
    query_language: str | None = None
    raw_query: str
    normalized_query: str
    query_hash: str
    referenced_metrics: list[str] = Field(default_factory=list)
    referenced_labels: list[str] = Field(default_factory=list)
    referenced_variables: list[str] = Field(default_factory=list)
    functions: list[str] = Field(default_factory=list)
    range_vectors: list[str] = Field(default_factory=list)
    has_regex_selector: bool = False


class VariableUsage(BaseModel):
    variable: str
    panel_id: int
    panel_title: str
    query_ref: str | None = None
    query_hash: str


class DuplicateQueryGroup(BaseModel):
    query_hash: str
    normalized_query: str
    occurrences: list[dict[str, Any]] = Field(default_factory=list)


class StaticAnalysisFinding(BaseModel):
    rule_id: str
    severity: FindingSeverity
    category: str
    title: str
    description: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    recommendation: str


class DashboardAnalysisReport(BaseModel):
    dashboard_uid: str
    title: str
    panel_count: int
    variable_count: int
    query_inventory: list[AnalyzedQuery] = Field(default_factory=list)
    variable_graph: list[VariableUsage] = Field(default_factory=list)
    unused_variables: list[str] = Field(default_factory=list)
    duplicate_queries: list[DuplicateQueryGroup] = Field(default_factory=list)
    filter_intelligence: FilterIntelligenceReport | None = None
    findings: list[StaticAnalysisFinding] = Field(default_factory=list)
