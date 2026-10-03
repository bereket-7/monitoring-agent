"""CONS-001/002/003 consistency validators."""

from __future__ import annotations

from app.schemas.validation import MetricObservation, ValidationContext, ValidationFinding
from app.validators.base import evidence_from_observation, first_by_role, scopes_compatible


class TotalConsistencyValidator:
    rule_id = "CONS-001"

    async def validate(self, context: ValidationContext) -> list[ValidationFinding]:
        success = first_by_role(context, "success")
        error = first_by_role(context, "error")
        total = first_by_role(context, "total")

        if success is None or error is None or total is None:
            return [
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="warning",
                    category="consistency",
                    title="Insufficient observations for total consistency",
                    description=(
                        "CONS-001 requires success, error, and total observations."
                    ),
                    observed_value=None,
                    expected_value="success, error, and total present",
                    evidence=[],
                    recommendation="Collect all three series before checking success+error≈total.",
                )
            ]

        evidence = [
            evidence_from_observation(success),
            evidence_from_observation(error),
            evidence_from_observation(total),
        ]

        if (
            context.semantics.success_definition is None
            or context.semantics.error_definition is None
            or context.semantics.total_definition is None
        ):
            return [
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="warning",
                    category="consistency",
                    title="Cannot verify total consistency without semantics",
                    description=(
                        "Success, error, and total semantics must all be configured "
                        "and compatible before checking success+error≈total."
                    ),
                    observed_value=context.semantics.model_dump(),
                    expected_value="configured success/error/total definitions",
                    evidence=evidence,
                    recommendation="Configure metric semantics for all three roles.",
                )
            ]

        if any(value is None for value in (success.value, error.value, total.value)):
            return [
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="consistency",
                    title="Missing telemetry for total consistency",
                    description=(
                        "One or more of success/error/total values are missing. "
                        "Missing telemetry is not treated as zero."
                    ),
                    observed_value={
                        "success": success.value,
                        "error": error.value,
                        "total": total.value,
                    },
                    expected_value="numeric success, error, and total",
                    evidence=evidence,
                    recommendation="Resolve missing series before consistency checks.",
                )
            ]

        assert success.value is not None
        assert error.value is not None
        assert total.value is not None

        if not (
            scopes_compatible(success, total)
            and scopes_compatible(error, total)
            and scopes_compatible(success, error)
        ):
            return [
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="consistency",
                    title="Incompatible scopes for total consistency",
                    description=(
                        "success+error≈total is only valid when all three share "
                        "compatible filters and time ranges."
                    ),
                    observed_value=None,
                    expected_value="matched scopes",
                    evidence=evidence,
                    recommendation="Align filters and windows across the three metrics.",
                )
            ]

        combined = success.value + error.value
        if total.value == 0:
            relative_delta = abs(combined - total.value)
            ok = relative_delta <= context.consistency_tolerance
        else:
            relative_delta = abs(combined - total.value) / abs(total.value)
            ok = relative_delta <= context.consistency_tolerance

        if not ok:
            return [
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="consistency",
                    title="Success + error not consistent with total",
                    description=(
                        f"success+error differs from total beyond tolerance "
                        f"{context.consistency_tolerance}."
                    ),
                    observed_value={
                        "success": success.value,
                        "error": error.value,
                        "sum": combined,
                        "total": total.value,
                        "relative_delta": relative_delta,
                        "tolerance": context.consistency_tolerance,
                    },
                    expected_value=f"|success+error-total|/|total| <= {context.consistency_tolerance}",
                    evidence=evidence,
                    recommendation=(
                        "Investigate dropped samples, definition mismatch, or scrape gaps."
                    ),
                )
            ]

        return [
            ValidationFinding(
                rule_id=self.rule_id,
                severity="info",
                category="consistency",
                title="Total consistency check passed",
                description="success+error is within configured tolerance of total.",
                observed_value={
                    "sum": combined,
                    "total": total.value,
                    "relative_delta": relative_delta,
                    "tolerance": context.consistency_tolerance,
                },
                expected_value=f"relative delta <= {context.consistency_tolerance}",
                evidence=evidence,
                recommendation="No change required for total consistency.",
            )
        ]


class TimeWindowConsistencyValidator:
    rule_id = "CONS-002"

    async def validate(self, context: ValidationContext) -> list[ValidationFinding]:
        related = _related_rate_observations(context)
        if len(related) < 2:
            return []

        baseline = related[0].time_range
        mismatched = [
            item for item in related[1:] if item.time_range != baseline
        ]
        if not mismatched:
            return []

        return [
            ValidationFinding(
                rule_id=self.rule_id,
                severity="error",
                category="consistency",
                title="Related metrics use different time windows",
                description=(
                    "Success/error/total observations do not share the same time range."
                ),
                observed_value={
                    item.name: item.time_range.model_dump() if item.time_range else None
                    for item in related
                },
                expected_value="identical time ranges",
                evidence=[evidence_from_observation(item) for item in related],
                recommendation="Evaluate related metrics over the same time window.",
            )
        ]


class FilterConsistencyValidator:
    rule_id = "CONS-003"

    async def validate(self, context: ValidationContext) -> list[ValidationFinding]:
        related = _related_rate_observations(context)
        if len(related) < 2:
            return []

        baseline = related[0].filters
        mismatched = [item for item in related[1:] if item.filters != baseline]
        if not mismatched:
            return []

        return [
            ValidationFinding(
                rule_id=self.rule_id,
                severity="error",
                category="consistency",
                title="Related metrics use different filters",
                description=(
                    "Success/error/total observations do not share the same filter scope."
                ),
                observed_value={item.name: item.filters for item in related},
                expected_value="identical filters",
                evidence=[evidence_from_observation(item) for item in related],
                recommendation="Align service/environment/endpoint filters across related metrics.",
            )
        ]


def _related_rate_observations(context: ValidationContext) -> list[MetricObservation]:
    roles = {"success", "error", "total"}
    return [item for item in context.observations if item.role in roles]
