# Metric Semantics

This is one of the most important documents in the project.

## Principle

Never assume that a metric named `success`, `error`, or `requests` has universal semantics.

Definitions must come from:

1. explicit metric registry
2. service documentation
3. query semantics
4. verified telemetry conventions

If semantics cannot be established, report uncertainty.

## Canonical HTTP definitions

These are defaults only and must be configurable.

### Total

```text
all requests included by the selected scope
```

### Success

Default:

```text
HTTP status 200-399
```

### Client error

```text
HTTP status 400-499
```

### Server error

```text
HTTP status 500-599
```

### Error

Must be configured. Possible definition:

```text
status >= 400
```

Do not silently choose another definition.

## Success rate

```text
successful / total * 100
```

The numerator and denominator must use compatible:

- time range
- filters
- service
- endpoint
- method
- environment
- aggregation semantics

## Error rate

```text
errors / total * 100
```

Again, numerator and denominator must have equivalent scope.

## Consistency checks

For compatible definitions:

```text
success + error ≈ total
```

Use tolerance because telemetry can contain:

- dropped samples
- retries
- asynchronous events
- distinct event streams
- scrape gaps

Tolerance must be configurable and findings must explain it.

## Latency

Do not calculate p95 by averaging p95 values across instances.

Prefer histogram/summary-aware PromQL patterns and preserve correct aggregation semantics.

## Rates

Counters should normally use `rate()` or `increase()` over an appropriate window.

Detect likely misuse such as applying `rate()` to gauges.
