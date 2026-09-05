from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from salvage.domain.models import PaymentState
from salvage.persistence.db import connect


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stable_id(prefix: str, source: str) -> str:
    return f"{prefix}_{hashlib.sha256(source.encode()).hexdigest()[:20]}"


@dataclass(frozen=True, slots=True)
class EventProjection:
    event_id: str
    event_type: str
    payment_id: str
    order_id: str | None
    amount_minor: int
    currency: str
    method: str | None
    reason: str
    source: str | None
    step: str | None
    status: str
    received_at: datetime
    payload_digest: str


def store_event_and_job(
    path: Path, event: EventProjection, *, transaction: sqlite3.Connection | None = None
) -> bool:
    with nullcontext(transaction) if transaction is not None else connect(path) as connection:
        if transaction is None:
            connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = connection.execute(
                """
                INSERT INTO ingress_events(
                    event_id, event_type, payment_id, order_id, amount_minor, currency,
                    method, reason, source, step, status, received_at, payload_digest
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO NOTHING
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.payment_id,
                    event.order_id,
                    event.amount_minor,
                    event.currency,
                    event.method,
                    event.reason,
                    event.source,
                    event.step,
                    event.status,
                    iso(event.received_at),
                    event.payload_digest,
                ),
            )
            inserted = cursor.rowcount == 1
            if inserted:
                connection.execute(
                    """
                    INSERT INTO jobs(job_id, event_id, state, created_at)
                    VALUES (?, ?, 'queued', ?)
                    """,
                    (stable_id("job", event.event_id), event.event_id, iso(event.received_at)),
                )
            if transaction is None:
                connection.execute("COMMIT")
            return inserted
        except Exception:
            if transaction is None:
                connection.execute("ROLLBACK")
            raise


def claim_job(path: Path, owner: str, now: datetime, lease_seconds: int = 30) -> sqlite3.Row | None:
    with connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = cast(
                sqlite3.Row | None,
                connection.execute(
                    """
                    SELECT * FROM jobs
                    WHERE state = 'queued' OR (state = 'leased' AND lease_expires_at < ?)
                    ORDER BY created_at, job_id LIMIT 1
                    """,
                    (iso(now),),
                ).fetchone(),
            )
            if row is None:
                connection.execute("COMMIT")
                return None
            connection.execute(
                """
                UPDATE jobs SET state = 'leased', lease_owner = ?, lease_expires_at = ?,
                    attempt_count = attempt_count + 1
                WHERE job_id = ?
                """,
                (owner, iso(now + timedelta(seconds=lease_seconds)), row["job_id"]),
            )
            claimed = cast(
                sqlite3.Row | None,
                connection.execute(
                    "SELECT * FROM jobs WHERE job_id = ?", (row["job_id"],)
                ).fetchone(),
            )
            if claimed is None:
                raise RuntimeError("Leased job disappeared")
            connection.execute("COMMIT")
            return claimed
        except Exception:
            connection.execute("ROLLBACK")
            raise


def get_event(path: Path, event_id: str) -> sqlite3.Row:
    with connect(path) as connection:
        row = cast(
            sqlite3.Row | None,
            connection.execute(
                "SELECT * FROM ingress_events WHERE event_id = ?", (event_id,)
            ).fetchone(),
        )
    if row is None:
        raise KeyError(event_id)
    return row


def get_or_create_payment_state(path: Path, event: sqlite3.Row) -> PaymentState:
    with connect(path) as connection:
        connection.execute(
            """
            INSERT INTO payment_state(payment_id, amount_minor, currency)
            VALUES (?, ?, ?) ON CONFLICT(payment_id) DO NOTHING
            """,
            (event["payment_id"], event["amount_minor"], event["currency"]),
        )
        row = connection.execute(
            "SELECT * FROM payment_state WHERE payment_id = ?", (event["payment_id"],)
        ).fetchone()
    if row is None:
        raise RuntimeError("Payment state was not created")
    return PaymentState(
        payment_id=row["payment_id"],
        amount_minor=row["amount_minor"],
        currency=row["currency"],
        attempt_count=row["attempt_count"],
        contact_count=row["contact_count"],
        last_effect_at=parse_time(row["last_effect_at"]),
        manual_stop=bool(row["manual_stop"]),
        state_version=row["state_version"],
    )


def mark_job_failed(path: Path, job_id: str, message: str, *, max_attempts: int = 3) -> None:
    with connect(path) as connection:
        row = connection.execute(
            "SELECT attempt_count FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            return
        state = "dead_letter" if row["attempt_count"] >= max_attempts else "queued"
        connection.execute(
            """
            UPDATE jobs SET state = ?, lease_owner = NULL, lease_expires_at = NULL,
                last_error = ? WHERE job_id = ?
            """,
            (state, message[:500], job_id),
        )


def list_decision_rows(
    path: Path, limit: int = 100, *, event_id: str | None = None
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        rows = connection.execute(
            """
            SELECT d.*, e.amount_minor, e.currency, e.method,
                   fx.idempotency_key, fx.action AS effect_action, fx.state AS effect_state
            FROM decisions d
            JOIN ingress_events e ON e.event_id = d.event_id
            LEFT JOIN effect_intents fx ON fx.decision_id = d.decision_id
            WHERE (? IS NULL OR d.event_id = ?)
            ORDER BY d.created_at DESC, d.decision_id DESC LIMIT ?
            """,
            (event_id, event_id, limit),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["allowed_actions"] = json.loads(item.pop("allowed_actions_json"))
            item["decision_reasons"] = json.loads(item.pop("decision_reasons_json"))
            item["known_reason"] = bool(item["known_reason"])
            item["review_required"] = bool(item["review_required"])
            checks = connection.execute(
                "SELECT check_name, passed, explanation FROM gate_checks "
                "WHERE decision_id = ? ORDER BY check_name",
                (item["decision_id"],),
            ).fetchall()
            item["gate_checks"] = [
                {
                    "name": check["check_name"],
                    "passed": bool(check["passed"]),
                    "explanation": check["explanation"],
                }
                for check in checks
            ]
            result.append(item)
        return result


def database_counts(path: Path) -> dict[str, int]:
    tables = ["ingress_events", "jobs", "decisions", "effect_intents", "ledger_entries"]
    with connect(path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # noqa: S608
            for table in tables
        }
