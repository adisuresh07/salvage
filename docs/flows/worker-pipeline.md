# Flow: Worker Decision Pipeline

**Path:** Asynchronous — processes one queued job at a time.

This is the core decision pipeline. The worker atomically claims a job and drives
it through triage → Rulebook → optional advisory → Gatekeeper → effect intent →
adapter → ledger. Every stage is deterministic except the optional advisor, which
is advisory-only and cannot alter the executable outcome.

```mermaid
flowchart TD
    A([⏰ Worker loop\nnext iteration]) --> B

    B["🔒 Atomically lease next queued job\nSET state=leased, lease_owner, lease_expires_at\nSingle UPDATE … RETURNING"]
    B --> C{"Job\nleased?"}

    C -->|"No jobs"| IDLE([💤 Sleep, retry later])
    C -->|"Yes"| D

    D["📖 Re-read ingress_event\n& payment_state from DB"]
    D --> E

    subgraph TRIAGE["🩺 Triage — reason → class"]
        E["Load versioned YAML reason map\n(validated at startup, fingerprinted)"]
        E --> F{"Reason code\nin approved map?"}
        F -->|"Known + approved"| G["Use configured class\n(A / B / C / D)"]
        F -->|"Risk source or\nexplicit hard-stop"| H["Effective Class D\nregardless of mapping"]
        F -->|"Unknown / ambiguous\n/ invalid"| I["Effective Class D\nreview required flag"]
    end

    G --> POLICY
    H --> POLICY
    I --> POLICY

    subgraph POLICY["📐 Rulebook — pure function, no I/O"]
        POLICY["decide(payment_state, effective_class,\npolicy, injected_now)\n→ PolicyDecision"]
        POLICY --> PD["Outputs:\n• effective class\n• allowed action set\n• deterministic default action\n• next eligible time\n• policy fingerprint"]
    end

    PD --> ADV_CHECK{"Advisor\nconfigured?"}

    ADV_CHECK -->|"No / disabled"| GATE
    ADV_CHECK -->|"Yes"| ADV

    subgraph ADV["💬 Advisor — annotation only"]
        ADV1["Send redacted facts\n+ closed schema to provider"]
        ADV1 --> ADV2["Pydantic-validate response\nOne bounded repair attempt"]
        ADV2 --> ADV3{"Valid\nresponse?"}
        ADV3 -->|"Yes"| ADV4["Store as annotation\nProviderReason recorded"]
        ADV3 -->|"No / timeout / error"| ADV5["Deterministic omission\nJob continues normally"]
    end

    ADV4 --> GATE
    ADV5 --> GATE

    subgraph GATE["🛡️ Gatekeeper — 9 independent checks"]
        GATE["Re-read stored facts\nRecord each check result"]
        GATE --> GATE_R{"All checks\npass?"}
    end

    GATE_R -->|"Reject"| ESC["📢 Operator escalation\nno automated effect\nRecord rejection evidence"]
    GATE_R -->|"Approve"| TX

    subgraph TX["🗄️ Decision transaction"]
        TX["BEGIN IMMEDIATE TRANSACTION\nVerify state version unchanged"]
        TX --> TX2["INSERT decision, gate_checks\nINSERT unique effect_intent\nINSERT outbox row (if B/C)\nUPDATE payment_state\nINSERT ledger entry"]
        TX2 --> TX3["Mark job completed\nCOMMIT"]
    end

    TX3 --> EXEC_CHECK{"Adapter\ncapability\nenabled?"}

    EXEC_CHECK -->|"dry_run"| DRY["📝 dry_run adapter\nRecord intent, no network"]
    EXEC_CHECK -->|"razorpay_test"| RZP["🔌 razorpay_test adapter\nTest Mode operation\nIdempotency key SHA-256"]
    EXEC_CHECK -->|"Capability absent"| DRY

    DRY --> LEDGER
    RZP --> LEDGER

    LEDGER["📋 Append ledger entry\nprev_hash → entry_hash chain\nDecision hash (deterministic)"]
    LEDGER --> DONE([✅ Job complete\nWorker loop continues])

    ESC --> DONE

    style IDLE fill:#1c1c1c,stroke:#555,color:#aaa
    style DONE fill:#14532d,stroke:#22c55e,color:#bbf7d0
    style ESC fill:#3b1f00,stroke:#f97316,color:#fed7aa
    style ADV5 fill:#1c1c1c,stroke:#555,color:#aaa
```

## Concurrency and recovery

| Scenario | Behavior |
|----------|----------|
| Worker crash mid-job | Lease expires; next worker resumes with same idempotency keys |
| State version changed | Transaction aborts; computation retried from fresh read |
| Duplicate job claim | Atomic `UPDATE … WHERE state=queued` prevents dual claiming |
| Advisor outage | Cache/provider fallback, then omit; job continues |
| External API 5xx | Intent stays `retryable`; same idempotency key reused |

## Related flows

- [Webhook ingress](./webhook-ingress.md) — creates the job
- [Triage decision](./triage-decision.md) — detailed class mapping logic
- [Gatekeeper checks](./gatekeeper-checks.md) — the 9 checks expanded
- [Audit ledger](./audit-ledger.md) — hash chain structure
