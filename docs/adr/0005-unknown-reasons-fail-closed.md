# ADR-0005: Unknown reasons fail closed

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

The deterministic map will not cover every Razorpay reason during the MVP.
Allowing a model classification of an unknown reason to trigger an automated
retry would contradict ADR-0004 and risk misclassifying a risk decline.

## Decision

Unknown, ambiguous, invalid, or unapproved reason-map entries get effective
Class D and `review_required`. A model may suggest a class in shadow mode. A
human can later promote the reason by reviewing evidence and changing the map
through normal tests/review. Existing events are not silently re-decided.

Risk-originated events are Class D regardless of a conflicting generic reason
mapping.

## Alternatives considered

- Trust model classification after schema validation: rejected because schema
  correctness is not policy correctness.
- Map every published reason immediately: infeasible and likely to create poorly
  reviewed policy.
- Random/manual fallback per event: non-reproducible and unsafe.

## Consequences

### Positive

- Coverage gaps are safe and measurable.
- Shadow data can guide future mapping without actuating.
- No provider is required for correctness.

### Negative / trade-offs

- Lower apparent recovery coverage during MVP.
- Operator review queue may grow.
- The demo must report fallback rate plainly.

## Verification

- Property test: any unmapped reason yields no retry/contact effect.
- Golden test for risk source overriding a non-D mapping.
- Evaluation report always includes deterministic-map and fallback coverage.

## Supersedes / superseded by

Supersedes the historical automatic LLM long-tail classification path.
