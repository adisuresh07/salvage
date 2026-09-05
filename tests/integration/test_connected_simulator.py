from __future__ import annotations

import json
from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from salvage.advisory.cloud import explain
from salvage.api.app import create_app
from salvage.config import Settings
from salvage.ingress.webhook import signature_for
from salvage.persistence.db import connect, migrate
from salvage.simulator.razorpay import ProviderError, RazorpayTest
from salvage.simulator.service import Simulator

HEADERS = {"Origin": "http://127.0.0.1:5173", "X-Salvage-Playground": "1"}
CLOUD_BODY = {
    "model": "gpt-oss:20b",
    "done": True,
    "prompt_eval_count": 101,
    "eval_count": 72,
    "message": {
        "content": json.dumps(
            {
                "suggested_class": "A",
                "confidence": "low",
                "explanation": "Advisory text only. The deterministic decision stays unchanged.",
                "operator_note": "Review the recorded failure; no real-money action was taken.",
            }
        )
    },
}


@pytest.fixture
def connected_settings(test_settings: Settings) -> Settings:
    return test_settings.model_copy(
        update={
            "simulator_enabled": True,
            "simulator_database_path": test_settings.database_path.with_name("connected.db"),
            "ollama_api_key": SecretStr("fake-cloud-test-key"),
            "razorpay_key_id": "rzp_test_fixture",
            "razorpay_key_secret": SecretStr("fake-razorpay-test-key"),
        }
    )


@pytest.fixture
def provider_requests(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    captured: list[httpx.Request] = []
    real_client = httpx.Client

    def respond(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url == "https://ollama.com/api/chat":
            return httpx.Response(200, json=CLOUD_BODY)
        if request.url == "https://api.razorpay.com/v1/orders" and request.method == "POST":
            return httpx.Response(
                200, json={"id": "order_fixture001", "amount": 125000, "currency": "INR"}
            )
        if request.url == "https://api.razorpay.com/v1/orders/order_fixture001/payments":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "pay_fixture001",
                            "order_id": "order_fixture001",
                            "amount": 125000,
                            "currency": "INR",
                            "status": "failed",
                            "method": "card",
                            "error_reason": "insufficient_funds",
                            "error_source": "customer",
                        }
                    ]
                },
            )
        raise AssertionError(f"Unexpected external request: {request.method} {request.url}")

    def client(**kwargs: object) -> httpx.Client:
        return real_client(**kwargs, transport=httpx.MockTransport(respond))  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "Client", client)
    return captured


@pytest.fixture
def client(connected_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(Simulator, "start", lambda self: migrate(self.path))
    with TestClient(create_app(connected_settings), base_url="http://127.0.0.1:8000") as client:
        yield client


def request(source: str = "synthetic", scenario: str = "risk_threshold") -> dict[str, object]:
    return {
        "run_id": str(uuid4()),
        "source": source,
        "scenario": scenario,
        "amount_minor": 125000,
        "method": "card",
    }


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("gateway_timeout", "A"),
        ("insufficient_funds", "B"),
        ("card_expired", "C"),
        ("risk_threshold", "D"),
        ("processor_code_z91", "D"),
    ],
)
def test_cloud_decision_and_replay(
    client: TestClient,
    provider_requests: list[httpx.Request],
    connected_settings: Settings,
    scenario: str,
    expected: str,
) -> None:
    body = request(scenario=scenario)
    response = client.post("/simulator/v1/runs", headers=HEADERS, json=body)
    assert response.status_code == 200, response.text
    client.app.state.simulator.tick()  # type: ignore[union-attr]
    run = client.get(f"/simulator/v1/runs/{body['run_id']}").json()
    assert run["decision"]["effective_class"] == expected
    assert run["advice"]["status"] == "fresh"
    assert run["advice"]["result"]["suggested_class"] == "A"
    assert run["event_source"] == "synthetic" and not run["webhook_received"]
    assert run["ledger_valid"]
    assert run["advice"]["input_tokens"] == 101
    payload = json.loads(provider_requests[0].content)
    prompt = payload["messages"][-1]["content"]
    for forbidden in ("125000", "INR", "pay_", str(body["run_id"]), "fake-cloud-test-key"):
        assert forbidden not in prompt
    assert "format" not in payload  # Ollama Cloud does not enforce structured outputs.
    assert len(provider_requests) == 1
    replay = client.post("/simulator/v1/runs", headers=HEADERS, json=body).json()
    client.app.state.simulator.tick()  # type: ignore[union-attr]
    assert replay["advice"] == run["advice"] and len(provider_requests) == 1
    export = client.get(f"/simulator/v1/runs/{body['run_id']}/receipt")
    assert export.status_code == 200 and "attachment" in export.headers["content-disposition"]
    with connect(connected_settings.simulator_database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0] == 2
        assert (
            db.execute("SELECT COUNT(*) FROM effect_intents WHERE state != 'dry_run'").fetchone()[0]
            == 0
        )
        if expected == "D":
            assert db.execute("SELECT COUNT(*) FROM effect_intents").fetchone()[0] == 0
    with connect(connected_settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0


def test_order_and_real_shape_webhook(
    client: TestClient, connected_settings: Settings, provider_requests: list[httpx.Request]
) -> None:
    body = request("razorpay_test")
    run = client.post("/simulator/v1/runs", headers=HEADERS, json=body).json()
    assert run["order_id"] == "order_fixture001"
    assert run["checkout_key_id"].startswith("rzp_test_")
    assert "fake-razorpay-test-key" not in json.dumps(run)
    raw = json.dumps(
        {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fixture001",
                        "order_id": run["order_id"],
                        "amount": 125000,
                        "currency": "INR",
                        "method": "card",
                        "status": "failed",
                        "error_reason": "gateway_timeout",
                        "error_source": "gateway",
                        "email": "private@example.com",
                        "card": {"number": "never-store-this"},
                    }
                }
            },
        }
    ).encode()
    webhook_headers = {
        "X-Razorpay-Signature": signature_for(raw, connected_settings.webhook_secret),
        "X-Razorpay-Event-Id": "evt_provider001",
    }
    bad = client.post("/webhooks/razorpay/test", content=raw + b" ", headers=webhook_headers)
    assert bad.status_code == 401
    assert (
        client.post("/webhooks/razorpay/test", content=raw, headers=webhook_headers).status_code
        == 202
    )
    assert len(provider_requests) == 1  # Only order creation, never AI in ingress.
    replay = client.post("/webhooks/razorpay/test", content=raw, headers=webhook_headers)
    assert replay.json()["duplicate"]
    client.app.state.simulator.tick()  # type: ignore[union-attr]
    result = client.get(f"/simulator/v1/runs/{body['run_id']}").json()
    assert result["webhook_received"] and result["webhook_deliveries"] == 2
    assert result["event_source"] == "razorpay_webhook"
    assert "private@example.com" not in json.dumps(result)
    assert "never-store-this" not in json.dumps(result)
    assert result["advice"]["status"] == "fresh"
    client.post("/simulator/v1/runs", headers=HEADERS, json=body)
    assert len(provider_requests) == 2  # One order plus one cloud generation.


@pytest.mark.parametrize(
    "mode", ["timeout", "rate_limit", "authentication", "bad_json", "redirect"]
)
def test_cloud_failure_never_falls_back(
    connected_settings: Settings, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    real_client = httpx.Client
    captured: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        assert request.url == "https://ollama.com/api/chat"
        if mode == "timeout":
            raise httpx.ReadTimeout("synthetic timeout")
        if mode == "bad_json":
            return httpx.Response(200, json={"done": True, "message": {"content": "not json"}})
        return httpx.Response(
            {"rate_limit": 429, "authentication": 401, "redirect": 302}[mode],
            headers={"Location": "http://127.0.0.1:11434/api/chat"},
        )

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(respond)),
    )
    result = explain(
        connected_settings,
        run_id="fixture",
        reason="risk_threshold",
        effective_class="D",
        action="escalate_review",
    )
    assert result.status in {"unavailable", "invalid_response"} and result.result is None
    assert len(captured) == 1


def test_guards_and_conflicting_input(
    client: TestClient, provider_requests: list[httpx.Request]
) -> None:
    body = request()
    assert client.post("/simulator/v1/runs", json=body).status_code == 403
    assert client.get("/simulator/v1/status", headers={"Host": "evil.example"}).status_code == 403
    assert (
        client.post(
            "/simulator/v1/runs", json={**body, "email": "x@example.com"}, headers=HEADERS
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/simulator/v1/runs", json={**body, "amount_minor": True}, headers=HEADERS
        ).status_code
        == 422
    )
    assert client.post("/simulator/v1/runs", json=body, headers=HEADERS).status_code == 200
    assert (
        client.post(
            "/simulator/v1/runs", json={**body, "amount_minor": 200}, headers=HEADERS
        ).status_code
        == 409
    )
    assert provider_requests == []


def test_live_keys_rejected(connected_settings: Settings) -> None:
    unsafe = connected_settings.model_copy(update={"razorpay_key_id": "rzp_live_never_allowed"})
    with pytest.raises(ValueError):
        unsafe.assert_safe()
    with pytest.raises(ProviderError):
        RazorpayTest(unsafe)


def test_api_reconciliation_is_not_webhook_evidence(
    client: TestClient,
    provider_requests: list[httpx.Request],
    connected_settings: Settings,
) -> None:
    body = request("razorpay_test")
    client.post("/simulator/v1/runs", json=body, headers=HEADERS)
    response = client.post(f"/simulator/v1/runs/{body['run_id']}/sync", headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.json()["event_source"] == "razorpay_api"
    assert response.json()["webhook_received"] is False
    client.app.state.simulator.tick()  # type: ignore[union-attr]
    run = client.get(f"/simulator/v1/runs/{body['run_id']}").json()
    assert run["decision"]["effective_class"] == "B"
    assert run["advice"]["status"] == "fresh"
    assert len(provider_requests) == 3
    assert (
        client.post(f"/simulator/v1/runs/{body['run_id']}/sync", headers=HEADERS).status_code == 429
    )
    raw = json.dumps(
        {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fixture001",
                        "order_id": "order_fixture001",
                        "amount": 125000,
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_reason": "insufficient_funds",
                        "error_source": "customer",
                    }
                }
            },
        }
    ).encode()
    headers = {
        "X-Razorpay-Signature": signature_for(raw, connected_settings.webhook_secret),
        "X-Razorpay-Event-Id": "evt_after_api",
    }
    assert client.post("/webhooks/razorpay/test", content=raw, headers=headers).status_code == 202
    after = client.get(f"/simulator/v1/runs/{body['run_id']}").json()
    assert after["webhook_received"] and after["webhook_deliveries"] == 1
    assert after["decision"]["decision_hash"] == run["decision"]["decision_hash"]
    assert after["advice"] == run["advice"] and len(provider_requests) == 3


def test_uncertain_order_is_not_automatically_recreated(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def unavailable(self: RazorpayTest, amount: int, receipt: str) -> str:
        nonlocal calls
        calls += 1
        raise ProviderError("razorpay_unavailable")

    monkeypatch.setattr(RazorpayTest, "create_order", unavailable)
    body = request("razorpay_test")
    for _ in range(2):
        response = client.post("/simulator/v1/runs", json=body, headers=HEADERS)
        assert response.json()["stage"] == "order_uncertain"
    assert calls == 1


def test_cloud_failure_still_saves_a_valid_hard_stop(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client.app.state.simulator.settings, "ollama_api_key", SecretStr(""))  # type: ignore[union-attr]
    body = request(scenario="risk_threshold")
    client.post("/simulator/v1/runs", headers=HEADERS, json=body)
    client.app.state.simulator.tick()  # type: ignore[union-attr]
    run = client.get(f"/simulator/v1/runs/{body['run_id']}").json()
    assert run["stage"] == "complete" and run["ledger_valid"]
    assert run["advice"]["status"] == "unavailable"
    assert run["decision"]["effective_class"] == "D" and run["decision"]["effect_state"] is None
