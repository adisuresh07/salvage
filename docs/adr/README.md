# ADR index and process

Architecture decision records capture choices that are consequential, costly to
reverse, safety-relevant, or likely to be questioned later.

## Status vocabulary

- **Proposed:** under review; implementation must not assume acceptance.
- **Accepted:** current decision.
- **Deprecated:** retained for history but discouraged; not fully replaced.
- **Superseded:** replaced by a named newer ADR.
- **Rejected:** considered and not chosen.

## Filename and template

Use `NNNN-short-kebab-title.md`.

```markdown
# ADR-NNNN: Decision title

- **Status:** Proposed
- **Date:** YYYY-MM-DD

## Context

## Decision

## Alternatives considered

## Consequences

### Positive

### Negative / trade-offs

## Verification

## Supersedes / superseded by
```

## Rules

- Never rewrite an accepted decision into a different decision.
- Small clarifications may be appended with a dated note if they do not change
  the decision.
- Link affected requirements, architecture, test plan, and implementation PR.
- Verification must be observable: test, generated artifact, runtime check, or
  documented operational evidence.
- Record rejected plausible alternatives so future maintainers know they were
  considered.
