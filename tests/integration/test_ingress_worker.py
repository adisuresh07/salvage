from __future__ import annotations

from fastapi.testclient import TestClient

from salvage.api.app import create_app
from salvage.audit.ledger import verify_ledger
from salvage.config import Settings
from salvage.execution.worker import process_all
from salvage.ingress.webhook import signature_for
from salvage.persistence.repository import database_counts, list_decision_rows
from tests.conftest import webhook_body


def _headers(body: bytes, secret: str, event_id: str = "evt_contract_001") -> dict[str, str]:
    return {
        "X-Razorpay-Signature": signature_for(body, secret),
        "x-razorpay-event-id": event_id,
        "Content-Type": "application/json",
    }


def test_valid_duplicate_and_invalid_delivery(test_settings: Settings) -> None:
    body = webhook_body()
    with TestClient(create_app(test_settings)) as client:
        invalid = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": "bad", "x-razorpay-event-id": "evt_bad"},
        )
        assert invalid.status_code == 401
        first = client.post(
            "/webhooks/razorpay", content=body, headers=_headers(body, test_settings.webhook_secret)
        )
        duplicate = client.post(
            "/webhooks/razorpay", content=body, headers=_headers(body, test_settings.webhook_secret)
        )
    assert first.status_code == 202 and first.json()["duplicate"] is False
    assert duplicate.status_code == 202 and duplicate.json()["duplicate"] is True
    assert database_counts(test_settings.database_path)["ingress_events"] == 1
    assert database_counts(test_settings.database_path)["jobs"] == 1


def test_unknown_reason_reaches_class_d_without_effect(test_settings: Settings) -> None:
    test_settings = test_settings.model_copy(update={"llm": "cache-only"})
    body = webhook_body(reason="brand_new_reason", source="gateway")
    with TestClient(create_app(test_settings)) as client:
        response = client.post(
            "/webhooks/razorpay",
            content=body,
            headers=_headers(body, test_settings.webhook_secret, "evt_unknown"),
        )
    assert response.status_code == 202
    assert len(process_all(test_settings)) == 1
    decision = list_decision_rows(test_settings.database_path)[0]
    assert decision["effective_class"] == "D"
    assert decision["advisory_class"] is None
    assert decision["review_required"] is True
    assert decision["effect_state"] is None
    assert verify_ledger(test_settings.database_path).valid


def test_shadow_suggestion_cannot_change_decision(test_settings: Settings) -> None:
    body = webhook_body(reason="processor_code_z91", source="gateway")
    cached = test_settings.model_copy(update={"llm": "cache-only"})
    with TestClient(create_app(cached)) as client:
        response = client.post(
            "/webhooks/razorpay",
            content=body,
            headers=_headers(body, cached.webhook_secret, "evt_shadow"),
        )
    assert response.status_code == 202
    process_all(cached)
    decision = list_decision_rows(cached.database_path)[0]
    assert decision["effective_class"] == "D"
    assert decision["advisory_class"] == "A"
    assert decision["selected_action"] == "escalate_review"
    assert decision["effect_state"] is None


def test_read_api_has_no_mutation_routes(test_settings: Settings) -> None:
    with TestClient(create_app(test_settings)) as client:
        methods = {
            method
            for route in client.app.routes
            if getattr(route, "path", "").startswith("/api/")
            for method in getattr(route, "methods", set())
        }
    assert methods <= {"GET", "HEAD"}
