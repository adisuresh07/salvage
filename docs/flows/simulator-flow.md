# Flow: Connected Cloud Simulator

**Component:** `src/salvage/simulator/` · API: `POST /simulator/v1/runs`

> **Opt-in only.** Requires `SALVAGE_SIMULATOR_ENABLED=true`, valid Ollama Cloud
> API key, and Razorpay Test Mode credentials. Uses a separate SQLite database
> (`data/salvage-simulator.db`). All recovery effects remain dry-run.

The connected simulator creates either a **synthetic failure investigation** (no
Razorpay call) or a **real Test Mode order** (Razorpay Checkout), runs it through
the deterministic pipeline, then calls Ollama Cloud for advisory analysis. A
replay path returns stored results without re-issuing any external request.

```mermaid
flowchart TD
    UI(["🖥️ Operator Console\n/simulator panel"]) --> MODE

    MODE{"Run type"}

    MODE -->|"Synthetic failure\n(Cloud Failure Lab)"| SYN
    MODE -->|"Razorpay Checkout"| RZP_ORDER

    subgraph SYN["🧪 Synthetic investigation"]
        SYN1["POST /simulator/v1/runs\ntype=synthetic\ngenerate failure scenario"]
        SYN1 --> SYN2["Commit to simulator_runs\n(no Razorpay call)"]
        SYN2 --> SYN3["Run deterministic pipeline\nTriage → Rulebook → Gatekeeper"]
        SYN3 --> SYN4["Commit decision\n(simulator DB, isolated)"]
    end

    subgraph RZP_ORDER["💳 Razorpay Test Mode"]
        RZP1["POST /simulator/v1/runs\ntype=razorpay_checkout"]
        RZP1 --> RZP2["Create real Test Mode order\nvia Razorpay API\nRecord order_id, amount"]
        RZP2 --> RZP3["Return checkout URL\nto console"]
        RZP3 --> RZP4(["Customer opens Checkout\nUses test card details\nSelects Failure option"])
        RZP4 --> RZP5["POST /simulator/v1/runs/{id}/sync\nFetch payments server-side\nVerify order/amount/currency/status"]
        RZP5 --> RZP6["Label provenance:\nAPI-observed vs webhook-received"]
        RZP6 --> SYN3
    end

    subgraph WEBHOOK_RECV["📡 Optional: actual webhook delivery"]
        WH1(["Razorpay sends signed\npayment.failed webhook\nto public tunnel URL"])
        WH1 --> WH2["POST /webhooks/razorpay/test\n(webhook_public:app only)"]
        WH2 --> WH3["HMAC verify + deduplicate\nstore in simulator_deliveries"]
        WH3 --> WH4["UI shows:\n'Signed webhook received'"]
    end

    SYN4 --> OLLAMA
    WH4 -.->|"async, separate"| OLLAMA

    subgraph OLLAMA["☁️ Ollama Cloud advisory"]
        OL1["Background worker\ncalls Ollama Cloud directly"]
        OL1 --> OL2["Pydantic-validate response\nRecord usage + timing"]
        OL2 --> OL3["Store advisory ledger entry\nSeparate from decision entry"]
        OL3 --> OL4["Advisory annotation ONLY\nCannot affect execution path"]
    end

    OLLAMA --> REPLAY

    subgraph REPLAY["🔁 Replay path"]
        RE1["GET /simulator/v1/runs/{run_id}"]
        RE1 --> RE2{"Already\ncomplete?"}
        RE2 -->|"Yes"| RE3["Return stored\norder + decision + generation\nNo re-creation"]
        RE2 -->|"No"| RE4["Return in-progress status"]
    end

    REPLAY --> OUT(["📊 Console displays:\n• Decision + class\n• Advisory analysis\n• Ollama usage/timing\n• Webhook provenance\n• Receipt download"])

    style OUT fill:#14532d,stroke:#22c55e,color:#bbf7d0
    style OL4 fill:#2d1b69,stroke:#8b5cf6,color:#ddd6fe
    style WH4 fill:#1e3a5f,stroke:#3b82f6,color:#bfdbfe
```

## Isolation boundaries

| Database | Contents | Isolated from |
|----------|----------|---------------|
| `data/salvage.db` | Seeded evaluation, offline demo | All simulator data |
| `data/salvage-simulator.db` | Simulator runs, deliveries, advisory | Seeded results, playground |
| `data/salvage-playground.db` | Local playground dry-run tests | Operator data |

## Limits

- Max 200 simulator runs (local)
- Max 30 Razorpay Test Mode order attempts
- Tunnel (zrok) exposes **only port 8002** — never the main API or Ollama service

## Related flows

- [Webhook ingress](./webhook-ingress.md) — the `/webhooks/razorpay/test` path
- [Worker pipeline](./worker-pipeline.md) — same core pipeline used inside simulator
- [Playground flow](./playground-flow.md) — offline-only alternative
