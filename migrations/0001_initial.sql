PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingress_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    payment_id TEXT NOT NULL,
    order_id TEXT,
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    currency TEXT NOT NULL,
    method TEXT,
    reason TEXT NOT NULL,
    source TEXT,
    step TEXT,
    status TEXT NOT NULL,
    received_at TEXT NOT NULL,
    payload_digest TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE REFERENCES ingress_events(event_id),
    state TEXT NOT NULL CHECK (state IN ('queued', 'leased', 'completed', 'dead_letter')),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    lease_owner TEXT,
    lease_expires_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS payment_state (
    payment_id TEXT PRIMARY KEY,
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    currency TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    contact_count INTEGER NOT NULL DEFAULT 0 CHECK (contact_count >= 0),
    last_effect_at TEXT,
    manual_stop INTEGER NOT NULL DEFAULT 0 CHECK (manual_stop IN (0, 1)),
    state_version INTEGER NOT NULL DEFAULT 0 CHECK (state_version >= 0)
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE REFERENCES ingress_events(event_id),
    payment_id TEXT NOT NULL REFERENCES payment_state(payment_id),
    created_at TEXT NOT NULL,
    reason TEXT NOT NULL,
    effective_class TEXT NOT NULL CHECK (effective_class IN ('A', 'B', 'C', 'D')),
    advisory_class TEXT CHECK (advisory_class IS NULL OR advisory_class IN ('A', 'B', 'C', 'D')),
    known_reason INTEGER NOT NULL CHECK (known_reason IN (0, 1)),
    review_required INTEGER NOT NULL CHECK (review_required IN (0, 1)),
    triage_rationale TEXT NOT NULL,
    allowed_actions_json TEXT NOT NULL,
    selected_action TEXT NOT NULL,
    decision_reasons_json TEXT NOT NULL,
    next_eligible_at TEXT,
    reason_map_fingerprint TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    policy_fingerprint TEXT NOT NULL,
    decision_hash TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS gate_checks (
    decision_id TEXT NOT NULL REFERENCES decisions(decision_id),
    check_name TEXT NOT NULL,
    passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
    explanation TEXT NOT NULL,
    PRIMARY KEY (decision_id, check_name)
);

CREATE TABLE IF NOT EXISTS effect_intents (
    idempotency_key TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL UNIQUE REFERENCES decisions(decision_id),
    payment_id TEXT NOT NULL,
    action TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('dry_run', 'pending', 'in_flight', 'succeeded', 'failed')),
    created_at TEXT NOT NULL,
    external_reference TEXT
);

CREATE TABLE IF NOT EXISTS outbox_messages (
    message_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE REFERENCES effect_intents(idempotency_key),
    audience TEXT NOT NULL CHECK (audience IN ('customer', 'operator')),
    rendered_text TEXT NOT NULL,
    transport_state TEXT NOT NULL CHECK (transport_state = 'disabled')
);

CREATE TABLE IF NOT EXISTS ledger_entries (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    content_json TEXT NOT NULL,
    prev_hash TEXT,
    entry_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eval_batches (
    batch_id TEXT PRIMARY KEY,
    seed INTEGER NOT NULL,
    scenario_count INTEGER NOT NULL,
    batch_digest TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state, lease_expires_at, created_at);
CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_class ON decisions(effective_class, review_required);
