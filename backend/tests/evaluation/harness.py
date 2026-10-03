"""Shared evaluation harness for Phase 9 golden regression."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.schemas.validation import (
    MetricObservation,
    MetricSemantics,
    TimeRange,
    ValidationContext,
    ValidationFinding,
)
from app.validators import ValidationEngine

DATASET_DIR = Path(__file__).resolve().parent / "dataset"


@dataclass(slots=True)
class FindingExpectation:
    rule_id: str
    severity: str | None = None


@dataclass(slots=True)
class CaseResult:
    case_id: str
    category: str
    false_negatives: list[str] = field(default_factory=list)
    false_positives: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.false_negatives and not self.false_positives


def load_json(name: str) -> Any:
    path = DATASET_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def finding_matches(finding: ValidationFinding | dict[str, Any], expected: FindingExpectation) -> bool:
    rule_id = finding.rule_id if isinstance(finding, ValidationFinding) else str(finding.get("rule_id"))
    severity = finding.severity if isinstance(finding, ValidationFinding) else str(finding.get("severity"))
    if rule_id != expected.rule_id:
        return False
    if expected.severity is None:
        return True
    return severity == expected.severity


def evaluate_findings(
    *,
    case_id: str,
    category: str,
    findings: list[ValidationFinding] | list[dict[str, Any]],
    expected: list[FindingExpectation],
    forbidden: list[FindingExpectation],
) -> CaseResult:
    result = CaseResult(case_id=case_id, category=category)
    for item in expected:
        if not any(finding_matches(finding, item) for finding in findings):
            label = f"{item.rule_id}:{item.severity or '*'}"
            result.false_negatives.append(label)
    for item in forbidden:
        if any(finding_matches(finding, item) for finding in findings):
            label = f"{item.rule_id}:{item.severity or '*'}"
            result.false_positives.append(label)
    return result


def parse_expectations(raw: list[dict[str, Any]] | None) -> list[FindingExpectation]:
    return [
        FindingExpectation(
            rule_id=str(item["rule_id"]),
            severity=str(item["severity"]) if item.get("severity") is not None else None,
        )
        for item in (raw or [])
    ]


def context_from_case(case: dict[str, Any]) -> ValidationContext:
    payload = case["validation"]
    observations: list[MetricObservation] = []
    for item in payload.get("observations") or []:
        time_range = None
        if item.get("time_range") is not None:
            time_range = TimeRange.model_validate(item["time_range"])
        observations.append(MetricObservation.model_validate({**item, "time_range": time_range}))

    semantics_raw = payload.get("semantics") or {}
    return ValidationContext(
        dashboard_uid=payload.get("dashboard_uid"),
        panel_id=payload.get("panel_id"),
        observations=observations,
        semantics=MetricSemantics.model_validate(semantics_raw),
        consistency_tolerance=float(payload.get("consistency_tolerance", 0.02)),
        reported_success_rate=payload.get("reported_success_rate"),
        reported_error_rate=payload.get("reported_error_rate"),
    )


async def run_validation_case(case: dict[str, Any]) -> CaseResult:
    engine = ValidationEngine()
    context = context_from_case(case)
    rule_id = case.get("rule_id")
    if rule_id:
        findings = await engine.run_rule(str(rule_id), context)
    else:
        findings = await engine.run(context)

    result = evaluate_findings(
        case_id=str(case["id"]),
        category=str(case.get("category", "correctness")),
        findings=findings,
        expected=parse_expectations(case.get("expected_findings")),
        forbidden=parse_expectations(case.get("forbidden_findings")),
    )

    required_evidence = case.get("required_evidence") or []
    if required_evidence:
        evidence_blob = json.dumps([finding.model_dump() for finding in findings], default=str)
        for token in required_evidence:
            if token not in evidence_blob:
                result.notes.append(f"missing_required_evidence:{token}")
                result.false_negatives.append(f"evidence:{token}")
    return result


def summarize_results(results: list[CaseResult]) -> dict[str, Any]:
    total = len(results)
    fn = sum(len(item.false_negatives) for item in results)
    fp = sum(len(item.false_positives) for item in results)
    passed = sum(1 for item in results if item.passed)
    return {
        "cases": total,
        "passed": passed,
        "failed": total - passed,
        "false_negatives": fn,
        "false_positives": fp,
        "false_negative_rate": (fn / total) if total else 0.0,
        "false_positive_rate": (fp / total) if total else 0.0,
    }
