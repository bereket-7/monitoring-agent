"""Prometheus metrics for agent quality and request volume."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

AGENT_REQUESTS = Counter(
    "agent_requests_total",
    "Total agent chat requests",
    ["status"],
)
AGENT_REQUEST_DURATION = Histogram(
    "agent_request_duration_seconds",
    "Agent chat request duration",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120),
)
AGENT_TOOL_CALLS = Counter(
    "agent_tool_calls_total",
    "Total agent tool calls",
    ["tool_name", "status"],
)
AGENT_TOOL_DURATION = Histogram(
    "agent_tool_call_duration_seconds",
    "Agent tool call duration",
    ["tool_name"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 15),
)
AGENT_TOOL_ERRORS = Counter(
    "agent_tool_errors_total",
    "Total agent tool errors",
    ["tool_name"],
)
AGENT_FINDINGS = Counter(
    "agent_analysis_findings_total",
    "Findings produced during agent analysis",
    ["severity"],
)
AGENT_LLM_REQUESTS = Counter(
    "agent_llm_requests_total",
    "Total LLM completion requests",
    ["status"],
)
AGENT_LLM_ERRORS = Counter(
    "agent_llm_errors_total",
    "Total LLM errors",
)
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP API requests",
    ["method", "path", "status"],
)


def observe_agent_request(*, status: str, duration_seconds: float, findings_count: int = 0) -> None:
    AGENT_REQUESTS.labels(status=status).inc()
    AGENT_REQUEST_DURATION.observe(duration_seconds)
    if findings_count:
        AGENT_FINDINGS.labels(severity="mixed").inc(findings_count)


def observe_tool_call(*, tool_name: str, status: str, duration_seconds: float) -> None:
    AGENT_TOOL_CALLS.labels(tool_name=tool_name, status=status).inc()
    AGENT_TOOL_DURATION.labels(tool_name=tool_name).observe(duration_seconds)
    if status in {"error", "denied"}:
        AGENT_TOOL_ERRORS.labels(tool_name=tool_name).inc()


def observe_llm_request(*, status: str) -> None:
    AGENT_LLM_REQUESTS.labels(status=status).inc()
    if status == "error":
        AGENT_LLM_ERRORS.inc()


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
