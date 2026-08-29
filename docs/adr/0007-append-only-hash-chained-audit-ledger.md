# ADR-0007: Append-only hash-chained audit ledger

Status: Accepted

Date: 2026-08-29

## Context

Operators and reviewers need the complete decision chain and evidence that
retained entries were not quietly edited. Ordinary mutable logs do not provide
that signal, while a production-grade external immutable ledger is beyond MVP.

## Decision

Append canonical JSON ledger entries whose hash includes the previous entry
hash. Application code exposes append and verify operations, not update/delete.
Verification reports the first mismatch. The report calls the ledger
tamper-evident, not immutable.

Evaluation uses a separate deterministic decision hash excluding operational
timestamps/IDs that are deliberately variable in live ingestion.

## Alternatives considered

- Plain structured logs: insufficient alteration evidence.
- Database triggers only: useful defense but does not prove content chain.
- Blockchain/external WORM service: unnecessary, costly, and misleading for an
  MVP.

## Consequences

### Positive

- Compact, inspectable audit evidence.
- Replay proof is easy to demonstrate.
- Version fingerprints travel with each decision.

### Negative / trade-offs

- Does not prevent deletion/replacement by a privileged actor.
- Canonical encoding must be stable and tested.
- Schema evolution requires explicit entry versions.

## Verification

- Valid chain, modified content, removed/reordered entry, and wrong previous
  hash tests.
- Cross-process canonical JSON golden vectors.
- Release/demo fails when verification fails.

## Supersedes / superseded by

Initial decision.
