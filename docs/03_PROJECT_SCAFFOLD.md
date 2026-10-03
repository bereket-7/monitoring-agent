# Project Scaffold

Use this structure unless there is a documented reason to change it.

```text
monitoring-dashboard-agent/
├── README.md
├── pyproject.toml
├── .env.example
├── docker-compose.yml
├── Makefile
├── alembic.ini
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── logging.py
│   │   │
│   │   ├── api/
│   │   │   ├── routes_health.py
│   │   │   ├── routes_dashboards.py
│   │   │   ├── routes_analysis.py
│   │   │   └── routes_agent.py
│   │   │
│   │   ├── clients/
│   │   │   ├── grafana.py
│   │   │   ├── prometheus.py
│   │   │   ├── loki.py
│   │   │   └── llm.py
│   │   │
│   │   ├── models/
│   │   │   ├── dashboard.py
│   │   │   ├── metric.py
│   │   │   ├── query.py
│   │   │   ├── validation.py
│   │   │   └── analysis.py
│   │   │
│   │   ├── analyzers/
│   │   │   ├── dashboard.py
│   │   │   ├── query.py
│   │   │   ├── filters.py
│   │   │   └── cardinality.py
│   │   │
│   │   ├── validators/
│   │   │   ├── base.py
│   │   │   ├── success_rate.py
│   │   │   ├── error_rate.py
│   │   │   ├── consistency.py
│   │   │   ├── latency.py
│   │   │   └── filters.py
│   │   │
│   │   ├── agent/
│   │   │   ├── orchestrator.py
│   │   │   ├── state.py
│   │   │   ├── tools.py
│   │   │   ├── policies.py
│   │   │   └── prompts.py
│   │   │
│   │   ├── repositories/
│   │   ├── services/
│   │   └── db/
│   │
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── evaluation/
│
├── frontend/
│   └── ...
│
├── rules/
│   ├── metric_definitions/
│   └── validation_rules/
│
├── prompts/
│
├── migrations/
│
└── docs/
```

## Scaffold rules

- Keep business logic out of FastAPI route handlers.
- Keep external API calls behind client interfaces.
- Keep database access behind repositories/services.
- Keep validators deterministic and independently testable.
- Keep agent tools thin; they should call domain services.
- Never put credentials in source control.
