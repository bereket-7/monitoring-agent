"""ER-001 error rate validator."""

from __future__ import annotations

from app.schemas.validation import ValidationContext, ValidationFinding
from app.validators.base import evidence_from_observation, first_by_role, scopes_compatible


class ErrorRateValidator:
    rule_id = "ER-001"

    async def validate(self, context: ValidationContext) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        error = first_by_role(context, "error")
        total = first_by_role(context, "total")

        if error is None or total is None:
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="error_rate",
                    title="Error rate inputs missing",
                    description=(
                        "Error rate validation requires both error and total observations."
                    ),
                    observed_value={
                        "error_present": error is not None,
                        "total_present": total is not None,
                    },
                    expected_value={"error_present": True, "total_present": True},
                    evidence=[],
                    recommendation="Provide error and total metric observations with compatible scope.",
                )
            )
            return findings

        evidence = [evidence_from_observation(error), evidence_from_observation(total)]

        if context.semantics.error_definition is None:
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="error_rate",
                    title="Error metric semantics not configured",
                    description=(
                        "Error definition must be configured explicitly "
                        "(for example status>=400 or 5xx-only). "
                        "The validator will not silently choose a definition."
                    ),
                    observed_value=None,
                    expected_value="configured error_definition",
                    evidence=evidence,
                    recommendation="Set error semantics in the metric registry before validating error rate.",
                )
            )
            return findings

        if error.value is None or total.value is None:
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="error_rate",
                    title="Missing telemetry for error rate",
                    description=(
                        "Error or total value is missing. Missing telemetry must not "
                        "be treated as zero."
                    ),
                    observed_value={"error": error.value, "total": total.value},
                    expected_value="numeric error and total values",
                    evidence=evidence,
                    recommendation="Investigate missing series before computing error rate.",
                )
            )
            return findings

        if not scopes_compatible(error, total):
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="error_rate",
                    title="Error rate scope mismatch",
                    description=(
                        "Error and total observations do not share compatible filters "
                        "and time range."
                    ),
                    observed_value={
                        "error_filters": error.filters,
                        "total_filters": total.filters,
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
                    category="error_rate",
                    title="Error rate division by zero",
                    description="Total requests is zero; error rate is undefined.",
                    observed_value={"error": error.value, "total": total.value},
                    expected_value="total > 0",
                    evidence=evidence,
                    recommendation="Avoid rendering an error rate when the denominator is zero.",
                )
            )
            return findings

        computed = (error.value / total.value) * 100.0
        if context.reported_error_rate is not None:
            if abs(computed - context.reported_error_rate) > 0.05:
                findings.append(
                    ValidationFinding(
                        rule_id=self.rule_id,
                        severity="error",
                        category="error_rate",
                        title="Reported error rate does not match formula",
                        description="Reported error rate differs from error/total*100.",
                        observed_value=context.reported_error_rate,
                        expected_value=computed,
                        evidence=evidence,
                        recommendation="Recalculate the panel using error/total*100 with matched scope.",
                    )
                )
                return findings

        findings.append(
            ValidationFinding(
                rule_id=self.rule_id,
                severity="info",
                category="error_rate",
                title="Error rate formula valid",
                description="Error rate can be computed as error/total*100 with compatible scope.",
                observed_value=computed,
                expected_value=computed,
                evidence=evidence,
                recommendation="No change required for formula correctness.",
            )
        )
        return findings
