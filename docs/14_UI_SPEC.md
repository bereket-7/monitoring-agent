# UI Specification

## MVP

Build a web application with:

1. Dashboard selector
2. Time range selector
3. Filter selector
4. Dashboard overview
5. Findings panel
6. Agent chat
7. Evidence panel

## Layout

```text
+---------------------------------------------------------+
| Dashboard | Time Range | Environment | Service          |
+---------------------------------------------------------+
|                                                         |
|                 Grafana / dashboard view                |
|                                                         |
+-----------------------------------+---------------------+
| Validation Findings               | AI Agent            |
|                                   |                     |
| ERROR Success rate                | Ask a question...  |
| WARNING Filter not propagated     |                     |
| INFO Duplicate query              |                     |
+-----------------------------------+---------------------+
| Evidence / Query / Calculation                          |
+---------------------------------------------------------+
```

## Finding UX

Each finding should show:

- severity
- title
- panel
- explanation
- observed values
- expected values
- query
- time range
- filters
- recommendation

## Agent UX

The agent should expose tool/evidence progress in a compact form:

```text
Analyzing dashboard...
✓ Read panel 12
✓ Executed PromQL
✓ Compared success/error/total
✓ Validation complete
```

Do not expose hidden chain-of-thought. Show concise tool actions and evidence only.

## Accessibility

- keyboard navigation
- semantic HTML
- readable contrast
- no information conveyed only by color
