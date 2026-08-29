# Salvage

Salvage is a payment-recovery prototype that reacts to _why_ a Razorpay payment
failed instead of blindly retrying every failure. Deterministic code owns
classification for known reasons, policy, stopping rules, and every executable
action. Models may explain, draft, or advise, but cannot move money or contact a
customer.

> **Status:** documentation-first MVP, not production-ready. Use Razorpay Test
> Mode and synthetic data only. Live credentials and real customer data are
> outside the current scope.

## Start here

1. [Project context](CONTEXT.md)
2. [Documentation map](docs/README.md)
3. [Product requirements](docs/product-requirements.md)
4. [Glossary](docs/glossary.md)
5. [Architecture](docs/architecture.md)
6. [Technology stack](docs/tech-stack.md)
7. [Development toolstack](docs/toolstack.md)
8. [Testing strategy](docs/testing/test-plan.md)
9. [MVP implementation plan](docs/plans/mvp-implementation-plan.md)
10. [Architecture decisions](docs/adr.md)

## Foundational safety claims

- The model is not in the executable money or customer-contact path.
- Unknown reason codes fail closed to human review.
- Class D failures can never produce a retry or customer contact.
- Webhooks are authenticated over their raw bytes, deduplicated, stored, and
  acknowledged before slow work starts.
- Every external effect uses a stable idempotency key.
- Money is represented only as integer minor units.
- The audit ledger is append-only by application contract and hash-chained to
  make silent alteration detectable.
- The offline demo requires no provider key, Razorpay account, or internet.

## Existing source material

The original strategy and explanatory artifacts remain useful historical inputs:

- `TheRecoveryPlay.docx`
- `Salvage-HowItWorks.docx`
- `Salvage-HowItWorks.html`
- `Salvage-diagrams.md`

When those sources conflict with an accepted ADR or a maintained document under
`docs/`, the accepted ADR and maintained document win.

## Repository ownership

This project belongs only to the personal GitHub account `rajpaladitiya`. Never
create or mutate project resources in EC-aware or another organization.

## License

Salvage source code and maintained project documentation are available under the
[MIT License](LICENSE). Third-party dependencies and historical source artifacts
retain their own applicable terms.
