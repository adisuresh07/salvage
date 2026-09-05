# Flow: Local Synthetic Playground

**Component:** `src/salvage/api/` (demo routes) · API: `POST /demo/v1/runs`

> **Offline, local-only.** No network, no provider key, no Razorpay account
> required. Uses a separate database (`data/salvage-playground.db`). Only
> available when the API runs in demo mode. Seeded evaluation data is never
> modified by a playground test.

The playground is a bounded synchronous test runner for the local operator.
It submits preset synthetic failures through the real deterministic pipeline
and returns a receipt with the actual decision, ledger verification, and
per-event record counts.

```mermaid
flowchart TD
    A(["🖥️ Console /demo\nPlayground panel"]) --> B

    B["GET /demo/v1/playground\nFetch: presets, recent tests\nremaining local capacity"]
    B --> C["Operator selects preset\nfailure scenario"]

    C --> D["POST /demo/v1/runs\n• preset failure ID\n• synthetic payment facts\n• unique UUID\n(no real payment IDs,\nno contacts, no credentials)"]

    D --> GUARD

    subgraph GUARD["🔐 Guards (loopback only)"]
        G1["Origin check:\nloopback IP only"]
        G1 --> G2["Custom header check:\nX-Demo-Request present"]
        G2 --> G3["Demo mode check:\nroute registered only\nif SALVAGE_DEMO=true"]
    end

    GUARD --> E["Route to separate\nplayground SQLite DB\n(data/salvage-playground.db)"]

    E --> F

    subgraph PIPELINE ["Real deterministic pipeline"]
        F["Ingress projection (synthetic facts only)"]
        F --> G["Triage → Rulebook → Gatekeeper"]
        G --> H["Effect intent created\n(dry-run adapter ONLY\ncache-only advice forced)"]
        H --> I["Ledger entry appended"]
    end

    I --> J["Synchronous response\n(no async worker needed)"]

    J --> K["Return receipt:\n• decision + effective class\n• gatekeeper results\n• per-event record counts\n• ledger verification result\n• idempotency key"]

    K --> L["GET /demo/v1/runs/{run_id}/receipt\nDownload stored evidence as JSON\n(read-only, no replay triggered)"]

    L --> OUT(["✅ Evidence stored\nOperator data unchanged\nSeeded eval data unchanged"])

    style OUT fill:#14532d,stroke:#22c55e,color:#bbf7d0
    style G1 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style G2 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
    style G3 fill:#1c2a3a,stroke:#3b82f6,color:#e2e8f0
```

## Isolation guarantees

| Constraint | Enforcement |
|------------|-------------|
| Separate database | `data/salvage-playground.db` never touches `salvage.db` |
| Dry-run effects only | `dry_run` adapter forced; no network calls |
| Cache-only advice | `SALVAGE_LLM=cache-only` forced for playground routes |
| No real payment IDs | Input schema rejects Razorpay-format IDs |
| Loopback only | Route middleware checks `request.client.host` |
| No operator data change | Playground DB is separate; operator tables untouched |

## API surface (demo mode only)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/demo/v1/playground` | `GET` | Presets, recent tests, remaining capacity |
| `/demo/v1/runs` | `POST` | Submit a synthetic failure and get decision |
| `/demo/v1/runs/{run_id}/receipt` | `GET` | Download stored evidence JSON |

## Related flows

- [Worker pipeline](./worker-pipeline.md) — same pipeline, synchronous in playground
- [Simulator flow](./simulator-flow.md) — the opt-in connected alternative
- [Evaluation flow](./evaluation-flow.md) — batch evaluation (separate from playground)
