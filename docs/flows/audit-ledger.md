# Flow: Audit Ledger & Hash Chain

**Component:** `src/salvage/audit/` · CLI: `salvage verify-ledger`

The ledger is append-only by application contract. Each entry carries a SHA-256
hash of its canonical content chained to the previous entry's hash. This makes
silent alteration of retained entries detectable without requiring a distributed
consensus system.

```mermaid
flowchart TD
    A(["🔄 Decision pipeline\ncompletes a stage"]) --> B

    B["Collect canonical facts:\n• sequence number\n• event_id, decision_id\n• effective class + advisory class\n• allowed set + action taken\n• Gatekeeper check results\n• Effect / outbox outcomes\n• Fingerprints:\n  reason-map, policy,\n  schema, prompt"]

    B --> C["Encode as canonical JSON\n(deterministic field order\nno timestamps for replay hash)"]

    C --> D["Compute entry hash:\nSHA-256(canonical_json + prev_hash)"]

    D --> E["INSERT ledger_entries:\n• sequence (monotonic)\n• entry_hash (UNIQUE)\n• prev_hash\n• canonical payload"]

    E --> F(["✅ Entry committed\nin same decision transaction"])

    subgraph CHAIN["🔗 Hash chain structure"]
        direction LR
        E0["Entry #0\nprev_hash = '0000...'\nentry_hash = H0"]
        E1["Entry #1\nprev_hash = H0\nentry_hash = H1"]
        E2["Entry #2\nprev_hash = H1\nentry_hash = H2"]
        EN["Entry #N\nprev_hash = H(N-1)\nentry_hash = HN"]

        E0 --> E1 --> E2 --> EN
    end

    F -.-> CHAIN

    subgraph VERIFY["🔍 salvage verify-ledger"]
        V1["Read all entries\nin sequence order"]
        V1 --> V2["For each entry:\nrecompute SHA-256\n(canonical_json + prev_hash)"]
        V2 --> V3{"Computed hash\n= stored entry_hash?"}
        V3 -->|"✅ All match"| V4["Report: chain intact\nDisplay final hash"]
        V3 -->|"❌ Mismatch at seq N"| V5["Report: tampered at seq N\nMark audit_status = failed\nBlock release / demo success"]
    end

    style V4 fill:#14532d,stroke:#22c55e,color:#bbf7d0
    style V5 fill:#4a1919,stroke:#dc2626,color:#fca5a5
    style E0 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style E1 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style E2 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style EN fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
```

## Entry content

Each ledger entry contains:

```json
{
  "sequence": 42,
  "event_id": "evt_...",
  "decision_id": "dec_...",
  "effective_class": "B",
  "advisory_class": "B",
  "allowed_actions": ["schedule_retry"],
  "deterministic_action": "schedule_retry",
  "gatekeeper_checks": {
    "in_allowed_set": true,
    "class_not_hard_stop": true,
    "attempt_cap": true,
    "cooldown_elapsed": true,
    "contact_cap": true,
    "not_on_stop_list": true,
    "adapter_capability": true,
    "amount_currency_match": true,
    "not_prohibited_type": true
  },
  "effect_outcome": "dry_run_recorded",
  "fingerprints": {
    "reason_map": "sha256:abc...",
    "policy": "sha256:def...",
    "schema": "sha256:ghi..."
  },
  "prev_hash": "sha256:...",
  "entry_hash": "sha256:..."
}
```

## Tamper-evidence scope

| Scenario | Detected? |
|----------|-----------|
| Single entry field modified | ✅ Yes — hash mismatch |
| Entry deleted from middle | ✅ Yes — sequence gap + hash chain break |
| Entry appended with wrong prev_hash | ✅ Yes — chain break |
| Entire database replaced | ❌ No — ledger says "tamper-evident", not "immutable" |

## Decision hash (evaluation)

A separate **decision hash** is computed for evaluation replay. It excludes
non-deterministic operational timestamps so that the same seed, reason-map, and
policy version always produce the same hash regardless of wall-clock time.

## Related flows

- [Worker pipeline](./worker-pipeline.md) — appends entries after each stage
- [Evaluation flow](./evaluation-flow.md) — verifies decision hash on replay
