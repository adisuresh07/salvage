# ADR-0010: Honest counterfactual evaluation

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

The buildathon asks for measured batch recovery, but hundreds of real failed
payments and their counterfactual outcomes are unavailable in Test Mode.
Invented performance claims would undermine the project.

## Decision

Generate one seeded synthetic batch with visible scenario facts and separately
held hidden truth. Run retry-all, never-retry, and Salvage against identical
visible inputs. Only the scorer can access hidden truth. Record assumptions,
seed, versions, policy actions, metrics, and real-vs-simulated statement.

Run a sensitivity sweep over probability assumptions (default ±30%). Report
unfavorable metrics and never describe simulated results as real uplift.

## Alternatives considered

- Demo one payment: insufficient batch evidence.
- Generate separate random batches per policy: invalid comparison.
- Claim simulator probabilities as industry data: rejected without sources.
- Use only raw recovery rate: hides attempts, contacts, and safety costs.

## Consequences

### Positive

- Reproducible, auditable comparison.
- Trade-offs are visible.
- Hidden-truth separation prevents policy cheating.

### Negative / trade-offs

- Cannot establish real-world causal uplift.
- Results depend on disclosed assumptions.
- Sensitivity implementation and reporting add scope.

## Verification

- Type/module test prevents hidden truth in policy input.
- Same batch digest for every policy.
- Same seed/version reproduces results and decision hashes.
- Report contains assumptions and real-vs-simulated table.

## Supersedes / superseded by

Initial decision.
