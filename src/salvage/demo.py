from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from salvage.audit.ledger import verify_ledger
from salvage.config import Settings
from salvage.evaluation.runner import run_evaluation, write_artifacts
from salvage.execution.worker import process_all
from salvage.ingress.webhook import project_event
from salvage.persistence.db import connect, migrate
from salvage.persistence.repository import (
    database_counts,
    iso,
    list_decision_rows,
    store_event_and_job,
)

DEMO_PAYMENTS: tuple[dict[str, Any], ...] = (
    {"reason": "gateway_timeout", "source": "gateway", "amount": 1240000, "method": "card"},
    {"reason": "insufficient_funds", "source": "customer", "amount": 875000, "method": "upi"},
    {"reason": "authentication_failed", "source": "customer", "amount": 2490000, "method": "card"},
    {"reason": "risk_threshold", "source": "risk", "amount": 4200000, "method": "card"},
    {"reason": "bank_technical_error", "source": "bank", "amount": 1565000, "method": "netbanking"},
    {"reason": "card_expired", "source": "customer", "amount": 695000, "method": "card"},
    {"reason": "processor_code_z91", "source": "gateway", "amount": 1830000, "method": "upi"},
    {"reason": "gateway_technical_error", "source": "gateway", "amount": 960000, "method": "card"},
    {"reason": "balance_insufficient", "source": "customer", "amount": 537000, "method": "upi"},
    {"reason": "incorrect_pin", "source": "customer", "amount": 1285000, "method": "card"},
    {"reason": "payment_declined", "source": "issuer", "amount": 2199000, "method": "card"},
    {"reason": "gateway_timeout", "source": "gateway", "amount": 745000, "method": "upi"},
)


def _body(index: int, item: dict[str, Any]) -> bytes:
    payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_SALVAGE{index:03d}",
                    "order_id": f"order_DEMO{index:03d}",
                    "amount": item["amount"],
                    "currency": "INR",
                    "method": item["method"],
                    "status": "failed",
                    "error_reason": item["reason"],
                    "error_source": item["source"],
                    "error_step": "payment_authorization",
                    "description": "Synthetic demo payment. No real customer data.",
                }
            }
        },
    }
    return json.dumps(payload, separators=(",", ":")).encode()


def seed_demo(settings: Settings) -> int:
    migrate(settings.database_path)
    base_time = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    inserted = 0
    for index, item in enumerate(DEMO_PAYMENTS, start=1):
        event_id = f"evt_demo_{index:03d}"
        projection = project_event(
            _body(index, item), event_id, base_time + timedelta(minutes=index)
        )
        inserted += int(store_event_and_job(settings.database_path, projection))
    process_all(settings, now=base_time + timedelta(hours=1))
    return inserted


def save_evaluation(
    settings: Settings, *, seed: int = 20260829, count: int = 500
) -> dict[str, Any]:
    result = run_evaluation(seed, count)
    write_artifacts(result, settings.reports_dir)
    with connect(settings.database_path) as connection:
        connection.execute(
            """
            INSERT INTO eval_batches(
                batch_id, seed, scenario_count, batch_digest, result_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(batch_id) DO UPDATE SET result_json = excluded.result_json,
                batch_digest = excluded.batch_digest
            """,
            (
                result["batch_id"],
                result["seed"],
                result["scenario_count"],
                result["batch_digest"],
                json.dumps(result, separators=(",", ":")),
                iso(datetime(2026, 8, 29, 12, 0, tzinfo=UTC)),
            ),
        )
    return result


def ensure_demo(settings: Settings) -> None:
    migrate(settings.database_path)
    if database_counts(settings.database_path)["decisions"] == 0:
        seed_demo(settings)
    with connect(settings.database_path) as connection:
        batches = int(connection.execute("SELECT COUNT(*) FROM eval_batches").fetchone()[0])
    if batches == 0:
        save_evaluation(settings)


def export_console_bundle(settings: Settings) -> Path:
    with connect(settings.database_path) as connection:
        batch_rows = [
            dict(row)
            for row in connection.execute(
                "SELECT batch_id, seed, scenario_count, batch_digest, created_at "
                "FROM eval_batches ORDER BY created_at DESC"
            ).fetchall()
        ]
        result_row = connection.execute(
            "SELECT result_json FROM eval_batches ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    ledger = verify_ledger(settings.database_path)
    bundle = {
        "decisions": {
            "items": list_decision_rows(settings.database_path, 100),
            "next_cursor": None,
        },
        "batches": {"items": batch_rows},
        "ledger": {
            "valid": ledger.valid,
            "entry_count": ledger.entry_count,
            "final_hash": ledger.final_hash,
            "first_mismatch_sequence": ledger.first_mismatch_sequence,
        },
        "result": json.loads(result_row["result_json"]) if result_row else None,
        "source": "static_demo",
    }
    target = settings.console_dist.parent / "public" / "demo-data.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return target


def reset_demo_database(path: Path) -> None:
    resolved = path.resolve()
    if resolved.suffix not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError("Refusing to reset a path without a SQLite file extension")
    for candidate in (resolved, Path(f"{resolved}-wal"), Path(f"{resolved}-shm")):
        if candidate.exists() and candidate.is_file():
            candidate.unlink()


def run_demo(settings: Settings, *, reset: bool = True) -> dict[str, Any]:
    settings.assert_safe()
    if settings.mode != "demo":
        raise ValueError("The offline demo is available only in demo mode")
    if reset:
        reset_demo_database(settings.database_path)
    migrate(settings.database_path)
    seed_demo(settings)
    result = save_evaluation(settings)
    export_console_bundle(settings)
    ledger = verify_ledger(settings.database_path)
    if not ledger.valid:
        raise RuntimeError("Ledger verification failed; refusing a green demo result")
    return {
        "database": str(settings.database_path),
        "reports": str(settings.reports_dir),
        "counts": database_counts(settings.database_path),
        "ledger": {
            "valid": ledger.valid,
            "entry_count": ledger.entry_count,
            "final_hash": ledger.final_hash,
        },
        "batch_id": result["batch_id"],
        "batch_digest": result["batch_digest"],
    }
