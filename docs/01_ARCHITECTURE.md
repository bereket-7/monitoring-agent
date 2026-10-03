# Architecture

## Logical architecture

```text
                         User
                           |
                           v
                    Web UI / API
                           |
                           v
                  Agent Orchestrator
                  /       |        \
                 /        |         \
                v         v          v
          Dashboard    Metric      Query
           Analyzer    Registry    Analyzer
                \         |         /
                 \        |        /
                  v       v       v
                   Validation Engine
                           |
              +------------+------------+
              |            |            |
              v            v            v
         Prometheus      Loki        Grafana
              |            |            |
              +------------+------------+
                           |
                           v
                    Evidence Store
                           |
                           v
                     Report / Chat
```

## Deployment architecture

MVP:

```text
Browser
  |
  v
Next.js
  |
  v
FastAPI
  |
  +--> PostgreSQL
  +--> Redis
  +--> Grafana
  +--> Prometheus
  +--> Loki
  +--> LLM provider
```

## Component responsibilities

### API

Authentication, request validation, orchestration entry points, response serialization.

### Grafana client

Read dashboards, folders, datasource metadata, panel definitions, variables.

### Prometheus client

Execute PromQL, retrieve metadata, labels, label values, series metadata.

### Loki client

Execute LogQL and retrieve labels/values when enabled.

### Dashboard analyzer

Parse dashboards into normalized internal models.

### Query analyzer

Parse/inspect PromQL/LogQL and identify referenced metrics, labels, variables, aggregations, and suspicious patterns.

### Metric registry

Store authoritative semantics for important business/technical metrics.

### Validation engine

Perform deterministic checks.

### Agent

Interpret natural language, select tools, build investigation plans, and explain results.

### Evidence store

Persist analysis inputs, outputs, query fingerprints, validation findings, and provenance.

## Agent safety boundaries

The initial agent has only read-only tools:

- get dashboard
- get panel
- get variables
- query Prometheus
- query Loki
- get metric metadata
- get label values
- validate formula
- compare query results
- inspect historical validation

No shell, kubectl, SQL write, Grafana write, or infrastructure mutation tools are allowed in MVP.
