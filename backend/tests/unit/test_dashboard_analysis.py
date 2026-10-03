"""Unit tests for deterministic dashboard analysis reports."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.dashboard_analysis import analyze_grafana_payload

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "sample_grafana_dashboard.json"
)


def test_analyze_sample_dashboard_builds_report() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    report = analyze_grafana_payload(payload)

    assert report.dashboard_uid == "api-overview"
    assert report.panel_count == 3
    assert report.variable_count == 2
    assert len(report.query_inventory) == 3
    assert {query.panel_id for query in report.query_inventory} == {2, 3, 4}

    used = {edge.variable for edge in report.variable_graph}
    assert "service" in used
    assert report.unused_variables == []

    success = next(q for q in report.query_inventory if q.panel_id == 3)
    assert "http_requests_total" in success.referenced_metrics
    assert "service" in success.referenced_variables


def test_duplicate_and_unused_variable_detection() -> None:
    payload = {
        "uid": "dup-dash",
        "title": "Dup",
        "templating": {
            "list": [
                {"name": "service", "type": "query", "query": "label_values(up, service)"},
                {"name": "unused", "type": "custom", "query": "a,b"},
            ]
        },
        "panels": [
            {
                "id": 1,
                "title": "A",
                "type": "stat",
                "targets": [
                    {
                        "refId": "A",
                        "expr": 'sum(rate(http_requests_total{service="$service"}[5m]))',
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
                        "expr": 'sum(rate(http_requests_total{service="$service"}[5m]))',
                    }
                ],
            },
        ],
    }
    report = analyze_grafana_payload(payload)
    assert report.unused_variables == ["unused"]
    assert len(report.duplicate_queries) == 1
    assert any(item.rule_id == "QUERY-001" for item in report.findings)
    assert any(item.rule_id == "DASH-002" for item in report.findings)
