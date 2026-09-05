from __future__ import annotations

from salvage.ingress.webhook import project_event, signature_for, verify_signature
from tests.conftest import webhook_body


def test_hmac_is_over_exact_raw_bytes() -> None:
    body = webhook_body()
    signature = signature_for(body, "fixture-secret")
    assert verify_signature(body, signature, "fixture-secret")
    assert not verify_signature(body + b" ", signature, "fixture-secret")


def test_projection_allowlists_payment_facts() -> None:
    projection = project_event(webhook_body(), "evt_fixture")
    assert projection.payment_id == "pay_test_001"
    assert projection.amount_minor == 125_000
    assert projection.reason == "gateway_timeout"
