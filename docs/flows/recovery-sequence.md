# End-to-End Payment Recovery Sequence Flow

Interactive showcase: [Interactive Sequence Diagram (HTML)](html/recovery-sequence.html)
Specification: [Archify Sequence Spec (JSON)](specs/recovery-sequence.sequence.json)

## Overview

The end-to-end recovery sequence details the timeline and ownership boundaries from the initial `payment.failed` webhook delivery to final ledger sealing.

```mermaid
sequenceDiagram
    autonumber
    participant RZ as Razorpay Test Mode
    participant ING as Webhook Ingress
    participant DB as SQLite WAL Store
    participant WRK as Recovery Worker
    participant RBK as Rulebook Engine
    participant GTK as Gatekeeper Gate
    participant ADP as Effect Adapter
    participant LDG as Audit Ledger

    RZ->>ING: POST /webhooks/razorpay (payment.failed + HMAC)
    ING->>ING: Verify HMAC signature over raw bytes
    ING->>DB: INSERT event + job (ON CONFLICT DO NOTHING)
    DB-->>ING: Inserted (or duplicate acknowledged)
    ING-->>RZ: 202 Accepted (< 15ms)
    
    WRK->>DB: Atomically lease next queued job (SET state=leased)
    WRK->>RBK: Triage error code & evaluate policy
    RBK-->>WRK: PolicyDecision (action, allowed set, delays)
    WRK->>GTK: Validate proposed action against 9 invariants
    GTK-->>WRK: Approved (all 9 checks pass)
    WRK->>DB: BEGIN TX: record decision + state mutation
    WRK->>ADP: Execute effect intent + idempotency key
    ADP-->>WRK: Execution result (dry_run / rzp_test)
    WRK->>LDG: Append hash-chained audit entry (prev_hash -> entry_hash)
```

## Key Invariants in Sequence
- **Sub-second ACK**: Fast path returns 202 before slow processing begins.
- **Atomic Lease**: Multiple worker instances cannot lease the same job concurrently.
- **Deterministic Evaluation**: Pure rulebook has zero network or clock dependencies.
- **Pre-execution Gate**: Gatekeeper re-reads state to guarantee fresh checks before execution.
