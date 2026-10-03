"""RATE-001 counter rate validator."""

from __future__ import annotations

import re

from app.schemas.validation import ValidationContext, ValidationFinding
from app.validators.base import evidence_from_observation

_RATE_FN = re.compile(r"\b(?:rate|increase)\s*\(", re.IGNORECASE)


class CounterRateValidator:
    rule_id = "RATE-001"

    async def validate(self, context: ValidationContext) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for observation in context.observations:
            if observation.metric_type != "counter":
                continue
            if _RATE_FN.search(observation.query):
                continue
            findings.append(
                ValidationFinding(
                    rule_id=self.rule_id,
                    severity="error",
                    category="rate",
                    title="Counter used without rate/increase",
                    description=(
                        f"Observation '{observation.name}' is typed as a counter but the "
                        "query does not use rate() or increase()."
                    ),
                    observed_value=observation.query,
                    expected_value="rate(...[window]) or increase(...[window]) over a counter",
                    evidence=[evidence_from_observation(observation)],
                    recommendation=(
                        "Wrap counters with rate() or increase() over an appropriate window."
                    ),
                )
            )
        return findings
