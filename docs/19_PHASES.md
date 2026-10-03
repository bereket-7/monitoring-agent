# Implementation Phases

## Phase 0 — Specification

Deliver:

- repository
- documentation
- coding standards
- architecture
- environment contract

Acceptance:
- all docs reviewed
- no implementation ambiguity in MVP boundaries

## Phase 1 — Scaffold

Build:

- FastAPI
- configuration
- PostgreSQL
- migrations
- logging
- health endpoints
- Docker Compose

Acceptance:
- app starts
- DB connects
- tests run
- lint/type checks run

## Phase 2 — Grafana integration

Build:

- Grafana client
- dashboard sync
- dashboard parser
- normalized models

Acceptance:
- real dashboard can be imported
- panels and variables are extracted correctly

## Phase 3 — Prometheus/Loki

Build:

- Prometheus client
- Loki client
- query models
- timeout/error handling

Acceptance:
- real queries execute
- failures are represented correctly

## Phase 4 — Validation engine

Build deterministic rules.

Acceptance:
- golden test suite passes
- success/error/consistency checks are reproducible

## Phase 5 — Dashboard analyzer

Build:

- query inventory
- variable graph
- duplicate detection
- query quality analysis

Acceptance:
- dashboard report generated without LLM

## Phase 6 — Filter intelligence

Build:

- label discovery
- cardinality checks
- variable propagation
- dead-variable detection

Acceptance:
- known filter test cases pass

## Phase 7 — Agent

Build:

- tool registry
- agent state
- structured tool calling
- evidence collector
- response formatter

Acceptance:
- agent answers dashboard questions using actual tools
- no fabricated evidence

## Phase 8 — UI

Build:

- dashboard selector
- analysis page
- findings
- evidence
- chat

Acceptance:
- user can select dashboard and run analysis end-to-end

## Phase 9 — Evaluation

Build golden dataset and regression suite.

Acceptance:
- deterministic validator quality established
- agent grounding evaluated

## Phase 10 — Production hardening

Build:

- authentication
- rate limits
- redaction
- tracing
- metrics
- deployment manifests
- backups

Acceptance:
- production security review complete
