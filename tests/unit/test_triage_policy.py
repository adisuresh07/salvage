from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from salvage.config import ROOT
from salvage.domain.loading import load_policy
from salvage.domain.models import AUTOMATED_ACTIONS, ActionClass, ActionType, PaymentState
from salvage.domain.policy import decide
from salvage.domain.triage import triage_reason

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)


def test_known_reason_maps_to_reviewed_class() -> None:
    result = triage_reason("gateway_timeout", "gateway", ROOT / "policy/reason-map.yaml")
    assert result.effective_class is ActionClass.A
    assert result.known_reason
    assert not result.review_required


def test_unknown_reason_fails_closed() -> None:
    result = triage_reason("new_processor_code", "gateway", ROOT / "policy/reason-map.yaml")
    assert result.effective_class is ActionClass.D
    assert not result.known_reason
    assert result.review_required


def test_risk_source_overrides_mapping() -> None:
    result = triage_reason("gateway_timeout", "risk", ROOT / "policy/reason-map.yaml")
    assert result.effective_class is ActionClass.D
    assert result.review_required


@given(st.integers(min_value=0, max_value=10), st.integers(min_value=0, max_value=10))
def test_class_d_never_allows_automated_effect(attempts: int, contacts: int) -> None:
    policy = load_policy(ROOT / "policy/recovery-policy.yaml")
    state = PaymentState("pay_property", 1_000, "INR", attempts, contacts)
    decision = decide(state, ActionClass.D, policy, NOW, review_required=True)
    assert decision.selected_action is ActionType.ESCALATE_REVIEW
    assert not (set(decision.allowed_actions) & AUTOMATED_ACTIONS)


def test_class_a_respects_attempt_cap() -> None:
    policy = load_policy(ROOT / "policy/recovery-policy.yaml")
    eligible = decide(PaymentState("pay_a", 1_000, "INR"), ActionClass.A, policy, NOW)
    capped = decide(
        PaymentState("pay_a", 1_000, "INR", attempt_count=3), ActionClass.A, policy, NOW
    )
    assert eligible.selected_action is ActionType.SCHEDULE_RETRY
    assert capped.selected_action is ActionType.STOP


def test_class_c_respects_contact_cap() -> None:
    policy = load_policy(ROOT / "policy/recovery-policy.yaml")
    eligible = decide(PaymentState("pay_c", 1_000, "INR"), ActionClass.C, policy, NOW)
    capped = decide(
        PaymentState("pay_c", 1_000, "INR", contact_count=1), ActionClass.C, policy, NOW
    )
    assert eligible.selected_action is ActionType.CREATE_PAYMENT_LINK
    assert capped.selected_action is ActionType.STOP
