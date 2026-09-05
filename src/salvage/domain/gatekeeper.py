from __future__ import annotations

from datetime import datetime

from salvage.domain.models import (
    AUTOMATED_ACTIONS,
    CONTACT_ACTIONS,
    RETRY_ACTIONS,
    ActionClass,
    ActionType,
    GateCheck,
    GateResult,
    PaymentState,
    PolicyDecision,
    RecoveryPolicy,
)


def evaluate(
    decision: PolicyDecision,
    state: PaymentState,
    policy: RecoveryPolicy,
    now: datetime,
    *,
    proposed_amount_minor: int | None = None,
    proposed_currency: str | None = None,
) -> GateResult:
    action = decision.selected_action
    class_policy = policy.classes[decision.effective_class]
    is_effect = action in AUTOMATED_ACTIONS
    checks = (
        GateCheck(
            "allowed_set", action in decision.allowed_actions, "Action is in the Rulebook set."
        ),
        GateCheck(
            "class_stop",
            not (decision.effective_class is ActionClass.D and is_effect),
            "Effective Class D cannot create automated effects.",
        ),
        GateCheck(
            "attempt_cap",
            action not in RETRY_ACTIONS or state.attempt_count < class_policy.attempt_cap,
            "Attempt count remains below the configured cap.",
        ),
        GateCheck(
            "cooldown",
            decision.next_eligible_at is None
            or action is ActionType.SCHEDULE_LATER_RETRY
            or now >= decision.next_eligible_at,
            "The deterministic cooldown boundary is respected.",
        ),
        GateCheck(
            "contact_cap",
            action not in CONTACT_ACTIONS
            or state.contact_count
            < min(class_policy.contact_cap, policy.customer_contact_window_cap),
            "Customer contact stays inside both limits.",
        ),
        GateCheck(
            "stop_list", not state.manual_stop or not is_effect, "No manual stop blocks the action."
        ),
        GateCheck(
            "capability",
            not is_effect or action in policy.adapter_capabilities,
            "The dry-run adapter declares this capability.",
        ),
        GateCheck(
            "immutable_money",
            (proposed_amount_minor is None or proposed_amount_minor == state.amount_minor)
            and (proposed_currency is None or proposed_currency == state.currency),
            "Amount and currency match stored payment facts.",
        ),
    )
    approved = all(check.passed for check in checks)
    return GateResult(
        approved=approved,
        checks=checks,
        final_action=action if approved else ActionType.ESCALATE_REVIEW,
    )
