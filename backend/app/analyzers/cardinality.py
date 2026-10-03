"""Label cardinality classification (safe / review / avoid)."""

from __future__ import annotations

from app.schemas.filters import CardinalityClass

# Technical defaults when live cardinality is unavailable.
_HEURISTIC_CARDINALITY: dict[str, int] = {
    "environment": 5,
    "env": 5,
    "service": 40,
    "namespace": 30,
    "region": 10,
    "cluster": 15,
    "method": 10,
    "status_code": 40,
    "status": 40,
    "endpoint": 200,
    "handler": 200,
    "path": 500,
    "instance": 2000,
    "pod": 5000,
    "container": 3000,
    "node": 800,
    "request_id": 100000,
    "trace_id": 100000,
    "user_id": 50000,
    "userid": 50000,
    "ip": 20000,
}

SAFE_MAX = 50
REVIEW_MAX = 500


def estimate_cardinality(label: str, observed: int | None = None) -> int | None:
    """Return observed cardinality when provided, else a heuristic estimate."""
    if observed is not None:
        return observed
    return _HEURISTIC_CARDINALITY.get(label.lower())


def classify_cardinality(cardinality: int | None) -> CardinalityClass:
    """Classify label cardinality for filter safety."""
    if cardinality is None:
        return "review"
    if cardinality <= SAFE_MAX:
        return "safe"
    if cardinality <= REVIEW_MAX:
        return "review"
    return "avoid"
