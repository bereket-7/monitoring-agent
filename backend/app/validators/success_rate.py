"""SR-001 success rate validator."""

from __future__ import annotations

from app.schemas.validation import ValidationContext, ValidationFinding
from app.validators.base import evidence_from_observation, first_by_role, scopes_compatible


class SuccessRateValidator:
    rule_id = "SR-001"

    async def validate(self, context: ValidationContext) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        success = first_by_role(context, "success")
        total = first_by_role(context, "total")

        if success is None or total is None:
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="success_rate",
                    title="Success rate inputs missing",
                    description=(
                        "Success rate validation requires both success and total "
                        "observations. One or both were not provided."
                    ),
                    observed_value={
                        "success_present": success is not None,
                        "total_present": total is not None,
                    },
                    expected_value={"success_present": True, "total_present": True},
                    evidence=[],
                    recommendation=(
                        "Provide success and total metric observations with compatible scope."
                    ),
                )
            )
            return findings

        evidence = [
            evidence_from_observation(success),
            evidence_from_observation(total),
        ]

        if context.semantics.success_definition is None:
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="warning",
                    category="success_rate",
                    title="Success metric semantics unknown",
                    description=(
                        "Success semantics are not configured. The validator cannot "
                        "confirm the numerator means successful requests."
                    ),
                    observed_value=None,
                    expected_value="configured success_definition",
                    evidence=evidence,
                    recommendation=(
                        "Configure metric registry success semantics before treating "
                        "the rate as authoritative."
                    ),
                )
            )

        if success.value is None or total.value is None:
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="success_rate",
                    title="Missing telemetry for success rate",
                    description=(
                        "Success or total value is missing. Missing telemetry must not "
                        "be treated as zero."
                    ),
                    observed_value={"success": success.value, "total": total.value},
                    expected_value="numeric success and total values",
                    evidence=evidence,
                    recommendation="Investigate missing series/scrape gaps before computing rates.",
                )
            )
            return findings

        if not scopes_compatible(success, total):
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="success_rate",
                    title="Success rate scope mismatch",
                    description=(
                        "Success and total observations do not share compatible filters "
                        "and time range."
                    ),
                    observed_value={
                        "success_filters": success.filters,
                        "total_filters": total.filters,
                        "success_time_range": success.time_range,
                        "total_time_range": total.time_range,
                    },
                    expected_value="identical filters and time range",
                    evidence=evidence,
                    recommendation="Align numerator/denominator selectors and evaluation window.",
                )
            )
            return findings

        if total.value == 0:
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="success_rate",
                    title="Success rate division by zero",
                    description="Total requests is zero; success rate is undefined.",
                    observed_value={"success": success.value, "total": total.value},
                    expected_value="total > 0",
                    evidence=evidence,
                    recommendation="Avoid rendering a success rate when the denominator is zero.",
                )
            )
            return findings

        computed = (success.value / total.value) * 100.0
        if context.reported_success_rate is not None:
            delta = abs(computed - context.reported_success_rate)
            # Exact formula check uses a tight absolute epsilon for percentage points.
            if delta > 0.05:
                findings.append(
                    ValidationFinding(
                        rule_id=self.rule_id,
                        severity="error",
                        category="success_rate",
                        title="Reported success rate does not match formula",
                        description=(
                            "Reported success rate differs from success/total*100."
                        ),
                        observed_value=context.reported_success_rate,
                        expected_value=computed,
                        evidence=evidence,
                        recommendation="Recalculate the panel using success/total*100 with matched scope.",
                    )
                )
                return findings

        findings.append(
            ValidationFinding(
                rule_id=self.rule_id,
                severity="info",
                category="success_rate",
                title="Success rate formula valid",
                description="Success rate can be computed as success/total*100 with compatible scope.",
                observed_value=computed,
                expected_value=computed,
                evidence=evidence,
                recommendation="No change required for formula correctness.",
            )
        )
        return findings
