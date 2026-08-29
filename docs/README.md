# Documentation map

This directory is the maintained source of truth for Salvage.

## Reading order

1. [`../CONTEXT.md`](../CONTEXT.md) — purpose, scope, actors, and invariants.
2. [`product-requirements.md`](product-requirements.md) — what the MVP must do.
3. [`glossary.md`](glossary.md) — canonical project vocabulary.
4. [`architecture.md`](architecture.md) — components, flows, data, APIs, and
   trust boundaries.
5. [`tech-stack.md`](tech-stack.md) — runtime and library decisions.
6. [`toolstack.md`](toolstack.md) — development, quality, and delivery tools.
7. [`testing/test-plan.md`](testing/test-plan.md) — test strategy and gates.
8. [`security/threat-model.md`](security/threat-model.md) — threats and
   mitigations.
9. [`plans/mvp-implementation-plan.md`](plans/mvp-implementation-plan.md) —
   ordered delivery plan.
10. [`adr.md`](adr.md) and [`adr/`](adr/) — accepted decision history.

## Authority order

When maintained documents conflict, use this order:

1. Newest accepted ADR relevant to the issue.
2. `CONTEXT.md` invariants and product boundaries.
3. Product requirements and architecture.
4. Stack, toolstack, testing, and security details.
5. Plans and roadmap dates.
6. Historical source documents at repository root.

Do not silently resolve a conflict. Update the affected documents in the same
change and call out any ADR that must be superseded.

## File ownership

- Product or policy change: update `CONTEXT.md`, requirements, glossary, and
  relevant ADRs.
- Component or data-flow change: update architecture and an ADR.
- Dependency change: update tech stack, toolstack if relevant, lockfiles, and
  the dependency ADR.
- Test guarantee change: update the test plan and ADR-0009.
- External platform claim: update `assumptions-and-verification.md` with its
  last-verified date and primary source.

## Documentation quality gate

Every maintained Markdown file must pass formatting, spelling allowlist, local
link validation, and a manual contradiction review. Commands live in
`toolstack.md`; CI ownership lives in the test plan.
