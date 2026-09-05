# ADR-0001: Python modular monolith with a read-only React console

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

The MVP must be built quickly, run from a clean clone, keep money-affecting
logic highly testable, and still present an operator-friendly UI. A distributed
system or two independently authoritative backends would consume time and make
policy consistency harder.

## Decision

Implement one Python package containing ingress, domain policy, worker,
persistence, execution adapters, audit, evaluation, API, and CLI. Run API and
worker as separate processes/invocations when needed, but deploy them from the
same codebase.

Implement a React/TypeScript static console that reads versioned GET endpoints.
It contains no payment policy and no mutation controls.

## Alternatives considered

- TypeScript for the entire system: viable, but Python provides Pydantic,
  Hypothesis, and numeric evaluation leverage.
- Python-rendered HTML only: simpler, but weaker interactive operator UX and
  does not exercise the requested jsdom/component test stack.
- Microservices: rejected as unnecessary operational complexity.
- Full-stack React/Next.js: rejected because server rendering and Node backend
  add no safety benefit here.

## Consequences

### Positive

- One source for policy and data contracts.
- Strong Python property testing and schema validation.
- UI can evolve independently as a read-only projection.
- Simple local execution and debugging.

### Negative / trade-offs

- Two language toolchains and lockfiles.
- Generated OpenAPI types are required to prevent boundary drift.
- SQLite file coordination must be explicit between API and worker.

## Verification

- No TypeScript module defines action-class or retry policy.
- Console API client types are generated from OpenAPI.
- Architecture dependency test forbids domain imports from adapter/API layers in
  the wrong direction.

## Supersedes / superseded by

Initial decision.

2026-08-31: [ADR-0013](0013-isolated-local-synthetic-playground.md) introduces
an isolated, demo-only synthetic playground. It narrowly supersedes the ban on
all UI mutation controls; the operator API remains read-only.
