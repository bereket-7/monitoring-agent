"""Filter discovery, propagation, and multi-value syntax analysis."""

from __future__ import annotations

import re
from typing import Any

from app.analyzers.cardinality import classify_cardinality, estimate_cardinality
from app.analyzers.query import analyze_query
from app.schemas.analysis import AnalyzedQuery
from app.schemas.dashboard import NormalizedDashboard, NormalizedVariable
from app.schemas.filters import (
    AllValueBehavior,
    FilterContract,
    FilterIntelligenceReport,
    LabelCandidate,
    PanelFilterUsage,
)

_COMMON_FILTER_LABELS = {
    "environment",
    "env",
    "service",
    "namespace",
    "region",
    "cluster",
    "method",
    "endpoint",
    "status_code",
    "status",
}


def analyze_filters(
    dashboard: NormalizedDashboard,
    *,
    label_cardinality: dict[str, int] | None = None,
    query_inventory: list[AnalyzedQuery] | None = None,
) -> FilterIntelligenceReport:
    """Build filter contracts and propagation findings for a dashboard."""
    inventory = query_inventory or _build_inventory(dashboard)
    cardinality = label_cardinality or {}

    candidates = _discover_candidates(dashboard, inventory, cardinality)
    contracts: list[FilterContract] = []
    dead: list[str] = []
    partial: list[str] = []
    findings: list[dict[str, Any]] = []

    panel_ids = [panel.grafana_panel_id for panel in dashboard.panels if panel.queries]

    for variable in dashboard.variables:
        contract = _build_contract(variable, inventory, panel_ids, cardinality)
        contracts.append(contract)

        if not contract.affected_panels:
            dead.append(variable.name)
            findings.append(
                {
                    "rule_id": "FILTER-002",
                    "severity": "warning",
                    "category": "filters",
                    "title": "Dead dashboard variable",
                    "description": (
                        f"Variable '${variable.name}' does not affect any panel query."
                    ),
                    "evidence": [{"variable": variable.name}],
                    "recommendation": "Remove the variable or apply it to relevant queries.",
                }
            )
        elif contract.unaffected_panels:
            partial.append(variable.name)
            findings.append(
                {
                    "rule_id": "FILTER-001",
                    "severity": "warning",
                    "category": "filters",
                    "title": "Variable only partially propagated",
                    "description": (
                        f"Variable '${variable.name}' is used by some panels but missing from others."
                    ),
                    "evidence": [
                        {
                            "variable": variable.name,
                            "affected_panels": contract.affected_panels,
                            "unaffected_panels": contract.unaffected_panels,
                        }
                    ],
                    "recommendation": (
                        "Apply the variable to all relevant panels or document intentional exclusions."
                    ),
                }
            )

        syntax_findings = _multi_value_syntax_findings(variable, inventory)
        findings.extend(syntax_findings)
        if syntax_findings:
            contract.query_syntax_ok = False

        if contract.cardinality_class == "avoid":
            findings.append(
                {
                    "rule_id": "FILTER-003",
                    "severity": "error",
                    "category": "filters",
                    "title": "High-cardinality filter candidate",
                    "description": (
                        f"Label/filter '{contract.label or variable.name}' is classified as avoid "
                        f"(estimated cardinality={contract.estimated_cardinality})."
                    ),
                    "evidence": [
                        {
                            "variable": variable.name,
                            "label": contract.label,
                            "cardinality_class": contract.cardinality_class,
                            "estimated_cardinality": contract.estimated_cardinality,
                        }
                    ],
                    "recommendation": (
                        "Do not expose high-cardinality labels as dashboard filters."
                    ),
                }
            )

    return FilterIntelligenceReport(
        candidates=candidates,
        contracts=contracts,
        dead_variables=sorted(dead),
        partially_propagated=sorted(partial),
        findings=findings,
    )


def _build_inventory(dashboard: NormalizedDashboard) -> list[AnalyzedQuery]:
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


def _discover_candidates(
    dashboard: NormalizedDashboard,
    inventory: list[AnalyzedQuery],
    cardinality: dict[str, int],
) -> list[LabelCandidate]:
    labels: dict[str, LabelCandidate] = {}

    for analyzed in inventory:
        for label in analyzed.referenced_labels:
            est = estimate_cardinality(label, cardinality.get(label))
            labels[label] = LabelCandidate(
                label=label,
                source="query",
                estimated_cardinality=est,
                cardinality_class=classify_cardinality(est),
                evidence=[{"panel_id": analyzed.panel_id, "query": analyzed.raw_query}],
            )

    for variable in dashboard.variables:
        inferred = _infer_label(variable)
        if inferred is None:
            continue
        est = estimate_cardinality(inferred, cardinality.get(inferred))
        existing = labels.get(inferred)
        if existing is None:
            labels[inferred] = LabelCandidate(
                label=inferred,
                source="variable",
                estimated_cardinality=est,
                cardinality_class=classify_cardinality(est),
                evidence=[{"variable": variable.name}],
            )
        else:
            existing.evidence.append({"variable": variable.name})

    # Suggest common filter labels seen in queries even if not yet variables.
    for label in list(labels):
        if label.lower() in _COMMON_FILTER_LABELS and labels[label].source == "query":
            labels[label].evidence.append({"note": "common_filter_label"})

    return sorted(labels.values(), key=lambda item: item.label)


def _build_contract(
    variable: NormalizedVariable,
    inventory: list[AnalyzedQuery],
    panel_ids: list[int],
    cardinality: dict[str, int],
) -> FilterContract:
    label = _infer_label(variable)
    est = estimate_cardinality(label or variable.name, cardinality.get(label or variable.name))
    usage: list[PanelFilterUsage] = []
    affected: list[int] = []
    unaffected: list[int] = []

    panels_to_queries: dict[int, list[AnalyzedQuery]] = {}
    for analyzed in inventory:
        panels_to_queries.setdefault(analyzed.panel_id, []).append(analyzed)

    for panel_id in panel_ids:
        queries = panels_to_queries.get(panel_id, [])
        matching = [q for q in queries if variable.name in q.referenced_variables]
        uses = bool(matching)
        title = matching[0].panel_title if matching else (
            queries[0].panel_title if queries else f"Panel {panel_id}"
        )
        usage.append(
            PanelFilterUsage(
                panel_id=panel_id,
                panel_title=title,
                uses_variable=uses,
                query_refs=[q.ref_id or "" for q in matching if q.ref_id],
            )
        )
        if uses:
            affected.append(panel_id)
        else:
            unaffected.append(panel_id)

    return FilterContract(
        variable_name=variable.name,
        label=label,
        source="dashboard_variable",
        variable_type=variable.variable_type,
        multi=variable.multi,
        include_all=variable.include_all,
        current_value=variable.current_value,
        cardinality_class=classify_cardinality(est),
        estimated_cardinality=est,
        affected_panels=affected,
        unaffected_panels=unaffected,
        all_value_behavior=_infer_all_value_behavior(variable, inventory),
        panel_usage=usage,
    )


def _infer_label(variable: NormalizedVariable) -> str | None:
    # Common Grafana pattern: label_values(metric, label)
    if variable.query:
        match = re.search(
            r"label_values\s*\(\s*[^,]+,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)",
            variable.query,
        )
        if match:
            return match.group(1)
    if variable.name.lower() in _COMMON_FILTER_LABELS:
        return variable.name
    # Often variable name matches label name.
    if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", variable.name):
        return variable.name
    return None


def _infer_all_value_behavior(
    variable: NormalizedVariable,
    inventory: list[AnalyzedQuery],
) -> AllValueBehavior:
    if not variable.include_all:
        return "not_applicable"
    for analyzed in inventory:
        if variable.name not in analyzed.referenced_variables:
            continue
        query = analyzed.normalized_query
        if f"${{{variable.name}:pipe}}" in analyzed.raw_query:
            return "regex_all"
        if re.search(rf'{variable.name}\s*=~\s*[\'"]\${variable.name}[\'"]', query):
            return "regex_all"
        if re.search(rf'{variable.name}\s*=\s*[\'"]\${variable.name}[\'"]', query):
            return "literal_all"
    return "unknown"


def _multi_value_syntax_findings(
    variable: NormalizedVariable,
    inventory: list[AnalyzedQuery],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for analyzed in inventory:
        if variable.name not in analyzed.referenced_variables:
            continue
        query = analyzed.raw_query
        uses_equals = bool(
            re.search(rf'{variable.name}\s*=\s*[\'"]?\${{?{variable.name}}}?[\'"]?', query)
        )
        uses_regex = bool(
            re.search(rf'{variable.name}\s*=~\s*[\'"]?\${{?{variable.name}}}?[\'"]?', query)
        )

        if variable.multi and uses_equals and not uses_regex:
            findings.append(
                {
                    "rule_id": "FILTER-004",
                    "severity": "error",
                    "category": "filters",
                    "title": "Multi-value variable used with equality matcher",
                    "description": (
                        f"Variable '${variable.name}' is multi-value but query uses '='. "
                        "Multi-value filters typically require '=~' / regex joining."
                    ),
                    "evidence": [
                        {
                            "variable": variable.name,
                            "panel_id": analyzed.panel_id,
                            "query": analyzed.raw_query,
                            "mode": "multi",
                        }
                    ],
                    "recommendation": (
                        f'Use {variable.name}=~"${variable.name}" (or :regex) for multi-value filters.'
                    ),
                }
            )

        if variable.include_all and uses_equals and not uses_regex:
            findings.append(
                {
                    "rule_id": "FILTER-005",
                    "severity": "warning",
                    "category": "filters",
                    "title": "Include-all variable may produce invalid/over-narrow queries",
                    "description": (
                        f"Variable '${variable.name}' has includeAll enabled but is used with '='. "
                        "Selecting All can generate an invalid literal."
                    ),
                    "evidence": [
                        {
                            "variable": variable.name,
                            "panel_id": analyzed.panel_id,
                            "query": analyzed.raw_query,
                            "mode": "all",
                        }
                    ],
                    "recommendation": (
                        "Use regex matchers or Grafana format modifiers for All-value behavior."
                    ),
                }
            )

        # Empty-value risk: variable referenced but no matcher around it.
        if f"${variable.name}" in query and not uses_equals and not uses_regex:
            # Could be used in legend/title formatting; only warn for selector-less metric filters.
            if "{" in query:
                findings.append(
                    {
                        "rule_id": "FILTER-006",
                        "severity": "info",
                        "category": "filters",
                        "title": "Variable referenced without clear label matcher",
                        "description": (
                            f"Variable '${variable.name}' appears in a query without a clear "
                            "label matcher; empty values may broaden the query unexpectedly."
                        ),
                        "evidence": [
                            {
                                "variable": variable.name,
                                "panel_id": analyzed.panel_id,
                                "query": analyzed.raw_query,
                                "mode": "empty",
                            }
                        ],
                        "recommendation": "Bind the variable to an explicit label matcher.",
                    }
                )
    return findings
