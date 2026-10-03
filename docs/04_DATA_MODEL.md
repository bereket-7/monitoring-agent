# Data Model

Use PostgreSQL.

## Main entities

### dashboard

```text
id
grafana_uid
title
folder
url
json_hash
raw_json
created_at
updated_at
```

### dashboard_panel

```text
id
dashboard_id
grafana_panel_id
title
panel_type
datasource_uid
raw_definition
created_at
updated_at
```

### dashboard_variable

```text
id
dashboard_id
name
label
variable_type
query
current_value
multi
include_all
raw_definition
```

### metric_definition

```text
id
metric_name
metric_type
domain
meaning
unit
success_semantics
error_semantics
required_labels
optional_labels
definition_version
source
```

### analysis_run

```text
id
dashboard_id
status
started_at
completed_at
request_id
time_range
filters
agent_model
tool_call_count
```

### validation_finding

```text
id
analysis_run_id
rule_id
severity
category
dashboard_panel_id
title
description
observed_value
expected_value
evidence
recommendation
created_at
```

### query_snapshot

```text
id
analysis_run_id
panel_id
datasource_type
query_language
raw_query
normalized_query
query_hash
referenced_metrics
referenced_labels
```

## Data principles

- Store raw dashboard definitions for reproducibility.
- Hash queries to detect duplicates.
- Store enough provenance to reconstruct findings.
- Never store API secrets.
- Redact sensitive log content before persistence.
