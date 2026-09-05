from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import UTC, datetime
from typing import Any

from salvage.persistence.repository import EventProjection


def signature_for(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()


def verify_signature(raw_body: bytes, provided: str, secret: str) -> bool:
    if not re.fullmatch(r"[0-9a-f]{64}", provided):
        return False
    expected = signature_for(raw_body, secret)
    return hmac.compare_digest(expected, provided)


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def project_event(
    raw_body: bytes, event_id: str, received_at: datetime | None = None
) -> EventProjection:
    parsed = _mapping(json.loads(raw_body), "webhook")
    event_type = str(parsed.get("event", ""))
    if event_type != "payment.failed":
        raise ValueError("Only payment.failed is accepted by the MVP ingress")
    payload = _mapping(parsed.get("payload"), "payload")
    payment_wrapper = _mapping(payload.get("payment"), "payload.payment")
    payment = _mapping(payment_wrapper.get("entity"), "payload.payment.entity")
    error_reason = payment.get("error_reason") or payment.get("reason")
    payment_id = payment.get("id")
    if not isinstance(payment_id, str) or not payment_id:
        raise ValueError("Payment ID is required")
    if not isinstance(error_reason, str) or not error_reason:
        raise ValueError("Failure reason is required")
    amount = payment.get("amount")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        raise ValueError("Amount must be a non-negative integer in minor units")
    currency = payment.get("currency")
    if not isinstance(currency, str) or not currency:
        raise ValueError("Currency is required")
    return EventProjection(
        event_id=event_id,
        event_type=event_type,
        payment_id=payment_id,
        order_id=str(payment["order_id"]) if payment.get("order_id") else None,
        amount_minor=amount,
        currency=currency,
        method=str(payment["method"]) if payment.get("method") else None,
        reason=error_reason,
        source=str(payment["error_source"]) if payment.get("error_source") else None,
        step=str(payment["error_step"]) if payment.get("error_step") else None,
        status=str(payment.get("status", "failed")),
        received_at=received_at or datetime.now(UTC),
        payload_digest=hashlib.sha256(raw_body).hexdigest(),
    )
