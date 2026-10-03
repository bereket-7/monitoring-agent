"""Format AgentState into the public chat response."""

from __future__ import annotations

from app.agent.state import AgentState
from app.schemas.agent import AgentChatResponse, Confidence


def compute_confidence(state: AgentState) -> Confidence:
    """Deterministic confidence from evidence coverage, not model intuition."""
    if state.stopped_reason == "budget_exhausted" and not state.evidence:
        return "low"

    has_query = state.has_successful_query()
    has_validation = state.has_validation_evidence()
    has_dashboard = state.has_dashboard_context()
    incomplete = bool(state.limitations)

    if has_query and has_validation and has_dashboard and not incomplete:
        return "high"
    if (has_query or has_validation) and has_dashboard:
        return "medium"
    if has_dashboard or has_query or has_validation:
        return "medium" if not incomplete else "low"
    return "low"


def format_response(state: AgentState) -> AgentChatResponse:
    """Build the structured agent response with required sections."""
    confidence = compute_confidence(state)
    state.confidence = confidence

    answer = state.final_answer or (
        "Evidence is incomplete. I could not finish the investigation with available tools."
    )

    evidence_lines = [item.summary for item in state.evidence] or ["No observed evidence collected."]
    query_lines = [
        f"{item.datasource}: `{item.query}` — {item.result_summary}" for item in state.queries
    ] or ["No queries were executed successfully."]
    finding_lines = [
        f"[{item.severity}] {item.title}: {item.description}" for item in state.findings
    ] or ["No deterministic findings recorded."]
    limitation_lines = state.limitations or ["None stated."]
    recommendation_lines = state.recommendations or [
        item.recommendation
        for item in state.findings
        if item.recommendation
    ] or ["No recommendations supported by evidence."]

    sections = {
        "Answer": answer,
        "Evidence": "\n".join(f"- {line}" for line in evidence_lines),
        "Calculation/query": "\n".join(f"- {line}" for line in query_lines),
        "Findings": "\n".join(f"- {line}" for line in finding_lines),
        "Limitations": "\n".join(f"- {line}" for line in limitation_lines),
        "Recommendation": "\n".join(f"- {line}" for line in recommendation_lines),
    }

    return AgentChatResponse(
        answer=answer,
        findings=state.findings,
        evidence=state.evidence,
        queries=state.queries,
        confidence=confidence,
        limitations=state.limitations,
        recommendations=[
            line for line in recommendation_lines if line != "No recommendations supported by evidence."
        ],
        tool_calls=state.tool_calls,
        sections=sections,
    )
