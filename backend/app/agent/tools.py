"""Read-only tool registry for the monitoring agent."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.policies import DEFAULT_TOOL_POLICIES, assert_tool_allowed, policy_for
from app.analyzers.dashboard import normalize_grafana_dashboard
from app.analyzers.query import analyze_query
from app.clients.errors import ExternalClientError
from app.clients.grafana import GrafanaClient
from app.clients.loki import LokiClient
from app.clients.prometheus import PrometheusClient
from app.config import Settings, get_settings
from app.repositories.dashboard import DashboardRepository
from app.schemas.validation import (
    MetricObservation,
    MetricSemantics,
    TimeRange,
    ValidationContext,
)
from app.services.dashboard_analysis import analyze_normalized_dashboard
from app.validators.engine import ValidationEngine

ToolHandler = Callable[["ToolContext", dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolContext:
    session: AsyncSession
    prometheus: PrometheusClient
    loki: LokiClient
    grafana: GrafanaClient | None = None
    settings: Settings = field(default_factory=get_settings)
    call_counts: dict[str, int] = field(default_factory=dict)


class ToolRegistry:
    """Approved read-only tools with typed handlers."""

    def __init__(self, tools: list[ToolSpec] | None = None) -> None:
        specs = tools if tools is not None else default_tools()
        self._tools = {spec.name: spec for spec in specs}
        for name in self._tools:
            assert_tool_allowed(name)

    def list_openai_tools(self) -> list[dict[str, Any]]:
        return [spec.openai_schema() for spec in self._tools.values()]

    def names(self) -> list[str]:
        return sorted(self._tools)

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> dict[str, Any]:
        assert_tool_allowed(name)
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")

        policy = policy_for(name)
        used = context.call_counts.get(name, 0)
        if used >= policy.max_calls_per_request:
            raise PermissionError(
                f"Tool '{name}' exceeded per-request limit ({policy.max_calls_per_request})"
            )
        context.call_counts[name] = used + 1

        try:
            return await self._tools[name].handler(context, arguments)
        except ExternalClientError as exc:
            raise RuntimeError(str(exc)) from exc


async def _load_normalized(context: ToolContext, uid: str) -> Any:
    repo = DashboardRepository(context.session)
    dashboard = await repo.get_by_uid(uid)
    if dashboard is None:
        raise LookupError(f"Dashboard '{uid}' not found locally. Sync it first.")
    return normalize_grafana_dashboard(
        {
            "dashboard": dashboard.raw_json,
            "meta": {
                "uid": dashboard.grafana_uid,
                "url": dashboard.url,
                "folderTitle": dashboard.folder,
            },
        }
    )


async def _get_dashboard(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    uid = str(args.get("dashboard_uid") or "")
    if not uid:
        raise ValueError("dashboard_uid is required")
    normalized = await _load_normalized(context, uid)
    return {
        "summary": f"Loaded dashboard '{normalized.title}' ({normalized.grafana_uid})",
        "dashboard_uid": normalized.grafana_uid,
        "title": normalized.title,
        "panel_count": len(normalized.panels),
        "variable_count": len(normalized.variables),
        "panels": [
            {
                "id": panel.grafana_panel_id,
                "title": panel.title,
                "type": panel.panel_type,
                "query_count": len(panel.queries),
            }
            for panel in normalized.panels
        ],
    }


async def _get_panel(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    uid = str(args.get("dashboard_uid") or "")
    panel_id = args.get("panel_id")
    if not uid or panel_id is None:
        raise ValueError("dashboard_uid and panel_id are required")
    normalized = await _load_normalized(context, uid)
    for panel in normalized.panels:
        if panel.grafana_panel_id == int(panel_id):
            return {
                "summary": f"Loaded panel '{panel.title}' (id={panel.grafana_panel_id})",
                "panel": {
                    "id": panel.grafana_panel_id,
                    "title": panel.title,
                    "type": panel.panel_type,
                    "datasource_uid": panel.datasource_uid,
                    "queries": [query.model_dump() for query in panel.queries],
                },
            }
    raise LookupError(f"Panel {panel_id} not found on dashboard '{uid}'")


async def _list_variables(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    uid = str(args.get("dashboard_uid") or "")
    if not uid:
        raise ValueError("dashboard_uid is required")
    normalized = await _load_normalized(context, uid)
    variables = [
        {
            "name": variable.name,
            "type": variable.variable_type,
            "query": variable.query,
            "multi": variable.multi,
            "include_all": variable.include_all,
            "current_value": variable.current_value,
        }
        for variable in normalized.variables
    ]
    return {
        "summary": f"Found {len(variables)} variables on dashboard '{uid}'",
        "variables": variables,
    }


async def _query_prometheus(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "")
    if not query:
        raise ValueError("query is required")
    mode = str(args.get("mode") or "instant")
    if mode == "range":
        start = args.get("start")
        end = args.get("end")
        if start is None or end is None:
            raise ValueError("start and end are required for range queries")
        result = await context.prometheus.range_query(
            query,
            start=start,
            end=end,
            step=args.get("step") or "60s",
        )
    else:
        result = await context.prometheus.instant_query(query, time=args.get("time"))

    sample_count = len(result.result)
    return {
        "summary": f"Prometheus {result.result_type} query returned {sample_count} series",
        "result_type": result.result_type,
        "sample_count": sample_count,
        "samples": [sample.model_dump() for sample in result.result[:20]],
        "observed": True,
    }


async def _query_loki(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    if not context.loki.enabled:
        raise RuntimeError("Loki is not configured (LOKI_URL unset)")
    query = str(args.get("query") or "")
    if not query:
        raise ValueError("query is required")
    mode = str(args.get("mode") or "range")
    if mode == "instant":
        result = await context.loki.instant_query(query, time=args.get("time"))
    else:
        start = args.get("start")
        end = args.get("end")
        if start is None or end is None:
            raise ValueError("start and end are required for Loki range queries")
        result = await context.loki.range_query(
            query,
            start=start,
            end=end,
            limit=args.get("limit"),
            step=args.get("step"),
        )
    stream_count = len(result.result)
    return {
        "summary": f"Loki {result.result_type} query returned {stream_count} streams",
        "result_type": result.result_type,
        "stream_count": stream_count,
        "streams": [stream.model_dump() for stream in result.result[:10]],
        "observed": True,
    }


async def _get_metric_metadata(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    metric = args.get("metric")
    metadata = await context.prometheus.metadata(str(metric) if metric else None)
    return {
        "summary": f"Retrieved metadata for {len(metadata)} metric entries",
        "metadata": [item.model_dump() for item in metadata[:50]],
        "observed": True,
    }


async def _get_label_values(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    label = str(args.get("label") or "")
    if not label:
        raise ValueError("label is required")
    values = await context.prometheus.label_values(label)
    return {
        "summary": f"Label '{label}' has {len(values)} values",
        "label": label,
        "values": values[:200],
        "observed": True,
    }


async def _analyze_query(_context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "")
    if not query:
        raise ValueError("query is required")
    analyzed = analyze_query(
        raw_query=query,
        panel_id=int(args.get("panel_id") or 0),
        panel_title=str(args.get("panel_title") or ""),
        query_language=str(args.get("query_language") or "promql"),
    )
    return {
        "summary": f"Analyzed query hash={analyzed.query_hash}",
        "analysis": analyzed.model_dump(),
    }


async def _validate_metric(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    raw_observations = args.get("observations") or []
    if not isinstance(raw_observations, list) or not raw_observations:
        raise ValueError("observations list is required")

    observations: list[MetricObservation] = []
    for item in raw_observations:
        if not isinstance(item, dict):
            continue
        time_range = None
        if isinstance(item.get("time_range"), dict):
            time_range = TimeRange.model_validate(item["time_range"])
        observations.append(
            MetricObservation.model_validate(
                {
                    "name": str(item.get("name") or "metric"),
                    "role": item.get("role") or "other",
                    "value": item.get("value"),
                    "query": str(item.get("query") or ""),
                    "time_range": time_range,
                    "filters": dict(item.get("filters") or {}),
                    "metric_type": item.get("metric_type") or "unknown",
                }
            )
        )

    semantics_raw = args.get("semantics") or {}
    semantics = MetricSemantics.model_validate(semantics_raw) if semantics_raw else MetricSemantics()
    validation_context = ValidationContext(
        dashboard_uid=args.get("dashboard_uid"),
        panel_id=args.get("panel_id"),
        observations=observations,
        semantics=semantics,
        consistency_tolerance=context.settings.validation_consistency_tolerance,
        reported_success_rate=args.get("reported_success_rate"),
        reported_error_rate=args.get("reported_error_rate"),
    )
    findings = await ValidationEngine().run(validation_context)
    return {
        "summary": f"Validation produced {len(findings)} findings",
        "findings": [finding.model_dump() for finding in findings],
    }


async def _compare_metric_results(
    _context: ToolContext,
    args: dict[str, Any],
) -> dict[str, Any]:
    left = args.get("left")
    right = args.get("right")
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise ValueError("left and right observation objects are required")
    left_value = left.get("value")
    right_value = right.get("value")
    if left_value is None or right_value is None:
        raise ValueError("Both observations must include numeric values")
    left_f = float(left_value)
    right_f = float(right_value)
    tolerance = float(args.get("tolerance") or 0.02)
    delta = abs(left_f - right_f)
    denom = max(abs(left_f), abs(right_f), 1e-9)
    relative = delta / denom
    compatible = relative <= tolerance
    return {
        "summary": (
            "Observations are within tolerance"
            if compatible
            else "Observations differ beyond tolerance"
        ),
        "left": left,
        "right": right,
        "absolute_delta": delta,
        "relative_delta": relative,
        "tolerance": tolerance,
        "compatible": compatible,
    }


async def _get_previous_analysis(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    uid = str(args.get("dashboard_uid") or "")
    if not uid:
        raise ValueError("dashboard_uid is required")
    normalized = await _load_normalized(context, uid)
    report = analyze_normalized_dashboard(normalized)
    return {
        "summary": (
            f"Dashboard analysis for '{uid}' "
            f"({len(report.findings)} findings, {len(report.query_inventory)} queries)"
        ),
        "dashboard_uid": report.dashboard_uid,
        "title": report.title,
        "findings": [finding.model_dump() for finding in report.findings],
        "unused_variables": report.unused_variables,
        "duplicate_query_count": len(report.duplicate_queries),
        "filter_intelligence": (
            report.filter_intelligence.model_dump() if report.filter_intelligence else None
        ),
    }


def _object_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def default_tools() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="get_dashboard",
            description=DEFAULT_TOOL_POLICIES["get_dashboard"].purpose,
            parameters=_object_schema(
                {"dashboard_uid": {"type": "string"}},
                ["dashboard_uid"],
            ),
            handler=_get_dashboard,
        ),
        ToolSpec(
            name="get_panel",
            description=DEFAULT_TOOL_POLICIES["get_panel"].purpose,
            parameters=_object_schema(
                {
                    "dashboard_uid": {"type": "string"},
                    "panel_id": {"type": "integer"},
                },
                ["dashboard_uid", "panel_id"],
            ),
            handler=_get_panel,
        ),
        ToolSpec(
            name="list_dashboard_variables",
            description=DEFAULT_TOOL_POLICIES["list_dashboard_variables"].purpose,
            parameters=_object_schema(
                {"dashboard_uid": {"type": "string"}},
                ["dashboard_uid"],
            ),
            handler=_list_variables,
        ),
        ToolSpec(
            name="query_prometheus",
            description=DEFAULT_TOOL_POLICIES["query_prometheus"].purpose,
            parameters=_object_schema(
                {
                    "query": {"type": "string"},
                    "mode": {"type": "string", "enum": ["instant", "range"]},
                    "time": {},
                    "start": {},
                    "end": {},
                    "step": {"type": "string"},
                },
                ["query"],
            ),
            handler=_query_prometheus,
        ),
        ToolSpec(
            name="query_loki",
            description=DEFAULT_TOOL_POLICIES["query_loki"].purpose,
            parameters=_object_schema(
                {
                    "query": {"type": "string"},
                    "mode": {"type": "string", "enum": ["instant", "range"]},
                    "time": {},
                    "start": {},
                    "end": {},
                    "limit": {"type": "integer"},
                    "step": {},
                },
                ["query"],
            ),
            handler=_query_loki,
        ),
        ToolSpec(
            name="get_metric_metadata",
            description=DEFAULT_TOOL_POLICIES["get_metric_metadata"].purpose,
            parameters=_object_schema({"metric": {"type": "string"}}),
            handler=_get_metric_metadata,
        ),
        ToolSpec(
            name="get_label_values",
            description=DEFAULT_TOOL_POLICIES["get_label_values"].purpose,
            parameters=_object_schema(
                {"label": {"type": "string"}},
                ["label"],
            ),
            handler=_get_label_values,
        ),
        ToolSpec(
            name="analyze_query",
            description=DEFAULT_TOOL_POLICIES["analyze_query"].purpose,
            parameters=_object_schema(
                {
                    "query": {"type": "string"},
                    "panel_id": {"type": "integer"},
                    "panel_title": {"type": "string"},
                    "query_language": {"type": "string"},
                },
                ["query"],
            ),
            handler=_analyze_query,
        ),
        ToolSpec(
            name="validate_metric",
            description=DEFAULT_TOOL_POLICIES["validate_metric"].purpose,
            parameters=_object_schema(
                {
                    "observations": {"type": "array"},
                    "semantics": {"type": "object"},
                    "dashboard_uid": {"type": "string"},
                    "panel_id": {"type": "integer"},
                    "reported_success_rate": {"type": "number"},
                    "reported_error_rate": {"type": "number"},
                },
                ["observations"],
            ),
            handler=_validate_metric,
        ),
        ToolSpec(
            name="compare_metric_results",
            description=DEFAULT_TOOL_POLICIES["compare_metric_results"].purpose,
            parameters=_object_schema(
                {
                    "left": {"type": "object"},
                    "right": {"type": "object"},
                    "tolerance": {"type": "number"},
                },
                ["left", "right"],
            ),
            handler=_compare_metric_results,
        ),
        ToolSpec(
            name="get_previous_analysis",
            description=DEFAULT_TOOL_POLICIES["get_previous_analysis"].purpose,
            parameters=_object_schema(
                {"dashboard_uid": {"type": "string"}},
                ["dashboard_uid"],
            ),
            handler=_get_previous_analysis,
        ),
    ]


def tool_result_message(tool_call_id: str, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": name,
        "content": json.dumps(payload, default=str),
    }
