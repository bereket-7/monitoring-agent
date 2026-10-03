# Agent Design

## Role

The agent is a monitoring/dashboard analysis assistant.

It is not an autonomous infrastructure operator.

## Core loop

```text
User intent
  ↓
Context discovery
  ↓
Plan investigation
  ↓
Call read-only tools
  ↓
Collect evidence
  ↓
Run deterministic validators
  ↓
Interpret findings
  ↓
Answer with evidence
```

## Tools

Initial tools:

```text
get_dashboard
get_panel
list_dashboard_variables
query_prometheus
query_loki
get_metric_metadata
get_label_values
analyze_query
validate_metric
compare_metric_results
get_previous_analysis
```

## Tool policy

Every tool must have:

- name
- purpose
- typed input
- typed output
- timeout
- error mapping
- permission class

All MVP tools are read-only.

## Agent state

```python
AgentState:
    user_message
    dashboard_uid
    time_range
    filters
    findings
    evidence
    tool_calls
    remaining_budget
    final_answer
```

## Tool budget

Set a maximum number of tool calls per request.

Recommended MVP default:

```text
20 calls
```

Stop early when sufficient evidence exists.

## Hallucination controls

The agent must:

- never fabricate query results
- never fabricate metric meanings
- never fabricate Grafana panels
- never claim a query was executed unless execution succeeded
- distinguish observed data from interpretation
- state when evidence is incomplete

## Response format

```text
Answer
Evidence
Calculation/query
Findings
Limitations
Recommendation
```

## Confidence

Use evidence coverage, not model intuition.

Example:

High confidence:
- authoritative query executed
- expected semantics known
- validation passed
- sufficient data

Medium:
- query executed
- semantics partially inferred
- no contradictory evidence

Low:
- incomplete telemetry
- unknown metric semantics
- missing data
