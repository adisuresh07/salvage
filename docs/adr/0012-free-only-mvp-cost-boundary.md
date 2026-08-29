# ADR-0012: Free-only MVP cost boundary

Status: Accepted

Date: 2026-08-29

## Context

The project is an MVP/working prototype. The user requires free tools only. Free
cloud tiers can change or incur overage if billing is enabled, so “uses a free
tier” is weaker than “runs without the service.”

## Decision

The mandatory build, complete offline test suite, demo, evaluation, and report
must cost zero and use free/open-source local software. Hosted free tiers may
provide optional evidence only. No automatic paid fallback or billing-enabled
resource is permitted.

Create the GitHub repository under personal owner `rajpaladitiya`, private
initially. Use included CI quota with zero paid overage, then public standard
runners when the repository passes publication review.

## Alternatives considered

- Small paid hosted database/model/deployment: rejected because it makes the
  demo dependent on billing and availability.
- Free-tier-only cloud architecture: rejected because terms/limits can change.
- No CI: rejected; local fallback plus free CI is achievable.

## Consequences

### Positive

- Anyone can reproduce the core proof.
- No surprise spend.
- Provider/platform outages do not block acceptance.

### Negative / trade-offs

- No production hosting or managed observability.
- Cloud evidence volume is limited.
- Local setup owns more responsibility.

## Verification

- Offline demo runs with network denied and no keys.
- Documentation lists cost/license posture for direct dependencies.
- CI billing limit remains zero/no paid overage.
- No required setup step asks for payment details.

## Supersedes / superseded by

Initial decision.
