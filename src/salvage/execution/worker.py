from __future__ import annotations

from datetime import UTC, datetime

from salvage.advisory.cache import ShadowSuggestion, get_shadow_suggestion
from salvage.audit.ledger import append_entry
from salvage.config import Settings
from salvage.domain.gatekeeper import evaluate
from salvage.domain.loading import canonical_json, fingerprint, load_policy
from salvage.domain.models import (
    AUTOMATED_ACTIONS,
    CONTACT_ACTIONS,
    RETRY_ACTIONS,
    ActionType,
)
from salvage.domain.policy import decide
from salvage.domain.triage import triage_reason
from salvage.persistence.db import connect
from salvage.persistence.repository import (
    claim_job,
    get_event,
    get_or_create_payment_state,
    iso,
    mark_job_failed,
    stable_id,
)


def _decision_content(
    event: object, triage: object, decision: object, gate: object
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "event_id": event["event_id"],  # type: ignore[index]
        "payment_id": event["payment_id"],  # type: ignore[index]
        "reason": event["reason"],  # type: ignore[index]
        "effective_class": triage.effective_class.value,  # type: ignore[attr-defined]
        "known_reason": triage.known_reason,  # type: ignore[attr-defined]
        "review_required": decision.review_required,  # type: ignore[attr-defined]
        "allowed_actions": [action.value for action in decision.allowed_actions],  # type: ignore[attr-defined]
        "selected_action": decision.selected_action.value,  # type: ignore[attr-defined]
        "decision_reasons": list(decision.reason_codes),  # type: ignore[attr-defined]
        "gate_checks": [
            {"name": check.name, "passed": check.passed}
            for check in gate.checks  # type: ignore[attr-defined]
        ],
        "reason_map_fingerprint": triage.reason_map_fingerprint,  # type: ignore[attr-defined]
        "policy_fingerprint": decision.policy_fingerprint,  # type: ignore[attr-defined]
    }


def _persist(
    settings: Settings,
    job: object,
    event: object,
    state: object,
    triage: object,
    decision: object,
    gate: object,
    advisory: ShadowSuggestion | None,
    now: datetime,
) -> str:
    decision_id = stable_id("dec", event["event_id"])  # type: ignore[index]
    content = _decision_content(event, triage, decision, gate)
    decision_hash = fingerprint(content)
    action = gate.final_action  # type: ignore[attr-defined]
    with connect(settings.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            current = connection.execute(
                "SELECT state_version FROM payment_state WHERE payment_id = ?",
                (event["payment_id"],),  # type: ignore[index]
            ).fetchone()
            if current is None or current["state_version"] != state.state_version:  # type: ignore[attr-defined]
                raise RuntimeError("Payment state changed; retry deterministic computation")
            existing = connection.execute(
                "SELECT decision_id FROM decisions WHERE event_id = ?",
                (event["event_id"],),  # type: ignore[index]
            ).fetchone()
            if existing:
                connection.execute(
                    "UPDATE jobs SET state = 'completed', completed_at = ? WHERE job_id = ?",
                    (iso(now), job["job_id"]),  # type: ignore[index]
                )
                connection.execute("COMMIT")
                return str(existing["decision_id"])
            connection.execute(
                """
                INSERT INTO decisions(
                    decision_id, event_id, payment_id, created_at, reason, effective_class,
                    advisory_class, advisory_rationale, advisory_confidence,
                    advisory_provider, advisory_cache_key, known_reason,
                    review_required, triage_rationale,
                    allowed_actions_json, selected_action, decision_reasons_json,
                    next_eligible_at, reason_map_fingerprint, policy_version,
                    policy_fingerprint, decision_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    event["event_id"],  # type: ignore[index]
                    event["payment_id"],  # type: ignore[index]
                    iso(now),
                    event["reason"],  # type: ignore[index]
                    triage.effective_class.value,  # type: ignore[attr-defined]
                    advisory.suggested_class.value if advisory else None,
                    advisory.rationale if advisory else None,
                    advisory.confidence if advisory else None,
                    advisory.provider if advisory else None,
                    advisory.cache_key if advisory else None,
                    int(triage.known_reason),  # type: ignore[attr-defined]
                    int(decision.review_required),  # type: ignore[attr-defined]
                    triage.rationale,  # type: ignore[attr-defined]
                    canonical_json([a.value for a in decision.allowed_actions]),  # type: ignore[attr-defined]
                    decision.selected_action.value,  # type: ignore[attr-defined]
                    canonical_json(list(decision.reason_codes)),  # type: ignore[attr-defined]
                    iso(decision.next_eligible_at) if decision.next_eligible_at else None,  # type: ignore[attr-defined]
                    triage.reason_map_fingerprint,  # type: ignore[attr-defined]
                    decision.policy_version,  # type: ignore[attr-defined]
                    decision.policy_fingerprint,  # type: ignore[attr-defined]
                    decision_hash,
                ),
            )
            for check in gate.checks:  # type: ignore[attr-defined]
                connection.execute(
                    "INSERT INTO gate_checks VALUES (?, ?, ?, ?)",
                    (decision_id, check.name, int(check.passed), check.explanation),
                )
            if gate.approved and action in AUTOMATED_ACTIONS:  # type: ignore[attr-defined]
                key = fingerprint(
                    {
                        "version": "1",
                        "payment_id": state.payment_id,  # type: ignore[attr-defined]
                        "decision_id": decision_id,
                        "action": action.value,
                        "attempt": state.attempt_count + 1,  # type: ignore[attr-defined]
                    }
                )
                connection.execute(
                    """
                    INSERT INTO effect_intents(
                        idempotency_key, decision_id, payment_id, action, state, created_at
                    ) VALUES (?, ?, ?, ?, 'dry_run', ?)
                    """,
                    (key, decision_id, state.payment_id, action.value, iso(now)),  # type: ignore[attr-defined]
                )
                attempt_delta = int(action in RETRY_ACTIONS)
                contact_delta = int(action in CONTACT_ACTIONS)
                connection.execute(
                    """
                    UPDATE payment_state
                    SET attempt_count = attempt_count + ?, contact_count = contact_count + ?,
                        last_effect_at = ?, state_version = state_version + 1
                    WHERE payment_id = ? AND state_version = ?
                    """,
                    (
                        attempt_delta,
                        contact_delta,
                        iso(now),
                        state.payment_id,  # type: ignore[attr-defined]
                        state.state_version,  # type: ignore[attr-defined]
                    ),
                )
                if action is ActionType.CREATE_PAYMENT_LINK:
                    connection.execute(
                        """
                        INSERT INTO outbox_messages(
                            message_id, idempotency_key, audience, rendered_text, transport_state
                        ) VALUES (?, ?, 'customer', ?, 'disabled')
                        """,
                        (
                            stable_id("msg", key),
                            key,
                            "Your original payment method needs attention. "
                            "A fresh test payment path is available.",
                        ),
                    )
            ledger_content = {
                **content,
                "advisory": advisory.model_dump(mode="json") if advisory else None,
            }
            ledger_hash = append_entry(connection, "decision", decision_id, ledger_content, now)
            connection.execute(
                "UPDATE jobs SET state = 'completed', completed_at = ?, "
                "lease_owner = NULL, lease_expires_at = NULL WHERE job_id = ?",
                (iso(now), job["job_id"]),  # type: ignore[index]
            )
            connection.execute("COMMIT")
            return f"{decision_id}:{ledger_hash}"
        except Exception:
            connection.execute("ROLLBACK")
            raise


def process_next(
    settings: Settings, *, owner: str = "worker-1", now: datetime | None = None
) -> str | None:
    current_time = now or datetime.now(UTC)
    job = claim_job(settings.database_path, owner, current_time)
    if job is None:
        return None
    try:
        event = get_event(settings.database_path, str(job["event_id"]))
        state = get_or_create_payment_state(settings.database_path, event)
        triage = triage_reason(
            str(event["reason"]),
            str(event["source"]) if event["source"] else None,
            settings.policy_dir / "reason-map.yaml",
        )
        policy = load_policy(settings.policy_dir / "recovery-policy.yaml")
        decision = decide(
            state,
            triage.effective_class,
            policy,
            current_time,
            review_required=triage.review_required,
        )
        gate = evaluate(
            decision,
            state,
            policy,
            current_time,
            proposed_amount_minor=int(event["amount_minor"]),
            proposed_currency=str(event["currency"]),
        )
        advisory = get_shadow_suggestion(
            str(event["reason"]), settings.llm, settings.advisory_cache_path
        )
        return _persist(
            settings,
            job,
            event,
            state,
            triage,
            decision,
            gate,
            advisory,
            current_time,
        )
    except Exception as exc:
        mark_job_failed(settings.database_path, str(job["job_id"]), str(exc))
        raise


def process_all(settings: Settings, *, now: datetime | None = None) -> list[str]:
    results: list[str] = []
    while True:
        result = process_next(settings, now=now)
        if result is None:
            break
        results.append(result)
    return results
