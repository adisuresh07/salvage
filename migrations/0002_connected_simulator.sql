CREATE TABLE simulator_runs (
    run_id TEXT PRIMARY KEY,
    source TEXT NOT NULL CHECK(source IN ('synthetic', 'razorpay_test')),
    scenario TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
    method TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    order_id TEXT UNIQUE,
    payment_id TEXT,
    event_id TEXT UNIQUE,
    event_source TEXT,
    stage TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_sync_at TEXT,
    error_code TEXT,
    advice_json TEXT
);
CREATE INDEX idx_simulator_runs_created ON simulator_runs(created_at DESC);
CREATE TABLE simulator_deliveries (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES simulator_runs(run_id),
    payload_digest TEXT NOT NULL,
    first_received_at TEXT NOT NULL,
    last_received_at TEXT NOT NULL,
    delivery_count INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_simulator_deliveries_run ON simulator_deliveries(run_id);
