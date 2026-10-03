# Monitoring Dashboard Intelligence Agent

Validate Grafana dashboards against real observability data — with deterministic rules first, and an LLM only for investigation and explanation.

The agent helps engineers answer a single critical question:

> Are the numbers on this dashboard correct, consistent, explainable, and properly filterable?

---

## Why this exists

Grafana dashboards often look authoritative while hiding subtle failures:

- success rates with mismatched numerators and denominators
- filters that apply to some panels but not others
- counters used without `rate` / `increase`
- high-cardinality variables that make dashboards slow or misleading
- duplicate or contradictory PromQL across panels

This project separates **mathematical correctness** (deterministic validators) from **reasoning** (read-only LLM tool calling), so explanations never override observed evidence.

---

## Features

| Area | Capability |
| --- | --- |
| Dashboard sync | Import Grafana dashboards (panels, variables, queries) into PostgreSQL |
| Query analysis | Normalize PromQL/LogQL, detect duplicates, surface static query issues |
| Filter intelligence | Variable propagation, dead/partial filters, cardinality classification |
| Validation engine | Success/error rates, consistency, latency aggregation, counter rate checks |
| Agent chat | Budgeted, read-only tool loop with grounded evidence and confidence |
| Web UI | Select a dashboard, run analysis, inspect findings/evidence, chat |
| Production hardening | API keys, rate limits, secret redaction, metrics, optional OpenTelemetry |

**Read-only by design.** The MVP does not write to Grafana, mutate infrastructure, or execute shell/kubectl.

---

## Architecture (high level)

```text
Browser (Next.js)
        │
        ▼
   FastAPI (/api/v1)
        │
        ├── Deterministic analyzers & validators
        ├── Read-only agent (structured tool calling)
        └── Clients → Grafana · Prometheus · Loki · LLM
                 │
                 ▼
            PostgreSQL · Redis
```

Confidence and factual claims are derived from successful tool results and validator output — not model intuition.

---

## Quick start

### Prerequisites

- Python 3.12+
- Node.js 20+ (for the UI)
- Docker Compose (PostgreSQL + Redis)
- Optional: Grafana, Prometheus, Loki, and an OpenAI-compatible API key

### Backend

```bash
cp .env.example .env
docker compose up -d postgres redis
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --app-dir backend --reload
```

API base: `http://127.0.0.1:8000`  
PostgreSQL is published on host port `15432` (see `.env.example`).

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

UI: `http://localhost:3000`  
Next.js rewrites `/api/v1/*` to the backend (`API_ORIGIN`, default `http://127.0.0.1:8000`).

### Sync a dashboard

```bash
# Requires GRAFANA_URL and a read-only GRAFANA_API_TOKEN
curl -X POST http://127.0.0.1:8000/api/v1/dashboards/<uid>/sync
```

Then open the UI, select the dashboard, run analysis, and (optionally) ask the agent a question.

---

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness |
| `GET` | `/ready` | Readiness (PostgreSQL) |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/api/v1/dashboards` | List synced dashboards |
| `GET` | `/api/v1/dashboards/{uid}` | Dashboard detail |
| `POST` | `/api/v1/dashboards/{uid}/sync` | Sync from Grafana |
| `GET` | `/api/v1/analysis/dashboards/{uid}` | Deterministic analysis report |
| `POST` | `/api/v1/agent/chat` | Read-only agent investigation |

In production, protect `/api/v1/*` with `API_KEYS` (Bearer or `X-API-Key`). Health, readiness, and metrics remain public.

---

## Validation rules (deterministic)

| Rule ID | Focus |
| --- | --- |
| `SR-001` | Success rate formula and scope |
| `ER-001` | Error rate and required error semantics |
| `CONS-001` | Success + error ≈ total |
| `CONS-002` | Compatible time windows |
| `CONS-003` | Compatible filter scopes |
| `LAT-001` | Quantile aggregation misuse |
| `RATE-001` | Counters without rate/increase |
| `FILTER-*` | Dead, partial, multi-value, and high-cardinality filters |
| `QUERY-*` / `DASH-*` | Static query and dashboard quality findings |

The LLM **cannot** override these results.

---

## Configuration

All runtime config is via environment variables. See:

- [`.env.example`](.env.example)
- [`docs/27_ENVIRONMENT_CONTRACT.md`](docs/27_ENVIRONMENT_CONTRACT.md)

Important production settings:

| Variable | Purpose |
| --- | --- |
| `APP_ENV=production` | Enables production defaults |
| `API_KEYS` | Comma-separated API keys (required when auth is on) |
| `GRAFANA_API_TOKEN` | **Read-only** Grafana token |
| `OPENAI_API_KEY` | Required for live agent chat |
| `OTEL_ENABLED` / `OTEL_EXPORTER_OTLP_ENDPOINT` | Optional tracing |

---

## Development & quality gates

```bash
make check          # ruff + mypy + pytest
make eval           # golden evaluation / regression suite
# or
docker compose run --rm --build check
```

Frontend:

```bash
cd frontend && npm run lint && npm run build
```

---

## Deployment

- Compose service: `docker compose up api` (with resource limits and healthchecks)
- Kubernetes manifests: [`deploy/kubernetes/`](deploy/kubernetes/)
- Postgres backup helper: [`deploy/backup/postgres-backup.sh`](deploy/backup/postgres-backup.sh)
- Security checklist: [`docs/29_PRODUCTION_SECURITY_REVIEW.md`](docs/29_PRODUCTION_SECURITY_REVIEW.md)

---

## Stack

| Layer | Technology |
| --- | --- |
| API | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2 |
| Data | PostgreSQL, Redis |
| Observability backends | Grafana, Prometheus, Loki (HTTP, read-only) |
| Agent | OpenAI-compatible structured tool calling |
| UI | Next.js / React |
| Quality | pytest, Ruff, mypy, golden evaluation suite |
| Ops | Docker Compose, Kubernetes, Prometheus metrics, OpenTelemetry |

---

## Documentation

| Document | Description |
| --- | --- |
| [`DOC_INDEX.md`](DOC_INDEX.md) | Full documentation index |
| [`docs/00_MASTER_SPEC.md`](docs/00_MASTER_SPEC.md) | Product mission and system boundary |
| [`docs/25_MVP_BOUNDARIES.md`](docs/25_MVP_BOUNDARIES.md) | In-scope / out-of-scope lock |
| [`docs/16_SECURITY.md`](docs/16_SECURITY.md) | Security principles |
| [`docs/19_PHASES.md`](docs/19_PHASES.md) | Implementation phases |
| [`docs/28_PHASE_STATUS.md`](docs/28_PHASE_STATUS.md) | Current delivery status |

---

## Non-goals (MVP)

- Autonomous remediation or infrastructure mutation
- Shell / kubectl / SQL write tools
- Automatic Grafana dashboard writes
- Treating screenshots or OCR as metric truth
- Letting the LLM decide mathematical correctness without validators

---

## License

Proprietary — see repository owner for distribution terms.
