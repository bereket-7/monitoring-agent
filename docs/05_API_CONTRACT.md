# API Contract

Base path: `/api/v1`

## Health

```http
GET /health
GET /ready
```

## Dashboards

```http
GET /dashboards
GET /dashboards/{uid}
POST /dashboards/{uid}/sync
```

## Analysis

```http
POST /analysis/dashboard
GET /analysis/{run_id}
GET /analysis/{run_id}/findings
```

Example:

```json
{
  "dashboard_uid": "api-overview",
  "time_range": {
    "from": "now-24h",
    "to": "now"
  },
  "filters": {
    "environment": "production",
    "service": "payment-api"
  },
  "checks": [
    "success_rate",
    "error_rate",
    "consistency",
    "filters",
    "query_quality"
  ]
}
```

## Agent

```http
POST /agent/chat
```

Request:

```json
{
  "message": "Is the success rate on this dashboard correct?",
  "dashboard_uid": "api-overview",
  "context": {
    "time_range": {
      "from": "now-6h",
      "to": "now"
    },
    "filters": {
      "service": "payment-api"
    }
  }
}
```

Response must distinguish:

```json
{
  "answer": "...",
  "findings": [],
  "evidence": [],
  "queries": [],
  "confidence": "high"
}
```

Do not return an unsupported confidence level. Confidence must come from deterministic evidence coverage rules.
