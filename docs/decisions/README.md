# Decision records

Decision records preserve the reason for consequential choices that would be
costly or confusing to reverse. They do not restate feature requirements or act
as a changelog.

Use a record when a choice:

- changes a dependency boundary or architectural invariant;
- commits the project to a substantial platform or framework;
- resolves an important tradeoff likely to be questioned later; or
- reverses a previous recorded decision.

Do not create one for ordinary implementation details.

## Format

```markdown
# NNNN — Short decision title

Status: Proposed | Accepted | Superseded
Date: YYYY-MM-DD

## Context
What forces a choice?

## Decision
What is chosen?

## Consequences
What becomes easier, harder, or intentionally deferred?
```

Number records sequentially. Do not edit an Accepted decision to conceal a new
direction; add a superseding record and link both.

## Records

- [`0001-python-pyside.md`](0001-python-pyside.md) — Python and PySide6 for the
  initial desktop prototype (**Accepted**)
