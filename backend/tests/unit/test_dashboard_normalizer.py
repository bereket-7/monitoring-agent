"""Unit tests for Grafana dashboard normalization."""

from __future__ import annotations

import json
from pathlib import Path

from app.analyzers.dashboard import normalize_grafana_dashboard

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "sample_grafana_dashboard.json"
)


def test_normalize_sample_dashboard_extracts_panels_and_variables() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    normalized = normalize_grafana_dashboard(payload)

    assert normalized.grafana_uid == "api-overview"
    assert normalized.title == "API Overview"
    assert normalized.folder == "Observability"
    assert normalized.url == "/d/api-overview/api-overview"
    assert len(normalized.json_hash) == 64

    # Row itself is skipped; nested panels are extracted.
    assert [panel.grafana_panel_id for panel in normalized.panels] == [2, 3, 4]
    assert {panel.panel_type for panel in normalized.panels} == {
        "timeseries",
        "stat",
        "logs",
    }

    success = next(panel for panel in normalized.panels if panel.grafana_panel_id == 3)
    assert success.title == "Success Rate"
    assert success.datasource_uid == "prom-uid"
    assert len(success.queries) == 1
    assert success.queries[0].query_language == "promql"
    assert "http_requests_total" in success.queries[0].raw_query

    logs = next(panel for panel in normalized.panels if panel.grafana_panel_id == 4)
    assert logs.queries[0].query_language == "logql"

    assert [variable.name for variable in normalized.variables] == [
        "service",
        "environment",
    ]
    service = normalized.variables[0]
    assert service.multi is True
    assert service.include_all is True
    assert service.current_value == "payment-api"
    assert "label_values" in (service.query or "")


def test_normalize_bare_dashboard_json() -> None:
    payload = {
        "uid": "bare-dash",
        "title": "Bare",
        "panels": [
            {
                "id": 10,
                "title": "Total",
                "type": "gauge",
                "datasource": "prom-uid",
                "targets": [{"refId": "A", "expr": "up"}],
            }
        ],
        "templating": {"list": []},
    }
    normalized = normalize_grafana_dashboard(payload)
    assert normalized.grafana_uid == "bare-dash"
    assert len(normalized.panels) == 1
    assert normalized.panels[0].datasource_uid == "prom-uid"
