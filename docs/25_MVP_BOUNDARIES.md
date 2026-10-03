# MVP Boundaries (Phase 0 Lock)

This document removes implementation ambiguity for the first MVP.
It is authoritative for scope decisions until Phase 9 evaluation expands intentionally.

## In scope

Exactly the product loop defined in `docs/23_FIRST_MVP.md`:

1. Connect to Grafana (read-only).
2. Select a dashboard by UID.
3. Read panels, variables, and PromQL targets.
4. Connect to Prometheus (read-only).
5. Execute relevant queries with timeouts and typed errors.
6. Deterministically validate:
   - success rate (`SR-001`)
   - error rate (`ER-001`)
   - total consistency (`CONS-001`)
   - time-range consistency (`CONS-002`)
   - filter consistency (`CONS-003`)
7. Show findings with evidence (queries, values, scope, rule IDs).
8. Answer: "Is the success rate correct?" via the read-only agent.
9. Return calculation, queries, observed values, and limitations.

Supporting MVP capabilities:

- PostgreSQL persistence for dashboards, analysis runs, findings, query snapshots
- Redis for cache/coordination as needed
- Optional Loki reads for supporting evidence (graceful degradation when unset)
- FastAPI `/api/v1` health, dashboard sync, analysis, and agent chat endpoints
- Minimal UI to select a dashboard, run analysis, view findings/evidence, and chat

## Out of scope for MVP

Do not implement unless a later phase explicitly expands scope:

- shell execution, kubectl, or infrastructure mutation
- Grafana write/update/delete operations
- autonomous remediation or auto-fixing dashboards
- screenshot/OCR as a source of metric truth
- LLM-only mathematical correctness without deterministic validators
- Tempo/traces (optional post-MVP unless needed for a specific finding)
- write tools of any kind
- unbounded agent loops or unconstrained tool budgets
- production multi-tenant auth beyond Phase 10 hardening (Phase 1 may use a simple local config)

## Trust and correctness rules (non-negotiable)

- Monitoring systems are authoritative for observed values.
- Deterministic validators are authoritative for formula/consistency correctness.
- LLM output must never override query results or validator findings.
- Missing telemetry is not treated as zero.
- Compatible scope is required for numerator/denominator comparisons.
- Consistency tolerance is configurable and must be stated in findings.
- Do not average quantiles; preserve histogram/summary semantics.

## Phase gate

- Phase 0 ends when repository, docs, coding standards, architecture, and environment contract are in place and this boundary document is accepted.
- Phase 1 begins scaffold runtime (FastAPI, config, DB, health, Compose).
- Do not skip phases.

## Ambiguity resolutions

| Topic | Decision |
| --- | --- |
| Success default | HTTP 200–399 unless metric registry overrides |
| Error default | Must be configured; do not silently pick 4xx vs 5xx |
| Loki | Optional; degrade when unavailable |
| Tempo | Not required for first MVP |
| Agent tool budget | Default 20 calls (`AGENT_MAX_TOOL_CALLS`) |
| Confidence | Derived from evidence coverage rules only |
| Secrets | Environment / secret manager only; never committed |
