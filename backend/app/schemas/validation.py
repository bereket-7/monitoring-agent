"""Validation engine schemas (findings, context, observations)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "warning", "error", "critical"]
MetricRole = Literal["success", "error", "total", "latency", "rate", "other"]
MetricType = Literal["counter", "gauge", "histogram", "summary", "unknown"]


class TimeRange(BaseModel):
    start: str | float | None = None
    end: str | float | None = None
    window: str | None = None


class MetricSemantics(BaseModel):
    """Configurable semantics; unknown fields must remain None."""

    success_definition: str | None = None
    error_definition: str | None = None
    total_definition: str | None = None


class MetricObservation(BaseModel):
    name: str
    role: MetricRole
    value: float | None = None
    query: str
    time_range: TimeRange | None = None
    filters: dict[str, str] = Field(default_factory=dict)
    metric_type: MetricType = "unknown"
    unit: str | None = None


class ValidationContext(BaseModel):
    dashboard_uid: str | None = None
    panel_id: int | None = None
    observations: list[MetricObservation] = Field(default_factory=list)
    semantics: MetricSemantics = Field(default_factory=MetricSemantics)
    consistency_tolerance: float = Field(default=0.02, ge=0.0)
    reported_success_rate: float | None = None
    reported_error_rate: float | None = None


class ValidationFinding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    description: str
    observed_value: Any = None
    expected_value: Any = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    recommendation: str
    category: str
