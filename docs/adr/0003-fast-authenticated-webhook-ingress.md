# ADR-0003: Fast authenticated webhook ingress

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

Razorpay requires a 2xx response within five seconds, retries failed deliveries,
and may disable a persistently failing endpoint. Webhooks are at-least-once, may
be duplicated/out of order, and must be authenticated using the exact raw
request body.

## Decision

Ingress verifies HMAC-SHA256 over raw bytes before parsing, requires the unique
event header, projects allowlisted fields, inserts event and job atomically, and
returns 202. Duplicate authenticated deliveries return 202 without a new job.
All policy, model, external API, and report work happens after response in the
worker.

## Alternatives considered

- Inline processing: rejected due to provider/network latency and disablement
  risk.
- Acknowledge before durable persistence: rejected because accepted work could
  disappear on crash.
- Parse then re-serialize for HMAC: rejected as incorrect.
- External managed queue: rejected for cost/setup; SQLite is enough for MVP.

## Consequences

### Positive

- Large timeout margin and durable accepted work.
- Duplicate delivery becomes routine behavior.
- Provider outages cannot slow webhook acknowledgement.

### Negative / trade-offs

- Eventual rather than inline decisions.
- Requires queue monitoring and dead-letter handling.
- SQLite write contention must remain within a strict budget.

## Verification

- Raw-byte signature mutation tests.
- Local p95 <100 ms, p99 <250 ms, hard test <1 second.
- Duplicate and out-of-order integration tests.
- Test that model/Razorpay HTTP adapters cannot be reached from route handling.

## Supersedes / superseded by

Initial decision.
