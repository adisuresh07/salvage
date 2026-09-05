# Architecture & Execution Flows Index

This directory contains comprehensive architecture, sequence, lifecycle, and data flow documentation for the Salvage recovery platform.

## 🎨 Interactive Archify Showcases

| Flow | Diagram Type | Interactive HTML | Spec |
| :--- | :---: | :---: | :---: |
| **System Architecture** | Architecture | [Interactive HTML](html/system-architecture.html) | [system-architecture.architecture.json](specs/system-architecture.architecture.json) |
| **Recovery Sequence** | Sequence | [Interactive HTML](html/recovery-sequence.html) | [recovery-sequence.sequence.json](specs/recovery-sequence.sequence.json) |
| **Worker Decision Pipeline** | Workflow | [Interactive HTML](html/worker-pipeline.html) | [worker-pipeline.workflow.json](specs/worker-pipeline.workflow.json) |
| **Payment Recovery Lifecycle** | Lifecycle | [Interactive HTML](html/payment-lifecycle.html) | [payment-lifecycle.lifecycle.json](specs/payment-lifecycle.lifecycle.json) |

## 📖 Detailed Markdown Flow Documentation

1. [System Architecture Flow](system-architecture.md) — System boundaries, components, and communication corridors
2. [End-to-End Recovery Sequence](recovery-sequence.md) — Step-by-step timeline from webhook reception to ledger sealing
3. [Worker Decision Pipeline](worker-pipeline.md) — Decision DAG from job claim through gating to effect intent
4. [Payment Recovery Lifecycle](payment-lifecycle.md) — State machine transitions and terminal outcome branches
5. [Webhook Ingress Flow](webhook-ingress.md) — Raw byte HMAC verification and database deduplication
6. [Triage & Decision Engine Flow](triage-decision.md) — Reason code classification and pure rulebook execution
7. [Gatekeeper Safety Checks Flow](gatekeeper-checks.md) — Independent 9-invariant verification engine
8. [Evaluation Benchmark Flow](evaluation-flow.md) — Monte Carlo 500-scenario evaluation harness
9. [Connected Simulator Flow](simulator-flow.md) — Razorpay Test Mode + Ollama Cloud connected loop
10. [Audit Ledger & Hash Chain Flow](audit-ledger.md) — Cryptographic SHA-256 tamper-evident chaining
11. [Complete Data Model](data-model.md) — SQLite tables, constraints, foreign keys, and indexes
