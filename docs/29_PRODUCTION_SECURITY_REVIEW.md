# Production Security Review (Phase 10)

## Scope

Hardening for the Monitoring Dashboard Intelligence Agent API and supporting deployment assets.

## Controls implemented

| Control | Status | Notes |
| --- | --- | --- |
| API authentication | Done | Bearer / `X-API-Key`; required by default in `production` |
| Rate limiting | Done | Per-identity Redis limiter with in-memory fallback |
| Secret redaction | Done | Applied before LLM calls and in audit events |
| Structured audit events | Done | `agent_run_complete`, `agent_tool_call` |
| Metrics | Done | Prometheus `/metrics` (`agent_*`, `http_requests_total`) |
| Tracing | Done | Optional OpenTelemetry OTLP exporter |
| Health / readiness | Done | `/health`, `/ready` |
| Query bounds | Done | length, time range, timeouts, response size, concurrency |
| Read-only posture | Required | Grafana/Prometheus/Loki credentials must be read-only |
| Deployment manifests | Done | `deploy/kubernetes/*` with probes + resource limits |
| Backups | Done | `deploy/backup/postgres-backup.sh` |

## Credential posture (must verify operationally)

- Grafana token: dashboards/datasources **read** only — no write/Admin
- Prometheus: query API only (no remote-write credentials in this app)
- Loki: query API only
- PostgreSQL role: least privilege for app schema
- LLM key: stored in secret manager, never logged

## Release gate checklist

- [ ] `API_KEYS` configured in production secret store
- [ ] `APP_ENV=production` and TLS terminated at ingress
- [ ] CORS origins restricted to the UI hostname
- [ ] OTEL endpoint points at the org collector (or disabled intentionally)
- [ ] Backup cron validated with restore drill
- [ ] No write tools registered (`app.agent.policies.FORBIDDEN_TOOL_NAMES`)
- [ ] Evaluation suite green (`make eval`)

## Residual risks

- Prompt injection via dashboard/log content is mitigated by policy + redaction, not eliminated
- In-memory rate limiting is per-replica if Redis is unavailable
- Frontend still needs the API key injected for authenticated environments
