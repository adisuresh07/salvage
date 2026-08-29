# ADR-0011: Generate console types from OpenAPI

Status: Accepted

Date: 2026-08-29

## Context

Python owns the data contracts while TypeScript consumes them. Handwritten
interfaces can drift silently, especially around enums, nullability, and error
states.

## Decision

Generate a deterministic OpenAPI JSON artifact from FastAPI/Pydantic and use
`openapi-typescript` to generate console types. Commit both generated artifacts
for review. CI regenerates and fails on a diff. The console may add view models
but cannot redefine transport contracts.

## Alternatives considered

- Handwritten TypeScript interfaces: rejected for drift.
- Share Zod schemas across a Node backend: incompatible with the chosen Python
  core.
- Runtime code generation only: hurts clean-clone review and offline builds.

## Consequences

### Positive

- One contract source with reviewable diffs.
- Compile-time detection of backend/UI drift.
- Easier MSW fixtures and API tests.

### Negative / trade-offs

- Generated files and regeneration step.
- Pydantic/OpenAPI expressiveness must remain compatible with the generator.
- Type generation is not runtime validation; API tests remain necessary.

## Verification

- Clean-generation CI diff.
- Representative success/error responses validate against Pydantic schemas.
- TypeScript compilation covers all API response handling.

## Supersedes / superseded by

Initial decision.
