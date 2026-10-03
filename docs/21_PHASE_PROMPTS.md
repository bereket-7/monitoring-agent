# Cursor Phase Prompts

Use one prompt at a time.

## Phase 0

```text
Read:
- README.md
- docs/00_MASTER_SPEC.md
- docs/01_ARCHITECTURE.md
- docs/02_REQUIREMENTS.md
- docs/03_PROJECT_SCAFFOLD.md
- docs/20_CURSOR_WORKFLOW.md

Do not implement application logic yet.

Create the repository scaffold, configuration files, development tooling, documentation links, and empty package boundaries.

Use Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL, pytest, Ruff, and mypy.

Create .env.example but never include real credentials.

Run the project checks and report results.
```

## Phase 1

```text
Read the Phase 1 section of docs/19_PHASES.md and the architecture/scaffold/security docs.

Implement the backend foundation:
- FastAPI app
- configuration
- structured logging
- request IDs
- PostgreSQL connection
- SQLAlchemy base
- Alembic
- health/readiness endpoints
- Docker Compose for PostgreSQL and Redis
- tests

Do not implement the AI agent yet.

Run tests, Ruff, and mypy.
```

## Phase 2

```text
Read docs/06_EXTERNAL_INTEGRATIONS.md and docs/09_DASHBOARD_ANALYZER.md.

Implement the Grafana read-only client and dashboard synchronization.

Add:
- typed Grafana client
- timeout handling
- error mapping
- dashboard repository
- normalized dashboard/panel/variable models
- sync endpoint
- tests using mocked Grafana responses

Do not use the LLM.

Prove that a real dashboard JSON can be normalized.
```

## Phase 3

```text
Read docs/06_EXTERNAL_INTEGRATIONS.md and docs/08_VALIDATION_ENGINE.md.

Implement Prometheus and Loki read-only clients.

Support:
- instant query
- range query
- metadata
- label names/values
- Loki range queries

Add typed responses, timeouts, size limits, and tests.

Do not allow arbitrary shell commands.
```

## Phase 4

```text
Read docs/07_METRIC_SEMANTICS.md and docs/08_VALIDATION_ENGINE.md.

Implement the deterministic validation engine.

Start with:
- SR-001
- ER-001
- CONS-001
- CONS-002
- CONS-003
- LAT-001
- RATE-001

Create golden tests for correct and incorrect dashboards.

The validator must not use an LLM.
```

## Phase 5

```text
Read docs/09_DASHBOARD_ANALYZER.md and docs/11_QUERY_ANALYZER.md.

Implement dashboard and query analysis.

Add:
- query extraction
- query normalization
- query hashes
- metric/label references
- duplicate query detection
- variable-to-query relationship graph
- static query quality findings

Keep analysis deterministic.
```

## Phase 6

```text
Read docs/10_FILTER_ENGINE.md.

Implement filter intelligence.

Discover candidate labels, classify cardinality, map variables to panels/queries, and detect dead or partially propagated variables.

Create tests for:
- single value
- multi-value
- all value
- unused variable
- filter affecting only some panels
- high-cardinality labels
```

## Phase 7

```text
Read docs/12_AGENT_DESIGN.md and docs/13_AGENT_PROMPTS.md.

Implement the read-only AI agent.

Use structured tool calling.

Create:
- AgentState
- tool registry
- tool policies
- bounded orchestration loop
- evidence collection
- response formatter

The LLM must never fabricate query results or override deterministic validation.

Add mocked LLM/tool tests.
```

## Phase 8

```text
Read docs/14_UI_SPEC.md.

Build the web UI.

Implement:
- dashboard selection
- analysis execution
- findings
- evidence
- filters
- agent chat

Keep the UI focused on monitoring analysis. Do not rebuild Grafana.
```

## Phase 9

```text
Read docs/15_TESTING_AND_EVALUATION.md.

Create a golden evaluation dataset.

Test:
- correctness
- evidence grounding
- tool efficiency
- false positives
- false negatives
- filter correctness
- query validity

Create a regression command that can run in CI.
```

## Phase 10

```text
Read docs/16_SECURITY.md, docs/17_OBSERVABILITY.md, and docs/18_DEPLOYMENT.md.

Harden the application for production.

Implement:
- authentication
- rate limiting
- secret redaction
- OpenTelemetry
- structured audit events
- health/readiness
- secure deployment configuration
- resource limits

Verify that production credentials are read-only.
```
