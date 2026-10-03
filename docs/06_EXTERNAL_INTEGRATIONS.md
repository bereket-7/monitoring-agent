# External Integrations

## Grafana

Required read operations:

- get dashboard by UID
- list/search dashboards when supported
- get datasource metadata
- read folders
- read alert/rule metadata if useful

Use a dedicated `GrafanaClient`.

All requests need:

- timeout
- structured error mapping
- request correlation
- safe retry for idempotent reads

## Prometheus

Required operations:

- instant query
- range query
- metadata
- label names
- label values
- series discovery

Create `PrometheusClient`.

Never let the LLM directly construct an arbitrary HTTP request. The tool receives typed arguments and the client performs the request.

## Loki

Required operations:

- range query
- instant query where supported
- label names
- label values

Treat logs as supporting evidence, not as an automatic replacement for authoritative metrics.

## Tempo / traces

Optional phase.

Use traces to correlate:

- service latency
- dependency latency
- error spans
- trace volume

## LLM

Use structured tool calling.

The model receives:

- user question
- normalized dashboard context
- available tool definitions
- evidence collected so far
- explicit system rules

The model does not receive unrestricted credentials or arbitrary execution capability.
