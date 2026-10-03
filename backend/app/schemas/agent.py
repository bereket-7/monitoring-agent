"""Agent chat request/response and evidence schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]
ToolStatus = Literal["success", "error", "denied"]


class AgentTimeRange(BaseModel):
    from_: str | float | None = Field(default=None, alias="from")
    to: str | float | None = None

    model_config = {"populate_by_name": True}


class AgentContext(BaseModel):
    time_range: AgentTimeRange | None = None
    filters: dict[str, str] = Field(default_factory=dict)


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    dashboard_uid: str | None = None
    context: AgentContext = Field(default_factory=AgentContext)


class EvidenceItem(BaseModel):
    source: str
    tool_name: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    observed: bool = True


class ToolCallRecord(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: ToolStatus
    result: dict[str, Any] | None = None
    error: str | None = None


class AgentFinding(BaseModel):
    rule_id: str | None = None
    severity: str = "info"
    title: str
    description: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    recommendation: str | None = None


class QueryEvidence(BaseModel):
    tool_name: str
    query: str
    datasource: str
    result_summary: str
    raw: dict[str, Any] = Field(default_factory=dict)


class AgentChatResponse(BaseModel):
    answer: str
    findings: list[AgentFinding] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    queries: list[QueryEvidence] = Field(default_factory=list)
    confidence: Confidence
    limitations: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)
