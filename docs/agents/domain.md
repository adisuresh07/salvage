# Domain documentation

This repository uses a single-context documentation model.

## Required reading order

Before changing the system, read the relevant parts of:

1. `CONTEXT.md` — product purpose, boundaries, actors, and domain overview.
2. `docs/glossary.md` — canonical domain vocabulary.
3. `docs/architecture.md` — system structure, components, and data flows.
4. `docs/tech-stack.md` — approved languages, frameworks, and libraries.
5. `docs/toolstack.md` — development, quality, testing, and delivery tools.
6. `docs/testing/test-plan.md` — testing strategy, suites, and release gates.
7. `docs/adr/` — accepted architecture decisions relevant to the change.

Proceed silently if a referenced file has not been created yet.

## Layout

```text
/
├── AGENTS.md
├── CLAUDE.md
├── CONTEXT.md
└── docs/
    ├── glossary.md
    ├── architecture.md
    ├── tech-stack.md
    ├── toolstack.md
    ├── adr/
    │   ├── README.md
    │   └── NNNN-decision-title.md
    └── testing/
        └── test-plan.md
```

## Source-of-truth rules

- Use terms exactly as defined in `docs/glossary.md`.
- Do not introduce synonyms for established domain concepts without updating the
  glossary.
- Accepted ADRs record why consequential decisions were made.
- When documents conflict, the newest accepted ADR takes precedence.
- Update architecture, stack, testing, and glossary documents in the same change
  when implementation makes them inaccurate.
- Proposed decisions must not silently replace accepted decisions.
- Explicitly identify conflicts with existing ADRs.
- Keep `AGENTS.md` and `CLAUDE.md` synchronized.

## Decision records

Create an ADR when a decision:

- changes a system boundary or data flow;
- introduces or replaces a significant dependency;
- affects security, privacy, money movement, auditability, or reliability;
- changes testing or release guarantees;
- is costly to reverse;
- rejects a plausible alternative future maintainers may reconsider.

Each ADR must include context, decision, alternatives, consequences, status, and
verification requirements.
