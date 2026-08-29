# ADR-0006: Effect intents, idempotency, and outbox

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

Webhook redelivery, job retry, process crash, and network ambiguity can repeat
execution. External systems do not provide a universal exactly-once guarantee.
Test Mode communication behavior can also differ from real delivery.

## Decision

Persist an effect intent before any external call. Give it a stable unique
idempotency key derived from versioned effect identity. Adapters reuse that key
and have bounded retry/state transitions.

Customer/operator messages are durable outbox rows. The MVP has no real customer
transport; it renders the outbox in console/report. Only an explicit future
adapter/ADR can send.

## Alternatives considered

- Call external API then write result: rejected because crash loses knowledge
  and encourages duplicate calls.
- Mark complete before external call: rejected because work can be lost.
- Rely only on provider idempotency: rejected because not every operation has
  identical semantics and local replay still needs a record.
- Send Test Mode notifications directly: rejected as unreliable and unnecessary
  for proof.

## Consequences

### Positive

- Replays create one logical effect.
- Pending/ambiguous effects are inspectable and recoverable.
- Message proof does not depend on delivery.

### Negative / trade-offs

- More states and crash-window tests.
- Exactly-once is still not claimed.
- External reconciliation may be needed after ambiguous timeouts.

## Verification

- Duplicate effect-key constraint tests.
- Crash before call, during call, and after response/before update tests.
- Adapter request assertions reuse the same key.
- Outbox has no enabled network transport in MVP configuration.

## Supersedes / superseded by

Initial decision.
