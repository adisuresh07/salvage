# Flow: Gatekeeper Checks

**Component:** `src/salvage/domain/` (gatekeeper module)

The Gatekeeper is an independent safety layer that re-reads stored facts and
validates a proposed deterministic action through nine sequential checks. A
single failure converts the effect to an operator escalation. Rejection is never
silently replaced with a more aggressive fallback.

```mermaid
flowchart TD
    IN(["🛡️ Proposed action\n+ PolicyDecision\nenters Gatekeeper"]) --> C1

    C1{"Check 1\nAction in Rulebook\nallowed set?"}
    C1 -->|"❌ Fail"| REJECT
    C1 -->|"✅ Pass"| C2

    C2{"Check 2\nEffective class is not\na hard stop for action?"}
    C2 -->|"❌ Fail (Class D + retry)"| REJECT
    C2 -->|"✅ Pass"| C3

    C3{"Check 3\nAttempt count below\nconfigured cap?"}
    C3 -->|"❌ Fail"| REJECT
    C3 -->|"✅ Pass"| C4

    C4{"Check 4\nCooldown period\nhas elapsed?"}
    C4 -->|"❌ Fail"| REJECT
    C4 -->|"✅ Pass"| C5

    C5{"Check 5\nContact count below\nboth payment &\ncustomer-window caps?"}
    C5 -->|"❌ Fail"| REJECT
    C5 -->|"✅ Pass"| C6

    C6{"Check 6\nPayment / customer\nnot on manual stop list?"}
    C6 -->|"❌ Fail"| REJECT
    C6 -->|"✅ Pass"| C7

    C7{"Check 7\nAdapter declares\nrequired capability?"}
    C7 -->|"❌ Fail"| REJECT
    C7 -->|"✅ Pass"| C8

    C8{"Check 8\nAmount & currency equal\nstored immutable\npayment facts?"}
    C8 -->|"❌ Fail"| REJECT
    C8 -->|"✅ Pass"| C9

    C9{"Check 9\nAction is not a\nprohibited type?\n(refund / credit / discount)"}
    C9 -->|"❌ Fail"| REJECT
    C9 -->|"✅ Pass"| APPROVE

    APPROVE(["✅ Gatekeeper approved\nProceed to effect intent\n& adapter execution"])
    REJECT(["🚫 Gatekeeper rejected\nRecord all check results\nConvert to operator escalation\nNo aggressive substitute"])

    style APPROVE fill:#14532d,stroke:#22c55e,color:#bbf7d0
    style REJECT fill:#4a1919,stroke:#dc2626,color:#fca5a5
    style C1 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style C2 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style C3 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style C4 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style C5 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style C6 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style C7 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style C8 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style C9 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
```

## Check reference table

| # | Check | What is verified | Failure result |
|---|-------|-----------------|----------------|
| 1 | Allowed set | Action is in `PolicyDecision.allowed_actions` | Escalation |
| 2 | Hard-stop class | Effective class does not prohibit this action type | Escalation |
| 3 | Attempt cap | `payment_state.attempt_count < policy.max_attempts` | Escalation |
| 4 | Cooldown | `now >= last_attempt_at + policy.cooldown` | Escalation |
| 5 | Contact cap | Both per-payment and per-customer-window limits respected | Escalation |
| 6 | Stop list | `payment_state.manual_stop = false` | Escalation |
| 7 | Adapter capability | Adapter's declared capability set includes action type | Keep dry-run |
| 8 | Amount/currency | Match stored immutable facts (money as integer minor units) | Escalation |
| 9 | Prohibited type | Not a refund, credit, discount, or live payment | Escalation |

## Key guarantees

- **No silent substitution:** A rejected action is never replaced with a harsher fallback.
- **Evidence always recorded:** Every check result is stored in `gate_checks` with its outcome.
- **Re-reads fresh state:** Gatekeeper reads from the database again, not from in-memory computation, preventing race conditions.
- **Class D invariant:** Check 2 makes it structurally impossible for a Class D decision to produce an automated effect.

## Related flows

- [Worker pipeline](./worker-pipeline.md) — Gatekeeper sits after Rulebook
- [Triage decision](./triage-decision.md) — produces effective class consumed by Check 2
