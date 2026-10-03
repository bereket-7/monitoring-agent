"""Golden tests for deterministic validation rules."""

from __future__ import annotations

import pytest

from app.schemas.validation import (
    MetricObservation,
    MetricSemantics,
    TimeRange,
    ValidationContext,
    ValidationFinding,
)
from app.validators import ValidationEngine


def _ctx(
    *,
    success: float | None = 97.0,
    error: float | None = 3.0,
    total: float | None = 100.0,
    success_filters: dict[str, str] | None = None,
    error_filters: dict[str, str] | None = None,
    total_filters: dict[str, str] | None = None,
    success_window: str | None = "5m",
    error_window: str | None = "5m",
    total_window: str | None = "5m",
    semantics: MetricSemantics | None = None,
    reported_success_rate: float | None = None,
    reported_error_rate: float | None = None,
    extra: list[MetricObservation] | None = None,
    tolerance: float = 0.02,
) -> ValidationContext:
    default_filters = {"service": "payment-api", "environment": "production"}
    observations = [
        MetricObservation(
            name="success",
            role="success",
            value=success,
            query='sum(rate(http_requests_total{status=~"2..|3.."}[5m]))',
            time_range=TimeRange(window=success_window),
            filters=success_filters or default_filters,
            metric_type="counter",
        ),
        MetricObservation(
            name="error",
            role="error",
            value=error,
            query='sum(rate(http_requests_total{status=~"5.."}[5m]))',
            time_range=TimeRange(window=error_window),
            filters=error_filters or default_filters,
            metric_type="counter",
        ),
        MetricObservation(
            name="total",
            role="total",
            value=total,
            query="sum(rate(http_requests_total[5m]))",
            time_range=TimeRange(window=total_window),
            filters=total_filters or default_filters,
            metric_type="counter",
        ),
    ]
    if extra:
        observations.extend(extra)
    return ValidationContext(
        observations=observations,
        semantics=semantics
        or MetricSemantics(
            success_definition="http_2xx_3xx",
            error_definition="http_5xx",
            total_definition="all_requests",
        ),
        consistency_tolerance=tolerance,
        reported_success_rate=reported_success_rate,
        reported_error_rate=reported_error_rate,
    )


def _has(
    findings: list[ValidationFinding],
    rule_id: str,
    severity: str | None = None,
) -> bool:
    for item in findings:
        if item.rule_id != rule_id:
            continue
        if severity is None or item.severity == severity:
            return True
    return False


@pytest.mark.asyncio
async def test_correct_success_and_error_rates() -> None:
    engine = ValidationEngine()
    context = _ctx(reported_success_rate=97.0, reported_error_rate=3.0)
    findings = await engine.run(context)
    assert _has(findings, "SR-001", "info")
    assert _has(findings, "ER-001", "info")
    assert _has(findings, "CONS-001", "info")


@pytest.mark.asyncio
async def test_wrong_denominator_scope() -> None:
    engine = ValidationEngine()
    context = _ctx(
        total_filters={"service": "checkout-api", "environment": "production"},
        reported_success_rate=97.0,
    )
    findings = await engine.run_rule("SR-001", context)
    assert _has(findings, "SR-001", "error")
    assert "scope mismatch" in findings[0].title.lower()


@pytest.mark.asyncio
async def test_wrong_numerator_missing_success() -> None:
    engine = ValidationEngine()
    context = ValidationContext(
        observations=[
            MetricObservation(
                name="total",
                role="total",
                value=100,
                query="sum(rate(http_requests_total[5m]))",
                filters={"service": "payment-api"},
            )
        ],
        semantics=MetricSemantics(success_definition="http_2xx_3xx"),
    )
    findings = await engine.run_rule("SR-001", context)
    assert _has(findings, "SR-001", "error")


@pytest.mark.asyncio
async def test_error_definition_must_be_configured() -> None:
    engine = ValidationEngine()
    context = _ctx(
        semantics=MetricSemantics(
            success_definition="http_2xx_3xx",
            error_definition=None,
            total_definition="all_requests",
        )
    )
    findings = await engine.run_rule("ER-001", context)
    assert _has(findings, "ER-001", "error")
    assert "not configured" in findings[0].title.lower()


@pytest.mark.asyncio
async def test_5xx_only_error_definition_can_pass() -> None:
    engine = ValidationEngine()
    context = _ctx(
        semantics=MetricSemantics(
            success_definition="http_2xx_3xx",
            error_definition="http_5xx",
            total_definition="all_requests",
        ),
        reported_error_rate=3.0,
    )
    findings = await engine.run_rule("ER-001", context)
    assert _has(findings, "ER-001", "info")


@pytest.mark.asyncio
async def test_mismatched_time_ranges() -> None:
    engine = ValidationEngine()
    context = _ctx(success_window="5m", total_window="1h")
    findings = await engine.run_rule("CONS-002", context)
    assert _has(findings, "CONS-002", "error")


@pytest.mark.asyncio
async def test_mismatched_service_filters() -> None:
    engine = ValidationEngine()
    context = _ctx(
        success_filters={"service": "payment-api"},
        total_filters={"service": "checkout-api"},
    )
    findings = await engine.run_rule("CONS-003", context)
    assert _has(findings, "CONS-003", "error")


@pytest.mark.asyncio
async def test_counter_without_rate() -> None:
    engine = ValidationEngine()
    context = ValidationContext(
        observations=[
            MetricObservation(
                name="raw_counter",
                role="total",
                value=10,
                query="http_requests_total",
                metric_type="counter",
            )
        ]
    )
    findings = await engine.run_rule("RATE-001", context)
    assert _has(findings, "RATE-001", "error")


@pytest.mark.asyncio
async def test_bad_p95_aggregation() -> None:
    engine = ValidationEngine()
    context = ValidationContext(
        observations=[
            MetricObservation(
                name="latency_p95",
                role="latency",
                value=0.2,
                query="avg(histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])))",
                metric_type="histogram",
            )
        ]
    )
    findings = await engine.run_rule("LAT-001", context)
    assert _has(findings, "LAT-001", "error")


@pytest.mark.asyncio
async def test_missing_telemetry_not_zero() -> None:
    engine = ValidationEngine()
    context = _ctx(success=None, total=100.0)
    findings = await engine.run_rule("SR-001", context)
    assert _has(findings, "SR-001", "error")
    assert "missing telemetry" in findings[0].title.lower()


@pytest.mark.asyncio
async def test_unknown_success_semantics_warning() -> None:
    engine = ValidationEngine()
    context = _ctx(
        semantics=MetricSemantics(
            success_definition=None,
            error_definition="http_5xx",
            total_definition="all_requests",
        ),
        reported_success_rate=97.0,
    )
    findings = await engine.run_rule("SR-001", context)
    assert _has(findings, "SR-001", "warning")


@pytest.mark.asyncio
async def test_total_consistency_failure() -> None:
    engine = ValidationEngine()
    context = _ctx(success=80.0, error=5.0, total=100.0, tolerance=0.02)
    findings = await engine.run_rule("CONS-001", context)
    assert _has(findings, "CONS-001", "error")


@pytest.mark.asyncio
async def test_division_by_zero() -> None:
    engine = ValidationEngine()
    context = _ctx(success=0.0, total=0.0, reported_success_rate=0.0)
    findings = await engine.run_rule("SR-001", context)
    assert _has(findings, "SR-001", "error")
    assert "division by zero" in findings[0].title.lower()
