"""Mutable agent investigation state."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.agent import (
    AgentFinding,
    Confidence,
    EvidenceItem,
    QueryEvidence,
    ToolCallRecord,
)


class AgentState(BaseModel):
    """Tracks one agent investigation turn."""

    user_message: str
    dashboard_uid: str | None = None
    time_range: dict[str, Any] = Field(default_factory=dict)
    filters: dict[str, str] = Field(default_factory=dict)
    findings: list[AgentFinding] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    queries: list[QueryEvidence] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    remaining_budget: int = 20
    final_answer: str | None = None
    limitations: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: Confidence = "low"
    messages: list[dict[str, Any]] = Field(default_factory=list)
    stopped_reason: str | None = None

    def consume_budget(self) -> bool:
        """Decrement tool budget. Returns False when exhausted."""
        if self.remaining_budget <= 0:
            return False
        self.remaining_budget -= 1
        return True

    def has_successful_query(self) -> bool:
        return any(item.status == "success" for item in self.tool_calls if item.name.startswith("query_"))

    def has_validation_evidence(self) -> bool:
        return any(
            item.status == "success" and item.name in {"validate_metric", "analyze_query", "get_previous_analysis"}
            for item in self.tool_calls
        )

    def has_dashboard_context(self) -> bool:
        return any(
            item.status == "success" and item.name in {"get_dashboard", "get_panel", "list_dashboard_variables"}
            for item in self.tool_calls
        )
