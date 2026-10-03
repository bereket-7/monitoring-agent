# Environment Contract

All runtime configuration is supplied through environment variables.
Copy `.env.example` to `.env` for local development. Never commit `.env`.

## Required for local Phase 1+

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | `development` / `staging` / `production` |
| `LOG_LEVEL` | Structured log level |
| `DATABASE_URL` | Async SQLAlchemy PostgreSQL URL (Compose publishes Postgres on host port `15432`) |
| `REDIS_URL` | Redis connection URL |

## Required for dashboard analysis

| Variable | Purpose |
| --- | --- |
| `GRAFANA_URL` | Grafana base URL |
| `GRAFANA_API_TOKEN` | Read-only Grafana API token |
| `PROMETHEUS_URL` | Prometheus base URL |

## Optional / degradable

| Variable | Purpose |
| --- | --- |
| `LOKI_URL` | Loki base URL; omit to disable Loki |
| `OPENAI_API_KEY` | LLM provider key; required for agent chat |
| `OPENAI_MODEL` | Model name for structured tool calling |

## Safety bounds

| Variable | Default intent |
| --- | --- |
| `REQUEST_TIMEOUT_SECONDS` | Default outbound HTTP timeout |
| `GRAFANA_TIMEOUT_SECONDS` | Grafana client timeout |
| `PROMETHEUS_TIMEOUT_SECONDS` | Prometheus client timeout |
| `LOKI_TIMEOUT_SECONDS` | Loki client timeout |
| `PROMETHEUS_MAX_RESPONSE_BYTES` | Response size guard |
| `LOKI_MAX_RESPONSE_BYTES` | Response size guard |
| `AGENT_MAX_TOOL_CALLS` | Max tool calls per agent run (MVP: 20) |
| `AGENT_MAX_ANALYSIS_SECONDS` | Wall-clock analysis budget |
| `VALIDATION_CONSISTENCY_TOLERANCE` | Relative tolerance for CONS-001 |
| `MAX_QUERY_LENGTH` | Reject oversized queries |
| `MAX_TIME_RANGE_SECONDS` | Reject excessive ranges |
| `QUERY_CONCURRENCY_LIMIT` | Cap concurrent external queries |
| `API_AUTH_ENABLED` | Force API key auth; default true in production |
| `API_KEYS` | Comma-separated API keys (required in production) |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Per-identity request budget (0 disables) |
| `REDACT_EMAILS` | Redact emails before LLM/audit |
| `REQUIRE_READONLY_CREDENTIALS` | Emit startup posture that tokens must be read-only |
| `OTEL_ENABLED` | Enable OpenTelemetry tracing |
| `OTEL_SERVICE_NAME` | Trace service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP HTTP traces endpoint |

## Secrets policy

- Store secrets only in environment variables (local) or a secret manager (production)
- Never commit credentials, tokens, or `.env`
- Never put secrets in prompts, logs, or API responses
- Prefer read-only Grafana/Prometheus/Loki credentials

See also: `docs/16_SECURITY.md`, `docs/18_DEPLOYMENT.md`, `docs/29_PRODUCTION_SECURITY_REVIEW.md`, `.env.example`.
