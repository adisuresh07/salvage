# External assumptions and verification register

Last verification pass: 2026-08-29

External platforms change. This file distinguishes verified behavior from
project assumptions. Re-check items marked “day-one test” against the actual
account before implementation depends on them.

| Claim                                                                                                  | Status                                                          | Consequence                                                                                                                                      | Primary source                                                                                        |
| ------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| Razorpay webhook endpoints must return a 2xx within 5 seconds.                                         | Verified 2026-08-29                                             | Ingress persists and returns 202 before slow work; CI guardrail is 1 second.                                                                     | [Setup/edit payments webhooks](https://razorpay.com/docs/webhooks/setup-edit-payments/)               |
| Failed deliveries are retried over 24 hours and continuing failure disables the webhook.               | Verified 2026-08-29                                             | Durable dedupe and alerting are mandatory.                                                                                                       | [Setup/edit payments webhooks](https://razorpay.com/docs/webhooks/setup-edit-payments/)               |
| Signature validation must use the exact raw request body and HMAC-SHA256.                              | Verified 2026-08-29                                             | Authenticate before JSON parsing; retain fixtures for byte-level tests.                                                                          | [Validate and test webhooks](https://razorpay.com/docs/webhooks/validate-test/)                       |
| Duplicate deliveries are expected and `x-razorpay-event-id` identifies them.                           | Verified 2026-08-29                                             | Database primary/unique key provides dedupe.                                                                                                     | [Webhook FAQ](https://razorpay.com/docs/webhooks/faqs/)                                               |
| Webhook order is not guaranteed.                                                                       | Verified 2026-08-29                                             | State transitions cannot assume arrival order.                                                                                                   | [Validate and test webhooks](https://razorpay.com/docs/webhooks/validate-test/)                       |
| Webhook URLs use ports 80 or 443.                                                                      | Verified 2026-08-29                                             | Use a supported HTTPS share/staging host.                                                                                                        | [About webhooks](https://razorpay.com/docs/webhooks/)                                                 |
| Common request-interceptor/tunnel domains may be blacklisted; Razorpay documents zrok.                 | Verified 2026-08-29                                             | Default local tunnel tool is `zrok2`.                                                                                                            | [Validate and test webhooks](https://razorpay.com/docs/webhooks/validate-test/)                       |
| Test cards and a mock-bank success/failure choice can create test scenarios without real money.        | Verified 2026-08-29                                             | Sandbox evidence uses documented cards and generic reason parsing.                                                                               | [Test card details](https://razorpay.com/docs/payments/payments/test-card-details/)                   |
| Test subscription card tokens permit subsequent debit only within three days.                          | Verified 2026-08-29                                             | Create sandbox subscription evidence close to the test run.                                                                                      | [Test subscriptions](https://razorpay.com/docs/payments/subscriptions/test/)                          |
| Test subscription charges can be triggered from the Dashboard.                                         | Verified 2026-08-29                                             | Manual evidence is possible, but should not be presented as an automated API retry.                                                              | [Test subscriptions](https://razorpay.com/docs/payments/subscriptions/test/)                          |
| Standard Payment Links have a Test Mode limit of 30 per business.                                      | Verified 2026-08-29                                             | Keep sandbox evidence small and use dry-run for batch evaluation.                                                                                | [Create Standard Payment Link](https://razorpay.com/docs/api/payments/payment-links/create-standard/) |
| UPI Payment Links are unsupported in Test Mode.                                                        | Verified 2026-08-29                                             | Use Standard Payment Links or dry-run; do not promise Test Mode UPI link execution.                                                              | [Create Standard Payment Link](https://razorpay.com/docs/api/payments/payment-links/create-standard/) |
| `payment_risk_check_failed` customer guidance suggests another card, but it is a fraud/risk decline.   | Verified 2026-08-29                                             | Merchant automation intentionally treats it as Class D.                                                                                          | [Card error codes](https://razorpay.com/docs/errors/payments/cards/)                                  |
| Test Mode SMS/email suppression returns success without delivery.                                      | Not confirmed in the current docs reviewed                      | Do not rely on suppression. The MVP disables real transports and uses its own outbox regardless. Verify manually if demonstrating notifications. | Day-one test; record evidence in `INCIDENTS.md`.                                                      |
| The published reason list contains “roughly 130” reasons.                                              | Historical source claim; exact current count not re-established | Never encode the count as a contract. Report actual map coverage against the fetched/versioned reference set.                                    | [Razorpay payment error list](https://razorpay.com/docs/errors/payments/list/)                        |
| Ollama has a $0 Free plan with cloud access, one concurrent model, and variable session/weekly limits. | Verified 2026-08-29                                             | Optional only; no fixed call budget is assumed.                                                                                                  | [Ollama pricing](https://ollama.com/pricing)                                                          |
| Ollama Cloud currently does not support structured outputs.                                            | Verified 2026-08-29                                             | Prompt for JSON, validate locally, bound repair/fallback; never trust provider shape.                                                            | [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)                  |
| Groq strict structured outputs support GPT-OSS 20B and 120B.                                           | Verified 2026-08-29                                             | Optional strict provider still passes local Pydantic validation.                                                                                 | [Groq structured outputs](https://console.groq.com/docs/structured-outputs)                           |
| Groq Free Plan lists 30 RPM, 1K RPD, 8K TPM and 200K TPD for GPT-OSS 20B/120B.                         | Verified 2026-08-29; account limits may differ                  | Cache semantic tasks; inspect actual account headers/limits before provider evaluation.                                                          | [Groq rate limits](https://console.groq.com/docs/rate-limits)                                         |
| GitHub Actions standard runners are free for public repositories.                                      | Verified 2026-08-29                                             | Keep local `make check`; private repo uses only included quota until public.                                                                     | [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)  |

## Project assumptions to expose in every evaluation

- Recovery probabilities are synthetic unless backed by a cited dataset.
- Class mix and amount distribution are generator inputs, not merchant facts.
- Retry scheduling defaults are prototype policy, not a recommendation.
- A simulated success means the hidden synthetic truth allowed recovery, not
  that Razorpay processed real money.
- “Compliance violation” is the project's tested Class D invariant, not legal
  certification.
- Sensitivity sweep range is ±30% around each recovery-probability assumption
  unless the evaluation manifest declares another range.

## Day-one verification checklist

- Receive one valid Test Mode `payment.failed` webhook and record its headers
  and allowlisted shape.
- Confirm one invalid signature is rejected.
- Confirm duplicate event ID behavior through the public endpoint.
- Confirm which documented test cards/reasons are reproducible in this account.
- Confirm Standard Payment Link creation and its Test Mode limits/capability.
- Confirm whether any notification is delivered in Test Mode; keep transport
  disabled either way.
- Confirm zrok domain acceptance and teardown behavior.
- Inspect actual Ollama/Groq free-account limits before any repeated test.
