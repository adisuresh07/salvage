# ADR-0013: Isolated local synthetic playground

- **Status:** Accepted
- **Date:** 2026-08-31

## Context

The user requested a hands-on experience after inspecting the read-only console.
Recorded evidence alone does not let a reviewer submit a failure and inspect a
fresh result. Adding operator payment controls would violate ADR-0001 and the
MVP's no-live-money boundary.

## Decision

Add an explicitly synthetic playground, separate from the operator API:

- `GET /demo/v1/playground` lists preset scenarios and recent local tests.
- `POST /demo/v1/runs` accepts a UUID, preset scenario, bounded integer amount,
  and payment method. No payment ID, credential, contact, or arbitrary payload
  can be supplied.
- `GET /demo/v1/runs/{run_id}/receipt` downloads stored evidence as JSON without
  replaying the event. Delivery-duplicate and elapsed-time fields are null for
  this read because it performs no delivery or execution timing measurement.
- Routes exist only in `demo` mode. POST requires an allowlisted loopback origin
  and a custom header; no CORS access is enabled.
- Derive synthetic event/payment IDs from the UUID. Use a separate sibling
  `*-playground.db`, never the operator database or evaluation batch.
- Reuse raw-byte signature helpers, projection, durable queue, worker, Rulebook,
  Gatekeeper, dry-run persistence, and audit verification. This is a local test
  runner, not an actual Razorpay webhook delivery.
- Force cache-only advice and dry-run execution. There is no external API call,
  active charge schedule, payment link, or sent customer message.
- A bounded synchronous invocation processes the local test. ADR-0003's real
  webhook acknowledgement path remains unchanged.
- The single-process demo serializes test submissions and permits at most 200
  distinct events. Duplicates reuse their identity; changed input with the same
  identity is rejected. Results survive page reloads and process restarts.
- Static hosting displays an unavailable message instead of pretending to run
  a backend. The operator `/api/v1` endpoints remain GET-only.

## Alternatives considered

- Client-only simulation: rejected because it would not exercise the backend.
- Mutating operator payment state: rejected because it weakens the trust boundary.
- Requiring provider credentials first: rejected because this usability slice
  must remain free, offline, and safe.

## Consequences

Reviewers can run, replay, inspect, and download evidence without secrets.
The UI now contains a narrowly scoped synthetic mutation surface, not merchant
payment controls. The local-origin guard intentionally prevents the playground
from working on a public static Vercel deployment. Multi-worker/public hosting
would require authentication, rate limits, and transactional global quotas.

## Verification

Test A/B/C/D and unknown scenarios, same-ID replay, changed-input conflict,
origin/header rejection, invalid/extra fields, integer amount bounds, run cap,
disabled non-demo routes, persisted history, and unchanged operator data.
Component tests cover submission, uncertain-response retry identity, display,
validation, and unavailable backend. Verify the browser-to-API-to-SQLite result.

## Supersedes / superseded by

Narrowly supersedes ADR-0001's prohibition of all UI mutation controls for this
isolated synthetic playground only. Read-only operator and no-live-money
requirements remain in force.
