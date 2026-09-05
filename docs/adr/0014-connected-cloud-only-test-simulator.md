# ADR-0014: Connected cloud-only Test Mode simulator

- **Status:** Accepted
- **Date:** 2026-08-31

## Context

The user explicitly requested actual Ollama Cloud responses and Razorpay Test
Mode integration, supplied credentials, and prohibited local-model fallback.
The original offline playground does not meet that connected-use requirement.

## Decision

Add an opt-in connected simulator, separate from both the seeded evaluation and
ADR-0013's offline fixtures. Preserve the existing Python/httpx and React stack.

- Store runs, provider order IDs, webhook deliveries, cloud results, and an audit
  chain in a separate SQLite file. Reserve a UUID before external work. One run
  has at most one failure decision, one order-creation attempt, and one cloud
  generation attempt. Reopening/replaying reads the original evidence.
- The local UI may create an original Razorpay **Test Mode order** and open
  Standard Checkout. This is not an automatic recovery effect. Only test keys
  are accepted; the adapter has no refund, capture, or live-payment methods.
- Browser success/failure callbacks are notifications, never proof. An explicit
  server-side Orders Payments API check verifies the order, amount, currency,
  and status. An API-observed failure is labelled `razorpay_api`, not a webhook.
- A dedicated `payment.failed` receiver authenticates raw bytes, correlates to
  a locally created test order, and atomically stores the event, job, and
  delivery evidence before returning 202. Duplicate deliveries add a delivery
  count, not another effect. Other attempts on the same order do not replace the
  run's first failure evidence.
- A single background worker commits the deterministic decision with advice off
  before requesting Ollama Cloud. Then it saves a validated explanation and
  separate audit annotation. Model output cannot alter the decision hash,
  effective class, action, amounts, or effects.
- Cloud requests go directly to `https://ollama.com/api/chat`. No local AI,
  provider fallback, automatic generation retry, or canned substitute exists.
  Unknown/failed/invalid advice is visible. Prompt inputs contain only bounded
  reason codes and deterministic class/action, not IDs, money, or contacts.
- Cloud metadata includes a stable ID, requested model, timestamps, token usage,
  and latency. Cost is explicitly unknown when the provider does not report it.
  Interrupted generations/orders are marked uncertain, not silently repeated.
- All recovery effects remain dry-run and all customer transports disabled.
  Synthetic recovery percentages below the simulator are not connected results.
- Local controls require loopback Host, an allowlisted Origin for POST, and a
  custom header. Hard caps are 200 runs and 30 order attempts. This is a
  single-process developer simulator, not public multi-user authentication.

## Webhook exposure

The dashboard stays local. `salvage.api.webhook_public:app` exposes only the
signed receiver on a separate port; docs, console, and control APIs are absent.
The preferred zrok flow requires separate account setup. For this development
session, allow an account-free Cloudflare Quick Tunnel to **that receiver only**.
This explicitly amends the toolstack's default-tunnel guidance for this case.
Use the random temporary hostname, not a branded domain. It has no uptime
guarantee, changes after restart, and may be rejected by Razorpay. Only a real
received delivery establishes end-to-end webhook verification. No claim of
delivery is based on tunnel reachability alone. Stop the tunnel after the user
finishes the test session. Never expose the main API or an Ollama endpoint.

## Alternatives considered

- Local Ollama or fixture fallback: rejected by the user's explicit requirement.
- Cloud-only rule selection: rejected because the money path must be deterministic.
- Client-reported payment failure as a webhook: rejected as unauthenticated and misleading.
- Public hosting of unauthenticated controls: rejected. Docker deployment remains
  supported; public multi-user hosting needs an additional authentication ADR.
- Static-only Vercel/Sites deployment: cannot supply the persistent Python worker
  or webhook runtime and is not a substitute for the connected simulator.

## Verification

Verify cloud success, invalid JSON, timeout, 429, redirects, no local fallback,
prompt redaction, hard-stop invariance, persisted generations, and replay.
Verify test-order creation, no automatic retry after uncertain creation,
API payment correlation, signed delivery/deduplication, invalid signatures,
unchanged offline data, origin guards, caps, and live-key rejection.
Run a small number of actual cloud calls and test orders; browser-check the
controls and provider Checkout. Dashboard registration and actual webhook
delivery are separate evidence gates, not implied by mocked contract tests.

## Supersedes / superseded by

Narrowly supersedes ADR-0001's UI-mutation restriction and ADR-0008's local/provider
fallback options for this opt-in simulator. ADR-0013 remains the offline fixture
tool. ADR-0004's deterministic authority and the no-live-money boundary remain.
