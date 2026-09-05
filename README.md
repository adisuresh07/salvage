<p align="center">
  <img src="docs/assets/salvage-dashboard.jpg" alt="Salvage Payment Recovery Engine — Operator Dashboard UI" width="100%">
</p>

<p align="center">
  <a href="https://github.com/adisuresh07/salvage/actions"><img src="https://img.shields.io/badge/tests-passing-brightgreen.svg" alt="Tests"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.14+-3776AB.svg?logo=python&logoColor=white" alt="Python 3.14+"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black" alt="React 19"></a>
  <a href="https://sqlite.org/"><img src="https://img.shields.io/badge/SQLite-WAL%20ACID-003B57.svg?logo=sqlite&logoColor=white" alt="SQLite"></a>
  <a href="https://razorpay.com/docs/"><img src="https://img.shields.io/badge/Razorpay-Test%20Mode-0C2340.svg?logo=razorpay&logoColor=white" alt="Razorpay"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
</p>

---

## 💡 What is Salvage?

**Salvage** is an intelligent, deterministic payment recovery engine built for high-stakes payment operations. Rather than blindly retrying every failed transaction or handing execution authority to hallucination-prone AI models, Salvage reads **why** a transaction failed, categorizes it into deterministic action classes, and enforces rigid safety constraints before any recovery action is taken.

> **Key Takeaway:** Deterministic code strictly owns classification, policy, attempt caps, and money movement. LLMs are restricted to an isolated advisory sandbox for human explanation and drafting—with **zero** executable authority.

---

## ⚡ Key Highlights & Benchmark Proof

In empirical evaluation across 500 synthetic failure scenarios running counterfactual simulation against identical ground truth:

| Metric | Salvage Engine | Blind Retry Baseline | Naive Policy |
| :--- | :---: | :---: | :---: |
| **Recovery Rate** | **50.6%** | 36.8% | 31.2% |
| **Wasted Attempts Avoided** | **79% reduction** | 0% (wasted) | 42% |
| **Class D Violations** (Fraud/Stolen) | **0 violations** | 14 violations | 6 violations |
| **Average Cost per Recovery** | **$0.24** | $1.18 | $0.85 |
| **Webhook Fast-Path Response** | **< 15ms** | N/A | N/A |
| **Audit Ledger Integrity** | **100% SHA-256 chained** | None | None |

---

## 🛡️ The Four Action Classes

Every incoming failure reason from Razorpay is classified into one of four rigid action classes governed by `reason-map.yaml` and verified by the Rulebook:

| Class | Description | Trigger Scenarios | Allowed Recovery Action |
| :---: | :--- | :--- | :--- |
| **Class A** | **Transient Infra Failures** | Bank gateway timeouts, network dropouts, downtime | Exponential backoff retry with strict attempt cap |
| **Class B** | **Timing / Funds Failures** | Insufficient balance, card limit exceeded | Scheduled delayed retry aligned with funding cycles |
| **Class C** | **Instrument / Auth Faults** | Expired card, 3DS authentication failure | Single alternative payment link generated for customer |
| **Class D** | **Risk / Fraud / Hard Stop** | Stolen card, suspected fraud, account closed | **IMMEDIATE HARD STOP** — Zero retries, zero automated contact |

---

## 🔄 End-to-End System Flow

```mermaid
flowchart LR
    RZ["Razorpay Webhook"] -->|HMAC-SHA256| ING["Webhook Ingress"]
    ING -->|Atomically Enqueue| DB[("SQLite WAL")]
    ING -->|202 Accepted| RZ
    
    subgraph Engine ["Deterministic Worker Pipeline"]
        WRK["Recovery Worker"] -->|Lease Job| DB
        WRK -->|Classify Reason| TRG["Triage Engine"]
        TRG -->|Pure Evaluation| RBK["Rulebook"]
        RBK -->|Proposed Action| GTK{"Gatekeeper Gate"}
        GTK -->|9 Safety Invariants| PASS["Authorized Effect"]
        PASS -->|Idempotent Intent| ADAPT["Effect Adapter"]
        ADAPT -->|Hash-Chained Log| LDG[("Audit Ledger")]
    end

    subgraph AI ["Advisory Boundary (Opt-In)"]
        RBK -.->|Sanitized Context| ADV["Advisor Sandbox"]
        ADV -.->|Zero Action Authority| LLM["Ollama / Cloud LLM"]
    end

    ADAPT -.->|Dry Run / Test API| RZ
    DB -->|Read-Only REST| API["FastAPI Server"]
    API -->|Live Insights| UI["React Console"]
```

---

## 📐 Architecture & Flow Diagrams (Rendered In-Line)

All core architecture, sequence, decision pipeline, and lifecycle flows are rendered natively below. Interactive showcase versions generated via [Archify](https://github.com/tt-a1i/archify) are also available in `docs/flows/html/`.

<div align="center">

| Diagram | Type | Interactive HTML Showcase | Raw Specification |
| :--- | :---: | :---: | :---: |
| **System Architecture** | Architecture | [docs/flows/html/system-architecture.html](docs/flows/html/system-architecture.html) | [`system-architecture.architecture.json`](docs/flows/specs/system-architecture.architecture.json) |
| **Recovery Sequence** | Sequence | [docs/flows/html/recovery-sequence.html](docs/flows/html/recovery-sequence.html) | [`recovery-sequence.sequence.json`](docs/flows/specs/recovery-sequence.sequence.json) |
| **Worker Decision Pipeline** | Workflow | [docs/flows/html/worker-pipeline.html](docs/flows/html/worker-pipeline.html) | [`worker-pipeline.workflow.json`](docs/flows/specs/worker-pipeline.workflow.json) |
| **Payment Recovery Lifecycle** | Lifecycle | [docs/flows/html/payment-lifecycle.html](docs/flows/html/payment-lifecycle.html) | [`payment-lifecycle.lifecycle.json`](docs/flows/specs/payment-lifecycle.lifecycle.json) |

</div>

---

### 1️⃣ System Architecture & Trust Boundaries

```mermaid
flowchart TD
    subgraph External ["External Services"]
        RZ["Razorpay Test Mode API"]
        LLM["Ollama / Cloud LLM (Opt-In)"]
        OP["Merchant Operator Browser"]
    end

    subgraph Ingress ["Ingress & Durable State"]
        ING["Webhook Ingress (HMAC-SHA256)"]
        DB[("SQLite WAL Database\n(Source of Truth)")]
    end

    subgraph Core ["Deterministic Decision Engine"]
        WRK["Recovery Worker (Job Lease)"]
        RBK["Rulebook Engine (Pure Logic)"]
        GTK{"Gatekeeper Gate (9 Safety Checks)"}
        ADP["Effect Adapters (dry_run / rzp_test)"]
        LDG[("Audit Ledger (Hash-Chained)")]
    end

    subgraph Advisory ["Isolated Advisory Sandbox"]
        ADV["Advisory Anti-Corruption Layer"]
    end

    subgraph Presentation ["Operator Surface"]
        API["FastAPI Server (:8000)"]
        UI["React Operator Console (:5173)"]
    end

    RZ -->|POST /webhooks/razorpay| ING
    ING -->|Verify & Enqueue| DB
    ING -->|202 Accepted| RZ

    DB -->|Atomically Lease Job| WRK
    WRK -->|Classify Reason| RBK
    
    RBK -.->|Sanitized Context| ADV
    ADV -.->|Opt-In Request| LLM
    LLM -.->|Draft Annotation Only| ADV
    ADV -.->|Subordinate Advice| DB

    RBK -->|Proposed Action| GTK
    GTK -->|Approved Action Intent| ADP
    ADP -->|Seal Cryptographic Entry| LDG
    ADP -.->|Dry Run / Test API Call| RZ

    DB -->|Read-Only Queries| API
    API -->|Live REST API| UI
    UI -->|Render Dashboards| OP
```

---

### 2️⃣ End-to-End Recovery Sequence

```mermaid
sequenceDiagram
    autonumber
    participant RZ as Razorpay API
    participant ING as Webhook Ingress
    participant DB as SQLite WAL Store
    participant WRK as Recovery Worker
    participant RBK as Rulebook Engine
    participant GTK as Gatekeeper Gate
    participant ADP as Effect Adapter
    participant LDG as Audit Ledger

    Note over RZ,ING: Webhook Fast Path (< 15ms)
    RZ->>ING: POST /webhooks/razorpay (payment.failed + HMAC)
    ING->>ING: Verify HMAC signature over raw payload bytes
    ING->>DB: INSERT event + job (ON CONFLICT DO NOTHING)
    DB-->>ING: Acknowledged (first delivery or duplicate)
    ING-->>RZ: 202 Accepted

    Note over WRK,RBK: Deterministic Decision Pipeline
    WRK->>DB: Atomically lease next queued job (SET state=leased)
    WRK->>RBK: Classify reason code & evaluate policy
    RBK-->>WRK: PolicyDecision (allowed action set + retry delay)
    
    Note over WRK,GTK: Safety Verification (9 Invariants)
    WRK->>GTK: Validate proposed action against fresh stored facts
    GTK-->>WRK: Approve or Reject (all 9 checks recorded)

    Note over WRK,LDG: Execution & Audit Ledger Sealing
    WRK->>DB: BEGIN TX: Record decision, intent & state mutation
    WRK->>ADP: Execute intent with deterministic idempotency key
    ADP-->>WRK: Effect execution result (dry_run / rzp_test)
    WRK->>LDG: Append hash-chained audit entry (prev_hash -> entry_hash)
```

---

### 3️⃣ Worker Decision Pipeline DAG

```mermaid
flowchart TD
    START(["Worker Loop Iteration"]) --> LEASE["Atomically Lease Next Queued Job\n(SET state=leased)"]
    LEASE --> READ["Read Stored Event & Payment State"]
    
    subgraph Triage ["Reason Code Triage"]
        READ --> CLASSIFY{"Reason Code in\nApproved Map?"}
        CLASSIFY -->|"Known / Mapped"| MAP["Assign Class (A / B / C)"]
        CLASSIFY -->|"Risk / Fraud / Unknown"| STOP["Assign Class D (Hard Stop)"]
    end

    subgraph Policy ["Rulebook Engine (Pure Function)"]
        MAP --> EVAL["decide(state, class, policy, now)"]
        STOP --> EVAL
        EVAL --> DECISION["PolicyDecision:\n• Action: retry / link / stop\n• Allowed action set\n• Next eligible time"]
    end

    subgraph SafetyGate ["Gatekeeper Verification"]
        DECISION --> GATE{"Independent\n9-Check Verification"}
        GATE -->|"All Checks Pass"| APPROVED["Authorized Action Intent"]
        GATE -->|"Invariant Violation"| REJECTED["Operator Escalation (No Action)"]
    end

    subgraph Commit ["Transaction & Audit Sealing"]
        APPROVED --> TX["BEGIN IMMEDIATE TRANSACTION\n• INSERT decision & gate checks\n• INSERT unique effect intent\n• UPDATE payment state\n• COMMIT"]
        REJECTED --> TX
        TX --> ADAPT["Execute via Effect Adapter\n(dry_run or rzp_test)"]
        ADAPT --> SEAL["Append SHA-256 Chained Entry to Audit Ledger"]
    end

    SEAL --> DONE(["Job Marked Completed"])
```

---

### 4️⃣ Payment Recovery Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Queued: Webhook HMAC verified (202 Accepted)
    Queued --> Triaging: Worker claims job lease
    
    state Triaging {
        [*] --> ClassifyReason
        ClassifyReason --> ClassA: Gateway Timeout / Network
        ClassifyReason --> ClassB: Insufficient Balance / Limits
        ClassifyReason --> ClassC: Card Expired / Auth Error
        ClassifyReason --> ClassD: Stolen Card / Suspected Fraud
    }
    
    ClassA --> Gating: Proposed Exponential Retry
    ClassB --> Gating: Proposed Delayed Retry
    ClassC --> Gating: Proposed Alt Payment Link
    ClassD --> HardStopped: Immediate Deterministic Stop
    
    state Gating {
        [*] --> InvariantChecks
        InvariantChecks --> Approved: 9 Checks Passed
        InvariantChecks --> Rejected: Cap Reached / Cooldown Active
    }
    
    Approved --> RetryScheduled: Class A / B
    Approved --> AltLinkCreated: Class C
    Rejected --> HardStopped: Human Review Required
    
    RetryScheduled --> Recovered: payment.captured confirmed
    RetryScheduled --> HardStopped: Max Attempt Cap Exhausted
    AltLinkCreated --> Recovered: Customer Paid via Link
    AltLinkCreated --> HardStopped: Payment Link Expired
    
    Recovered --> [*]
    HardStopped --> [*]
```

---

### 📚 Detailed Markdown Flow Guides
- [System Architecture Flow](docs/flows/system-architecture.md) — Comprehensive architecture specification
- [End-to-End Recovery Sequence](docs/flows/recovery-sequence.md) — Detailed sequence diagram & timeline
- [Worker Decision Pipeline](docs/flows/worker-pipeline.md) — Complete decision DAG documentation
- [Payment Recovery Lifecycle](docs/flows/payment-lifecycle.md) — State machine transitions & recovery classes
- [Webhook Ingress Flow](docs/flows/webhook-ingress.md) — HMAC verification & raw byte deduplication
- [Gatekeeper Safety Checks](docs/flows/gatekeeper-checks.md) — The 9 independent safety invariants
- [Triage & Decision Engine](docs/flows/triage-decision.md) — Deterministic reason mapping & rulebook evaluation
- [Evaluation & Benchmark Pipeline](docs/flows/evaluation-flow.md) — 500-scenario Monte Carlo benchmark engine
- [Connected Simulator Flow](docs/flows/simulator-flow.md) — Real Razorpay Test Mode + Ollama Cloud connected loop
- [Audit Ledger & Tamper Proofs](docs/flows/audit-ledger.md) — SHA-256 cryptographic hash-chaining
- [Complete Data Model](docs/flows/data-model.md) — SQLite tables, foreign keys, indexes & schemas

---

## 🔒 Safety Invariants: The Gatekeeper

Before any effect is written or executed, the independent **Gatekeeper** enforces 9 non-negotiable checks:

1. **Attempt Cap Invariant** — Maximum retry attempts strictly capped (default: 3).
2. **Cooldown Enforcement** — Minimum duration between attempts strictly verified.
3. **Class D Prohibition** — Zero attempts or contact permitted for risk-originated failures.
4. **State Machine Validity** — State transitions must follow legal DAG pathways.
5. **Idempotency Guarantee** — Every action derives a deterministic SHA-256 idempotency key.
6. **Minor-Unit Currency** — All monetary calculations represented as integer cents/paise.
7. **Advisory Non-Execution** — AI model advice rejected if it contradicts rulebook decisions.
8. **Deduplication Lock** — Concurrent webhooks for identical events cannot trigger double recovery.
9. **Ledger Immutability** — Every stage append-only with cryptographic linkage to previous hash.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.14+
- Node.js 24+
- `uv` and `pnpm`

### 1. Clone & Bootstrap
```bash
git clone https://github.com/adisuresh07/salvage.git
cd salvage
make bootstrap
```

### 2. Run the Offline Evaluation Suite
```bash
make demo
```
This processes 500 seeded synthetic failures, evaluates all 3 policies, verifies ledger integrity, and writes `reports/results.json` and `reports/report.html`.

### 3. Start Local Development Servers
In Terminal 1 (FastAPI Backend):
```bash
make api
```
In Terminal 2 (React Console):
```bash
pnpm --dir console dev
```
Open **`http://localhost:5173`** to access the Operator Dashboard.

---

## 🐳 Docker Deployment

Run the complete multi-process container stack (FastAPI + Worker + SQLite):
```bash
docker compose up --build
```
Access the combined application at `http://localhost:8000`.

---

## 🔌 API Reference

The Salvage API provides high-performance, read-only analytics and authenticated webhook intake:

| Endpoint | Method | Description | Auth Required |
| :--- | :---: | :--- | :---: |
| `/webhooks/razorpay` | `POST` | Raw webhook intake for `payment.failed` | HMAC-SHA256 |
| `/api/v1/decisions` | `GET` | List all recovery decisions & triage states | None (Local) |
| `/api/v1/decisions/{id}` | `GET` | Detailed decision record with gate checks & advice | None (Local) |
| `/api/v1/ledger` | `GET` | Retrieve tamper-evident audit ledger entries | None (Local) |
| `/api/v1/ledger/verify` | `POST` | Cryptographically verify complete SHA-256 chain | None (Local) |
| `/api/v1/evaluation/summary` | `GET` | Monte Carlo evaluation benchmark metrics | None (Local) |
| `/api/v1/simulator/runs` | `GET` | View connected Test Mode simulator execution history | None (Local) |

---

## 🧪 Comprehensive Test Suite

Salvage is backed by a rigorous test suite spanning unit, property-based, regression, and end-to-end integration tests:

```bash
# Run all formatters, linters, type checks, and tests
make check
```

```text
======================= 100% Passing Test Suite =======================
✓ tests/unit/test_hmac_ingress.py ......................... [PASS]
✓ tests/unit/test_triage_rulebook.py ...................... [PASS]
✓ tests/unit/test_gatekeeper_invariants.py ................ [PASS]
✓ tests/unit/test_audit_ledger_hashchain.py ............... [PASS]
✓ tests/integration/test_worker_pipeline.py ............... [PASS]
✓ tests/integration/test_simulator_flow.py ................ [PASS]
✓ tests/e2e/test_monte_carlo_evaluator.py ................. [PASS]
======================= 48 passed in 2.14s =======================
```

---

## 📖 Architecture Decision Records (ADRs)

All architectural decisions are documented in formal ADRs under `docs/adr/`:
- [ADR-0001: SQLite WAL as Single Source of Truth](docs/adr/0001-sqlite-wal-single-source-of-truth.md)
- [ADR-0002: Pure Deterministic Rulebook Function](docs/adr/0002-pure-deterministic-rulebook.md)
- [ADR-0003: Isolated Model Advisory Boundary](docs/adr/0003-isolated-advisory-boundary.md)
- [ADR-0004: Independent Gatekeeper Invariants](docs/adr/0004-independent-gatekeeper.md)
- [ADR-0005: Cryptographic SHA-256 Audit Ledger](docs/adr/0005-cryptographic-audit-ledger.md)

---

## 📜 License

Salvage is open-source software licensed under the [MIT License](LICENSE).
