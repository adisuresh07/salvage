from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ActionClass(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ActionType(StrEnum):
    SCHEDULE_RETRY = "schedule_retry"
    SCHEDULE_LATER_RETRY = "schedule_later_retry"
    CREATE_PAYMENT_LINK = "create_payment_link"
    QUEUE_CUSTOMER_MESSAGE = "queue_customer_message"
    ESCALATE_REVIEW = "escalate_review"
    STOP = "stop"


AUTOMATED_ACTIONS = frozenset(
    {
        ActionType.SCHEDULE_RETRY,
        ActionType.SCHEDULE_LATER_RETRY,
        ActionType.CREATE_PAYMENT_LINK,
        ActionType.QUEUE_CUSTOMER_MESSAGE,
    }
)
CONTACT_ACTIONS = frozenset({ActionType.CREATE_PAYMENT_LINK, ActionType.QUEUE_CUSTOMER_MESSAGE})
RETRY_ACTIONS = frozenset({ActionType.SCHEDULE_RETRY, ActionType.SCHEDULE_LATER_RETRY})


@dataclass(frozen=True, slots=True)
class PaymentState:
    payment_id: str
    amount_minor: int
    currency: str
    attempt_count: int = 0
    contact_count: int = 0
    last_effect_at: datetime | None = None
    manual_stop: bool = False
    state_version: int = 0

    def __post_init__(self) -> None:
        if self.amount_minor < 0 or self.attempt_count < 0 or self.contact_count < 0:
            raise ValueError("Money and counters must be non-negative integers")


@dataclass(frozen=True, slots=True)
class TriageResult:
    effective_class: ActionClass
    known_reason: bool
    review_required: bool
    rationale: str
    reason_map_fingerprint: str


@dataclass(frozen=True, slots=True)
class ClassPolicy:
    attempt_cap: int
    cooldown_seconds: int
    contact_cap: int


@dataclass(frozen=True, slots=True)
class RecoveryPolicy:
    version: str
    fingerprint: str
    classes: dict[ActionClass, ClassPolicy]
    customer_contact_window_cap: int
    adapter_capabilities: frozenset[ActionType]


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    effective_class: ActionClass
    allowed_actions: tuple[ActionType, ...]
    selected_action: ActionType
    reason_codes: tuple[str, ...]
    next_eligible_at: datetime | None
    policy_version: str
    policy_fingerprint: str
    review_required: bool

    def __post_init__(self) -> None:
        if self.selected_action not in self.allowed_actions:
            raise ValueError("Selected deterministic action must belong to the allowed set")
        if self.effective_class is ActionClass.D and any(
            action in AUTOMATED_ACTIONS for action in self.allowed_actions
        ):
            raise ValueError("Effective Class D cannot allow an automated effect")


@dataclass(frozen=True, slots=True)
class GateCheck:
    name: str
    passed: bool
    explanation: str


@dataclass(frozen=True, slots=True)
class GateResult:
    approved: bool
    checks: tuple[GateCheck, ...]
    final_action: ActionType
