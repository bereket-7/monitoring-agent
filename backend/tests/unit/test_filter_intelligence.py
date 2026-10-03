"""Unit tests for Phase 6 filter intelligence."""

from __future__ import annotations

import pytest

from app.analyzers.cardinality import classify_cardinality, estimate_cardinality
from app.analyzers.dashboard import normalize_grafana_dashboard
from app.analyzers.filters import analyze_filters
from app.validators.filters import DeadVariableValidator, FilterPropagationValidator


def _dashboard(
    *,
    variables: list[dict[str, object]],
    panels: list[dict[str, object]],
) -> object:
    payload = {
        "uid": "filter-dash",
        "title": "Filter Dash",
        "templating": {"list": variables},
        "panels": panels,
    }
    return normalize_grafana_dashboard(payload)


def test_cardinality_classification() -> None:
    assert classify_cardinality(10) == "safe"
    assert classify_cardinality(200) == "review"
    assert classify_cardinality(5000) == "avoid"
    assert estimate_cardinality("pod") == 5000
    assert classify_cardinality(estimate_cardinality("service")) == "safe"


def test_single_value_filter_ok() -> None:
    dashboard = _dashboard(
        variables=[
            {
                "name": "service",
                "type": "query",
                "multi": False,
                "includeAll": False,
                "query": "label_values(http_requests_total, service)",
            }
        ],
        panels=[
            {
                "id": 1,
                "title": "Requests",
                "type": "stat",
                "targets": [
                    {
                        "refId": "A",
                        "expr": 'sum(rate(http_requests_total{service="$service"}[5m]))',
                    }
                ],
            }
        ],
    )
    report = analyze_filters(dashboard)
    contract = report.contracts[0]
    assert contract.multi is False
    assert contract.affected_panels == [1]
    assert contract.unaffected_panels == []
    assert contract.query_syntax_ok is True
    assert not any(item["rule_id"] == "FILTER-004" for item in report.findings)


def test_multi_value_requires_regex_matcher() -> None:
    dashboard = _dashboard(
        variables=[
            {
                "name": "service",
                "type": "query",
                "multi": True,
                "includeAll": False,
                "query": "label_values(http_requests_total, service)",
            }
        ],
        panels=[
            {
                "id": 1,
                "title": "Requests",
                "type": "stat",
                "targets": [
                    {
                        "refId": "A",
                        "expr": 'sum(rate(http_requests_total{service="$service"}[5m]))',
                    }
                ],
            }
        ],
    )
    report = analyze_filters(dashboard)
    assert any(item["rule_id"] == "FILTER-004" for item in report.findings)


def test_all_value_with_equality_warns() -> None:
    dashboard = _dashboard(
        variables=[
            {
                "name": "environment",
                "type": "custom",
                "multi": False,
                "includeAll": True,
                "query": "production,staging",
            }
        ],
        panels=[
            {
                "id": 1,
                "title": "Env",
                "type": "stat",
                "targets": [
                    {
                        "refId": "A",
                        "expr": 'sum(rate(http_requests_total{environment="$environment"}[5m]))',
                    }
                ],
            }
        ],
    )
    report = analyze_filters(dashboard)
    assert any(item["rule_id"] == "FILTER-005" for item in report.findings)


@pytest.mark.asyncio
async def test_unused_variable_is_dead() -> None:
    dashboard = _dashboard(
        variables=[
            {
                "name": "unused",
                "type": "custom",
                "multi": False,
                "includeAll": False,
                "query": "a,b",
            }
        ],
        panels=[
            {
                "id": 1,
                "title": "Up",
                "type": "stat",
                "targets": [{"refId": "A", "expr": "sum(up)"}],
            }
        ],
    )
    report = analyze_filters(dashboard)
    assert report.dead_variables == ["unused"]

    findings = await DeadVariableValidator().validate_dashboard(dashboard)
    assert any(item.rule_id == "FILTER-002" for item in findings)


@pytest.mark.asyncio
async def test_filter_affecting_only_some_panels() -> None:
    dashboard = _dashboard(
        variables=[
            {
                "name": "service",
                "type": "query",
                "multi": True,
                "includeAll": True,
                "query": "label_values(http_requests_total, service)",
            }
        ],
        panels=[
            {
                "id": 1,
                "title": "A",
                "type": "stat",
                "targets": [
                    {
                        "refId": "A",
                        "expr": 'sum(rate(http_requests_total{service=~"$service"}[5m]))',
                    }
                ],
            },
            {
                "id": 2,
                "title": "B",
                "type": "stat",
                "targets": [
                    {
                        "refId": "A",
                        "expr": "sum(rate(http_requests_total[5m]))",
                    }
                ],
            },
            {
                "id": 3,
                "title": "C",
                "type": "stat",
                "targets": [
                    {
                        "refId": "A",
                        "expr": 'sum(rate(http_requests_total{service=~"$service"}[5m]))',
                    }
                ],
            },
        ],
    )
    report = analyze_filters(dashboard)
    assert "service" in report.partially_propagated
    assert report.contracts[0].affected_panels == [1, 3]
    assert report.contracts[0].unaffected_panels == [2]

    findings = await FilterPropagationValidator().validate_dashboard(dashboard)
    assert any(item.rule_id == "FILTER-001" for item in findings)


def test_high_cardinality_label_classified_avoid() -> None:
    dashboard = _dashboard(
        variables=[
            {
                "name": "pod",
                "type": "query",
                "multi": True,
                "includeAll": True,
                "query": "label_values(up, pod)",
            }
        ],
        panels=[
            {
                "id": 1,
                "title": "Pods",
                "type": "stat",
                "targets": [
                    {"refId": "A", "expr": 'up{pod=~"$pod"}'},
                ],
            }
        ],
    )
    report = analyze_filters(dashboard, label_cardinality={"pod": 8000})
    assert report.contracts[0].cardinality_class == "avoid"
    assert any(item["rule_id"] == "FILTER-003" for item in report.findings)
    assert any(candidate.label == "pod" for candidate in report.candidates)
