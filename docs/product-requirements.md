# Product requirements

- **Status:** Approved for MVP planning
- **Last reviewed:** 2026-08-29

## 1. Product statement

Salvage classifies known payment-failure reasons into a merchant action class,
computes a bounded deterministic decision, refuses unsafe action, and compares
that policy against blind-retry and never-retry baselines over the same batch.

## 2. Primary users

- A merchant operator investigating recovery decisions.
- A reviewer evaluating safety, reproducibility, and engineering judgment.
- A developer maintaining the reason map, policy, and tests.

The customer is affected by a real production recovery system but is not an
interactive user of this prototype.

## 3. MVP journeys

### PR-01 — Receive a failed-payment event

Given a Razorpay Test Mode webhook, the system verifies the HMAC over the raw
body, rejects invalid signatures, deduplicates the event ID, stores an
allowlisted event projection and a job in one transaction, and returns a 2xx
response without running policy or model work inline.

### PR-02 — Produce a deterministic decision

The worker maps a known reason, evaluates policy from explicit state and an
injected clock, selects the deterministic default action, validates it through
the Gatekeeper, and records the complete decision.

### PR-03 — Fail closed on uncertainty

An unmapped reason, invalid policy state, missing required fact, provider
failure, or invalid model response cannot produce a retry or customer contact.
It becomes review-required and is visible to the operator.

### PR-04 — Create effects safely

Approved effects are stored as effect intents with stable idempotency keys.
Supported Test Mode adapters may execute them. Unsupported effects remain
dry-run records. A repeated job cannot create a second logical effect.

### PR-05 — Inspect the chain

The operator console shows reason, effective class, model suggestion if any,
allowed actions, deterministic decision, Gatekeeper checks, effect state, outbox
state, and ledger verification without offering write controls.

### PR-06 — Evaluate the policy

The evaluator runs `retry_all_3x`, `never_retry`, and `salvage` over the same
seeded batch and hidden truth. It reports recovery rate, recovered minor units
per attempt, wasted attempts, customer contacts, compliance violations, and
fallback rate.

### PR-07 — Prove replay behavior

Rebuilding the evaluation database from the same fixtures, seed, policy version,
and fixed clock produces the same decision sequence and final decision-ledger
hash. Live timestamps are not part of this claim.

### PR-08 — Demonstrate offline

One command runs the demo without network access, API keys, or a Razorpay
account by using committed fixtures, a generated SQLite database, cached
validated advisory responses, and deterministic adapters.

## 4. Functional requirements

| ID     | Requirement                                                                                                        | MVP acceptance evidence                        |
| ------ | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------- |
| FR-001 | Verify `X-Razorpay-Signature` over raw bytes using HMAC-SHA256 and constant-time comparison.                       | Negative/positive webhook tests.               |
| FR-002 | Deduplicate on `x-razorpay-event-id` with a database uniqueness constraint.                                        | Concurrent duplicate test.                     |
| FR-003 | Tolerate duplicate and out-of-order webhook delivery.                                                              | Integration fixtures and state tests.          |
| FR-004 | Acknowledge stored events with 202 within the local performance budget.                                            | Performance test and timing log.               |
| FR-005 | Map known reason codes from reviewable YAML, not branches.                                                         | Schema and golden-map tests.                   |
| FR-006 | Record reason-map and policy fingerprints with every decision.                                                     | Decision schema assertion.                     |
| FR-007 | Compute policy as a pure function of supplied state, policy, and time.                                             | Unit and property tests.                       |
| FR-008 | Keep executable action selection deterministic.                                                                    | ADR-0004 and tests forbidding model authority. |
| FR-009 | Fail unknown reasons to review-required effective Class D.                                                         | Unit, property, and E2E tests.                 |
| FR-010 | Re-check allowed set, class stop, caps, cooldown, contact limit, stop list, and capability before effect creation. | Gatekeeper branch coverage.                    |
| FR-011 | Store stable idempotency keys and enforce uniqueness.                                                              | Replay and crash-window tests.                 |
| FR-012 | Store messages in an outbox; do not send real messages in MVP.                                                     | Outbox integration test.                       |
| FR-013 | Append canonical ledger entries linked by SHA-256.                                                                 | Verify and tamper tests.                       |
| FR-014 | Cache advisory calls by task/schema/prompt/input/provider/model fingerprint.                                       | Cache hit/miss/version tests.                  |
| FR-015 | Support `SALVAGE_LLM=off`.                                                                                         | Offline demo and CI.                           |
| FR-016 | Expose versioned read-only JSON endpoints for the console.                                                         | OpenAPI contract tests.                        |
| FR-017 | Generate TypeScript API types from the backend OpenAPI schema.                                                     | Clean-generation CI diff.                      |
| FR-018 | Generate evaluation JSON and static HTML from the same result object.                                              | Golden result schema test.                     |
| FR-019 | Maintain a real-vs-simulated statement with every evaluation.                                                      | Report content assertion.                      |
| FR-020 | Provide CLI verbs for doctor, demo, seed, work, eval, and verify-ledger.                                           | CLI smoke tests.                               |

## 5. Provisional policy defaults

These are transparent prototype assumptions, not industry recommendations. They
live in versioned policy data and may change only with tests and an ADR.

| Class | Retry                                                               | Contact                                 | Default outcome                                            |
| ----- | ------------------------------------------------------------------- | --------------------------------------- | ---------------------------------------------------------- |
| A     | At most 3 total attempts, backoff schedule supplied by policy data. | None.                                   | Schedule retry when cap and cooldown pass; otherwise stop. |
| B     | At most 2 total attempts with at least a 12-hour cooldown.          | At most one pre-final outbox message.   | Schedule later retry or stop.                              |
| C     | No same-rail retry.                                                 | One payment link and one message total. | Create one test/dry-run link, then stop.                   |
| D     | Never.                                                              | Never customer contact.                 | Record and escalate to operator.                           |

Global controls include a manual stop list, explicit adapter capabilities, and a
per-customer contact window. Policy code never infers permission from a model
response.

## 6. Non-functional requirements

### Safety

- Zero Class D retry or customer-contact effects.
- Zero off-list effects.
- No real customer data, card data, or live API credentials.
- No UI endpoint that mutates payment state.

### Reliability

- At-least-once webhooks become one stored event and one logical decision.
- Jobs use leases, bounded retries, and a terminal dead-letter state.
- The offline path has no network dependency.

### Performance

- Local webhook handler target: p95 below 100 ms and p99 below 250 ms.
- Hard application guardrail: finish well before Razorpay's 5-second response
  window; CI fails at 1 second to retain margin.
- Console read endpoints target p95 below 250 ms for the seeded dataset.

### Reproducibility

- Pin runtime and dependency versions in lockfiles.
- Inject time, IDs, and random seed in evaluation mode.
- Commit text fixtures and cached validated responses; generate database files.

### Accessibility

- Operator views meet WCAG 2.2 AA intent for semantics, keyboard use, contrast,
  focus, and status communication.

### Cost

- A clean offline run costs zero.
- Mandatory components are free/open source.
- Optional cloud calls must stay within free plans and have a hard off switch.
- No billing-enabled resource may be required for MVP acceptance.

## 7. Excluded from MVP acceptance

- Live mode, production credentials, real notifications, and real automatic
  retries.
- A model choosing an executable action.
- Admin authentication or multi-user authorization.
- Complete merchant policy for all payment methods and jurisdictions.
- Claims that the hash chain prevents deletion or provides legal immutability.
- Claims that simulation establishes real recovery uplift.

## 8. Release acceptance

Release requires all mandatory gates in `testing/test-plan.md`, an accepted ADR
set, verified documentation links, an empty secret scan, a passing offline demo,
and a recorded sandbox evidence run or a clearly documented external blocker.
