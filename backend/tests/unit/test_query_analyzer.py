"""Unit tests for PromQL/LogQL query analysis."""

from __future__ import annotations

from app.analyzers.query import analyze_query, hash_query, normalize_query, static_query_findings


def test_normalize_and_hash_are_stable() -> None:
    raw = "  sum(  rate( http_requests_total{service=\"api\"} [5m] ) ) "
    normalized = normalize_query(raw)
    assert normalized == 'sum(rate(http_requests_total{service="api"}[5m]))'
    assert hash_query(normalized) == hash_query(normalize_query(normalized))


def test_analyze_query_extracts_structure() -> None:
    analyzed = analyze_query(
        raw_query=(
            'sum(rate(http_requests_total{service=~"$service", environment="$environment"}[5m]))'
        ),
        panel_id=2,
        panel_title="Request Count",
        ref_id="A",
        query_language="promql",
    )
    assert analyzed.referenced_metrics == ["http_requests_total"]
    assert analyzed.referenced_labels == ["environment", "service"]
    assert analyzed.referenced_variables == ["environment", "service"]
    assert "rate" in analyzed.functions
    assert "sum" in analyzed.functions
    assert analyzed.range_vectors == ["[5m]"]
    assert analyzed.has_regex_selector is True
    assert len(analyzed.query_hash) == 64


def test_static_findings_for_counter_without_rate() -> None:
    analyzed = analyze_query(
        raw_query="http_requests_total{service=\"api\"}",
        panel_id=1,
        panel_title="Raw",
        query_language="promql",
    )
    findings = static_query_findings(analyzed)
    assert any(item.rule_id == "QUERY-003" for item in findings)


def test_static_findings_for_avg_quantile() -> None:
    analyzed = analyze_query(
        raw_query="avg(histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])))",
        panel_id=1,
        panel_title="p95",
        query_language="promql",
    )
    findings = static_query_findings(analyzed)
    assert any(item.rule_id == "QUERY-004" for item in findings)
