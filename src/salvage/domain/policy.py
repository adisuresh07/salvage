from __future__ import annotations

from datetime import datetime, timedelta

from salvage.domain.models import (
    ActionClass,
    ActionType,
    PaymentState,
    PolicyDecision,
    RecoveryPolicy,
)


def decide(
    state: PaymentState,
    effective_class: ActionClass,
    policy: RecoveryPolicy,
    now: datetime,
    *,
    review_required: bool = False,
) -> PolicyDecision:
    class_policy = policy.classes[effective_class]
    reasons: list[str] = []
    next_eligible_at: datetime | None = None
    allowed: tuple[ActionType, ...]

    if state.manual_stop:
        allowed = (ActionType.ESCALATE_REVIEW,)
        selected = ActionType.ESCALATE_REVIEW
        reasons.append("manual_stop")
    elif effective_class is ActionClass.D:
        allowed = (ActionType.ESCALATE_REVIEW,)
        selected = ActionType.ESCALATE_REVIEW
        reasons.append("class_d_hard_stop")
        review_required = True
    elif effective_class is ActionClass.A:
        if state.attempt_count >= class_policy.attempt_cap:
            allowed = (ActionType.STOP,)
            selected = ActionType.STOP
            reasons.append("attempt_cap_reached")
        else:
            eligible_at = (
                state.last_effect_at + timedelta(seconds=class_policy.cooldown_seconds)
                if state.last_effect_at
                else now
            )
            next_eligible_at = eligible_at
            if now < eligible_at:
                allowed = (ActionType.STOP,)
                selected = ActionType.STOP
                reasons.append("cooldown_active")
            else:
                allowed = (ActionType.SCHEDULE_RETRY, ActionType.STOP)
                selected = ActionType.SCHEDULE_RETRY
                reasons.append("bounded_transient_retry")
    elif effective_class is ActionClass.B:
        if state.attempt_count >= class_policy.attempt_cap:
            allowed = (ActionType.STOP,)
            selected = ActionType.STOP
            reasons.append("attempt_cap_reached")
        else:
            eligible_at = (
                state.last_effect_at + timedelta(seconds=class_policy.cooldown_seconds)
                if state.last_effect_at
                else now + timedelta(seconds=class_policy.cooldown_seconds)
            )
            next_eligible_at = eligible_at
            allowed = (ActionType.SCHEDULE_LATER_RETRY, ActionType.STOP)
            selected = ActionType.SCHEDULE_LATER_RETRY
            reasons.append("funds_cooldown_scheduled")
    else:
        if state.contact_count >= min(class_policy.contact_cap, policy.customer_contact_window_cap):
            allowed = (ActionType.STOP,)
            selected = ActionType.STOP
            reasons.append("contact_cap_reached")
        else:
            allowed = (ActionType.CREATE_PAYMENT_LINK, ActionType.STOP)
            selected = ActionType.CREATE_PAYMENT_LINK
            reasons.append("alternative_payment_path")

    return PolicyDecision(
        effective_class=effective_class,
        allowed_actions=allowed,
        selected_action=selected,
        reason_codes=tuple(reasons),
        next_eligible_at=next_eligible_at,
        policy_version=policy.version,
        policy_fingerprint=policy.fingerprint,
        review_required=review_required,
    )
