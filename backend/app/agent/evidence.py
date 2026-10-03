"""Evidence collection from successful tool results only."""

from __future__ import annotations

from typing import Any

from app.agent.state import AgentState
from app.schemas.agent import EvidenceItem, QueryEvidence, ToolCallRecord


def record_tool_result(
    state: AgentState,
    *,
    name: str,
    arguments: dict[str, Any],
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> ToolCallRecord:
    """Append a tool call record and extract grounded evidence on success."""
    record = ToolCallRecord(
        name=name,
        arguments=arguments,
        status=status,  # type: ignore[arg-type]
        result=result,
        error=error,
    )
    state.tool_calls.append(record)

    if status != "success" or result is None:
        if error:
            state.limitations.append(f"Tool {name} failed: {error}")
        return record

    summary = str(result.get("summary") or f"{name} succeeded")
    state.evidence.append(
        EvidenceItem(
            source="tool",
            tool_name=name,
            summary=summary,
            data={"arguments": arguments, "result_keys": sorted(result.keys())},
            observed=True,
        )
    )

    if name in {"query_prometheus", "query_loki"}:
        query = str(arguments.get("query") or "")
        datasource = "prometheus" if name == "query_prometheus" else "loki"
        state.queries.append(
            QueryEvidence(
                tool_name=name,
                query=query,
                datasource=datasource,
                result_summary=summary,
                raw={"result_type": result.get("result_type")},
            )
        )

    if name == "validate_metric":
        for finding in result.get("findings") or []:
            if isinstance(finding, dict):
                from app.schemas.agent import AgentFinding

                state.findings.append(
                    AgentFinding(
                        rule_id=str(finding.get("rule_id")) if finding.get("rule_id") else None,
                        severity=str(finding.get("severity", "info")),
                        title=str(finding.get("title", "Validation finding")),
                        description=str(finding.get("description", "")),
                        evidence=list(finding.get("evidence") or []),
                        recommendation=(
                            str(finding["recommendation"])
                            if finding.get("recommendation") is not None
                            else None
                        ),
                    )
                )

    if name == "get_previous_analysis":
        for finding in result.get("findings") or []:
            if isinstance(finding, dict):
                from app.schemas.agent import AgentFinding

                state.findings.append(
                    AgentFinding(
                        rule_id=str(finding.get("rule_id")) if finding.get("rule_id") else None,
                        severity=str(finding.get("severity", "info")),
                        title=str(finding.get("title", "Analysis finding")),
                        description=str(finding.get("description", "")),
                        evidence=list(finding.get("evidence") or []),
                        recommendation=(
                            str(finding["recommendation"])
                            if finding.get("recommendation") is not None
                            else None
                        ),
                    )
                )

    return record
