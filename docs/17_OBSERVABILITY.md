# Observability of the Agent

The agent itself must be observable.

## Metrics

Track:

```text
agent_requests_total
agent_request_duration_seconds
agent_tool_calls_total
agent_tool_call_duration_seconds
agent_tool_errors_total
agent_analysis_findings_total
agent_llm_requests_total
agent_llm_tokens_total
agent_llm_errors_total
```

## Structured logs

Every request should include:

```text
request_id
analysis_id
dashboard_uid
tool_name
duration
status
```

Never log secrets.

## Tracing

Use OpenTelemetry.

Trace:

```text
API request
  ├── Grafana API
  ├── Prometheus query
  ├── Loki query
  ├── validator
  └── LLM request
```

## Agent quality telemetry

Track:

- average tool calls
- average analysis duration
- validation disagreement
- user feedback
- evidence completeness
- failed queries
