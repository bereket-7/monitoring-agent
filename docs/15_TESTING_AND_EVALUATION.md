# Testing and Evaluation

## Testing layers

### Unit tests

Test:

- metric formulas
- consistency rules
- query parsing
- filter propagation
- dashboard normalization
- cardinality classification

### Integration tests

Use a disposable monitoring stack where possible:

```text
Prometheus
Loki
Grafana
PostgreSQL
```

Verify end-to-end retrieval.

### Agent evaluation

Create a fixed dataset of realistic dashboards and questions.

Each evaluation case contains:

```json
{
  "question": "...",
  "dashboard": "...",
  "expected_findings": [],
  "required_evidence": [],
  "forbidden_claims": []
}
```

## Critical evaluation metrics

### Correctness

Does the agent reach the same deterministic validation result as the reference implementation?

### Evidence grounding

Are every factual claims supported by retrieved evidence?

### Tool efficiency

How many calls are required?

### False positives

How often does the system report a problem that is not present?

### False negatives

How often does it miss a known problem?

### Query validity

Are generated queries syntactically valid and semantically appropriate?

### Filter correctness

Does the filter actually propagate to relevant queries?

## Golden test categories

1. Correct success rate
2. Wrong denominator
3. Wrong numerator
4. 4xx excluded from error rate
5. 5xx-only error definition
6. mismatched time ranges
7. mismatched service filters
8. counter without rate
9. bad p95 aggregation
10. unused dashboard variable
11. high-cardinality filter
12. duplicate query
13. missing telemetry
14. unknown metric semantics

## Release gate

Do not release if:

- deterministic validator tests fail
- agent invents evidence in evaluation
- query execution errors are misrepresented as successful
- secrets appear in logs
- read-only boundary is violated
