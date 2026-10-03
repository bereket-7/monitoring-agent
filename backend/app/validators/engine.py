"""Deterministic validation engine orchestration."""

from __future__ import annotations

from app.schemas.validation import ValidationContext, ValidationFinding
from app.validators.base import Validator
from app.validators.consistency import (
    FilterConsistencyValidator,
    TimeWindowConsistencyValidator,
    TotalConsistencyValidator,
)
from app.validators.error_rate import ErrorRateValidator
from app.validators.latency import LatencyAggregationValidator
from app.validators.rate import CounterRateValidator
from app.validators.success_rate import SuccessRateValidator


def default_validators() -> list[Validator]:
    return [
        SuccessRateValidator(),
        ErrorRateValidator(),
        TotalConsistencyValidator(),
        TimeWindowConsistencyValidator(),
        FilterConsistencyValidator(),
        LatencyAggregationValidator(),
        CounterRateValidator(),
    ]


class ValidationEngine:
    """Run deterministic validators with no LLM dependency."""

    def __init__(self, validators: list[Validator] | None = None) -> None:
        self._validators = validators if validators is not None else default_validators()

    async def run(self, context: ValidationContext) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for validator in self._validators:
            findings.extend(await validator.validate(context))
        return findings

    async def run_rule(
        self,
        rule_id: str,
        context: ValidationContext,
    ) -> list[ValidationFinding]:
        for validator in self._validators:
            if validator.rule_id == rule_id:
                return await validator.validate(context)
        raise KeyError(f"Unknown validation rule: {rule_id}")
