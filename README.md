# Monitoring Dashboard Intelligence Agent

An AI-assisted observability engineering platform that sits on top of Grafana, Prometheus, Loki, and optionally Tempo.

## Product goal

Help engineers answer:

> Are the numbers in this Grafana dashboard correct, consistent, explainable, and properly filterable?

The system analyzes Grafana dashboards, PromQL/LogQL queries, metric semantics, filters, and real monitoring data. It validates calculations deterministically and uses an LLM for reasoning, investigation, explanation, and recommendations.

## Core principles

1. **Evidence first.** Every important answer must reference the query, time range, filters, and source data used.
2. **Deterministic correctness.** Mathematical and rule-based validation must not depend on the LLM.
3. **LLM for reasoning.** The LLM interprets intent, chooses tools, investigates discrepancies, and explains findings.
4. **Read-only by default.** Initial releases do not mutate Grafana dashboards or production infrastructure.
5. **Reproducible analysis.** The same inputs should produce the same validation result even if the wording of the explanation changes.
6. **Explicit uncertainty.** Never invent metric meanings, labels, or conclusions.
7. **Small, testable components.** Prefer typed services and deterministic analyzers over a large autonomous agent.

## Documentation

Start here:

- [DOC_INDEX.md](DOC_INDEX.md) — full documentation index
- [CURSOR_MASTER_PROMPT.md](CURSOR_MASTER_PROMPT.md) — implementation instruction for Cursor
- [docs/19_PHASES.md](docs/19_PHASES.md) — implementation phases
- [docs/23_FIRST_MVP.md](docs/23_FIRST_MVP.md) — tightly scoped first MVP
- [docs/25_MVP_BOUNDARIES.md](docs/25_MVP_BOUNDARIES.md) — locked MVP in/out scope
- [docs/26_CODING_STANDARDS.md](docs/26_CODING_STANDARDS.md) — coding standards
- [docs/27_ENVIRONMENT_CONTRACT.md](docs/27_ENVIRONMENT_CONTRACT.md) — environment variables

## Local development

```bash
cp .env.example .env
docker compose up -d postgres redis
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --app-dir backend --reload
```

Compose publishes PostgreSQL on host port `15432` (see `.env.example`).

Health probes:

- `GET /health` — liveness
- `GET /ready` — readiness (PostgreSQL)

Validate:

```bash
make check
# or
docker compose run --rm --build check
```

Follow [docs/19_PHASES.md](docs/19_PHASES.md). Do not skip phases.

## Initial scope

- Import/read Grafana dashboards.
- Read panels, queries, transformations, variables, and datasource references.
- Execute PromQL against Prometheus.
- Execute LogQL against Loki when configured.
- Analyze common reliability metrics:
  - request count
  - request rate
  - success rate
  - error rate
  - availability
  - latency p50/p95/p99
  - throughput
- Validate formulas and filter propagation.
- Detect common query problems.
- Produce evidence-backed reports.
- Provide an AI chat interface for dashboard questions.

## Explicit non-goals for MVP

- Autonomous infrastructure remediation.
- Arbitrary shell execution.
- Automatic production dashboard mutation.
- Treating screenshots as the primary source of metric truth.
- Allowing the LLM to decide mathematical correctness without deterministic validation.

## Stack

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- PostgreSQL
- Redis
- Grafana / Prometheus / Loki HTTP APIs
- OpenAI structured tool calling
- React/Next.js
- Docker Compose
- pytest, Ruff, mypy, OpenTelemetry

## Development order

Follow [docs/19_PHASES.md](docs/19_PHASES.md) and [docs/28_PHASE_STATUS.md](docs/28_PHASE_STATUS.md). Do not skip phases.
