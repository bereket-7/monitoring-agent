# First MVP Scope

Do not build everything in the documentation immediately.

The first useful product should do exactly this:

```text
1. Connect to Grafana.
2. Select a dashboard.
3. Read its panels and PromQL.
4. Connect to Prometheus.
5. Execute relevant queries.
6. Validate:
   - success rate
   - error rate
   - total request consistency
   - time-range consistency
   - filter consistency
7. Show findings with evidence.
8. Ask the AI:
   "Is the success rate correct?"
9. Return the calculation, queries, values, and limitations.
```

## Example expected output

```text
Success Rate Validation
=======================

Result: VALID

Successful requests: 121,820
Total requests:      125,430

Calculation:
121,820 / 125,430 × 100 = 97.12%

Error rate:
3,610 / 125,430 × 100 = 2.88%

Consistency:
121,820 + 3,610 = 125,430 ✓

Scope:
service=payment-api
environment=production
time=09:00-10:00 UTC

Evidence:
- Panel: API Success Rate
- Panel: API Error Rate
- Panel: Request Count
- Prometheus queries executed successfully

Limitations:
- Success is defined as HTTP 2xx/3xx according to the configured metric semantics.
```

The exact numbers above are illustrative only. The application must calculate real values from the configured monitoring system.
