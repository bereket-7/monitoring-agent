# Filter Intelligence

## Goal

Make Grafana filtering predictable and consistent.

## Candidate filters

Discover candidate labels from:

- Prometheus metadata
- actual dashboard queries
- metric registry
- service metadata

Potential filters:

```text
environment
service
namespace
region
cluster
method
endpoint
status_code
```

## Do not blindly expose all labels

High-cardinality labels can create:

- expensive queries
- unusable dropdowns
- excessive API requests
- poor dashboard performance

The engine should estimate cardinality and classify labels:

```text
safe
review
avoid
```

This is a technical classification, not a user preference ranking.

## Filter propagation

For each dashboard variable:

1. Find all relevant panels.
2. Inspect query references.
3. Determine whether the variable changes query scope.
4. Report panels that do not use the variable.

Example:

```text
service=payment-api

Panel A  ✓
Panel B  ✓
Panel C  ✗
Panel D  ✓
```

## Multi-value variables

Ensure query generation handles:

```text
single value
multiple values
all values
empty value
```

without generating invalid or overly broad queries.

## Filter contract

A filter should document:

- variable name
- label
- source
- allowed values
- cardinality
- affected panels
- query syntax
- all-value behavior
