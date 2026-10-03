"""Filter intelligence schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CardinalityClass = Literal["safe", "review", "avoid"]
AllValueBehavior = Literal["regex_all", "omit_selector", "literal_all", "unknown", "not_applicable"]


class LabelCandidate(BaseModel):
    label: str
    source: Literal["query", "variable", "metadata", "heuristic"]
    estimated_cardinality: int | None = None
    cardinality_class: CardinalityClass
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class PanelFilterUsage(BaseModel):
    panel_id: int
    panel_title: str
    uses_variable: bool
    query_refs: list[str] = Field(default_factory=list)


class FilterContract(BaseModel):
    variable_name: str
    label: str | None = None
    source: str
    variable_type: str
    multi: bool
    include_all: bool
    current_value: Any = None
    cardinality_class: CardinalityClass = "review"
    estimated_cardinality: int | None = None
    affected_panels: list[int] = Field(default_factory=list)
    unaffected_panels: list[int] = Field(default_factory=list)
    query_syntax_ok: bool = True
    all_value_behavior: AllValueBehavior = "unknown"
    panel_usage: list[PanelFilterUsage] = Field(default_factory=list)


class FilterIntelligenceReport(BaseModel):
    candidates: list[LabelCandidate] = Field(default_factory=list)
    contracts: list[FilterContract] = Field(default_factory=list)
    dead_variables: list[str] = Field(default_factory=list)
    partially_propagated: list[str] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
