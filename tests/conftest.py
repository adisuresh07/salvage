from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from salvage.config import ROOT, Settings


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        mode="razorpay_test",
        llm="off",
        database_path=tmp_path / "salvage-test.db",
        webhook_secret="synthetic-test-secret",  # noqa: S106 - labelled fixture credential
        policy_dir=ROOT / "policy",
        reports_dir=tmp_path / "reports",
        console_dist=tmp_path / "missing-console",
    )


def webhook_body(
    *,
    payment_id: str = "pay_test_001",
    reason: str = "gateway_timeout",
    source: str = "gateway",
    amount: int = 125_000,
) -> bytes:
    payload: dict[str, Any] = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": "order_synthetic_001",
                    "amount": amount,
                    "currency": "INR",
                    "method": "card",
                    "status": "failed",
                    "error_reason": reason,
                    "error_source": source,
                    "error_step": "payment_authorization",
                }
            }
        },
    }
    return json.dumps(payload, separators=(",", ":")).encode()
