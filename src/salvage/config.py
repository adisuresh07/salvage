from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DEMO_WEBHOOK_SECRET = "salvage-demo-webhook-secret"  # noqa: S105 - synthetic fixture only


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SALVAGE_", env_file=".env", extra="ignore")

    mode: Literal["demo", "razorpay_test"] = "demo"
    llm: Literal["off", "cache-only", "ollama", "groq"] = "off"
    database_path: Path = Field(default=ROOT / "data" / "salvage.db")
    webhook_secret: str = DEMO_WEBHOOK_SECRET
    max_body_bytes: int = 256_000
    policy_dir: Path = ROOT / "policy"
    advisory_cache_path: Path = ROOT / "fixtures" / "advisory-cache" / "suggestions.json"
    reports_dir: Path = ROOT / "reports"
    console_dist: Path = ROOT / "console" / "dist"
    simulator_enabled: bool = False
    simulator_database_path: Path = ROOT / "data" / "salvage-simulator.db"
    ollama_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="OLLAMA_API_KEY")
    ollama_model: str = "gpt-oss:20b"
    razorpay_key_id: str = ""
    razorpay_key_secret: SecretStr = SecretStr("")
    public_webhook_url: str = ""

    def assert_safe(self) -> None:
        if self.mode != "demo" and self.webhook_secret == DEMO_WEBHOOK_SECRET:
            raise ValueError("Razorpay Test Mode requires an explicit webhook secret")
        if self.mode not in {"demo", "razorpay_test"}:
            raise ValueError("Live mode does not exist in the Salvage MVP")
        if self.simulator_enabled:
            if self.razorpay_key_id and not self.razorpay_key_id.startswith("rzp_test_"):
                raise ValueError("The connected simulator accepts only Razorpay Test Mode keys")
            if self.simulator_database_path.resolve() == self.database_path.resolve():
                raise ValueError("The simulator must use its own database")


settings = Settings()
