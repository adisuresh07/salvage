from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from salvage.api.app import create_app
from salvage.config import Settings
from salvage.persistence.db import connect
from salvage.persistence.repository import database_counts

HEADERS = {"Origin": "http://127.0.0.1:5173", "X-Salvage-Playground": "1"}


@pytest.mark.parametrize(
    ("scenario", "expected_class", "effects"),
    [
        ("gateway_timeout", "A", 1),
        ("insufficient_funds", "B", 1),
        ("card_expired", "C", 1),
        ("risk_threshold", "D", 0),
        ("processor_code_z91", "D", 0),
    ],
)
def test_playground_uses_real_pipeline_in_isolated_store(
    test_settings: Settings, scenario: str, expected_class: str, effects: int
) -> None:
    settings = test_settings.model_copy(update={"mode": "demo"})
    request = {
        "run_id": str(uuid4()),
        "scenario": scenario,
        "amount_minor": 125025,
        "method": "card",
    }
    with TestClient(create_app(settings)) as client:
        baseline = database_counts(settings.database_path)
        response = client.post("/demo/v1/runs", json=request, headers=HEADERS)
        assert response.status_code == 200, response.text
        receipt = response.json()
        assert receipt["decision"]["effective_class"] == expected_class
        assert receipt["decision"]["amount_minor"] == 125025
        assert receipt["decision"]["payment_id"].startswith("pay_play_")
        assert receipt["safety_mode"] == "dry_run"
        assert receipt["ingress_verified"] and receipt["ledger_valid"]
        assert receipt["effect_count"] == effects
        assert (
            receipt["event_count"]
            == receipt["decision_count"]
            == receipt["ledger_entry_count"]
            == 1
        )
        assert database_counts(settings.database_path) == baseline
        duplicate = client.post("/demo/v1/runs", json=request, headers=HEADERS).json()
        assert duplicate["duplicate"]
        assert duplicate["decision"]["decision_hash"] == receipt["decision"]["decision_hash"]
        assert duplicate["effect_count"] == effects
        assert duplicate["ledger_entry_count"] == 1
        export = client.get(f"/demo/v1/runs/{request['run_id']}/receipt")
        assert export.status_code == 200
        assert "attachment" in export.headers["content-disposition"]
        assert export.json()["decision"]["decision_hash"] == receipt["decision"]["decision_hash"]
        assert export.json()["elapsed_ms"] is None
        assert export.json()["duplicate"] is None
        if scenario == "processor_code_z91":
            assert receipt["decision"]["advisory_class"] == "A"
            assert receipt["decision"]["selected_action"] == "escalate_review"
        sandbox = settings.database_path.with_name(f"{settings.database_path.stem}-playground.db")
        with connect(sandbox) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM effect_intents WHERE state != 'dry_run'"
                ).fetchone()[0]
                == 0
            )
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM outbox_messages WHERE transport_state != 'disabled'"
                ).fetchone()[0]
                == 0
            )
    with TestClient(create_app(settings)) as restarted:
        state = restarted.get("/demo/v1/playground").json()
        assert len(state["recent"]) == 1
        assert state["remaining_runs"] == 199


def test_playground_not_registered_in_razorpay_mode(test_settings: Settings) -> None:
    test_settings.console_dist.mkdir(parents=True)
    (test_settings.console_dist / "index.html").write_text("<html>Console shell</html>")
    with TestClient(create_app(test_settings)) as client:
        assert client.get("/demo/v1/playground").status_code == 404
        assert client.post("/demo/v1/runs", json={}).status_code in {404, 405}
        assert "/demo/v1/runs" not in client.get("/openapi.json").json()["paths"]
        assert client.get("/api/v1/not-an-endpoint").status_code == 404


def test_playground_rejects_cross_origin_and_changed_replay(test_settings: Settings) -> None:
    settings = test_settings.model_copy(update={"mode": "demo"})
    request = {"run_id": str(uuid4()), "scenario": "gateway_timeout", "amount_minor": 100}
    with TestClient(create_app(settings)) as client:
        assert client.post("/demo/v1/runs", json=request).status_code == 403
        assert (
            client.post(
                "/demo/v1/runs",
                json=request,
                headers={**HEADERS, "Origin": "https://untrusted.example"},
            ).status_code
            == 403
        )
        assert client.post("/demo/v1/runs", json=request, headers=HEADERS).status_code == 200
        assert (
            client.post(
                "/demo/v1/runs", json={**request, "amount_minor": 200}, headers=HEADERS
            ).status_code
            == 409
        )
        assert client.get("/demo/v1/playground").json()["remaining_runs"] == 199


@pytest.mark.parametrize(
    "invalid",
    [
        {"amount_minor": -1},
        {"amount_minor": True},
        {"amount_minor": 1.5},
        {"amount_minor": 100_000_001},
        {"scenario": "refund"},
        {"scenario": "card_expired", "method": "upi"},
        {"payment_id": "pay_real_123"},
        {"email": "person@example.com"},
        {"run_id": "../../salvage"},
    ],
)
def test_playground_rejects_non_synthetic_input(
    test_settings: Settings, invalid: dict[str, object]
) -> None:
    settings = test_settings.model_copy(update={"mode": "demo"})
    request = {
        "run_id": str(uuid4()),
        "scenario": "gateway_timeout",
        "amount_minor": 100,
        **invalid,
    }
    with TestClient(create_app(settings)) as client:
        assert client.post("/demo/v1/runs", json=request, headers=HEADERS).status_code == 422
        assert client.get("/demo/v1/playground").json()["recent"] == []


def test_playground_bounds_new_runs_but_allows_duplicates(
    test_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("salvage.api.playground.MAX_RUNS", 1)
    settings = test_settings.model_copy(update={"mode": "demo"})
    request = {"run_id": str(uuid4()), "scenario": "gateway_timeout", "amount_minor": 100}
    with TestClient(create_app(settings)) as client:
        assert client.post("/demo/v1/runs", json=request, headers=HEADERS).status_code == 200
        assert (
            client.post(
                "/demo/v1/runs", json={**request, "run_id": str(uuid4())}, headers=HEADERS
            ).status_code
            == 429
        )
        assert client.post("/demo/v1/runs", json=request, headers=HEADERS).json()["duplicate"]
