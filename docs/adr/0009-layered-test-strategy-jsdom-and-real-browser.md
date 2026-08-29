# ADR-0009: Layered tests using jsdom and real browsers

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

Safety claims need cheap exhaustive domain tests, while the console needs fast
component tests and some real-browser confidence. jsdom emulates DOM APIs but
does not perform layout or real navigation, so using it as the only UI test
environment would leave known gaps.

## Decision

Use:

- pytest examples and Hypothesis properties for policy/Gatekeeper invariants;
- real temporary SQLite files for persistence and queue integration;
- respx/MSW for network contracts;
- replay, golden, advisory contract, and adversarial suites;
- Vitest with jsdom and Testing Library for component semantics/interactions;
- Playwright for navigation, layout, responsive behavior, CSP, focus, and
  cross-browser release evidence;
- a small manual Razorpay Test Mode evidence suite separate from CI.

Target 100% branch coverage for Rulebook and Gatekeeper, not a misleading
repository-wide 100% target.

## Alternatives considered

- Jest: viable but less aligned with Vite and jsdom setup.
- happy-dom: faster, but jsdom is requested and implements more browser APIs.
- jsdom only: rejected for layout/navigation limitations.
- Playwright only: too slow for exhaustive component/domain feedback.
- snapshot-heavy tests: rejected because they overfit markup and understate
  behavior.

## Consequences

### Positive

- Fast local feedback and realistic release checks.
- Explicit ownership for each type of failure.
- Safety properties receive stronger testing than UI cosmetics.

### Negative / trade-offs

- Multiple runners and fixtures.
- Browser downloads and CI time.
- Test boundaries must be maintained to avoid duplication.

## Verification

- Test plan maps every requirement/invariant to a suite.
- jsdom tests contain no layout assertions.
- Chromium runs on pull requests; all three engines before release.
- Sandbox tests are marked and cannot run without explicit Test Mode config.

## Supersedes / superseded by

Initial decision.
