# Connected simulator verification — 2026-08-31

This records development-session evidence for ADR-0014, not production approval
or a claim that all planned acceptance gates are complete. No live-money
credentials, real payment capture, refunds, or customer messaging were used.

## Automated checks

`make check` passes: 52 Python tests, 15 console tests, Python formatting/lint,
static typing, TypeScript compilation, and the Vite production build. One
upstream Starlette/httpx test-client deprecation warning remains.

The connected tests cover five failure scenarios, cloud output validation,
redaction, timeouts, authentication/rate-limit failures, redirect rejection,
no local fallback, decision invariance, replay, and cloud-generation metadata.
Razorpay contract tests cover signed ingress/deduplication, API reconciliation
versus webhook evidence, uncertain order creation, local request guards, and
live-key rejection. A browser-reconnect regression test verifies that transient
refresh warnings clear when saved evidence becomes reachable again.

Mocked provider responses in these tests are not counted as live evidence.

## Actual provider and browser checks

| Check | Observed result |
| --- | --- |
| Ollama Cloud authentication and generation | Successful HTTP 200 from the cloud endpoint; model `gpt-oss:20b`. No local model was started. |
| Cloud gateway-timeout investigation | Run `d3975ea9-3c18-4f64-ab0e-f7d88279664e`: Class A, eight passing checks, dry-run intent, real cloud explanation, valid ledger. Browser create/replay/download controls verified. |
| Cloud risk investigation | Run `3e13aa20-3c20-40ad-8e75-33b54e268f93`: Class D, review escalation, no recovery effect, valid ledger. Actual cloud latency 4.197 seconds; 288 input and 196 output tokens. |
| Prompt provenance | The risk investigation records `operator-explanation-v2` and its prompt fingerprint. v2 explicitly tells the model no recovery was executed. The earlier v1 result is preserved as historical evidence, not rewritten. |
| Razorpay Test Mode authentication | Successful read-only Orders API response using the supplied test credentials. |
| Actual Test Mode order | `order_TWCykhcUbJPmkI`, ₹1,250.00, created for run `49f935b8-90f3-4057-b19f-27d606f3bfe1`. The public key and order, not the API secret, are passed to Checkout. |
| Official Checkout | Razorpay's actual Checkout loaded with a visible Test Mode badge. Completing the payment flow is a user step; no payment success/failure is claimed from merely opening it. |
| Public receiver | Temporary HTTPS tunnel to the dedicated webhook-only app. Unsigned webhook POST returns 401; simulator control path returns 404. Reachability is not webhook-delivery proof. |

## Deployment and secret checks

- Docker image built successfully. An isolated, key-free connected container
  returned ready and served simulator status; `/app/.env` was absent.
- The temporary smoke-test container was stopped and removed. Local development
  services and the webhook tunnel were left running for user testing.
- The connected Compose configuration validates and publishes local controls
  only on loopback. Production multi-user authentication is not implemented.
- Actual secret values were absent from Git-visible source and the browser
  bundle. Private `.env` permissions are owner-only (`0600`); environment files
  are excluded from Docker/Vercel build contexts. Credentials must be rotated
  after this temporary setup because the cloud key was shared in chat.

## Remaining end-to-end gate

The available Razorpay dashboard is signed out. The user must sign in and
register `payment.failed` against the public URL using the separate private
webhook secret, then complete a failed Test Mode payment for the saved order.
Only a matching authenticated delivery stored by the receiver completes the
actual Razorpay webhook gate. At verification time, **no actual Razorpay webhook
delivery had been verified**.

If the temporary tunnel domain is rejected, use the documented zrok/staging
path. Stop the tunnel after the test session. The UI remains a local developer
simulator; static Vercel hosting does not provide its connected Python backend.
