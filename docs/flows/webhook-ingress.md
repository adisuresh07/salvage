# Flow: Webhook Ingress

**Path:** Fast path — response budget under 1 second.

This flow describes how a raw Razorpay `payment.failed` webhook is received,
authenticated, deduplicated, and durably enqueued before the 202 response is
returned. No policy, model, or Razorpay API call occurs in this path.

```mermaid
flowchart TD
    A([🌐 Razorpay sends\npayment.failed webhook]) --> B

    B["📥 POST /webhooks/razorpay\nRead raw body bytes once"]
    B --> C{"X-Razorpay-Signature\n& x-razorpay-event-id\npresent?"}

    C -->|"No"| ERR1["🚫 Return 400\nLog metadata only\nDo not persist"]
    C -->|"Yes"| D

    D["🔐 HMAC-SHA256 verification\nCompute over exact raw bytes\nConstant-time compare"]
    D --> E{"Signature\nvalid?"}

    E -->|"No"| ERR2["🚫 Return 401\nLog rejection metadata\nDo not parse JSON"]
    E -->|"Yes"| F

    F["✅ Parse JSON only after auth\nProject allowlisted fields\nHash raw payload"]
    F --> G["🗄️ BEGIN IMMEDIATE TRANSACTION\nINSERT ingress_events\nON CONFLICT DO NOTHING"]

    G --> H{"First delivery\nor duplicate?"}

    H -->|"First delivery\n(inserted)"| I["➕ INSERT unique job\nstate = queued\nSET event_id FK"]
    H -->|"Duplicate event_id\n(conflict skipped)"| J["⏭️ No new job created\nEvent already stored"]

    I --> K["COMMIT"]
    J --> K

    K --> L["✅ Return 202 Accepted\nAcknowledge to Razorpay"]
    L --> M([🔁 Worker picks up job\nasynchronously])

    style ERR1 fill:#4a1919,stroke:#dc2626,color:#fca5a5
    style ERR2 fill:#4a1919,stroke:#dc2626,color:#fca5a5
    style L fill:#14532d,stroke:#22c55e,color:#bbf7d0
    style K fill:#1e3a5f,stroke:#3b82f6,color:#bfdbfe
```

## Key invariants enforced here

| Invariant | Enforcement point |
|-----------|-------------------|
| Authenticate before parse | HMAC checked before `json.loads()` |
| Idempotent delivery | `ON CONFLICT DO NOTHING` on `event_id` |
| Durability before 202 | Transaction committed before response |
| Raw bytes never retained | Only hash stored, not body |
| No slow work in fast path | Policy/model/API calls happen in worker |

## Related flows

- [Worker pipeline](./worker-pipeline.md) — processes the queued job
- [Gatekeeper checks](./gatekeeper-checks.md) — downstream safety validation
