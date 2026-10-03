# Master Project Specification

## Mission

Build a production-oriented Monitoring Dashboard Intelligence Agent that helps observability engineers verify and improve Grafana dashboards.

The agent should answer questions such as:

- Is this success rate calculated correctly?
- Why does success + error not equal total?
- Does the service filter affect every relevant panel?
- Which panels use inconsistent definitions?
- Is this PromQL unnecessarily expensive?
- Which labels can be used as safe dashboard filters?
- What is the evidence for this metric?
- Which dashboard panels are duplicated or contradictory?

## System boundary

The system consumes:

- Grafana dashboard definitions
- Prometheus metric metadata and time-series data
- Loki logs
- optional Tempo/OpenTelemetry traces
- metric semantic definitions
- service/environment metadata

It produces:

- validation findings
- query recommendations
- filter recommendations
- evidence reports
- dashboard quality reports
- conversational answers

## Architecture rule

Separate four concerns:

### 1. Retrieval

Get authoritative data from monitoring systems.

### 2. Deterministic analysis

Calculate, compare, validate, and detect known structural problems.

### 3. Agent reasoning

Use the LLM to decide what to inspect next, interpret user questions, and explain evidence.

### 4. Presentation

Expose results through API/UI.

## Trust model

Highest trust:
- raw monitoring query results
- deterministic calculations
- explicit metric registry definitions

Medium trust:
- stored dashboard metadata
- historical observations

Lowest trust:
- LLM-generated interpretation

LLM output must never override authoritative query results.

## Primary success criteria

A user can select a dashboard and obtain:

1. panel inventory
2. query inventory
3. metric inventory
4. filter inventory
5. correctness findings
6. inconsistent-definition findings
7. filter propagation findings
8. query optimization findings
9. evidence-backed recommendations

## Non-functional requirements

- Typed Python.
- Async I/O where useful.
- Unit and integration tests.
- Structured logs.
- Correlation/request IDs.
- No secrets in logs.
- Timeouts on external requests.
- Retries only for safe/idempotent reads.
- Rate-limit awareness.
- Graceful degradation when Loki/Tempo/LLM is unavailable.
- No unbounded agent loops.
- Maximum tool-call budget per run.
- Maximum analysis time per request.
