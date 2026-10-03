# Deterministic Validation Engine

The validation engine is the source of truth for correctness.

## Interface

```python
class Validator(Protocol):
    rule_id: str

    async def validate(
        self,
        context: ValidationContext,
    ) -> list[ValidationFinding]:
        ...
```

## Rule categories

### SR-001 Success rate formula

Check:

- numerator exists
- denominator exists
- numerator is semantically success
- scopes match
- denominator is non-zero
- formula is mathematically valid

### ER-001 Error rate formula

Check analogous properties.

### CONS-001 Total consistency

Compare total vs success + error where definitions are compatible.

### CONS-002 Time-window consistency

Detect different ranges in related metrics.

### CONS-003 Filter consistency

Detect mismatched filters between numerator and denominator.

### LAT-001 Quantile aggregation

Detect suspicious p95/p99 aggregation patterns.

### RATE-001 Counter rate

Detect likely counter calculations without rate/increase.

### FILTER-001 Variable propagation

Check dashboard variable usage.

### FILTER-002 Dead variable

Detect variables that do not affect any relevant query.

### QUERY-001 Duplicate query

Detect identical normalized query hashes.

## Finding structure

```python
ValidationFinding(
    rule_id="SR-001",
    severity="error",
    title="Success rate denominator mismatch",
    description="...",
    observed_value=...,
    expected_value=...,
    evidence=[...],
    recommendation="..."
)
```

## Rule implementation requirements

- deterministic
- unit tested
- no LLM dependency
- versioned
- explainable
- safe when data is missing
- never invent data
