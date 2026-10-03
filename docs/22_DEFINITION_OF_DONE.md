# Definition of Done

A feature is complete only when:

## Code

- typed
- documented
- modular
- no unnecessary dependency
- no secrets
- no debug code

## Tests

- unit tests
- integration tests where appropriate
- regression test for fixed bugs

## Agent

- bounded tool calls
- deterministic validation preserved
- evidence included
- uncertainty represented
- no unsupported claims

## External systems

- timeouts
- error handling
- retries only when safe
- rate-limit handling

## Security

- least privilege
- secrets protected
- logs redacted
- untrusted monitoring data treated as data

## Documentation

Update relevant docs when:

- API changes
- data model changes
- architecture changes
- validation semantics change
- new tool is introduced

## Release checklist

```text
[ ] Tests pass
[ ] Ruff passes
[ ] mypy passes
[ ] Integration tests pass
[ ] Evaluation regression passes
[ ] No secrets committed
[ ] No unauthorized write tools
[ ] Evidence is reproducible
[ ] Documentation updated
[ ] Docker build succeeds
```
