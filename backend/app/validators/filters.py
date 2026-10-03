"""FILTER-001/002 filter validators."""

from __future__ import annotations

from app.analyzers.filters import analyze_filters
from app.analyzers.query import analyze_query
from app.schemas.analysis import AnalyzedQuery
from app.schemas.dashboard import NormalizedDashboard
from app.schemas.validation import ValidationFinding


class FilterPropagationValidator:
    rule_id = "FILTER-001"

    async def validate_dashboard(
        self,
        dashboard: NormalizedDashboard,
        *,
        query_inventory: list[AnalyzedQuery] | None = None,
        label_cardinality: dict[str, int] | None = None,
    ) -> list[ValidationFinding]:
        report = analyze_filters(
            dashboard,
            query_inventory=query_inventory,
            label_cardinality=label_cardinality,
        )
        findings: list[ValidationFinding] = []
        for item in report.findings:
            if item.get("rule_id") != self.rule_id:
                continue
            findings.append(_to_finding(item))
        return findings


class DeadVariableValidator:
    rule_id = "FILTER-002"

    async def validate_dashboard(
        self,
        dashboard: NormalizedDashboard,
        *,
        query_inventory: list[AnalyzedQuery] | None = None,
        label_cardinality: dict[str, int] | None = None,
    ) -> list[ValidationFinding]:
        report = analyze_filters(
            dashboard,
            query_inventory=query_inventory,
            label_cardinality=label_cardinality,
        )
        findings: list[ValidationFinding] = []
        for item in report.findings:
            if item.get("rule_id") != self.rule_id:
                continue
            findings.append(_to_finding(item))
        return findings


def build_query_inventory(dashboard: NormalizedDashboard) -> list[AnalyzedQuery]:
    inventory: list[AnalyzedQuery] = []
    for panel in dashboard.panels:
        for query in panel.queries:
            inventory.append(
                analyze_query(
                    raw_query=query.raw_query,
                    panel_id=panel.grafana_panel_id,
                    panel_title=panel.title,
                    ref_id=query.ref_id,
                    datasource_uid=query.datasource_uid or panel.datasource_uid,
                    query_language=query.query_language,
                )
            )
    return inventory


def _to_finding(item: dict[str, object]) -> ValidationFinding:
    raw_evidence = item.get("evidence") or []
    evidence: list[dict[str, object]] = []
    if isinstance(raw_evidence, list):
        for entry in raw_evidence:
            if isinstance(entry, dict):
                evidence.append(dict(entry))
    return ValidationFinding(
        rule_id=str(item.get("rule_id")),
        severity=str(item.get("severity", "warning")),  # type: ignore[arg-type]
        category=str(item.get("category", "filters")),
        title=str(item.get("title", "Filter finding")),
        description=str(item.get("description", "")),
        evidence=evidence,
        recommendation=str(item.get("recommendation", "")),
    )
