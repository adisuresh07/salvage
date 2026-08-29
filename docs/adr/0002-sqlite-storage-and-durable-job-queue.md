# ADR-0002: SQLite storage and durable job queue

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

The MVP needs events, state, jobs, effect intents, outbox, advisory cache,
ledger, and evaluation results. Requiring Redis/Postgres would make clean-clone
reproduction harder and add free-hosting constraints. In-memory queues would
lose work on crash.

The source concept proposed committing a seeded database. Binary databases are
hard to review and can embed stale schema or accidental sensitive data.

## Decision

Use one SQLite database per runtime profile with explicit SQL migrations,
foreign keys, WAL mode, bounded busy timeout, unique constraints, and short
transactions. Implement a lease-based jobs table as the durable queue and run
one worker by default.

Commit text fixtures, migrations, and validated advisory-cache fixtures.
Generate demo database files deterministically; do not commit them as source of
truth.

## Alternatives considered

- PostgreSQL + Redis/Celery: rejected for setup and operational cost.
- In-memory queue: rejected because webhook acknowledgement would precede
  durable work.
- Commit a populated SQLite database: rejected for reviewability, schema drift,
  and data hygiene.
- ORM: rejected because the small safety-critical schema benefits from visible
  SQL and constraints.

## Consequences

### Positive

- Zero service setup and zero mandatory cost.
- Real transactional constraints and crash recovery.
- Demo state is reproducible and reviewable from text inputs.

### Negative / trade-offs

- Single-writer limitations and explicit busy handling.
- Not a production high-availability design.
- Query/result conversion requires disciplined handwritten code.

## Verification

- Migration-from-empty test.
- Two-worker lease race and expired-lease recovery tests.
- Duplicate event/decision/effect uniqueness tests.
- Clean demo rebuild produces the same deterministic hashes.

## Supersedes / superseded by

Supersedes the historical suggestion to commit a seeded database.
