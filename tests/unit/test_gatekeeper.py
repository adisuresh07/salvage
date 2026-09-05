from __future__ import annotations

from datetime import UTC, datetime

from salvage.config import ROOT
from salvage.domain.gatekeeper import evaluate
from salvage.domain.loading import load_policy
from salvage.domain.models import ActionClass, ActionType, PaymentState
from salvage.domain.policy import decide


def test_gatekeeper_approves_deterministic_bounded_retry() -> None:
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    policy = load_policy(ROOT / "policy/recovery-policy.yaml")
    state = PaymentState("pay_ok", 12_500, "INR")
    decision = decide(state, ActionClass.A, policy, now)
    result = evaluate(
        decision, state, policy, now, proposed_amount_minor=12_500, proposed_currency="INR"
    )
    assert result.approved
    assert result.final_action is ActionType.SCHEDULE_RETRY
    assert all(check.passed for check in result.checks)


def test_gatekeeper_rejects_money_mismatch() -> None:
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    policy = load_policy(ROOT / "policy/recovery-policy.yaml")
    state = PaymentState("pay_mismatch", 12_500, "INR")
    decision = decide(state, ActionClass.A, policy, now)
    result = evaluate(
        decision, state, policy, now, proposed_amount_minor=99_999, proposed_currency="INR"
    )
    assert not result.approved
    assert result.final_action is ActionType.ESCALATE_REVIEW
    assert next(check for check in result.checks if check.name == "immutable_money").passed is False
