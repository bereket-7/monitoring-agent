# Phase Status

## Current phase

**Phase 3 — Prometheus/Loki: COMPLETE**

Previous:
- Phase 0 — Specification: COMPLETE
- Phase 1 — Scaffold: COMPLETE
- Phase 2 — Grafana integration: COMPLETE

Next: **Phase 4 — Validation engine**

## Phase 3 acceptance

- [x] Typed read-only Prometheus client (instant/range/metadata/labels/series)
- [x] Typed read-only Loki client (instant/range/labels; graceful when unset)
- [x] Query/response models in `app.schemas.query`
- [x] Timeouts, retries, response size limits, query length limits
- [x] Typed failure mapping (`PrometheusQueryError`, `LokiUnavailableError`, etc.)
- [x] Unit tests with mocked HTTP
- [x] Lint / typecheck / tests green (27 tests)

## Validation

```bash
py -3 -m ruff check backend migrations
py -3 -m mypy
py -3 -m pytest
```
