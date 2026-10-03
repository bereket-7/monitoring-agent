# Future Roadmap

Only pursue these after the MVP is reliable.

## Dashboard auto-generation

Generate proposed Grafana panels from a metric registry.

## Dashboard diff

Show:

```text
Current
   vs
Proposed
```

before applying any change.

## Automatic dashboard repair

Potential future workflow:

```text
Detect problem
    ↓
Generate patch
    ↓
Show diff
    ↓
Human approval
    ↓
Apply
    ↓
Validate
```

## Historical intelligence

Learn recurring dashboard problems from previous validated analyses.

## Incident correlation

Correlate:

- metrics
- logs
- traces
- deployments
- dashboard changes

## SLO intelligence

Support:

- SLI definitions
- SLO targets
- error budgets
- burn-rate analysis

## Multi-environment comparison

Compare:

```text
production
staging
development
```

while clearly labeling population and time range.

## Autonomous scheduled audits

Run dashboard quality checks periodically and notify engineers.

Do not add autonomous mutation until the read-only analysis system has strong evaluation coverage and explicit approval controls.
