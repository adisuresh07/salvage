"""Local-only synthetic experiments, isolated from operator/payment data."""

from __future__ import annotations

import json
from threading import Lock
from time import perf_counter
from typing import Literal, Self
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from salvage.api.schemas import DecisionOut
from salvage.audit.ledger import verify_ledger
from salvage.config import DEMO_WEBHOOK_SECRET, Settings
from salvage.execution.worker import process_next
from salvage.ingress.webhook import project_event, signature_for, verify_signature
from salvage.persistence.db import connect, migrate
from salvage.persistence.repository import database_counts, get_event, list_decision_rows
from salvage.persistence.repository import store_event_and_job as store_event

Scenario = Literal[
    "gateway_timeout", "insufficient_funds", "card_expired", "risk_threshold", "processor_code_z91"
]
MAX_RUNS = 200
LOCAL_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
}


class PlaygroundScenario(BaseModel):
    id: Scenario
    label: str
    description: str


SCENARIOS = [
    PlaygroundScenario(
        id="gateway_timeout",
        label="Gateway timeout",
        description="The payment provider did not respond.",
    ),
    PlaygroundScenario(
        id="insufficient_funds",
        label="Insufficient funds",
        description="The payment needs more time, not an immediate retry.",
    ),
    PlaygroundScenario(
        id="card_expired",
        label="Expired card",
        description="Retrying the same instrument will not fix it.",
    ),
    PlaygroundScenario(
        id="risk_threshold", label="Risk decline", description="A risk signal requires a hard stop."
    ),
    PlaygroundScenario(
        id="processor_code_z91",
        label="Unknown reason",
        description="An unmapped code tests the fail-closed boundary.",
    ),
]


class PlaygroundInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    scenario: Scenario
    amount_minor: int = Field(strict=True, ge=1, le=100_000_000)
    method: Literal["card", "upi", "netbanking"] = "card"

    @model_validator(mode="after")
    def validate_instrument(self) -> Self:
        if self.scenario == "card_expired" and self.method != "card":
            raise ValueError("An expired-card scenario requires the card method")
        return self


class PlaygroundReceipt(BaseModel):
    request: PlaygroundInput
    decision: DecisionOut
    duplicate: bool | None
    ingress_verified: bool
    ledger_valid: bool
    event_count: int
    decision_count: int
    effect_count: int
    ledger_entry_count: int
    elapsed_ms: int | None
    safety_mode: Literal["dry_run"] = "dry_run"


class PlaygroundState(BaseModel):
    scenarios: list[PlaygroundScenario]
    recent: list[DecisionOut]
    remaining_runs: int


def create_playground_router(active: Settings) -> APIRouter:
    router = APIRouter(prefix="/demo/v1", tags=["local synthetic playground"])
    sandbox = active.model_copy(
        update={
            "database_path": active.database_path.with_name(
                f"{active.database_path.stem}-playground.db"
            ),
            "mode": "demo",
            "llm": "cache-only",
            "webhook_secret": DEMO_WEBHOOK_SECRET,
        }
    )
    lock = Lock()
    initialized = False

    def initialize() -> None:
        nonlocal initialized
        if not initialized:
            migrate(sandbox.database_path)
            initialized = True

    def receipt(
        run: PlaygroundInput, *, duplicate: bool | None, elapsed_ms: int | None = None
    ) -> PlaygroundReceipt:
        event_id = f"evt_play_{run.run_id.hex}"
        rows = list_decision_rows(sandbox.database_path, event_id=event_id)
        if not rows:
            raise HTTPException(503, "This test is not complete yet. Replay it to retry safely.")
        decision = DecisionOut.model_validate(rows[0])
        ledger = verify_ledger(sandbox.database_path)
        with connect(sandbox.database_path) as connection:
            effects = connection.execute(
                "SELECT COUNT(*) FROM effect_intents WHERE decision_id = ?", (decision.decision_id,)
            ).fetchone()[0]
            entries = connection.execute(
                "SELECT COUNT(*) FROM ledger_entries WHERE record_id = ?", (decision.decision_id,)
            ).fetchone()[0]
        return PlaygroundReceipt(
            request=run,
            decision=decision,
            duplicate=duplicate,
            ingress_verified=True,
            ledger_valid=ledger.valid,
            event_count=1,
            decision_count=len(rows),
            effect_count=effects,
            ledger_entry_count=entries,
            elapsed_ms=elapsed_ms,
        )

    @router.get("/playground", response_model=PlaygroundState)
    def state(response: Response) -> PlaygroundState:
        response.headers["Cache-Control"] = "no-store"
        with lock:
            initialize()
            return PlaygroundState(
                scenarios=SCENARIOS,
                recent=[
                    DecisionOut.model_validate(row)
                    for row in list_decision_rows(sandbox.database_path, 10)
                ],
                remaining_runs=max(
                    0, MAX_RUNS - database_counts(sandbox.database_path)["ingress_events"]
                ),
            )

    @router.post("/runs", response_model=PlaygroundReceipt)
    def run_scenario(
        run: PlaygroundInput,
        response: Response,
        origin: str | None = Header(default=None),
        x_salvage_playground: str | None = Header(default=None),
    ) -> PlaygroundReceipt:
        if origin not in LOCAL_ORIGINS or x_salvage_playground != "1":
            raise HTTPException(403, "Run synthetic tests from the local Salvage playground.")
        response.headers["Cache-Control"] = "no-store"
        started = perf_counter()
        event_id = f"evt_play_{run.run_id.hex}"
        raw = json.dumps(
            {
                "event": "payment.failed",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": f"pay_play_{run.run_id.hex}",
                            "amount": run.amount_minor,
                            "currency": "INR",
                            "method": run.method,
                            "status": "failed",
                            "error_reason": run.scenario,
                            "error_source": "risk"
                            if run.scenario == "risk_threshold"
                            else "gateway",
                        }
                    }
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        signature = signature_for(raw, sandbox.webhook_secret)
        if not verify_signature(raw, signature, sandbox.webhook_secret):
            raise HTTPException(500, "Synthetic signature verification failed.")
        event = project_event(raw, event_id)
        with lock:
            initialize()
            try:
                existing = get_event(sandbox.database_path, event_id)
            except KeyError:
                existing = None
            if existing is not None and existing["payload_digest"] != event.payload_digest:
                raise HTTPException(
                    409, "This test ID already belongs to different input. Start a new test."
                )
            if (
                existing is None
                and database_counts(sandbox.database_path)["ingress_events"] >= MAX_RUNS
            ):
                raise HTTPException(
                    429, "The local playground has reached its 200-test safety limit."
                )
            inserted = store_event(sandbox.database_path, event)
            # A bounded local test runner invokes the same durable worker as ingress.
            # The real webhook endpoint remains asynchronous and untouched.
            for _ in range(3):
                if list_decision_rows(sandbox.database_path, event_id=event_id):
                    break
                process_next(sandbox, owner="playground")
            return receipt(
                run, duplicate=not inserted, elapsed_ms=round((perf_counter() - started) * 1000)
            )

    @router.get("/runs/{run_id}/receipt", response_model=PlaygroundReceipt)
    def download_receipt(run_id: UUID, response: Response) -> PlaygroundReceipt:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Disposition"] = (
            f'attachment; filename="salvage-test-{run_id}.json"'
        )
        with lock:
            initialize()
            try:
                event = get_event(sandbox.database_path, f"evt_play_{run_id.hex}")
            except KeyError as exc:
                raise HTTPException(404, "Test not found") from exc
            run = PlaygroundInput.model_validate(
                {
                    "run_id": run_id,
                    "scenario": event["reason"],
                    "amount_minor": event["amount_minor"],
                    "method": event["method"],
                }
            )
            # An export is a read, not a new delivery or a timing measurement.
            return receipt(run, duplicate=None)

    return router
