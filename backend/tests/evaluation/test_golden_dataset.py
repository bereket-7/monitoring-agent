"""Parametrized golden dataset tests for validators, filters, and queries."""

from __future__ import annotations

from typing import Any

import pytest

from app.analyzers.dashboard import normalize_grafana_dashboard
from app.analyzers.filters import analyze_filters
from app.analyzers.query import analyze_query
from app.services.dashboard_analysis import analyze_grafana_payload
from tests.evaluation.harness import (
    evaluate_findings,
    load_json,
    parse_expectations,
    run_validation_case,
    summarize_results,
)


def _load_validation_cases() -> list[dict[str, Any]]:
    return list(load_json("validation_cases.json"))


def _load_dashboard_cases() -> list[dict[str, Any]]:
    return list(load_json("dashboard_cases.json"))


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _load_validation_cases(), ids=lambda c: c["id"])
async def test_validation_golden_case(case: dict[str, Any]) -> None:
    result = await run_validation_case(case)
    assert result.passed, (
        f"{case['id']} failed FN={result.false_negatives} FP={result.false_positives} "
        f"notes={result.notes}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _load_dashboard_cases(), ids=lambda c: c["id"])
async def test_dashboard_golden_case(case: dict[str, Any]) -> None:
    payload = case["dashboard"]
    label_cardinality = case.get("label_cardinality")

    if case["id"] == "query_structure_valid":
        query = payload["panels"][0]["targets"][0]["expr"]
        analyzed = analyze_query(
            raw_query=query,
            panel_id=1,
            panel_title="Requests",
            query_language="promql",
        )
        for metric in case.get("expected_metrics") or []:
            assert metric in analyzed.referenced_metrics
        for label in case.get("expected_labels") or []:
            assert label in analyzed.referenced_labels
        for function in case.get("expected_functions") or []:
            assert function in analyzed.functions
        return

    report = analyze_grafana_payload(payload, label_cardinality=label_cardinality)
    findings = [item.model_dump() for item in report.findings]

    if report.filter_intelligence is not None:
        findings.extend(report.filter_intelligence.findings)

    result = evaluate_findings(
        case_id=str(case["id"]),
        category=str(case.get("category", "filter_correctness")),
        findings=findings,
        expected=parse_expectations(case.get("expected_findings")),
        forbidden=parse_expectations(case.get("forbidden_findings")),
    )

    for name in case.get("expected_dead_variables") or []:
        dead = (
            report.filter_intelligence.dead_variables if report.filter_intelligence else []
        )
        assert name in dead

    for name in case.get("expected_partial_variables") or []:
        partial = (
            report.filter_intelligence.partially_propagated
            if report.filter_intelligence
            else []
        )
        assert name in partial

    expected_card = case.get("expected_cardinality_class") or {}
    if expected_card and report.filter_intelligence is not None:
        by_label: dict[str, str] = {}
        for contract in report.filter_intelligence.contracts:
            if contract.label:
                by_label[contract.label] = contract.cardinality_class
        for candidate in report.filter_intelligence.candidates:
            by_label.setdefault(candidate.label, candidate.cardinality_class)
        for label, expected_class in expected_card.items():
            assert by_label.get(label) == expected_class

    assert result.passed, (
        f"{case['id']} failed FN={result.false_negatives} FP={result.false_positives}"
    )


@pytest.mark.asyncio
async def test_validation_dataset_regression_summary() -> None:
    results = [await run_validation_case(case) for case in _load_validation_cases()]
    summary = summarize_results(results)
    assert summary["false_negatives"] == 0
    assert summary["false_positives"] == 0
    assert summary["passed"] == summary["cases"]


def test_filter_analyzer_matches_dashboard_analysis() -> None:
    """Correctness: filter analyzer and report wiring agree on dead variables."""
    case = next(c for c in _load_dashboard_cases() if c["id"] == "unused_dashboard_variable")
    normalized = normalize_grafana_dashboard(case["dashboard"])
    filter_report = analyze_filters(normalized)
    analysis = analyze_grafana_payload(case["dashboard"])
    assert analysis.filter_intelligence is not None
    assert filter_report.dead_variables == analysis.filter_intelligence.dead_variables
    assert "unused" in filter_report.dead_variables
