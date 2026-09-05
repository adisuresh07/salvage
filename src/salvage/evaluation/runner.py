from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, select_autoescape

from salvage.config import ROOT
from salvage.domain.loading import canonical_json

REAL_VS_SIMULATED = (
    "Real: deterministic triage, policy, Gatekeeper, idempotency and audit code. "
    "Simulated: batch volume, customer behavior and counterfactual recovery outcomes."
)


@dataclass(frozen=True, slots=True)
class Scenario:
    scenario_id: str
    reason: str
    effective_class: str
    amount_minor: int
    known_reason: bool


@dataclass(frozen=True, slots=True)
class HiddenTruth:
    retry_recovery_attempt: int | None
    link_recovers: bool


def _generate(
    seed: int, count: int, *, probability_multiplier: float = 1.0
) -> tuple[list[Scenario], dict[str, HiddenTruth]]:
    rng = random.Random(seed)  # noqa: S311 - deterministic simulator, never cryptography
    reason_mix = [
        ("gateway_timeout", "A", 0.23),
        ("gateway_technical_error", "A", 0.13),
        ("insufficient_funds", "B", 0.22),
        ("authentication_failed", "C", 0.16),
        ("card_expired", "C", 0.08),
        ("risk_threshold", "D", 0.10),
        ("processor_code_z91", "D", 0.08),
    ]
    cumulative: list[tuple[float, str, str]] = []
    total = 0.0
    for reason, action_class, weight in reason_mix:
        total += weight
        cumulative.append((total, reason, action_class))
    scenarios: list[Scenario] = []
    truth: dict[str, HiddenTruth] = {}
    for index in range(count):
        pick = rng.random()
        _, reason, action_class = next(row for row in cumulative if pick <= row[0])
        scenario_id = f"scn_{index + 1:04d}"
        amount_minor = rng.randrange(25, 2200) * 100
        outcome_roll = rng.random()
        attempt_roll = rng.random()
        link_roll = rng.random()
        retry_attempt: int | None = None
        link_recovers = False
        if action_class == "A" and outcome_roll < min(0.78 * probability_multiplier, 1.0):
            retry_attempt = 1 if attempt_roll < 0.62 else 2 if attempt_roll < 0.89 else 3
        elif action_class == "B" and outcome_roll < min(0.52 * probability_multiplier, 1.0):
            retry_attempt = 1 if attempt_roll < 0.3 else 2
        elif action_class == "C":
            link_recovers = link_roll < min(0.46 * probability_multiplier, 1.0)
        scenarios.append(
            Scenario(
                scenario_id, reason, action_class, amount_minor, reason != "processor_code_z91"
            )
        )
        truth[scenario_id] = HiddenTruth(retry_attempt, link_recovers)
    return scenarios, truth


def _metrics(
    policy: str, scenarios: list[Scenario], truth: dict[str, HiddenTruth]
) -> dict[str, Any]:
    recovered = 0
    recovered_minor = 0
    attempts = 0
    wasted = 0
    contacts = 0
    violations = 0
    decision_rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        hidden = truth[scenario.scenario_id]
        local_attempts = 0
        local_contacts = 0
        did_recover = False
        if policy == "retry_all_3x":
            local_attempts = (
                3 if hidden.retry_recovery_attempt is None else hidden.retry_recovery_attempt
            )
            did_recover = hidden.retry_recovery_attempt is not None
            wasted += 0 if did_recover else local_attempts
            if scenario.effective_class == "D":
                violations += local_attempts
        elif policy == "salvage":
            if scenario.effective_class == "A":
                local_attempts = (
                    3 if hidden.retry_recovery_attempt is None else hidden.retry_recovery_attempt
                )
                did_recover = hidden.retry_recovery_attempt is not None
                wasted += 0 if did_recover else local_attempts
            elif scenario.effective_class == "B":
                local_attempts = (
                    2 if hidden.retry_recovery_attempt is None else hidden.retry_recovery_attempt
                )
                did_recover = hidden.retry_recovery_attempt is not None
                wasted += 0 if did_recover else local_attempts
            elif scenario.effective_class == "C":
                local_contacts = 1
                did_recover = hidden.link_recovers
            # Class D has deliberately no effect.
        attempts += local_attempts
        contacts += local_contacts
        if did_recover:
            recovered += 1
            recovered_minor += scenario.amount_minor
        decision_rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "attempts": local_attempts,
                "contacts": local_contacts,
                "recovered": did_recover,
            }
        )
    return {
        "policy": policy,
        "scenario_count": len(scenarios),
        "recovered_count": recovered,
        "recovery_rate": round(recovered / len(scenarios) * 100, 2) if scenarios else 0.0,
        "recovered_minor_units": recovered_minor,
        "attempts": attempts,
        "recovered_minor_units_per_attempt": round(recovered_minor / attempts, 2)
        if attempts
        else 0.0,
        "wasted_attempts": wasted,
        "customer_contacts": contacts,
        "class_d_violations": violations,
        "decisions_digest": hashlib.sha256(canonical_json(decision_rows).encode()).hexdigest(),
    }


def run_evaluation(seed: int = 20260829, count: int = 500) -> dict[str, Any]:
    scenarios, hidden_truth = _generate(seed, count)
    visible = [asdict(scenario) for scenario in scenarios]
    batch_digest = hashlib.sha256(canonical_json(visible).encode()).hexdigest()
    policies = [
        _metrics("retry_all_3x", scenarios, hidden_truth),
        _metrics("never_retry", scenarios, hidden_truth),
        _metrics("salvage", scenarios, hidden_truth),
    ]
    sensitivity: list[dict[str, Any]] = []
    for label, multiplier in (("lower", 0.7), ("base", 1.0), ("upper", 1.3)):
        varied_scenarios, varied_truth = _generate(seed, count, probability_multiplier=multiplier)
        varied_visible = [asdict(scenario) for scenario in varied_scenarios]
        varied_digest = hashlib.sha256(canonical_json(varied_visible).encode()).hexdigest()
        if varied_digest != batch_digest:
            raise RuntimeError("Sensitivity sweep changed policy-visible scenarios")
        sensitivity.append(
            {
                "label": label,
                "probability_multiplier": multiplier,
                "batch_digest": varied_digest,
                "policies": [
                    _metrics("retry_all_3x", varied_scenarios, varied_truth),
                    _metrics("never_retry", varied_scenarios, varied_truth),
                    _metrics("salvage", varied_scenarios, varied_truth),
                ],
            }
        )
    fallback_count = sum(not scenario.known_reason for scenario in scenarios)
    return {
        "schema_version": "1.1",
        "batch_id": f"batch_{seed}_{count}",
        "seed": seed,
        "scenario_count": count,
        "batch_digest": batch_digest,
        "fixed_clock": "2026-08-29T12:00:00Z",
        "assumptions": {
            "version": "2026-08-29.1",
            "sensitivity_range_percent": 30,
            "note": "Probabilities are transparent prototype inputs, not industry benchmarks.",
        },
        "real_vs_simulated": REAL_VS_SIMULATED,
        "map_coverage_rate": round((count - fallback_count) / count * 100, 2) if count else 0.0,
        "fallback_rate": round(fallback_count / count * 100, 2) if count else 0.0,
        "policies": policies,
        "sensitivity": sensitivity,
        "generated_at": "2026-08-29T12:00:00Z",
    }


def write_artifacts(result: dict[str, Any], reports_dir: Path) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "results.json"
    html_path = reports_dir / "report.html"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    environment = Environment(autoescape=select_autoescape(["html", "xml"]))
    template_source = (ROOT / "src" / "salvage" / "evaluation" / "report.html.j2").read_text(
        encoding="utf-8"
    )
    html_path.write_text(
        environment.from_string(template_source).render(result=result), encoding="utf-8"
    )
    return json_path, html_path
