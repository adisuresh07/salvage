from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from salvage.domain.loading import canonical_json
from salvage.persistence.db import connect
from salvage.persistence.repository import iso


def entry_hash(prev_hash: str | None, content_json: str) -> str:
    envelope = canonical_json({"prev_hash": prev_hash, "content": json.loads(content_json)})
    return hashlib.sha256(envelope.encode()).hexdigest()


def append_entry(
    connection: sqlite3.Connection,
    entry_type: str,
    record_id: str,
    content: dict[str, Any],
    created_at: datetime,
) -> str:
    previous = connection.execute(
        "SELECT entry_hash FROM ledger_entries ORDER BY sequence DESC LIMIT 1"
    ).fetchone()
    previous_hash = previous["entry_hash"] if previous else None
    content_json = canonical_json(content)
    digest = entry_hash(previous_hash, content_json)
    connection.execute(
        """
        INSERT INTO ledger_entries(
            entry_type, record_id, content_json, prev_hash, entry_hash, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (entry_type, record_id, content_json, previous_hash, digest, iso(created_at)),
    )
    return digest


@dataclass(frozen=True, slots=True)
class LedgerStatus:
    valid: bool
    entry_count: int
    final_hash: str | None
    first_mismatch_sequence: int | None = None


def verify_ledger(path: Path) -> LedgerStatus:
    expected_previous: str | None = None
    count = 0
    with connect(path) as connection:
        rows = connection.execute("SELECT * FROM ledger_entries ORDER BY sequence").fetchall()
        for row in rows:
            count += 1
            expected_hash = entry_hash(expected_previous, row["content_json"])
            if row["prev_hash"] != expected_previous or row["entry_hash"] != expected_hash:
                return LedgerStatus(False, count, expected_previous, row["sequence"])
            expected_previous = row["entry_hash"]
    return LedgerStatus(True, count, expected_previous)
