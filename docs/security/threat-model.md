# Threat model

## Connected Test Mode simulator boundary (ADR-0014)

The connected simulator uses its own SQLite file and loopback-only controls.
Requests cannot supply provider hosts, secrets, contacts, or arbitrary prompts.
Razorpay credentials must be test keys. Public exposure is limited to a
dedicated HMAC-authenticated webhook-only application, which correlates events
to locally created orders. Browser callbacks are untrusted; an explicit API
check verifies payment/order/amount/currency facts. API evidence is not called a
webhook. Only bounded reason codes and deterministic class/action reach Ollama
Cloud; all model responses are schema-validated display annotations.

Credentials stay in ignored server settings excluded from Docker/deployment
contexts. Local files are permission-restricted. Provider errors are mapped to
fixed codes rather than logged raw. Caps limit cloud attempts and test orders;
uncertain external requests are not automatically retried. The simulator is
single-process and not suitable for public control access without authentication.

- **Status:** Required MVP controls
- **Last reviewed:** 2026-08-29

## 1. Scope and assets

The MVP handles test payment metadata and synthetic data only. Protected assets
are:

- Razorpay Test Mode key/secret and webhook secret;
- optional model-provider API keys;
- integrity of reason maps, policies, decisions, effect intents, and ledger;
- availability of webhook ingestion;
- confidentiality of any allowlisted test customer identifiers;
- credibility of evaluation results and real-vs-simulated claims.

Live credentials, real money, and real customer PII are prohibited assets: the
system must not accept them in this phase.

## 2. Security invariants

1. Unauthenticated bytes cannot create an event or job.
2. Duplicate/replayed delivery cannot create another logical effect.
3. Model or webhook text cannot authorize an effect.
4. Unknown or ambiguous reasons fail closed.
5. Class D cannot create retry/customer-contact effects.
6. A browser cannot mutate payment state.
7. Secrets and full raw payloads do not enter logs, reports, caches, or Git.
8. External calls target allowlisted HTTPS origins with fixed timeouts.
9. Evaluation policies cannot read hidden truth.
10. Live mode cannot be enabled by changing one environment variable.

## 3. Threat register

| Threat                       | Attack/failure                                              | Required mitigation                                                                                                        | Test evidence                                         |
| ---------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| Webhook spoofing             | Attacker posts a fabricated failure.                        | Raw-body HMAC-SHA256, required signature, constant-time comparison, secret separation.                                     | Valid/invalid/missing signature contract tests.       |
| Payload mutation             | JSON is parsed/re-encoded before verification.              | Capture raw bytes once; verify before parse; byte-level fixtures.                                                          | Whitespace/key-order mutation tests.                  |
| Replay/duplicate             | Same valid event arrives repeatedly/concurrently.           | Event ID primary key, one job per event, effect-key uniqueness.                                                            | Concurrent duplicate and replay property tests.       |
| Out-of-order events          | Later/earlier payment states arrive unpredictably.          | Versioned state reconciliation; no arrival-order assumption.                                                               | Permuted event sequence tests.                        |
| Prompt injection             | Failure description asks model to refund/ignore policy.     | Redact inputs, closed advisory schema, no model authority, escaped display.                                                | Named adversarial pipeline/UI tests.                  |
| Off-list action              | Defect or malicious advisory proposes unsupported effect.   | Deterministic action enum, allowed-set check, capability check, prohibited-action denylist.                                | Gatekeeper branch/property tests.                     |
| Cap race                     | Concurrent jobs both see remaining capacity.                | State-version check and unique intent within immediate transaction.                                                        | Two-worker race test.                                 |
| Crash after effect intent    | Worker restarts and calls again.                            | Intent-first transaction, stable idempotency key, bounded recovery state.                                                  | Injected crash-window integration tests.              |
| External retry amplification | HTTP retry layer duplicates unsafe request.                 | Retry only documented idempotent/idempotency-keyed operations; bounded attempts.                                           | Adapter request-count tests.                          |
| SQL injection                | External fields reach raw SQL.                              | Parameterized SQL only; identifiers never derived from requests.                                                           | Malicious reason/description fixtures.                |
| Stored XSS                   | Provider/webhook text renders script/HTML.                  | React text rendering, Jinja autoescape, CSP in served console, no raw HTML.                                                | jsdom and Playwright injection tests.                 |
| SSRF                         | Config/input redirects HTTP client to arbitrary host.       | Typed fixed provider origins, redirect policy off/strict, URL allowlist.                                                   | Configuration rejection and redirect tests.           |
| Secret leakage               | Keys committed or logged.                                   | `.env` ignored, sample placeholders, log redaction, local secret scan, no prompt/raw-body logging.                         | Gitleaks plus redaction tests.                        |
| Policy tampering             | Mapping changed without visibility.                         | Fingerprints in decisions/ledger, reviewed YAML, ADR/change test requirements.                                             | Golden diff and fingerprint tests.                    |
| Ledger alteration            | Row edited after decision.                                  | Hash-chain verification and release failure on mismatch.                                                                   | Edit/delete/reorder tamper tests.                     |
| Ledger replacement/deletion  | Attacker replaces whole DB and chain.                       | Explicit residual risk; external signed checkpoint is post-MVP.                                                            | Documentation assertion; no false immutability claim. |
| Hidden-truth leakage         | Policy reads simulator outcome.                             | Separate data types/modules and scorer-only access.                                                                        | API/schema boundary test.                             |
| Denial of service            | Large body, slow provider, queue flood.                     | Body-size limit, fast auth, short transaction, bounded queue/leases, provider timeout off fast path.                       | Size/latency/load tests.                              |
| Dependency compromise        | Malicious/transitively vulnerable package/action.           | Lockfiles, audits, minimal deps, pinned Action SHAs, license inventory.                                                    | CI audit job.                                         |
| Live-mode accident           | Test code receives live credentials or calls live endpoint. | Endpoint fixed to Test Mode configuration, key-prefix/account check where available, no live adapter, future ADR required. | Startup rejection tests.                              |
| Sensitive fixture            | Real payload copied into repository.                        | Synthetic/redacted fixtures, review checklist, secret/PII scan.                                                            | Fixture lint and manual review.                       |

## 4. Data minimization

After authentication, ingress persists only fields needed for policy, audit, and
correlation:

- event ID and type;
- payment/order identifiers;
- integer amount and currency;
- method, reason, source, step, and minimal status;
- received time and raw-payload digest.

Do not persist card number, CVV, OTP, token value, full email/phone, full notes,
or unneeded nested entities. Synthetic fixtures use clearly fake identifiers. If
contact grouping is needed, store a keyed digest of a synthetic/customer
identifier and keep the original out of logs/model prompts.

## 5. Secret handling

- `.env` and provider credential files are ignored.
- `.env.example` contains names and safe placeholders only.
- CI uses environment-scoped secrets only for manual sandbox evidence.
- Pull-request workflows from forks never receive secrets.
- Logs redact header values, authorization, cookies, keys, secrets, tokens, full
  URLs with credentials, and likely contact fields.
- `salvage doctor` reports presence/validity class, never values.
- Rotate any credential immediately if a scan or output exposes it; record the
  incident without reproducing the secret.

## 6. Web security headers

When FastAPI serves the console:

- `Content-Security-Policy: default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy` denying unused sensors/capabilities
- no wildcard CORS in the same-origin profile.

The Vite development server is not exposed through the public webhook tunnel.

## 7. Model security

- Prompts use a task-specific allowlisted object, not a whole webhook.
- Amount, customer contact, secrets, and internal policy limits are omitted
  unless needed for non-executable wording; amount remains unavailable for all
  advisory actions in MVP.
- Treat reason description as quoted data with explicit delimiters.
- Output schema uses enums and length limits; rationale has a small maximum.
- Validate output locally and store provider/model/prompt/schema fingerprints.
- Provider response cannot mutate action, class, caps, time, or recipient.
- Cache contains only redacted semantic inputs and validated outputs.
- Provider failure degrades to omission/review, never permissive action.

## 8. Residual risks

- SQLite and a hash chain do not protect against a privileged user replacing the
  whole database.
- Free cloud providers have external availability, retention, and account policy
  risks despite current documentation.
- Sandbox behavior can differ from live mode.
- Automated accessibility/security scanners do not replace human review.
- Prototype policy values are not legal/compliance certification.
- A single-machine modular monolith has no high-availability guarantee.

These are acceptable only because the MVP uses test/synthetic data and no live
money. Production work requires a new threat model and ADR set.

## 9. Security release checklist

The local synthetic playground (ADR-0013) adds a deliberately isolated test
surface. Only demo mode registers it. POST requires a fixed loopback origin and
custom header; no CORS access is provided. Closed schemas prohibit payment IDs,
contacts, credentials, or arbitrary payloads; amounts are bounded integer minor
units. The single-process test runner limits distinct runs to 200, persists only
synthetic facts in a separate sibling database, and forces cache-only advice and
dry-run effects. This guard is not authentication for a public service: exposing
the playground beyond loopback requires a new deployment/security review.

- All security/adversarial tests pass.
- Gitleaks reports no finding in files or history.
- Python and Node lockfile audits are reviewed; high/critical runtime findings
  block release.
- No live endpoint, real transport, or production credential path exists.
- CSP and escaped adversarial strings are verified in Playwright.
- Policy/map fingerprints appear in decisions and reports.
- Ledger verification passes after a clean demo rebuild.
- Public-repository history is inspected before visibility changes.
