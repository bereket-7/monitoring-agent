# Cursor Development Workflow

## Rule

Do not ask Cursor to build the entire system in one shot.

Implement one phase at a time.

For each phase:

1. Read relevant docs.
2. Inspect existing code.
3. State implementation plan.
4. Implement small increments.
5. Run tests.
6. Run lint/type checks.
7. Update documentation.
8. Stop when acceptance criteria are met.

## Cursor behavior

Cursor should:

- preserve existing working behavior
- avoid unnecessary dependencies
- prefer standard library/simple solutions where practical
- use typed interfaces
- write tests with new logic
- never silently change API contracts
- never add write access to monitoring systems without explicit approval
- never hard-code secrets
- never fabricate external API responses in production code

## Required response after each task

Cursor should summarize:

```text
Implemented:
- ...

Tests:
- ...

Validation:
- ...

Files changed:
- ...

Known limitations:
- ...
```

## Debugging protocol

When a test fails:

1. reproduce
2. inspect failure
3. identify root cause
4. implement minimal fix
5. rerun focused test
6. rerun full suite

Do not hide failures by weakening tests.

## Dependency policy

Before adding a package:

- determine whether existing dependencies solve the problem
- explain why the dependency is necessary
- prefer mature packages
- pin compatible versions
