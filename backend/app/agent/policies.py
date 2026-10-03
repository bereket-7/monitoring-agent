"""Tool budgets, permission classes, and safety policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PermissionClass = Literal["read_only"]

# Explicit denylist — never register these as tools.
FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "shell",
        "kubectl",
        "sql_write",
        "grafana_write",
        "delete_dashboard",
        "update_dashboard",
        "execute_command",
    }
)


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    name: str
    purpose: str
    permission_class: PermissionClass
    timeout_seconds: float
    max_calls_per_request: int = 5


DEFAULT_TOOL_POLICIES: dict[str, ToolPolicy] = {
    "get_dashboard": ToolPolicy(
        name="get_dashboard",
        purpose="Load a synced Grafana dashboard definition",
        permission_class="read_only",
        timeout_seconds=15.0,
    ),
    "get_panel": ToolPolicy(
        name="get_panel",
        purpose="Load a single panel and its queries",
        permission_class="read_only",
        timeout_seconds=10.0,
    ),
    "list_dashboard_variables": ToolPolicy(
        name="list_dashboard_variables",
        purpose="List dashboard template variables",
        permission_class="read_only",
        timeout_seconds=10.0,
    ),
    "query_prometheus": ToolPolicy(
        name="query_prometheus",
        purpose="Execute a read-only PromQL instant or range query",
        permission_class="read_only",
        timeout_seconds=15.0,
        max_calls_per_request=8,
    ),
    "query_loki": ToolPolicy(
        name="query_loki",
        purpose="Execute a read-only LogQL query when Loki is configured",
        permission_class="read_only",
        timeout_seconds=15.0,
        max_calls_per_request=5,
    ),
    "get_metric_metadata": ToolPolicy(
        name="get_metric_metadata",
        purpose="Fetch Prometheus metric type/help/unit metadata",
        permission_class="read_only",
        timeout_seconds=10.0,
    ),
    "get_label_values": ToolPolicy(
        name="get_label_values",
        purpose="List Prometheus label values",
        permission_class="read_only",
        timeout_seconds=10.0,
    ),
    "analyze_query": ToolPolicy(
        name="analyze_query",
        purpose="Deterministically analyze a PromQL/LogQL query structure",
        permission_class="read_only",
        timeout_seconds=5.0,
    ),
    "validate_metric": ToolPolicy(
        name="validate_metric",
        purpose="Run deterministic validation rules on metric observations",
        permission_class="read_only",
        timeout_seconds=10.0,
    ),
    "compare_metric_results": ToolPolicy(
        name="compare_metric_results",
        purpose="Compare two numeric observations for consistency",
        permission_class="read_only",
        timeout_seconds=5.0,
    ),
    "get_previous_analysis": ToolPolicy(
        name="get_previous_analysis",
        purpose="Run or return deterministic dashboard analysis findings",
        permission_class="read_only",
        timeout_seconds=20.0,
        max_calls_per_request=2,
    ),
}


def assert_tool_allowed(name: str) -> None:
    if name in FORBIDDEN_TOOL_NAMES:
        raise PermissionError(f"Tool '{name}' is forbidden in MVP")
    if name not in DEFAULT_TOOL_POLICIES:
        raise PermissionError(f"Tool '{name}' is not an approved read-only tool")


def policy_for(name: str) -> ToolPolicy:
    assert_tool_allowed(name)
    return DEFAULT_TOOL_POLICIES[name]
