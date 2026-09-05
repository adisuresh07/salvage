# Glossary

Use these terms in code, tests, issues, UI copy, and documentation. Avoid the
listed ambiguous synonyms where present.

| Term                       | Canonical meaning in Salvage                                                                                                                         |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Action class               | One of A, B, C, or D; a merchant-automation category derived deterministically for a known reason.                                                   |
| Adapter capability         | A declared effect type a configured adapter can actually perform. Missing capability means no execution.                                             |
| Advisory classification    | A model-suggested class recorded for review or evaluation. It cannot become the effective class automatically.                                       |
| Advisory response          | Any model output. It has no execution authority until deterministic code validates and uses it only in an allowed advisory role.                     |
| Allowed action set         | Actions the Rulebook says are permissible for the supplied state. An executor cannot go outside it.                                                  |
| Attempt                    | One policy-counted recovery try. Its precise definition is fixed in policy data and tests.                                                           |
| Attempt cap                | Maximum attempts allowed by policy for a payment/class.                                                                                              |
| At-least-once delivery     | A webhook may arrive more than once. Duplicate delivery is expected, not exceptional.                                                                |
| Audit ledger               | Ordered decision records used to explain what happened. Application code only appends.                                                               |
| Backoff                    | Deterministic delay schedule between Class A attempts.                                                                                               |
| Baseline                   | A comparison policy, currently `retry_all_3x` or `never_retry`.                                                                                      |
| Batch                      | Versioned set of payment scenarios evaluated together.                                                                                               |
| Canonical JSON             | Stable JSON encoding with defined key ordering and formatting, used as hash input.                                                                   |
| Class A                    | Known transient infrastructure failure; bounded retry may be allowed, no contact.                                                                    |
| Class B                    | Known timing/funds condition; later bounded retry may be allowed.                                                                                    |
| Class C                    | Known instrument/authentication issue; no same-rail retry, one alternative ask may be allowed.                                                       |
| Class D                    | Hard stop or review required; no retry and no automated customer contact.                                                                            |
| Compliance violation       | In the MVP evaluator, an automatic retry or customer contact on an effective Class D scenario. This is a project metric, not a legal conclusion.     |
| Contact                    | One customer-facing outbox intent, regardless of whether a transport sends it.                                                                       |
| Contact cap                | Maximum contacts allowed for a payment/customer window.                                                                                              |
| Cooldown                   | Minimum deterministic time between eligible effects.                                                                                                 |
| Counterfactual             | Outcome estimated for the same scenario under a different policy.                                                                                    |
| Customer guidance          | Advice describing what a customer may do. It is distinct from merchant automation policy.                                                            |
| Dead letter                | Job that exhausted bounded processing attempts and awaits operator review.                                                                           |
| Decision                   | Immutable record of inputs, policy versions, allowed actions, selected deterministic action, validation, and outcome.                                |
| Decision hash              | Hash of deterministic decision content used for replay comparison. It excludes live-only timestamps where specified.                                 |
| Deterministic              | The same defined inputs and versions produce the same decision. It does not promise identical uncached model wording or live timestamps.             |
| Doorman                    | Informal name for webhook ingress. Use `ingress` in package/module names.                                                                            |
| Dry-run effect             | Persisted effect intent that deliberately does not call an external service.                                                                         |
| Dunning                    | Recovery attempts and communications after a payment failure.                                                                                        |
| Effective class            | Class that policy is allowed to use. Unknown reasons have effective Class D in the MVP.                                                              |
| Effect                     | Externally observable action or durable intent, such as scheduling a retry, creating a link, or queuing a message.                                   |
| Effect intent              | Durable record created before an adapter call, with a unique idempotency key.                                                                        |
| Effectively-once           | One logical effect despite retries, achieved through idempotency and uniqueness. Do not call this guaranteed exactly-once delivery.                  |
| Eval harness               | Deterministic runner that compares policies over the same batch and hidden truth.                                                                    |
| Fail closed                | Resolve uncertainty to no automated action and human review.                                                                                         |
| Fallback rate              | Fraction of scenarios not resolved by the deterministic known-reason map.                                                                            |
| Gatekeeper                 | Deterministic validator that independently checks an effect before execution.                                                                        |
| Golden case                | Human-readable input and expected decision used as a reviewed contract test.                                                                         |
| Hash chain                 | Each ledger entry includes the prior entry hash. Alteration becomes detectable downstream; deletion prevention is not implied.                       |
| Hidden truth               | Synthetic recovery outcome data available only to the evaluator, never to a policy.                                                                  |
| Idempotency key            | Stable digest of effect identity used to prevent duplicate logical effects.                                                                          |
| Ingress event              | Authenticated, allowlisted projection of a received webhook.                                                                                         |
| Job lease                  | Time-bounded claim allowing one worker to process a queued job.                                                                                      |
| Ledger hash                | Hash linking a ledger entry to its predecessor. It is not the same as the replay decision hash.                                                      |
| Live mode                  | Razorpay environment involving real payment activity. Prohibited in the MVP.                                                                         |
| Long tail                  | Published failure reasons not yet in the deterministic map.                                                                                          |
| Merchant automation policy | Rules governing what the merchant system may do automatically.                                                                                       |
| Minor units                | Integer smallest currency unit; INR 1,234.56 is `123456` paise.                                                                                      |
| Model contract test        | Test that validates output shape, allowed values, fallback, and rates rather than exact prose.                                                       |
| Money path                 | Components that can authorize or create a monetary/customer-contact effect. Models are excluded.                                                     |
| Operator escalation        | Internal review record or console state. It is not customer contact.                                                                                 |
| Outbox                     | Durable table of messages/effects waiting for a pluggable delivery adapter.                                                                          |
| Planner                    | Historical source-doc term for a model choosing an action. In the maintained architecture the replacement is `advisor`, with no execution authority. |
| Policy fingerprint         | Digest of the exact normalized policy data used for a decision.                                                                                      |
| Prompt fingerprint         | Digest covering task, schema, prompt version, and semantic input for advisory caching.                                                               |
| Property-based test        | Generated test that searches many inputs for a violated invariant.                                                                                   |
| Pure function              | Function whose result depends only on explicit inputs and has no clock, randomness, network, database, or mutation side effect.                      |
| Razorpay Test Mode         | Sandbox with test credentials and no real money. Some operations and behaviors differ from live mode.                                                |
| Reason code                | Machine-readable Razorpay failure reason, such as `insufficient_funds`.                                                                              |
| Reason-map fingerprint     | Digest of the exact normalized reason mapping used for a decision.                                                                                   |
| Recovery                   | Successful payment outcome in real flows or a clearly labelled synthetic outcome in evaluation.                                                      |
| Replay                     | Reprocess the same defined evaluation inputs and compare deterministic decisions/hashes.                                                             |
| Review required            | Internal terminal state that blocks automated effects until future human action outside MVP.                                                         |
| Rulebook                   | Pure deterministic policy engine returning allowed actions and the default action. Use `policy` in package/module names.                             |
| Seed                       | Fixed input that makes synthetic generation reproducible.                                                                                            |
| Sensitivity sweep          | Re-running evaluation while varying assumptions over a documented range.                                                                             |
| Shadow mode                | Compute and record an advisory result without allowing it to influence effects.                                                                      |
| Stop list                  | Explicit payment/customer entry blocking automated effects.                                                                                          |
| Structured output          | Model response requested in a schema and always validated again in application code.                                                                 |
| Synthetic scenario         | Generated payment state with labelled assumptions and hidden truth.                                                                                  |
| Test Mode adapter          | Razorpay integration configured exclusively with test credentials and capability restrictions.                                                       |
| Triage                     | Deterministic mapping of a known reason to an effective class.                                                                                       |
| Unknown reason             | Reason absent from the approved map; effective Class D, optionally shadow-classified.                                                                |
| Webhook                    | HTTPS event notification from Razorpay.                                                                                                              |
| Webhook event ID           | Value of `x-razorpay-event-id`, used as the delivery deduplication key.                                                                              |
| Wasted attempt             | Evaluator retry against a scenario that cannot recover on that rail under hidden truth.                                                              |

## Local test interface

**Synthetic playground:** a local-only interface for creating isolated test
events, processing them through the shared pipeline, and inspecting dry-run
receipts. It is not a Razorpay Test Mode integration or live recovery control.

**Connected simulator:** opt-in local console using actual Ollama Cloud calls
and Razorpay Test Mode orders. Its synthetic events, API-observed failures, and
signed webhook deliveries have distinct provenance (ADR-0014).

**Cloud generation:** one persisted advisory attempt with a stable run ID,
model, timestamp, usage, latency, and an explicit success/unavailable status.

**API-observed failure:** a failed payment fetched server-side from Razorpay and
correlated to a test order. It is not evidence of webhook delivery.

## Avoided language

- Avoid **exactly once**; say **effectively-once logical effect**.
- Avoid **immutable ledger**; say **append-only by contract and
  tamper-evident**.
- Avoid **AI decision**; say **advisory suggestion** or **deterministic
  decision**.
- Avoid **real recovery rate** for simulator output; say **synthetic evaluation
  result**.
- Avoid **compliant** as a legal guarantee; name the tested project invariant.
