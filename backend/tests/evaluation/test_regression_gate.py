"""Release-gate aggregation for false positives/negatives and category coverage."""

from __future__ import annotations

from typing import Any

import pytest

from app.analyzers.query import analyze_query
from app.services.dashboard_analysis import analyze_grafana_payload
from tests.evaluation.harness import (
    CaseResult,
    evaluate_findings,
    load_json,
    parse_expectations,
    run_validation_case,
    summarize_results,
)

REQUIRED_CATEGORIES = {
    "correctness",
    "filter_correctness",
    "query_validity",
}


@pytest.mark.asyncio
async def test_release_gate_zero_fp_fn() -> None:
    validation_cases = list(load_json("validation_cases.json"))
    dashboard_cases = list(load_json("dashboard_cases.json"))

    results: list[CaseResult] = []
    categories: set[str] = set()

    for case in validation_cases:
        categories.add(str(case.get("category", "correctness")))
        results.append(await run_validation_case(case))

    for case in dashboard_cases:
        categories.add(str(case.get("category", "filter_correctness")))
        if case["id"] == "query_structure_valid":
            query = case["dashboard"]["panels"][0]["targets"][0]["expr"]
            analyzed = analyze_query(
                raw_query=query,
                panel_id=1,
                panel_title="Requests",
            )
            ok = all(
                metric in analyzed.referenced_metrics
                for metric in case.get("expected_metrics") or []
            )
            result = CaseResult(
                case_id=str(case["id"]),
                category=str(case.get("category", "query_validity")),
            )
            if not ok:
                result.false_negatives.append("query_structure")
            results.append(result)
            continue

        report = analyze_grafana_payload(
            case["dashboard"],
            label_cardinality=case.get("label_cardinality"),
        )
        findings: list[dict[str, Any]] = [item.model_dump() for item in report.findings]
        if report.filter_intelligence is not None:
            findings.extend(report.filter_intelligence.findings)
        results.append(
            evaluate_findings(
                case_id=str(case["id"]),
                category=str(case.get("category", "filter_correctness")),
                findings=findings,
                expected=parse_expectations(case.get("expected_findings")),
                forbidden=parse_expectations(case.get("forbidden_findings")),
            )
        )

    summary = summarize_results(results)
    assert REQUIRED_CATEGORIES.issubset(categories)
    assert summary["false_negatives"] == 0, summary
    assert summary["false_positives"] == 0, summary
    assert summary["failed"] == 0, summary


def test_golden_dataset_covers_doc_categories() -> None:
    """Ensure the dataset includes the critical Phase 9 evaluation themes."""
    validation_ids = {case["id"] for case in load_json("validation_cases.json")}
    dashboard_ids = {case["id"] for case in load_json("dashboard_cases.json")}

    required = {
        "correct_success_rate",
        "wrong_denominator",
        "wrong_numerator",
        "error_definition_required",
        "5xx_only_error_definition",
        "mismatched_time_ranges",
        "mismatched_service_filters",
        "counter_without_rate",
        "bad_p95_aggregation",
        "missing_telemetry",
        "unknown_metric_semantics",
        "unused_dashboard_variable",
        "high_cardinality_filter",
        "duplicate_query",
    }
    assert required.issubset(validation_ids | dashboard_ids)
