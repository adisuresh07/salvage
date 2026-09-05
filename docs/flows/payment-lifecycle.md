# Payment Recovery Lifecycle Flow

Interactive showcase: [Interactive Lifecycle Diagram (HTML)](html/payment-lifecycle.html)
Specification: [Archify Lifecycle Spec (JSON)](specs/payment-lifecycle.lifecycle.json)

## Overview

The payment recovery lifecycle models the complete state transitions of a failed payment from initial failure reception through triage, evaluation, execution, and terminal resolution.

```mermaid
stateDiagram-v2
    [*] --> Queued: Webhook HMAC verified (202)
    Queued --> Triaging: Worker leases job
    
    state Triaging {
        [*] --> Classify
        Classify --> ClassA: Transient Infra
        Classify --> ClassB: Timing / Funds
        Classify --> ClassC: Instrument / Auth
        Classify --> ClassD: Risk / Stolen / Fraud
    }
    
    ClassA --> Gating: Proposed Retry
    ClassB --> Gating: Proposed Delay Retry
    ClassC --> Gating: Proposed Alt Link
    ClassD --> HardStopped: Immediate Stop (No Gate)
    
    state Gating {
        [*] --> InvariantChecks
        InvariantChecks --> Approved: 9 Checks Pass
        InvariantChecks --> Rejected: Cap Exceeded / Violation
    }
    
    Approved --> RetryScheduled: Class A / B
    Approved --> AltLinkCreated: Class C
    Rejected --> HardStopped: Escalated
    
    RetryScheduled --> Recovered: payment.captured
    RetryScheduled --> HardStopped: Max Attempts Exhausted
    AltLinkCreated --> Recovered: Customer Paid Link
    AltLinkCreated --> HardStopped: Link Expired / Unused
    
    Recovered --> [*]
    HardStopped --> [*]
```

## Action Classes Breakdown
- **Class A**: Exponential backoff retry with strict attempt cap.
- **Class B**: Scheduled delayed retry for funds clearing.
- **Class C**: Single alternative payment link generated.
- **Class D**: Deterministic hard stop with operator escalation.
