# Data Model

**Storage:** SQLite with WAL mode, foreign keys enabled, bounded busy timeout.
**All times:** UTC ISO-8601. **Money:** integer minor units only — never floating point.

## Entity relationship diagram

```mermaid
erDiagram
    schema_migrations {
        text version PK
        text applied_at
    }

    ingress_events {
        text event_id PK
        text razorpay_payment_id
        text razorpay_order_id
        text reason_code
        text source
        text step
        integer amount_minor
        text currency
        text payload_hash
        text received_at
    }

    jobs {
        text job_id PK
        text event_id UK
        text state
        text lease_owner
        text lease_expires_at
        integer attempt_count
        text created_at
        text updated_at
    }

    payment_state {
        text payment_id PK
        integer attempt_count
        integer contact_count
        text last_attempt_at
        text last_contact_at
        boolean manual_stop
        integer state_version
        text updated_at
    }

    decisions {
        text decision_id PK
        text event_id UK
        text effective_class
        text advisory_class
        text selected_action
        text allowed_actions_json
        text reason_map_fingerprint
        text policy_fingerprint
        text decided_at
    }

    gate_checks {
        text decision_id PK
        text check_name PK
        boolean passed
        text detail
    }

    effect_intents {
        text idempotency_key PK
        text decision_id
        text action_type
        text state
        text external_ref
        text created_at
        text updated_at
    }

    outbox_messages {
        text message_id PK
        text effect_key UK
        text recipient_type
        text rendered_text
        text transport_state
        text created_at
    }

    llm_cache {
        text cache_key PK
        text task
        text provider
        text model
        text schema_digest
        text prompt_digest
        text input_digest
        text response_json
        text cached_at
    }

    ledger_entries {
        integer sequence PK
        text entry_hash UK
        text prev_hash
        text canonical_json
        text created_at
    }

    eval_batches {
        text batch_id PK
        text seed
        text fixture_version
        text policy_version
        text fixed_clock
        text created_at
    }

    eval_scenarios {
        text batch_id PK
        text scenario_key PK
        text visible_facts_json
        text created_at
    }

    eval_results {
        text batch_id PK
        text policy_name PK
        text scenario_key PK
        text action_taken
        text simulated_outcome
        text metrics_json
    }

    simulator_runs {
        text run_id PK
        text run_type
        text razorpay_order_id
        text decision_id
        text advisory_ledger_entry_id
        text created_at
    }

    simulator_deliveries {
        text delivery_id PK
        text run_id
        text event_id
        text received_at
    }

    ingress_events ||--o| jobs : "event_id"
    ingress_events ||--o| decisions : "event_id"
    decisions ||--o{ gate_checks : "decision_id"
    decisions ||--o{ effect_intents : "decision_id"
    effect_intents ||--o| outbox_messages : "idempotency_key"
    eval_batches ||--o{ eval_scenarios : "batch_id"
    eval_batches ||--o{ eval_results : "batch_id"
    simulator_runs ||--o{ simulator_deliveries : "run_id"
```

## Database isolation

| Database file | Purpose | Isolated from |
|---------------|---------|---------------|
| `data/salvage.db` | Core: webhooks, jobs, decisions, ledger, eval | Simulator, playground |
| `data/salvage-simulator.db` | Connected simulator runs + deliveries | Core, playground |
| `data/salvage-playground.db` | Local playground dry-run tests | Core, simulator |

## Key constraints

| Constraint | Table | Enforcement |
|-----------|-------|-------------|
| One job per event | `jobs.event_id` UNIQUE | `ON CONFLICT DO NOTHING` on ingress |
| One decision per event | `decisions.event_id` UNIQUE | Prevents duplicate processing |
| Idempotent effects | `effect_intents.idempotency_key` UNIQUE | SHA-256 of stable canonical fields |
| Monotonic ledger | `ledger_entries.sequence` monotonic | Application enforced |
| Non-duplicate hash | `ledger_entries.entry_hash` UNIQUE | Detects replay tampering |
| Integer money | `amount_minor` INTEGER | Schema-level type constraint |

## Related flows

- [Worker pipeline](./worker-pipeline.md) — writes to most tables
- [Webhook ingress](./webhook-ingress.md) — writes `ingress_events` + `jobs`
- [Audit ledger](./audit-ledger.md) — writes `ledger_entries`
- [Evaluation flow](./evaluation-flow.md) — writes `eval_*` tables
