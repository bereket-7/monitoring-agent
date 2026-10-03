# Requirements

## Functional requirements

### Dashboard ingestion

- Read dashboard JSON from Grafana API.
- Normalize panels recursively.
- Preserve panel IDs.
- Preserve datasource references.
- Preserve variables.
- Preserve query targets.
- Preserve transformations.
- Support nested rows/panels.

### Query inspection

For every query record:

- datasource type
- raw query
- query language
- referenced metrics
- referenced labels
- dashboard variables
- time range behavior
- aggregation operators where detectable

### Metric validation

Support:

- total request count
- request rate
- success rate
- error rate
- availability
- latency quantiles
- throughput

### Filter validation

Detect:

- unused variables
- variables referenced by only some panels
- variables that produce no query constraint
- inconsistent variable semantics
- unsafe high-cardinality filter candidates
- filters that change one panel but not related panels

### Evidence

Every finding should contain:

- finding ID
- severity
- category
- dashboard/panel
- explanation
- source queries
- query time range
- filters
- observed values
- expected relationship
- recommendation
- deterministic rule ID
- timestamp

## Severity definitions

Use:

- `info`: informational
- `warning`: potentially problematic
- `error`: correctness or functional problem
- `critical`: severe data-integrity issue affecting a key metric

Severity is about technical impact, not urgency of an incident.

## API requirements

All endpoints:

- validate input with Pydantic
- return structured errors
- include request ID
- use consistent response envelopes

## Performance requirements

Initial target:

- dashboard parse < 1s for ordinary dashboards
- local deterministic validation < 2s excluding external query latency
- external query timeout configurable
- agent tool budget configurable
