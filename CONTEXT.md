# Salvage domain context

Last reviewed: 2026-08-29

## Purpose

Salvage is a Razorpay AI Buildathon Track 03 prototype. It demonstrates that
payment recovery can be safer and more efficient when the merchant responds to
the failure reason rather than applying one blind retry schedule.

The prototype must be easy to inspect, deterministic where decisions matter,
safe when providers fail, honest about simulated outcomes, and runnable at no
cost from a clean clone.

## Problem

A failed payment is not one condition. Infrastructure outages, insufficient
funds, broken payment instruments, and risk declines require different merchant
behavior. Applying the same retry policy to all of them wastes attempts, annoys
customers, and can create unacceptable behavior such as automatically retrying a
risk-declined payment.

Razorpay documentation primarily describes what a customer should do next.
Salvage defines a separate merchant-automation policy: what the merchant's
system may safely do automatically.

## Product thesis

> Read the reason, apply a deterministic merchant policy, take the smallest
> permitted action, and refuse to act when action would be unsafe.

## Actors

- **Merchant operator:** inspects decisions, stopped items, batch results, and
  ledger integrity.
- **Razorpay Test Mode:** emits payment events and accepts supported test API
  operations.
- **Customer:** represented only by synthetic/test records in the MVP; no real
  customer should be contacted.
- **Policy maintainer:** reviews reason mappings, action-class definitions,
  limits, and ADRs.
- **Model provider:** optional advisory dependency used for text and shadow
  classification; never an authority for executable actions.
- **Reviewer or judge:** clones the repository and runs the offline demo and
  tests without secrets.

## Bounded contexts

This is a single-context repository with these internal areas:

- **Ingress:** verify, deduplicate, project, persist, and acknowledge webhooks.
- **Triage:** map a known reason to a merchant action class.
- **Policy:** compute a deterministic decision and allowed action set.
- **Advice:** optionally obtain model suggestions or wording without authority.
- **Gatekeeping:** independently validate a proposed deterministic effect.
- **Execution:** create idempotent effect intents and invoke a test adapter.
- **Audit:** append decision facts and verify the hash chain.
- **Evaluation:** compare policies against the same hidden synthetic truth.
- **Console:** render read-only operational and evaluation views.

## Four action classes

### Class A — transient infrastructure failure

The customer and instrument are not known to be at fault. A retry may be
scheduled under a deterministic cap and backoff. No customer contact is
required.

### Class B — timing or available-funds failure

An immediate retry is unlikely to help. A later retry may be scheduled under a
larger cooldown and a strict cap. A pre-final informational message may be
queued if policy allows it.

### Class C — instrument or authentication problem

Repeatedly retrying the same rail cannot resolve the issue. Do not retry it. The
prototype may create one alternative payment link and queue at most one customer
message, then stop.

### Class D — hard stop or review required

Do not retry and do not contact the customer automatically. Record the reason
and surface the item to an operator. Risk-originated failures and unknown reason
codes are effective Class D in the MVP.

## Model boundary

The model may:

- suggest a class for an unmapped reason in shadow mode;
- explain why a deterministic decision was made;
- draft customer or operator wording from non-sensitive facts;
- summarize a batch.

The model may not:

- select the executable action;
- change the effective class of an unmapped reason;
- set retry time, cap, cooldown, amount, recipient, or stop-list state;
- issue a refund, credit, discount, payment, or customer contact;
- override the Rulebook or Gatekeeper.

## Real and simulated boundary

Real in the MVP:

- source code, decision pipeline, webhook validation, SQLite transactions,
  reason taxonomy, policy, gatekeeper, idempotency, outbox, ledger, API, and
  console;
- Razorpay Test Mode webhooks and explicitly supported test API calls when
  sandbox credentials are supplied;
- optional model calls when a free/local provider is configured.

Simulated in the MVP:

- batch volume;
- whether a hypothetical retry would recover a payment;
- customer behavior over time;
- recovery probabilities and the counterfactual ground truth;
- unsupported automatic retry effects.

Simulation assumptions are inputs, not facts. They must be visible, versioned,
and tested with a sensitivity sweep.

## Non-goals

- Production payment orchestration or live money movement.
- Storing real card data, credentials, or customer PII.
- Sending real SMS or email.
- Multi-merchant tenancy, billing, SSO, or role administration.
- A complete mapping of every Razorpay failure reason.
- A distributed queue, horizontally scaled database, or high-availability
  deployment.
- Claiming exactly-once delivery from an external network.
- Treating simulated recovery output as an industry benchmark.

## Invariants

1. Effective Class D produces no retry and no customer-contact effect.
2. An action executed by an adapter must be in the deterministic Rulebook's
   allowed set and pass every Gatekeeper check.
3. Unknown reason codes fail closed.
4. Attempt and contact caps cannot be exceeded by replay, concurrency, or
   duplicate webhook delivery.
5. The same idempotency key cannot create two effect records.
6. Amounts are integers in minor units and never enter a model prompt.
7. Raw webhook bytes are authenticated before parsing.
8. The read-only console cannot trigger payment effects.
9. A model outage cannot prevent the deterministic pipeline from completing.
10. Live mode is impossible without an explicit future ADR and separate
    configuration path.

## Success definition

The MVP is complete when a clean clone can run an offline seeded batch, compare
three policies, generate `results.json` and a report, show zero Salvage Class D
violations, replay to the same deterministic decision hash, and pass the release
test suite. Sandbox tests must demonstrate at least one valid failure, one
duplicate delivery, one invalid signature, and one hard-stop decision through
the same core pipeline.
