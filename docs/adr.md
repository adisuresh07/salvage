# Architecture decision records

This is the human entry point for Salvage's architecture decisions. Individual
records live under [`adr/`](adr/); [`adr/README.md`](adr/README.md) defines the
format and status rules.

## Accepted decisions

| ADR                                                                        | Decision                                                                                                    |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| [ADR-0001](adr/0001-modular-monolith-python-core-react-console.md)         | Use a Python modular monolith with a read-only React/TypeScript console.                                    |
| [ADR-0002](adr/0002-sqlite-storage-and-durable-job-queue.md)               | Use SQLite for MVP persistence and a durable job queue; generate demo databases from text fixtures.         |
| [ADR-0003](adr/0003-fast-authenticated-webhook-ingress.md)                 | Authenticate and durably enqueue webhooks before returning 202; process asynchronously.                     |
| [ADR-0004](adr/0004-deterministic-action-authority-model-advisory-only.md) | Keep all executable action authority deterministic; models are advisory only.                               |
| [ADR-0005](adr/0005-unknown-reasons-fail-closed.md)                        | Treat unknown/ambiguous reasons as effective Class D until a reviewed map change.                           |
| [ADR-0006](adr/0006-effect-intents-idempotency-and-outbox.md)              | Use intent-first idempotent effects and a disabled-by-default message outbox.                               |
| [ADR-0007](adr/0007-append-only-hash-chained-audit-ledger.md)              | Use an append-only-by-contract, hash-chained, tamper-evident ledger.                                        |
| [ADR-0008](adr/0008-provider-neutral-free-and-offline-advisory-layer.md)   | Make advisory providers optional, provider-neutral, free/local, cached, and possible to disable completely. |
| [ADR-0009](adr/0009-layered-test-strategy-jsdom-and-real-browser.md)       | Use layered tests with jsdom for component semantics and Playwright for real-browser behavior.              |
| [ADR-0010](adr/0010-honest-counterfactual-evaluation.md)                   | Compare policies on one seeded batch while exposing assumptions and separating hidden truth.                |
| [ADR-0011](adr/0011-openapi-generated-console-types.md)                    | Generate console API types from FastAPI OpenAPI; do not duplicate contracts.                                |
| [ADR-0012](adr/0012-free-only-mvp-cost-boundary.md)                        | Require a zero-cost offline MVP and prohibit mandatory paid/billing-enabled services.                       |

## Decision precedence

The newest accepted ADR that explicitly supersedes another decision wins.
Editing an accepted ADR to change its decision is prohibited; write a new ADR
and mark the old one superseded.
