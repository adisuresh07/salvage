# Flow: Triage & Action Class Decision

**Component:** `src/salvage/domain/` + `policy/reason-map.yaml`

Triage maps a raw Razorpay failure reason code to one of four merchant action
classes. The mapping is owned by a versioned YAML file, validated at startup,
and fingerprinted. The model may suggest a class in shadow mode for unknown
reasons but **cannot change the effective class**.

```mermaid
flowchart TD
    A(["📨 Failure reason code\nfrom ingress_event"]) --> B

    B["Normalize reason string\n(lowercase, strip whitespace)"]
    B --> C{"Source field\n= 'risk'?"}

    C -->|"Yes"| RISK["⛔ Effective Class D\nRisk-originated failure\nNo retry, no contact\nOperator review required"]
    C -->|"No"| D

    D{"Explicit hard-stop\nsignal in event?"}
    D -->|"Yes"| HARD["⛔ Effective Class D\nExplicit hard stop\nNo retry, no contact"]
    D -->|"No"| E

    E["Look up reason in\nversioned reason-map.yaml"]
    E --> F{"Entry found\n& status = approved?"}

    F -->|"Not found"| UNK
    F -->|"Found but not approved\n(pending review)"| UNK
    F -->|"Approved"| G

    G{"Optional source/step\nrestrictions match?"}
    G -->|"Restrictions violated"| MISMATCH["⛔ Effective Class D\nReason valid but\ncontext mismatch"]
    G -->|"Match or no restriction"| MAPPED

    subgraph MAPPED["Mapped action classes"]
        CLA["🟦 Class A\nTransient infrastructure failure\nRetry allowed under cap + backoff\nNo customer contact required"]
        CLB["🟨 Class B\nTiming / available-funds failure\nLater retry under larger cooldown\nPre-final informational message allowed"]
        CLC["🟧 Class C\nInstrument / authentication problem\nNo retry on same rail\nOne alt payment link + one message max"]
        CLD["🟥 Class D\nHard stop / review required\nNo retry, no contact\nOperator escalation only"]
    end

    UNK["❓ Unknown / ambiguous reason\nEffective Class D\nreview required flag set"]

    UNK --> ADV_SHADOW
    MAPPED --> ADV_SHADOW

    subgraph ADV_SHADOW["💬 Advisory shadow (annotation only)"]
        ADV_SHADOW1{"Advisor\nconfigured?"}
        ADV_SHADOW1 -->|"Yes"| ADV_SHADOW2["suggest_class task\nfor unknown reasons"]
        ADV_SHADOW2 --> ADV_SHADOW3["Store advisory class\nas annotation ONLY\nCannot change effective class"]
        ADV_SHADOW1 -->|"No"| ADV_SHADOW4["Skip advisory"]
    end

    ADV_SHADOW3 --> OUT
    ADV_SHADOW4 --> OUT
    RISK --> OUT
    HARD --> Out2
    MISMATCH --> Out2

    Out2(["⛔ Effective Class D\npassed to Rulebook"])
    OUT(["✅ Effective class\npassed to Rulebook"])

    style RISK fill:#4a1919,stroke:#dc2626,color:#fca5a5
    style HARD fill:#4a1919,stroke:#dc2626,color:#fca5a5
    style MISMATCH fill:#4a1919,stroke:#dc2626,color:#fca5a5
    style UNK fill:#3b1f00,stroke:#f97316,color:#fed7aa
    style CLA fill:#1e3a5f,stroke:#3b82f6,color:#bfdbfe
    style CLB fill:#3b2e00,stroke:#eab308,color:#fef08a
    style CLC fill:#3b1800,stroke:#f97316,color:#fed7aa
    style CLD fill:#4a1919,stroke:#dc2626,color:#fca5a5
    style ADV_SHADOW3 fill:#2d1b69,stroke:#8b5cf6,color:#ddd6fe
```

## Reason map entry schema

```yaml
# policy/reason-map.yaml
- reason: "insufficient_funds"
  class: B
  rationale: "Customer account lacks funds; retry after cooldown may succeed."
  source_ref: "Razorpay error code docs §4.2"
  review_state: approved
  # optional:
  source_restrictions: []   # e.g. ["payment"] — restrict to specific event sources
  step_restrictions: []     # e.g. ["charge"] — restrict to specific payment steps
```

## Class summary

| Class | Cause | Retry | Contact | Stop |
|-------|-------|-------|---------|------|
| **A** | Transient infrastructure | ✅ Capped + backoff | ❌ | Auto after cap |
| **B** | Timing / funds | ✅ Later, large cooldown | ⚠️ Pre-final only | Auto after cap |
| **C** | Instrument / auth | ❌ Same rail | ⚠️ One message max | Immediate |
| **D** | Risk / unknown / hard-stop | ❌ | ❌ | Immediate |

## Related flows

- [Worker pipeline](./worker-pipeline.md) — triage sits inside the worker
- [Gatekeeper checks](./gatekeeper-checks.md) — enforces class constraints downstream
