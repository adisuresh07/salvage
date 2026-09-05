from __future__ import annotations

from pathlib import Path

from salvage.audit.ledger import verify_ledger
from salvage.config import Settings
from salvage.demo import run_demo
from salvage.evaluation.runner import run_evaluation
from salvage.persistence.db import connect


def test_evaluation_is_same_batch_and_deterministic() -> None:
    first = run_evaluation(seed=42, count=100)
    second = run_evaluation(seed=42, count=100)
    assert first == second
    assert first["batch_digest"] == second["batch_digest"]
    assert {policy["policy"] for policy in first["policies"]} == {
        "retry_all_3x",
        "never_retry",
        "salvage",
    }
    salvage = next(policy for policy in first["policies"] if policy["policy"] == "salvage")
    assert salvage["class_d_violations"] == 0
    assert "Simulated:" in first["real_vs_simulated"]
    assert [case["label"] for case in first["sensitivity"]] == ["lower", "base", "upper"]
    assert {case["batch_digest"] for case in first["sensitivity"]} == {first["batch_digest"]}
    sensitivity_rates = [
        next(policy for policy in case["policies"] if policy["policy"] == "salvage")[
            "recovery_rate"
        ]
        for case in first["sensitivity"]
    ]
    assert sensitivity_rates[0] < sensitivity_rates[1] < sensitivity_rates[2]
    assert all(
        next(policy for policy in case["policies"] if policy["policy"] == "salvage")[
            "class_d_violations"
        ]
        == 0
        for case in first["sensitivity"]
    )


def test_ledger_detects_tampering(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_path=tmp_path / "tamper.db",
        reports_dir=tmp_path / "reports",
        console_dist=tmp_path / "console" / "dist",
    )
    run_demo(settings)
    assert verify_ledger(settings.database_path).valid
    with connect(settings.database_path) as connection:
        connection.execute("UPDATE ledger_entries SET content_json = '{}' WHERE sequence = 1")
    status = verify_ledger(settings.database_path)
    assert not status.valid
    assert status.first_mismatch_sequence == 1
