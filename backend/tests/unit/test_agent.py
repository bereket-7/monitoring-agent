"""Unit tests for Phase 7 agent orchestration (mocked LLM/tools)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import delete

from app.agent.formatter import compute_confidence
from app.agent.orchestrator import (
    AgentOrchestrator,
    scripted_assistant_text,
    scripted_tool_calls,
)
from app.agent.policies import FORBIDDEN_TOOL_NAMES, assert_tool_allowed
from app.agent.prompts import build_system_messages, system_prompt
from app.agent.state import AgentState
from app.agent.tools import ToolContext, ToolRegistry
from app.analyzers.dashboard import normalize_grafana_dashboard
from app.clients.llm import ScriptedLLMClient
from app.clients.loki import LokiClient
from app.clients.prometheus import PrometheusClient
from app.config import Settings, clear_settings_cache
from app.db import dispose_engine, get_session_factory
from app.models.dashboard import Dashboard
from app.repositories.dashboard import DashboardRepository
from app.schemas.agent import AgentChatRequest, AgentContext, AgentTimeRange

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "sample_grafana_dashboard.json"
)


def test_prompts_load_from_files() -> None:
    text = system_prompt()
    assert "Never invent monitoring data" in text
    messages = build_system_messages()
    assert len(messages) == 3
    assert all(item["role"] == "system" for item in messages)


def test_forbidden_tools_denied() -> None:
    with pytest.raises(PermissionError):
        assert_tool_allowed("shell")
    assert "kubectl" in FORBIDDEN_TOOL_NAMES


def test_confidence_from_evidence_coverage() -> None:
    from app.schemas.agent import ToolCallRecord

    low = AgentState(user_message="q")
    assert compute_confidence(low) == "low"

    medium = AgentState(
        user_message="q",
        tool_calls=[
            ToolCallRecord(name="get_dashboard", arguments={}, status="success", result={}),
            ToolCallRecord(
                name="query_prometheus",
                arguments={"query": "up"},
                status="success",
                result={"summary": "ok"},
            ),
        ],
    )
    assert compute_confidence(medium) == "medium"

    high = AgentState(
        user_message="q",
        tool_calls=[
            ToolCallRecord(name="get_dashboard", arguments={}, status="success", result={}),
            ToolCallRecord(
                name="query_prometheus",
                arguments={"query": "up"},
                status="success",
                result={"summary": "ok"},
            ),
            ToolCallRecord(
                name="validate_metric",
                arguments={},
                status="success",
                result={"findings": []},
            ),
        ],
    )
    assert compute_confidence(high) == "high"


@pytest.mark.asyncio
async def test_analyze_and_compare_tools_no_external_io() -> None:
    settings = Settings(loki_url=None)
    registry = ToolRegistry()
    context = ToolContext(
        session=None,  # type: ignore[arg-type]
        prometheus=PrometheusClient(settings, transport=httpx.MockTransport(lambda r: httpx.Response(500))),
        loki=LokiClient(settings),
        settings=settings,
    )

    analyzed = await registry.execute(
        "analyze_query",
        {"query": 'sum(rate(http_requests_total{service="api"}[5m]))'},
        context,
    )
    assert analyzed["analysis"]["referenced_metrics"]

    compared = await registry.execute(
        "compare_metric_results",
        {
            "left": {"name": "a", "value": 0.98},
            "right": {"name": "b", "value": 0.97},
            "tolerance": 0.05,
        },
        context,
    )
    assert compared["compatible"] is True

    validated = await registry.execute(
        "validate_metric",
        {
            "observations": [
                {
                    "name": "success",
                    "role": "success",
                    "value": 90,
                    "query": "sum(success)",
                    "filters": {"service": "api"},
                },
                {
                    "name": "total",
                    "role": "total",
                    "value": 100,
                    "query": "sum(total)",
                    "filters": {"service": "api"},
                },
            ],
            "semantics": {"success_definition": "2xx", "total_definition": "all"},
            "reported_success_rate": 0.9,
        },
        context,
    )
    assert "findings" in validated


@pytest.mark.asyncio
async def test_orchestrator_uses_tools_without_fabricating_evidence() -> None:
    clear_settings_cache()
    await dispose_engine()
    settings = Settings(
        database_url=(
            "postgresql+asyncpg://postgres:postgres@localhost:15432/monitoring_agent"
        ),
        agent_max_tool_calls=10,
        loki_url=None,
        openai_api_key=None,
    )

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    normalized = normalize_grafana_dashboard(payload)

    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        await session.execute(delete(Dashboard).where(Dashboard.grafana_uid == "api-overview"))
        await session.commit()
        repo = DashboardRepository(session)
        await repo.upsert_normalized(normalized)
        await session.commit()

    def prom_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/query":
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "resultType": "vector",
                        "result": [
                            {
                                "metric": {"__name__": "up"},
                                "value": [1_700_000_000, "1"],
                            }
                        ],
                    },
                },
            )
        return httpx.Response(404, json={"status": "error", "error": "not found"})

    llm = ScriptedLLMClient(
        [
            scripted_tool_calls(
                [
                    ("get_dashboard", {"dashboard_uid": "api-overview"}),
                    ("get_previous_analysis", {"dashboard_uid": "api-overview"}),
                    ("query_prometheus", {"query": "up", "mode": "instant"}),
                ]
            ),
            scripted_assistant_text(
                "Answer: The dashboard is loaded and Prometheus returned up=1. "
                "Evidence comes only from tool results. "
                "Recommendation: keep validating success-rate panels with SR-001."
            ),
        ]
    )

    async with session_factory() as session:
        orchestrator = AgentOrchestrator(
            llm=llm,
            prometheus=PrometheusClient(settings, transport=httpx.MockTransport(prom_handler)),
            loki=LokiClient(settings),
            session=session,
            settings=settings,
        )
        response = await orchestrator.run(
            AgentChatRequest(
                message="Is this dashboard healthy?",
                dashboard_uid="api-overview",
                context=AgentContext(
                    time_range=AgentTimeRange(**{"from": "now-6h", "to": "now"}),
                    filters={"service": "payment-api"},
                ),
            )
        )

    assert response.confidence in {"high", "medium", "low"}
    assert response.tool_calls
    assert all(call.status in {"success", "error", "denied"} for call in response.tool_calls)
    assert any(call.name == "get_dashboard" and call.status == "success" for call in response.tool_calls)
    assert any(call.name == "query_prometheus" and call.status == "success" for call in response.tool_calls)
    assert response.queries
    assert response.evidence
    assert response.sections["Evidence"]
    # Evidence must be grounded in successful tools — no fabricated query claims without records.
    for query in response.queries:
        assert any(
            call.name == query.tool_name and call.status == "success" for call in response.tool_calls
        )

    await dispose_engine()
    clear_settings_cache()


@pytest.mark.asyncio
async def test_scripted_llm_stops_without_inventing_tool_results() -> None:
    settings = Settings(agent_max_tool_calls=2, loki_url=None)
    llm = ScriptedLLMClient(
        [
            scripted_tool_calls(
                [("analyze_query", {"query": "sum(up)"})]
            ),
            scripted_assistant_text(
                "I analyzed the query structure. No Prometheus execution was claimed."
            ),
        ]
    )

    class _DummySession:
        pass

    orchestrator = AgentOrchestrator(
        llm=llm,
        prometheus=PrometheusClient(settings, transport=httpx.MockTransport(lambda r: httpx.Response(500))),
        loki=LokiClient(settings),
        session=_DummySession(),  # type: ignore[arg-type]
        settings=settings,
    )
    response = await orchestrator.run(AgentChatRequest(message="Analyze sum(up)"))
    assert response.queries == []
    assert any(call.name == "analyze_query" and call.status == "success" for call in response.tool_calls)
    assert "Prometheus" not in response.sections["Calculation/query"] or "No queries" in response.sections["Calculation/query"]


@pytest.mark.asyncio
async def test_llm_tool_call_argument_parsing() -> None:
    from app.clients.llm import LLMClient

    client = LLMClient(Settings(openai_api_key="test"))
    parsed = client._parse_response(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "1",
                                "function": {
                                    "name": "get_dashboard",
                                    "arguments": '{"dashboard_uid":"api-overview"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
    )
    assert parsed.message.tool_calls[0].name == "get_dashboard"
    assert parsed.message.tool_calls[0].arguments["dashboard_uid"] == "api-overview"
    await client.aclose()
