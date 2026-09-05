from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class GateCheckOut(BaseModel):
    name: str
    passed: bool
    explanation: str


class DecisionOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision_id: str
    event_id: str
    payment_id: str
    created_at: str
    reason: str
    effective_class: str
    advisory_class: str | None
    advisory_rationale: str | None
    advisory_confidence: str | None
    advisory_provider: str | None
    advisory_cache_key: str | None
    known_reason: bool
    review_required: bool
    triage_rationale: str
    allowed_actions: list[str]
    selected_action: str
    decision_reasons: list[str]
    next_eligible_at: str | None
    reason_map_fingerprint: str
    policy_version: str
    policy_fingerprint: str
    decision_hash: str
    amount_minor: int
    currency: str
    method: str | None
    idempotency_key: str | None
    effect_action: str | None
    effect_state: str | None
    gate_checks: list[GateCheckOut]


class DecisionListOut(BaseModel):
    items: list[DecisionOut]
    next_cursor: str | None = None


class LedgerOut(BaseModel):
    valid: bool
    entry_count: int
    final_hash: str | None
    first_mismatch_sequence: int | None


class BatchOut(BaseModel):
    batch_id: str
    seed: int
    scenario_count: int
    batch_digest: str
    created_at: str


class BatchListOut(BaseModel):
    items: list[BatchOut]


class HealthOut(BaseModel):
    status: str
    details: dict[str, Any] | None = None


class PolicyMetricsOut(BaseModel):
    policy: str
    scenario_count: int
    recovered_count: int
    recovery_rate: float
    recovered_minor_units: int
    attempts: int
    recovered_minor_units_per_attempt: float
    wasted_attempts: int
    customer_contacts: int
    class_d_violations: int
    decisions_digest: str


class AssumptionsOut(BaseModel):
    version: str
    sensitivity_range_percent: int
    note: str


class SensitivityOut(BaseModel):
    label: str
    probability_multiplier: float
    batch_digest: str
    policies: list[PolicyMetricsOut]


class BatchResultOut(BaseModel):
    schema_version: str
    batch_id: str
    seed: int
    scenario_count: int
    batch_digest: str
    fixed_clock: str
    assumptions: AssumptionsOut
    real_vs_simulated: str
    map_coverage_rate: float
    fallback_rate: float
    policies: list[PolicyMetricsOut]
    sensitivity: list[SensitivityOut]
    generated_at: str
