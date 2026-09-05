from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import UTC, datetime
from threading import Event, Thread
from typing import Literal, cast
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from salvage.advisory.cloud import CloudResult, explain
from salvage.api.playground import SCENARIOS, PlaygroundScenario, Scenario
from salvage.api.schemas import DecisionOut
from salvage.audit.ledger import append_entry, verify_ledger
from salvage.config import DEMO_WEBHOOK_SECRET, Settings
from salvage.domain.loading import fingerprint
from salvage.execution.worker import process_next
from salvage.ingress.webhook import project_event, verify_signature
from salvage.persistence.db import connect, migrate
from salvage.persistence.repository import iso, list_decision_rows, store_event_and_job
from salvage.simulator.razorpay import ProviderError, RazorpayTest, TestPayment


class RunInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    source: Literal["synthetic", "razorpay_test"]
    scenario: Scenario = "gateway_timeout"
    amount_minor: int = Field(strict=True, ge=100, le=1_000_000)
    method: Literal["card", "upi", "netbanking"] = "card"

    @model_validator(mode="after")
    def valid_method(self) -> RunInput:
        if self.source == "synthetic" and self.scenario == "card_expired" and self.method != "card":
            raise ValueError("Expired card requires the card method")
        return self


class RunOut(BaseModel):
    run_id: str
    source: str
    scenario: str
    amount_minor: int
    method: str
    stage: str
    created_at: str
    order_id: str | None
    payment_id: str | None
    event_source: str | None
    error_code: str | None
    checkout_key_id: str | None
    decision: DecisionOut | None
    advice: CloudResult | None
    webhook_received: bool
    webhook_deliveries: int
    ledger_valid: bool
    safety_mode: Literal["test_only_dry_run_recovery"] = "test_only_dry_run_recovery"


class SimulatorState(BaseModel):
    cloud_configured: bool
    cloud_model: str
    razorpay_configured: bool
    public_webhook_url: str | None
    webhook_received: bool
    remaining_runs: int
    remaining_orders: int
    scenarios: list[PlaygroundScenario]
    recent: list[RunOut]


def now() -> str:
    return iso(datetime.now(UTC))


class Simulator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.simulator_database_path
        self.worker_settings = settings.model_copy(
            update={
                "database_path": self.path,
                "llm": "off",
                "simulator_enabled": False,
            }
        )
        self.stop_event = Event()
        self.thread: Thread | None = None

    def start(self) -> None:
        migrate(self.path)
        # An interrupted request is not silently repeated and billed again.
        with connect(self.path) as db:
            db.execute(
                "UPDATE simulator_runs SET stage='order_uncertain',"
                "error_code='order_creation_interrupted' WHERE stage='creating_order'"
            )
            rows = db.execute(
                "SELECT run_id, advice_json FROM simulator_runs WHERE advice_json IS NOT NULL"
            ).fetchall()
            for row in rows:
                advice = CloudResult.model_validate_json(row["advice_json"])
                if advice.status == "requesting":
                    advice.status = "unavailable"
                    advice.error_code = "generation_interrupted"
                    self.save_advice(row["run_id"], advice)
        self.thread = Thread(target=self.loop, daemon=True, name="salvage-simulator")
        self.thread.start()

    def close(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=30)

    def loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.tick()
            except Exception:
                # No provider response, key, raw event, or traceback enters the UI/logs.
                logging.getLogger(__name__).warning("Simulator worker cycle failed; retrying")
            self.stop_event.wait(0.4)

    def tick(self) -> None:
        process_next(self.worker_settings, owner="connected-simulator")
        with connect(self.path) as db:
            rows = db.execute(
                "SELECT r.run_id, r.event_id FROM simulator_runs r "
                "JOIN decisions d ON d.event_id = r.event_id "
                "WHERE r.advice_json IS NULL ORDER BY r.created_at LIMIT 1"
            ).fetchall()
            if not rows:
                return
            row = rows[0]
            pending = CloudResult(
                status="requesting", model=self.settings.ollama_model, generation_id=row["run_id"]
            )
            cursor = db.execute(
                "UPDATE simulator_runs SET advice_json = ?, stage = CASE WHEN "
                "stage='payment_succeeded' THEN stage ELSE 'analyzing' END "
                "WHERE run_id = ? AND advice_json IS NULL",
                (pending.model_dump_json(), row["run_id"]),
            )
            if cursor.rowcount != 1:
                return
        decision = list_decision_rows(self.path, event_id=row["event_id"])[0]
        advice = explain(
            self.settings,
            run_id=row["run_id"],
            reason=decision["reason"],
            effective_class=decision["effective_class"],
            action=decision["selected_action"],
        )
        self.save_advice(row["run_id"], advice)

    def save_advice(self, run_id: str, advice: CloudResult) -> None:
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE simulator_runs SET advice_json = ?, stage = CASE WHEN "
                "stage='payment_succeeded' THEN stage ELSE 'complete' END WHERE run_id = ?",
                (advice.model_dump_json(), run_id),
            )
            append_entry(
                db, "cloud_advisory", run_id, advice.model_dump(mode="json"), datetime.now(UTC)
            )
            db.execute("COMMIT")

    def row(self, run_id: str) -> sqlite3.Row:
        with connect(self.path) as db:
            row = db.execute("SELECT * FROM simulator_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Simulator run not found")
        return cast(sqlite3.Row, row)

    def result(self, run_id: str) -> RunOut:
        row = self.row(run_id)
        decisions = (
            list_decision_rows(self.path, event_id=row["event_id"]) if row["event_id"] else []
        )
        with connect(self.path) as db:
            deliveries = db.execute(
                "SELECT COALESCE(SUM(delivery_count), 0) FROM "
                "simulator_deliveries WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]
            job = db.execute(
                "SELECT state FROM jobs WHERE event_id = ?", (row["event_id"],)
            ).fetchone()
        stage = "needs_review" if job and job["state"] == "dead_letter" else row["stage"]
        return RunOut(
            **{
                key: row[key]
                for key in (
                    "run_id",
                    "source",
                    "scenario",
                    "amount_minor",
                    "method",
                    "created_at",
                    "order_id",
                    "payment_id",
                    "event_source",
                    "error_code",
                )
            },
            stage=stage,
            checkout_key_id=self.settings.razorpay_key_id if row["order_id"] else None,
            decision=DecisionOut.model_validate(decisions[0]) if decisions else None,
            advice=CloudResult.model_validate_json(row["advice_json"])
            if row["advice_json"]
            else None,
            webhook_received=deliveries > 0,
            webhook_deliveries=deliveries,
            ledger_valid=verify_ledger(self.path).valid,
        )

    def state(self) -> SimulatorState:
        with connect(self.path) as db:
            recent = db.execute(
                "SELECT run_id FROM simulator_runs ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
            count = db.execute("SELECT COUNT(*) FROM simulator_runs").fetchone()[0]
            orders = db.execute(
                "SELECT COUNT(*) FROM simulator_runs WHERE source = 'razorpay_test'"
            ).fetchone()[0]
            deliveries = db.execute("SELECT COUNT(*) FROM simulator_deliveries").fetchone()[0]
        return SimulatorState(
            cloud_configured=bool(self.settings.ollama_api_key.get_secret_value()),
            cloud_model=self.settings.ollama_model,
            razorpay_configured=self.settings.razorpay_key_id.startswith("rzp_test_")
            and bool(self.settings.razorpay_key_secret.get_secret_value()),
            public_webhook_url=self.settings.public_webhook_url or None,
            webhook_received=deliveries > 0,
            remaining_runs=max(0, 200 - count),
            remaining_orders=max(0, 30 - orders),
            scenarios=SCENARIOS,
            recent=[self.result(row["run_id"]) for row in recent],
        )

    def create(self, request: RunInput) -> RunOut:
        run_id = str(request.run_id)
        digest = fingerprint(request.model_dump(mode="json"))
        if request.source == "razorpay_test":
            try:
                RazorpayTest(self.settings)
            except ProviderError as exc:
                raise HTTPException(503, str(exc)) from exc
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT * FROM simulator_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if existing:
                db.execute("ROLLBACK")
                if existing["input_digest"] != digest:
                    raise HTTPException(409, "This run ID belongs to different input")
                return self.result(run_id)
            count = db.execute("SELECT COUNT(*) FROM simulator_runs").fetchone()[0]
            orders = db.execute(
                "SELECT COUNT(*) FROM simulator_runs WHERE source='razorpay_test'"
            ).fetchone()[0]
            if count >= 200 or (request.source == "razorpay_test" and orders >= 30):
                db.execute("ROLLBACK")
                raise HTTPException(429, "The simulator's local safety limit has been reached")
            db.execute(
                "INSERT INTO simulator_runs(run_id,source,scenario,amount_minor,method,"
                "input_digest,stage,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    request.source,
                    request.scenario,
                    request.amount_minor,
                    request.method,
                    digest,
                    "creating_order" if request.source == "razorpay_test" else "queued",
                    now(),
                ),
            )
            if request.source == "synthetic":
                entity = {
                    "id": f"pay_sim{request.run_id.hex}",
                    "amount": request.amount_minor,
                    "currency": "INR",
                    "method": request.method,
                    "status": "failed",
                    "error_reason": request.scenario,
                    "error_source": "risk" if request.scenario == "risk_threshold" else "gateway",
                }
                raw = json.dumps(
                    {"event": "payment.failed", "payload": {"payment": {"entity": entity}}}
                ).encode()
                projection = project_event(raw, f"evt_sim_{request.run_id.hex}")
                store_event_and_job(self.path, projection, transaction=db)
                db.execute(
                    "UPDATE simulator_runs SET event_id=?,payment_id=?,event_source='synthetic' "
                    "WHERE run_id=?",
                    (projection.event_id, projection.payment_id, run_id),
                )
            db.execute("COMMIT")
        if request.source == "razorpay_test":
            try:
                order_id = RazorpayTest(self.settings).create_order(
                    request.amount_minor, f"sim_{request.run_id.hex}"
                )
                with connect(self.path) as db:
                    db.execute(
                        "UPDATE simulator_runs SET order_id=?,stage='awaiting_payment' "
                        "WHERE run_id=?",
                        (order_id, run_id),
                    )
            except ProviderError as exc:
                # No automatic POST retry: the provider may have created the order.
                with connect(self.path) as db:
                    db.execute(
                        "UPDATE simulator_runs SET stage='order_uncertain',error_code=? "
                        "WHERE run_id=?",
                        (str(exc), run_id),
                    )
        return self.result(run_id)

    def sync(self, run_id: str) -> RunOut:
        row = self.row(run_id)
        if not row["order_id"]:
            raise HTTPException(409, "This run has no confirmed Razorpay order")
        with connect(self.path) as db:
            # Bound user-triggered provider polling. Reads never initiate provider calls.
            cutoff = datetime.now(UTC).timestamp() - 3
            if (
                row["last_sync_at"]
                and datetime.fromisoformat(row["last_sync_at"].replace("Z", "+00:00")).timestamp()
                > cutoff
            ):
                raise HTTPException(429, "Wait a few seconds before checking Razorpay again")
            db.execute("UPDATE simulator_runs SET last_sync_at=? WHERE run_id=?", (now(), run_id))
        try:
            payments = RazorpayTest(self.settings).payments(row["order_id"])
        except ProviderError as exc:
            raise HTTPException(502, str(exc)) from exc
        matches = [
            p
            for p in payments
            if p.order_id == row["order_id"]
            and p.amount == row["amount_minor"]
            and p.currency == "INR"
        ]
        succeeded = next((p for p in matches if p.status in {"authorized", "captured"}), None)
        if succeeded:
            with connect(self.path) as db:
                db.execute(
                    "UPDATE simulator_runs SET stage='payment_succeeded',payment_id=? "
                    "WHERE run_id=?",
                    (succeeded.id, run_id),
                )
        elif failed := next((p for p in matches if p.status == "failed"), None):
            raw = self.payment_body(failed)
            self.accept_failure(raw, f"evt_api_{failed.id}", "razorpay_api")
        return self.result(run_id)

    @staticmethod
    def payment_body(payment: TestPayment) -> bytes:
        entity = payment.model_dump()
        entity["error_reason"] = payment.error_reason or "unknown_provider_failure"
        return json.dumps(
            {"event": "payment.failed", "payload": {"payment": {"entity": entity}}}
        ).encode()

    def webhook(self, raw: bytes, signature: str, event_id: str) -> dict[str, bool | str]:
        if self.settings.webhook_secret == DEMO_WEBHOOK_SECRET:
            raise HTTPException(503, "A separate webhook secret must be configured")
        if not verify_signature(raw, signature, self.settings.webhook_secret):
            raise HTTPException(401, "Invalid webhook signature")
        return self.accept_failure(raw, event_id, "razorpay_webhook")

    def accept_failure(self, raw: bytes, event_id: str, source: str) -> dict[str, bool | str]:
        try:
            projection = project_event(raw, event_id)
        except (ValueError, TypeError, KeyError) as exc:
            raise HTTPException(422, "Invalid payment.failed event") from exc
        with connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM simulator_runs WHERE order_id=? AND source='razorpay_test'",
                (projection.order_id,),
            ).fetchone()
            if (
                row is None
                or row["amount_minor"] != projection.amount_minor
                or projection.currency != "INR"
                or projection.status != "failed"
            ):
                db.execute("ROLLBACK")
                raise HTTPException(422, "Event does not match a simulator Test Mode order")
            if source == "razorpay_webhook":
                if row["event_id"] and row["payment_id"] != projection.payment_id:
                    db.execute("ROLLBACK")
                    return {"status": "ignored_different_attempt", "duplicate": True}
                existing = db.execute(
                    "SELECT * FROM simulator_deliveries WHERE event_id=?", (event_id,)
                ).fetchone()
                if existing and existing["payload_digest"] != hashlib.sha256(raw).hexdigest():
                    db.execute("ROLLBACK")
                    raise HTTPException(409, "Changed body for an existing delivery ID")
                db.execute(
                    "INSERT INTO simulator_deliveries(event_id,run_id,payload_digest,"
                    "first_received_at,last_received_at) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(event_id) DO UPDATE SET delivery_count=delivery_count+1,"
                    "last_received_at=excluded.last_received_at",
                    (event_id, row["run_id"], projection.payload_digest, now(), now()),
                )
            duplicate = bool(row["event_id"])
            if not duplicate and row["stage"] != "payment_succeeded":
                store_event_and_job(self.path, projection, transaction=db)
                db.execute(
                    "UPDATE simulator_runs SET event_id=?,event_source=?,payment_id=?,"
                    "stage='queued' WHERE run_id=?",
                    (projection.event_id, source, projection.payment_id, row["run_id"]),
                )
            db.execute("COMMIT")
        return {"status": "accepted", "duplicate": duplicate}
