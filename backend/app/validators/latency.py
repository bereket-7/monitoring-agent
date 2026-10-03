"""LAT-001 latency quantile aggregation validator."""

from __future__ import annotations

import re

from app.schemas.validation import ValidationContext, ValidationFinding
from app.validators.base import evidence_from_observation

_AVG_OF_QUANTILE = re.compile(
    r"avg\s*\(\s*(?:histogram_quantile|quantile)\s*\(",
    re.IGNORECASE,
)
_AVG_OF_NAMED_QUANTILE = re.compile(
    r"avg\s*\(\s*[^)]*(?:p95|p99|p90|p50)[^)]*\)",
    re.IGNORECASE,
)


class LatencyAggregationValidator:
    rule_id = "LAT-001"

    async def validate(self, context: ValidationContext) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for observation in context.observations:
            query = observation.query
            suspicious = bool(
                _AVG_OF_QUANTILE.search(query) or _AVG_OF_NAMED_QUANTILE.search(query)
            )
            if not suspicious:
                continue

            severity = "error" if observation.role == "latency" else "warning"
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity=severity,  # type: ignore[arg-type]
                    category="latency",
                    title="Suspicious quantile aggregation",
                    description=(
                        "Query appears to average quantiles (for example "
                        "avg(histogram_quantile(...)) or avg of p95 values), "
                        "which is statistically incorrect."
                    ),
                    observed_value=query,
                    expected_value=(
                        "histogram_quantile over aggregated buckets, "
                        "or summary-aware aggregation"
                    ),
                    evidence=[evidence_from_observation(observation)],
                    recommendation=(
                        "Aggregate histogram buckets first, then compute quantiles. "
                        "Do not average p95/p99 values across instances."
                    ),
                )
            )
        return findings
