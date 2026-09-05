from __future__ import annotations

import re
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from salvage.config import Settings


class ProviderError(Exception):
    """Sanitized provider failure; never include a raw response or credentials."""


class TestPayment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(pattern=r"^pay_[A-Za-z0-9]+$")
    order_id: str = Field(pattern=r"^order_[A-Za-z0-9]+$")
    amount: int = Field(strict=True, ge=1)
    currency: str
    status: str
    method: str | None = None
    error_reason: str | None = None
    error_source: str | None = None
    error_step: str | None = None


class RazorpayTest:
    def __init__(self, settings: Settings):
        if not settings.razorpay_key_id.startswith("rzp_test_"):
            raise ProviderError("test_credentials_required")
        if not settings.razorpay_key_secret.get_secret_value():
            raise ProviderError("test_credentials_required")
        self.settings = settings

    def _request(self, method: str, path: str, body: dict[str, object] | None = None) -> Any:
        try:
            with httpx.Client(
                base_url="https://api.razorpay.com/v1/",
                timeout=httpx.Timeout(15, connect=5),
                follow_redirects=False,
                trust_env=False,
                auth=(
                    self.settings.razorpay_key_id,
                    self.settings.razorpay_key_secret.get_secret_value(),
                ),
            ) as client:
                response = client.request(method, path, json=body)
            if response.status_code not in {200, 201}:
                raise ProviderError("razorpay_request_rejected")
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError("razorpay_unavailable") from exc

    def create_order(self, amount: int, receipt: str) -> str:
        payload = self._request(
            "POST",
            "orders",
            {
                "amount": amount,
                "currency": "INR",
                "receipt": receipt,
                "notes": {"purpose": "Salvage sandbox only"},
            },
        )
        order_id = payload.get("id", "") if isinstance(payload, dict) else ""
        if not re.fullmatch(r"order_[A-Za-z0-9]+", order_id):
            raise ProviderError("razorpay_invalid_order")
        if payload.get("amount") != amount or payload.get("currency") != "INR":
            raise ProviderError("razorpay_order_mismatch")
        return str(order_id)

    def payments(self, order_id: str) -> list[TestPayment]:
        if not re.fullmatch(r"order_[A-Za-z0-9]+", order_id):
            raise ProviderError("invalid_order")
        try:
            data = self._request("GET", f"orders/{order_id}/payments")
            return [TestPayment.model_validate(item) for item in data["items"]]
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("razorpay_invalid_payment_response") from exc
