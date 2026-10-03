"""Agent evaluation: correctness vs validators, grounding, tool efficiency."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import delete

from app.agent.orchestrator import (
    AgentOrchestrator,
    scripted_assistant_text,
    scripted_tool_calls,
)
from app.analyzers.dashboard import normalize_grafana_dashboard
from app.clients.llm import ScriptedLLMClient
from app.clients.loki import LokiClient
from app.clients.prometheus import PrometheusClient
from app.config import Settings, clear_settings_cache
from app.db import dispose_engine, get_session_factory
from app.models.dashboard import Dashboard
from app.repositories.dashboard import DashboardRepository
from app.schemas.agent import AgentChatRequest, AgentContext
from app.schemas.validation import (
    MetricObservation,
    MetricSemantics,
    TimeRange,
    ValidationContext,
)
from app.validators import ValidationEngine

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_grafana_dashboard.json"


async def _seed_dashboard(settings: Settings) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    normalized = normalize_grafana_dashboard(payload)
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        await session.execute(delete(Dashboard).where(Dashboard.grafana_uid == "api-overview"))
        await session.commit()
        await DashboardRepository(session).upsert_normalized(normalized)
        await session.commit()


def _observations_payload() -> list[dict[str, object]]:
    return [
        {
            "name": "success",
            "role": "success",
            "value": 97.0,
            "query": 'sum(rate(http_requests_total{status=~"2..|3.."}[5m]))',
            "time_range": {"window": "5m"},
            "filters": {"service": "payment-api", "environment": "production"},
            "metric_type": "counter",
        },
        {
            "name": "error",
            "role": "error",
            "value": 3.0,
            "query": 'sum(rate(http_requests_total{status=~"5.."}[5m]))',
            "time_range": {"window": "5m"},
            "filters": {"service": "payment-api", "environment": "production"},
            "metric_type": "counter",
        },
        {
            "name": "total",
            "role": "total",
            "value": 100.0,
            "query": "sum(rate(http_requests_total[5m]))",
            "time_range": {"window": "5m"},
            "filters": {"service": "payment-api", "environment": "production"},
            "metric_type": "counter",
        },
    ]


@pytest.mark.asyncio
async def test_agent_matches_deterministic_validation() -> None:
    """Correctness: agent validate_metric findings match ValidationEngine."""
    clear_settings_cache()
    await dispose_engine()
    settings = Settings(
        database_url=(
            "postgresql+asyncpg://postgres:postgres@localhost:15432/monitoring_agent"
        ),
        agent_max_tool_calls=8,
        loki_url=None,
        openai_api_key=None,
    )
    await _seed_dashboard(settings)

    observations = _observations_payload()
    reference_context = ValidationContext(
        observations=[
            MetricObservation.model_validate(
                {
                    **item,
                    "time_range": TimeRange.model_validate(item["time_range"]),
                }
            )
            for item in observations
        ],
        semantics=MetricSemantics(
            success_definition="http_2xx_3xx",
            error_definition="http_5xx",
            total_definition="all_requests",
        ),
        reported_success_rate=97.0,
        reported_error_rate=3.0,
    )
    reference = await ValidationEngine().run(reference_context)
    reference_ids = sorted({item.rule_id for item in reference})

    llm = ScriptedLLMClient(
        [
            scripted_tool_calls(
                [
                    ("get_dashboard", {"dashboard_uid": "api-overview"}),
                    (
                        "validate_metric",
                        {
                            "observations": observations,
                            "semantics": {
                                "success_definition": "http_2xx_3xx",
                                "error_definition": "http_5xx",
                                "total_definition": "all_requests",
                            },
                            "reported_success_rate": 97.0,
                            "reported_error_rate": 3.0,
                        },
                    ),
                ]
            ),
            scripted_assistant_text(
                "Success and error rates match the deterministic validation findings."
            ),
        ]
    )

    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        response = await AgentOrchestrator(
            llm=llm,
            prometheus=PrometheusClient(
                settings,
                transport=httpx.MockTransport(lambda _r: httpx.Response(500)),
            ),
            loki=LokiClient(settings),
            session=session,
            settings=settings,
        ).run(
            AgentChatRequest(
                message="Is the success rate on this dashboard correct?",
                dashboard_uid="api-overview",
                context=AgentContext(filters={"service": "payment-api"}),
            )
        )

    agent_ids = sorted({item.rule_id for item in response.findings if item.rule_id})
    for rule_id in ("SR-001", "ER-001", "CONS-001"):
        assert rule_id in reference_ids
        assert rule_id in agent_ids

    assert len(response.tool_calls) <= settings.agent_max_tool_calls
    await dispose_engine()
    clear_settings_cache()


@pytest.mark.asyncio
async def test_agent_does_not_ground_fabricated_queries() -> None:
    """Evidence grounding: narrative claims do not create query evidence without tools."""
    clear_settings_cache()
    await dispose_engine()
    settings = Settings(
        database_url=(
            "postgresql+asyncpg://postgres:postgres@localhost:15432/monitoring_agent"
        ),
        agent_max_tool_calls=5,
        loki_url=None,
    )
    await _seed_dashboard(settings)

    llm = ScriptedLLMClient(
        [
            scripted_tool_calls([("get_dashboard", {"dashboard_uid": "api-overview"})]),
            scripted_assistant_text(
                "I executed PromQL sum(rate(http_requests_total[5m])) and got 100% success."
            ),
        ]
    )

    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        response = await AgentOrchestrator(
            llm=llm,
            prometheus=PrometheusClient(
                settings,
                transport=httpx.MockTransport(lambda _r: httpx.Response(500)),
            ),
            loki=LokiClient(settings),
            session=session,
            settings=settings,
        ).run(
            AgentChatRequest(
                message="What is the success rate?",
                dashboard_uid="api-overview",
            )
        )

    assert response.queries == []
    assert not any(call.name.startswith("query_") for call in response.tool_calls)
    # Forbidden: representing a failed/missing query as observed evidence.
    assert all(item.observed for item in response.evidence)
    assert "No queries were executed successfully." in response.sections["Calculation/query"]
    await dispose_engine()
    clear_settings_cache()


@pytest.mark.asyncio
async def test_agent_tool_budget_efficiency() -> None:
    """Tool efficiency: orchestration stops when the call budget is exhausted."""
    clear_settings_cache()
    await dispose_engine()
    settings = Settings(
        database_url=(
            "postgresql+asyncpg://postgres:postgres@localhost:15432/monitoring_agent"
        ),
        agent_max_tool_calls=2,
        loki_url=None,
    )
    await _seed_dashboard(settings)

    llm = ScriptedLLMClient(
        [
            scripted_tool_calls(
                [
                    ("get_dashboard", {"dashboard_uid": "api-overview"}),
                    ("list_dashboard_variables", {"dashboard_uid": "api-overview"}),
                    ("analyze_query", {"query": "sum(up)"}),
                ]
            ),
            scripted_assistant_text("Should not be needed if budget stops the loop."),
        ]
    )

    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        response = await AgentOrchestrator(
            llm=llm,
            prometheus=PrometheusClient(
                settings,
                transport=httpx.MockTransport(lambda _r: httpx.Response(500)),
            ),
            loki=LokiClient(settings),
            session=session,
            settings=settings,
        ).run(
            AgentChatRequest(
                message="Inspect the dashboard",
                dashboard_uid="api-overview",
            )
        )

    assert len(response.tool_calls) <= 2
    assert any("budget" in item.lower() for item in response.limitations) or len(
        response.tool_calls
    ) == 2
    await dispose_engine()
    clear_settings_cache()


@pytest.mark.asyncio
async def test_forbidden_tools_remain_unavailable() -> None:
    """Release gate: read-only boundary is not violated via registry."""
    from app.agent.policies import FORBIDDEN_TOOL_NAMES, assert_tool_allowed
    from app.agent.tools import ToolRegistry

    registry = ToolRegistry()
    for name in FORBIDDEN_TOOL_NAMES:
        with pytest.raises(PermissionError):
            assert_tool_allowed(name)
        assert name not in registry.names()
