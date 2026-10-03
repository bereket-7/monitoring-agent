# Deployment

## Local development

Use Docker Compose for:

- PostgreSQL
- Redis
- Prometheus
- Loki
- Grafana

The backend/frontend may run directly during development.

## Environment variables

Provide `.env.example`:

```text
APP_ENV=development
LOG_LEVEL=INFO

DATABASE_URL=
REDIS_URL=

GRAFANA_URL=
GRAFANA_API_TOKEN=

PROMETHEUS_URL=
LOKI_URL=

OPENAI_API_KEY=
OPENAI_MODEL=
```

Never commit `.env`.

## Production

Recommended:

```text
Ingress
  |
Frontend
  |
FastAPI replicas
  |
PostgreSQL
Redis
Monitoring backends
```

Use:

- TLS
- secret manager
- network policies
- resource limits
- health/readiness probes
- centralized logs
- backups

## Deployment rule

MVP must be deployable without giving the application write access to production Grafana or infrastructure.
