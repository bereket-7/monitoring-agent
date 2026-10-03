# Dashboard Analyzer

## Input

Grafana dashboard JSON.

## Output

Normalized representation:

```text
Dashboard
├── metadata
├── variables[]
├── panels[]
│   ├── id
│   ├── title
│   ├── datasource
│   ├── queries[]
│   ├── transformations[]
│   └── field_config
└── links
```

## Analyzer responsibilities

### Panel inventory

Identify:

- stat
- time series
- table
- gauge
- heatmap
- logs
- row

### Query extraction

Extract PromQL/LogQL targets and preserve raw text.

### Variable extraction

Identify:

- query variables
- custom variables
- interval variables
- datasource variables
- constant variables

### Relationships

Map:

```text
dashboard variable
        ↓
panel
        ↓
query
        ↓
metric/label
```

This relationship graph is necessary for filter validation.

## Dashboard quality checks

- duplicate panels
- duplicate queries
- missing titles
- inconsistent units
- inconsistent legends
- unused variables
- filters not applied
- same metric represented with conflicting definitions
