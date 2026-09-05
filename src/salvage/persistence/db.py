from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from salvage.config import ROOT


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5.0, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 2500")
    return connection


def migrate(path: Path) -> list[str]:
    applied: list[str] = []
    with connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for migration in sorted((ROOT / "migrations").glob("*.sql")):
            sql = migration.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            row = connection.execute(
                "SELECT checksum FROM schema_migrations WHERE version = ?", (migration.name,)
            ).fetchone()
            if row:
                if row["checksum"] != checksum:
                    raise RuntimeError(f"Migration checksum changed: {migration.name}")
                continue
            connection.executescript(sql)
            connection.execute(
                "INSERT INTO schema_migrations(version, checksum) VALUES (?, ?)",
                (migration.name, checksum),
            )
            applied.append(migration.name)
    return applied


def schema_current(path: Path) -> bool:
    migrate(path)
    with connect(path) as connection:
        connection.execute("SELECT 1").fetchone()
    return True
