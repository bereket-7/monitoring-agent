"""Validator protocol and shared helpers."""

from __future__ import annotations

from typing import Protocol

from app.schemas.validation import (
    MetricObservation,
    MetricRole,
    ValidationContext,
    ValidationFinding,
)


class Validator(Protocol):
    rule_id: str

    async def validate(self, context: ValidationContext) -> list[ValidationFinding]:
        """Run a deterministic validation rule."""


def observations_by_role(
    context: ValidationContext,
    role: MetricRole,
) -> list[MetricObservation]:
    return [item for item in context.observations if item.role == role]


def first_by_role(
    context: ValidationContext,
    role: MetricRole,
) -> MetricObservation | None:
    items = observations_by_role(context, role)
    return items[0] if items else None


def evidence_from_observation(observation: MetricObservation) -> dict[str, object]:
    return {
        "name": observation.name,
        "role": observation.role,
        "value": observation.value,
        "query": observation.query,
        "filters": observation.filters,
        "time_range": (
            observation.time_range.model_dump() if observation.time_range else None
        ),
        "metric_type": observation.metric_type,
    }


def scopes_compatible(left: MetricObservation, right: MetricObservation) -> bool:
    return left.filters == right.filters and _time_ranges_equal(
        left.time_range, right.time_range
    )


def _time_ranges_equal(
    left: object,
    right: object,
) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return bool(left == right)
