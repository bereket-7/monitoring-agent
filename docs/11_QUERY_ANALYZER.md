# Query Analyzer

## Goals

Analyze PromQL/LogQL structurally.

## PromQL checks

Detect:

- referenced metrics
- labels
- aggregations
- selectors
- range vectors
- functions
- recording rules
- dashboard variables
- regex selectors
- likely counter/gauge misuse
- duplicated expressions

## Query normalization

Normalize semantically equivalent formatting where safe.

Store:

```text
raw_query
normalized_query
query_hash
```

Do not rewrite semantics during normalization.

## Query optimization findings

Potential findings:

- unnecessary regex
- unnecessary labels
- repeated expensive expressions
- duplicate queries
- excessive cardinality
- opportunity for recording rules
- repeated range queries

Recommendations must be evidence-based.

Do not claim a query is faster unless performance was actually measured or the claim is explicitly marked as a static analysis recommendation.
