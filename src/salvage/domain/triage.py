from __future__ import annotations

from pathlib import Path

from salvage.domain.loading import load_reason_map
from salvage.domain.models import ActionClass, TriageResult

RISK_SOURCES = frozenset({"risk", "fraud", "risk_engine"})


def triage_reason(reason: str, source: str | None, reason_map_path: Path) -> TriageResult:
    reasons, _, map_fingerprint = load_reason_map(reason_map_path)
    if source and source.lower() in RISK_SOURCES:
        return TriageResult(
            effective_class=ActionClass.D,
            known_reason=reason in reasons,
            review_required=True,
            rationale="Risk-originated failures are a deterministic hard stop.",
            reason_map_fingerprint=map_fingerprint,
        )
    entry = reasons.get(reason)
    if entry is None:
        return TriageResult(
            effective_class=ActionClass.D,
            known_reason=False,
            review_required=True,
            rationale="Unknown reason failed closed to operator review.",
            reason_map_fingerprint=map_fingerprint,
        )
    effective_class = ActionClass(entry["class"])
    return TriageResult(
        effective_class=effective_class,
        known_reason=True,
        review_required=effective_class is ActionClass.D,
        rationale=entry["rationale"],
        reason_map_fingerprint=map_fingerprint,
    )
