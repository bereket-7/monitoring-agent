"""Build deterministic dashboard analysis reports without an LLM."""

from __future__ import annotations

from collections import defaultdict

from app.analyzers.dashboard import normalize_grafana_dashboard
from app.analyzers.filters import analyze_filters
from app.analyzers.query import analyze_query, static_query_findings
from app.schemas.analysis import (
    AnalyzedQuery,
    DashboardAnalysisReport,
    DuplicateQueryGroup,
    StaticAnalysisFinding,
    VariableUsage,
)
from app.schemas.dashboard import NormalizedDashboard


def analyze_normalized_dashboard(
    dashboard: NormalizedDashboard,
    *,
    label_cardinality: dict[str, int] | None = None,
) -> DashboardAnalysisReport:
    """Produce query inventory, variable graph, duplicates, filters, and static findings."""
    inventory: list[AnalyzedQuery] = []
    findings: list[StaticAnalysisFinding] = []

    for panel in dashboard.panels:
        if not panel.title or panel.title.startswith("Panel "):
            findings.append(
                StaticAnalysisFinding(
                    rule_id="DASH-001",
                    severity="warning",
                    category="dashboard_quality",
                    title="Panel missing meaningful title",
                    description=f"Panel id {panel.grafana_panel_id} has a weak or missing title.",
                    evidence=[
                        {
                            "panel_id": panel.grafana_panel_id,
                            "title": panel.title,
                            "panel_type": panel.panel_type,
                        }
                    ],
                    recommendation="Set a descriptive panel title for inventory and incident response.",
                )
            )

        for query in panel.queries:
            analyzed = analyze_query(
                raw_query=query.raw_query,
                panel_id=panel.grafana_panel_id,
                panel_title=panel.title,
                ref_id=query.ref_id,
                datasource_uid=query.datasource_uid or panel.datasource_uid,
                query_language=query.query_language,
            )
            inventory.append(analyzed)
            findings.extend(static_query_findings(analyzed))

    variable_graph = _build_variable_graph(inventory)
    used_variables = {edge.variable for edge in variable_graph}
    declared = [variable.name for variable in dashboard.variables]
    unused = sorted(name for name in declared if name not in used_variables)

    for name in unused:
        findings.append(
            StaticAnalysisFinding(
                rule_id="DASH-002",
                severity="warning",
                category="dashboard_quality",
                title="Unused dashboard variable",
                description=f"Variable '${name}' is declared but not referenced by any panel query.",
                evidence=[{"variable": name}],
                recommendation="Remove the variable or wire it into relevant panel queries.",
            )
        )

    duplicates = _find_duplicate_queries(inventory)
    for group in duplicates:
        findings.append(
            StaticAnalysisFinding(
                rule_id="QUERY-001",
                severity="warning",
                category="query_quality",
                title="Duplicate query detected",
                description=(
                    f"Normalized query hash {group.query_hash[:12]} appears "
                    f"{len(group.occurrences)} times."
                ),
                evidence=group.occurrences,
                recommendation=(
                    "Deduplicate panels/queries or extract a shared recording rule "
                    "if reuse is intentional."
                ),
            )
        )

    title_counts: dict[str, list[int]] = defaultdict(list)
    for panel in dashboard.panels:
        title_counts[panel.title].append(panel.grafana_panel_id)
    for title, panel_ids in title_counts.items():
        if len(panel_ids) > 1:
            findings.append(
                StaticAnalysisFinding(
                    rule_id="DASH-003",
                    severity="info",
                    category="dashboard_quality",
                    title="Duplicate panel titles",
                    description=f"Title '{title}' is used by multiple panels.",
                    evidence=[{"title": title, "panel_ids": panel_ids}],
                    recommendation="Use unique panel titles to reduce ambiguity in findings.",
                )
            )

    filter_report = analyze_filters(
        dashboard,
        query_inventory=inventory,
        label_cardinality=label_cardinality,
    )
    for item in filter_report.findings:
        findings.append(
            StaticAnalysisFinding(
                rule_id=str(item.get("rule_id", "FILTER")),
                severity=str(item.get("severity", "warning")),  # type: ignore[arg-type]
                category=str(item.get("category", "filters")),
                title=str(item.get("title", "Filter finding")),
                description=str(item.get("description", "")),
                evidence=list(item.get("evidence") or []),
                recommendation=str(item.get("recommendation", "")),
            )
        )

    return DashboardAnalysisReport(
        dashboard_uid=dashboard.grafana_uid,
        title=dashboard.title,
        panel_count=len(dashboard.panels),
        variable_count=len(dashboard.variables),
        query_inventory=inventory,
        variable_graph=variable_graph,
        unused_variables=unused,
        duplicate_queries=duplicates,
        filter_intelligence=filter_report,
        findings=findings,
    )


def analyze_grafana_payload(
    payload: dict[str, object],
    *,
    label_cardinality: dict[str, int] | None = None,
) -> DashboardAnalysisReport:
    """Normalize Grafana JSON then analyze it."""
    normalized = normalize_grafana_dashboard(payload)
    return analyze_normalized_dashboard(
        normalized,
        label_cardinality=label_cardinality,
    )


def _build_variable_graph(inventory: list[AnalyzedQuery]) -> list[VariableUsage]:
    edges: list[VariableUsage] = []
    for query in inventory:
        for variable in query.referenced_variables:
            edges.append(
                VariableUsage(
                    variable=variable,
                    panel_id=query.panel_id,
                    panel_title=query.panel_title,
                    query_ref=query.ref_id,
                    query_hash=query.query_hash,
                )
            )
    return edges


def _find_duplicate_queries(inventory: list[AnalyzedQuery]) -> list[DuplicateQueryGroup]:
    grouped: dict[str, list[AnalyzedQuery]] = defaultdict(list)
    for query in inventory:
        grouped[query.query_hash].append(query)

    duplicates: list[DuplicateQueryGroup] = []
    for query_hash, items in grouped.items():
        if len(items) < 2:
            continue
        duplicates.append(
            DuplicateQueryGroup(
                query_hash=query_hash,
                normalized_query=items[0].normalized_query,
                occurrences=[
                    {
                        "panel_id": item.panel_id,
                        "panel_title": item.panel_title,
                        "ref_id": item.ref_id,
                    }
                    for item in items
                ],
            )
        )
    return duplicates
